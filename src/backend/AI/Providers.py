"""
Thin clients for the supported AI providers.

Every provider exposes the same two operations:
    list_models() -> list[str]      used to fill the model combo box in the settings
    generate(system, user) -> str   one shot completion, returns the raw assistant text

Nothing in here touches Gtk, so all of it is safe to call from a worker thread.
"""

import requests

REQUEST_TIMEOUT = 20
GENERATE_TIMEOUT = 300


class ProviderError(Exception):
    """Raised for anything the user needs to see in the UI (missing key, http error, ...)."""
    pass


class LLMProvider:
    id: str = ""
    name: str = ""
    needs_api_key: bool = True
    needs_base_url: bool = False
    default_base_url: str = ""
    settings_hint: str = ""
    fallback_models: list[str] = []

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip().rstrip("/") or self.default_base_url

    def check_configured(self) -> None:
        if self.needs_api_key and not self.api_key:
            raise ProviderError(f"No API key set for {self.name}. Add one in Settings -> AI.")
        if not self.base_url:
            raise ProviderError(f"No server address set for {self.name}.")

    def list_models(self) -> list[str]:
        raise NotImplementedError

    def generate(self, system_prompt: str, user_prompt: str, model: str = "") -> str:
        raise NotImplementedError

    # Shared helpers

    def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            response = requests.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as e:
            raise ProviderError(f"Could not reach {self.name}: {e}") from e
        except requests.exceptions.Timeout as e:
            raise ProviderError(f"{self.name} did not answer in time.") from e
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Request to {self.name} failed: {e}") from e

        if response.status_code >= 400:
            raise ProviderError(f"{self.name} returned {response.status_code}: {self._error_detail(response)}")

        try:
            return response.json()
        except ValueError as e:
            raise ProviderError(f"{self.name} returned a non JSON response.") from e

    @staticmethod
    def _error_detail(response: requests.Response) -> str:
        try:
            data = response.json()
        except ValueError:
            return response.text[:300]

        if isinstance(data, dict):
            error = data.get("error", data)
            if isinstance(error, dict):
                return str(error.get("message") or error)
            return str(error)
        return str(data)[:300]


class ChatGPTProvider(LLMProvider):
    id = "chatgpt"
    name = "ChatGPT"
    default_base_url = "https://api.openai.com/v1"
    settings_hint = "Get an API key at https://platform.openai.com/api-keys"
    fallback_models = [
        "gpt-5",
        "gpt-5-mini",
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4o-mini",
    ]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def list_models(self) -> list[str]:
        self.check_configured()
        data = self._request("GET", f"{self.base_url}/models", headers=self._headers(), timeout=REQUEST_TIMEOUT)

        models = []
        for entry in data.get("data", []):
            model_id = entry.get("id", "")
            # The /models endpoint also lists embedding, audio and image models - keep the chat capable ones
            if model_id.startswith(("gpt-", "o1", "o3", "o4", "chatgpt-")):
                if any(part in model_id for part in ("audio", "realtime", "image", "tts", "transcribe", "search")):
                    continue
                models.append(model_id)

        return sorted(set(models)) or list(self.fallback_models)

    def generate(self, system_prompt: str, user_prompt: str, model: str = "") -> str:
        self.check_configured()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = self._request("POST", f"{self.base_url}/chat/completions", headers=self._headers(),
                             json=payload, timeout=GENERATE_TIMEOUT)

        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("ChatGPT returned no answer.")
        return choices[0].get("message", {}).get("content", "") or ""


class GeminiProvider(LLMProvider):
    id = "gemini"
    name = "Gemini"
    default_base_url = "https://generativelanguage.googleapis.com/v1beta"
    settings_hint = "Get an API key at https://aistudio.google.com/app/apikey"
    fallback_models = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]

    def list_models(self) -> list[str]:
        self.check_configured()
        data = self._request("GET", f"{self.base_url}/models", params={"key": self.api_key},
                             timeout=REQUEST_TIMEOUT)

        models = []
        for entry in data.get("models", []):
            if "generateContent" not in entry.get("supportedGenerationMethods", []):
                continue
            # Names come back as "models/gemini-2.5-pro"
            models.append(entry.get("name", "").split("/")[-1])

        return sorted(m for m in set(models) if m) or list(self.fallback_models)

    def generate(self, system_prompt: str, user_prompt: str, model: str = "") -> str:
        self.check_configured()
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        }
        url = f"{self.base_url}/models/{model}:generateContent"
        data = self._request("POST", url, params={"key": self.api_key}, json=payload, timeout=GENERATE_TIMEOUT)

        candidates = data.get("candidates") or []
        if not candidates:
            block_reason = data.get("promptFeedback", {}).get("blockReason")
            raise ProviderError(f"Gemini returned no answer{f' ({block_reason})' if block_reason else ''}.")

        parts = candidates[0].get("content", {}).get("parts", [])
        # Thinking models return their reasoning as parts flagged with "thought" - those are not the answer
        return "".join(part.get("text", "") for part in parts if not part.get("thought"))


class _OllamaAPI(LLMProvider):
    """Shared by the local server and the hosted one - ollama.com speaks the same API."""

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def list_models(self) -> list[str]:
        self.check_configured()
        data = self._request("GET", f"{self.base_url}/api/tags", headers=self._headers(),
                             timeout=REQUEST_TIMEOUT)
        models = [entry.get("name", "") for entry in data.get("models", [])]
        return sorted(m for m in models if m)

    def generate(self, system_prompt: str, user_prompt: str, model: str = "") -> str:
        self.check_configured()
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        data = self._request("POST", f"{self.base_url}/api/chat", headers=self._headers(),
                             json=payload, timeout=GENERATE_TIMEOUT)
        return data.get("message", {}).get("content", "") or ""


class OllamaProvider(_OllamaAPI):
    id = "ollama"
    name = "Ollama (local)"
    needs_api_key = False
    needs_base_url = True
    default_base_url = "http://localhost:11434"
    settings_hint = ("Runs on your own machine, no API key needed. Pick a model that is good at "
                     "writing code, for example qwen2.5-coder or deepseek-coder-v2.")
    fallback_models = []


class OllamaCloudProvider(_OllamaAPI):
    id = "ollama_cloud"
    name = "Ollama Cloud"
    default_base_url = "https://ollama.com"
    settings_hint = ("Large models hosted by Ollama, same API as the local server. "
                     "Get an API key at https://ollama.com/settings/keys")
    # Both Ollama flavours list their models live, so a hardcoded list would only ever go stale
    fallback_models = []


PROVIDERS: dict[str, type[LLMProvider]] = {
    ChatGPTProvider.id: ChatGPTProvider,
    GeminiProvider.id: GeminiProvider,
    OllamaProvider.id: OllamaProvider,
    OllamaCloudProvider.id: OllamaCloudProvider,
}


def get_provider_class(provider_id: str) -> type[LLMProvider]:
    return PROVIDERS.get(provider_id, ChatGPTProvider)
