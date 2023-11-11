from obswebsocket import obsws, requests
import obswebsocket
from loguru import logger as log

class OBSController(obsws):
    def __init__(self):
        self.connected = False
        self.event_obs: obsws = None # All events are connected to this to avoid crash if a request is made in an event
        pass

    def on_connect(self, obs):
        self.connected = True

    def on_disconnect(self, obs):
        self.connected = False

    def connect_to(self, host=None, port=None, timeout=1, legacy=False, **kwargs):
        try:
            log.debug(f"Trying to connect to obs with legacy: {legacy}")
            super().__init__(host=host, port=port, timeout=timeout, legacy=legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=True, **kwargs)
            self.event_obs = obsws(host=host, port=port, timeout=timeout, legacy=legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=True, **kwargs)
            self.connect()
        except obswebsocket.exceptions.ConnectionFailure as e:
            log.error(f"Failed to connect to OBS with legacy: {legacy}, trying with legacy: {not legacy}")
            super().__init__(host=host, port=port, timeout=timeout, legacy=not legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=True, **kwargs)
            self.event_obs = obsws(host=host, port=port, timeout=timeout, legacy=not legacy, on_connect=self.on_connect, on_disconnect=self.on_disconnect, authreconnect=True, **kwargs)
            self.connect()

        log.info("Successfully connected to OBS")

    def get_scenes(self) -> list:
        scenes = self.call(requests.GetSceneList()).getScenes()
        return [scene["sceneName"] for scene in scenes]
    
    def switch_to_scene(self, scene:str) -> None:
        self.call(requests.SetCurrentProgramScene(sceneName=scene))

    ## Stream methods
    def start_stream(self) -> None:
        self.call(requests.StartStream())

    def stop_stream(self) -> None:
        self.call(requests.StopStream())

    def toggle_stream(self):
        """
        outputActive: bool -> The new state of the stream
        """
        self.call(requests.ToggleStream())

    def get_stream_status(self) -> bool:
        """
        outputActive: bool -> Whether streaming is active
        outputReconnecting: bool -> Whether streaming is reconnecting
        outputTimecode: str -> The current timecode of the stream
        outputDuration: int -> The duration of the stream in milliseconds
        outputCongestion: int -> The congestion of the stream
        outputBytes: int -> The number of bytes written to the stream
        outputSkippedFrames: int -> The number of skipped frames
        outputTotalFrames: int -> The total number of delivered frames
        """
        return self.call(requests.GetStreamStatus())
    
    def send_stream_caption(self, caption:str):
        self.call(requests.SendStreamCaption(caption=caption))
    

    ## Record methods
    def start_record(self) -> None:
        return self.call(requests.StartRecord())
    
    def pause_record(self):
        return self.call(requests.PauseRecord())
    
    def resume_record(self):
        return self.call(requests.ResumeRecord())

    def stop_recording(self) -> None:
        """
        outputPath: str -> The path to the saved recording
        """
        return self.call(requests.StopRecord())
    
    def get_record_status(self):
        """
        outputActive: bool -> Whether recording is active
        outputPaused: bool -> Whether recording is paused
        outputTimecode: str -> The current timecode of the recording
        outputDuration: int -> The duration of the recording in milliseconds
        outputBytes: int -> The number of bytes written to the recording
        """
        return self.call(requests.GetRecordStatus())
    
    def toggle_record(self):
        return self.call(requests.ToggleRecord())
    
    def toggle_record_pause(self):
        return self.call(requests.ToggleRecordPause())
    

    ## UI methods
    def get_studio_mode_enabled(self):
        """
        studioModeEnabled: bool -> Whether studio mode is enabled
        """
        return self.call(requests.GetStudioModeEnabled())
    
    def set_studio_mode_enabled(self, enabled:bool):
        return self.call(requests.SetStudioModeEnabled(studioModeEnabled=enabled))
    
    
    ## Replay Buffer
    def start_replay_buffer(self):
        return self.call(requests.StartReplayBuffer())
    
    def stop_replay_buffer(self):
        return self.call(requests.StopReplayBuffer())
    
    def get_replay_buffer_status(self):
        """
        outputActive: bool -> Whether replay buffer is active
        """
        return self.call(requests.GetReplayBufferStatus())
    
    def register(self, *args, **kwargs):
        """
        Pass all event register calls to the event_obs.
        This avoid crashes if a request is made in an event
        """
        self.event_obs.register(*args, **kwargs)