"""
Author: Core447
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import base64
import hashlib
import socket
import struct
import threading

from loguru import logger as log

# RFC 6455
_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_CONTINUATION = 0x0
OP_TEXT = 0x1
OP_BINARY = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

MAX_PAYLOAD_SIZE = 64 * 1024 * 1024


class WebSocketConnection:
    """A single accepted WebSocket connection, served by its own thread."""

    def __init__(self, sock: socket.socket, server: "WebSocketServer"):
        self.socket = sock
        self.server = server
        self._send_lock = threading.Lock()
        self._closed = False

        # Set by the owner once the connection has identified itself
        self.identity = None

    def send_text(self, text: str) -> bool:
        return self._send_frame(OP_TEXT, text.encode("utf-8"))

    def _send_frame(self, opcode: int, payload: bytes) -> bool:
        if self._closed:
            return False

        length = len(payload)
        if length < 126:
            header = struct.pack("!BB", 0x80 | opcode, length)
        elif length < 65536:
            header = struct.pack("!BBH", 0x80 | opcode, 126, length)
        else:
            header = struct.pack("!BBQ", 0x80 | opcode, 127, length)

        try:
            with self._send_lock:
                if self._closed:
                    return False
                self.socket.sendall(header + payload)
            return True
        except OSError:
            self.close()
            return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.socket.close()
        except OSError:
            pass

    @property
    def closed(self) -> bool:
        return self._closed

    # ------------- #
    # Reading side  #
    # ------------- #

    def _recv_exactly(self, n: int) -> bytes | None:
        buf = bytearray()
        while len(buf) < n:
            try:
                chunk = self.socket.recv(n - len(buf))
            except OSError:
                return None
            if not chunk:
                return None
            buf.extend(chunk)
        return bytes(buf)

    def _read_frame(self) -> tuple[int, bytes] | None:
        header = self._recv_exactly(2)
        if header is None:
            return None

        fin = bool(header[0] & 0x80)
        opcode = header[0] & 0x0F
        masked = bool(header[1] & 0x80)
        length = header[1] & 0x7F

        if length == 126:
            extended = self._recv_exactly(2)
            if extended is None:
                return None
            length = struct.unpack("!H", extended)[0]
        elif length == 127:
            extended = self._recv_exactly(8)
            if extended is None:
                return None
            length = struct.unpack("!Q", extended)[0]

        if length > MAX_PAYLOAD_SIZE:
            log.warning(f"WebSocket frame of {length} bytes exceeds the limit, dropping connection")
            return None

        mask_key = None
        if masked:
            mask_key = self._recv_exactly(4)
            if mask_key is None:
                return None

        payload = self._recv_exactly(length) if length else b""
        if payload is None:
            return None

        if mask_key is not None:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

        return (opcode if fin else -opcode - 1), payload

    def run(self) -> None:
        """Read messages until the connection is closed, dispatching them to the server."""
        fragments = bytearray()
        fragment_opcode = None

        try:
            while not self._closed:
                frame = self._read_frame()
                if frame is None:
                    break
                opcode, payload = frame

                # Negative opcodes mark a non final frame
                is_final = opcode >= 0
                if not is_final:
                    opcode = -opcode - 1

                if opcode == OP_CLOSE:
                    self._send_frame(OP_CLOSE, b"")
                    break
                if opcode == OP_PING:
                    self._send_frame(OP_PONG, payload)
                    continue
                if opcode == OP_PONG:
                    continue

                if opcode == OP_CONTINUATION:
                    if fragment_opcode is None:
                        continue
                    fragments.extend(payload)
                else:
                    fragment_opcode = opcode
                    fragments = bytearray(payload)

                if not is_final:
                    continue

                if fragment_opcode == OP_TEXT:
                    try:
                        message = fragments.decode("utf-8")
                    except UnicodeDecodeError:
                        log.warning("Received a non utf-8 WebSocket text message, ignoring")
                    else:
                        self.server._dispatch_message(self, message)

                fragments = bytearray()
                fragment_opcode = None
        finally:
            self.close()
            self.server._dispatch_close(self)


class WebSocketServer:
    """
    A minimal RFC 6455 WebSocket server.

    Stream Deck SDK plugins and property inspectors expect to talk to a WebSocket
    server on localhost, so we ship a small self contained implementation rather than
    pulling in another dependency.
    """

    def __init__(self, on_message: callable, on_close: callable = None, host: str = "127.0.0.1"):
        self.host = host
        self.port: int = None
        self.on_message = on_message
        self.on_close = on_close

        self._server_socket: socket.socket = None
        self._thread: threading.Thread = None
        self._running = False
        self._connections: set[WebSocketConnection] = set()
        self._connections_lock = threading.Lock()

    def start(self, port: int = 0) -> int:
        """Start listening and return the bound port."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, port))
        self._server_socket.listen(16)
        self.port = self._server_socket.getsockname()[1]

        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, name="sd_sdk_websocket_server", daemon=True)
        self._thread.start()

        log.info(f"Stream Deck SDK WebSocket server listening on {self.host}:{self.port}")
        return self.port

    def stop(self) -> None:
        self._running = False
        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None

        with self._connections_lock:
            connections = list(self._connections)
            self._connections.clear()
        for connection in connections:
            connection.close()

    def _accept_loop(self) -> None:
        while self._running:
            try:
                client, _addr = self._server_socket.accept()
            except OSError:
                break

            threading.Thread(
                target=self._handle_client,
                args=(client,),
                name="sd_sdk_websocket_client",
                daemon=True
            ).start()

    def _handle_client(self, client: socket.socket) -> None:
        try:
            key = self._read_handshake(client)
        except OSError:
            key = None

        if key is None:
            try:
                client.close()
            except OSError:
                pass
            return

        accept = base64.b64encode(hashlib.sha1((key + _MAGIC).encode("ascii")).digest()).decode("ascii")
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        try:
            client.sendall(response.encode("ascii"))
        except OSError:
            try:
                client.close()
            except OSError:
                pass
            return

        connection = WebSocketConnection(client, self)
        with self._connections_lock:
            self._connections.add(connection)

        try:
            connection.run()
        finally:
            with self._connections_lock:
                self._connections.discard(connection)

    @staticmethod
    def _read_handshake(client: socket.socket) -> str | None:
        client.settimeout(10)
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = client.recv(4096)
            if not chunk:
                return None
            data.extend(chunk)
            if len(data) > 65536:
                return None
        client.settimeout(None)

        try:
            head = data.split(b"\r\n\r\n", 1)[0].decode("latin-1")
        except UnicodeDecodeError:
            return None

        lines = head.split("\r\n")
        if not lines or not lines[0].upper().startswith("GET "):
            return None

        for line in lines[1:]:
            name, _, value = line.partition(":")
            if name.strip().lower() == "sec-websocket-key":
                return value.strip()
        return None

    def _dispatch_message(self, connection: WebSocketConnection, message: str) -> None:
        try:
            self.on_message(connection, message)
        except Exception as e:
            log.error(f"Error while handling a Stream Deck SDK message: {e}")

    def _dispatch_close(self, connection: WebSocketConnection) -> None:
        if self.on_close is None:
            return
        try:
            self.on_close(connection)
        except Exception as e:
            log.error(f"Error while handling a Stream Deck SDK disconnect: {e}")
