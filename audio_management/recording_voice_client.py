import traceback

from discord import VoiceClient, ClientException
from discord.sinks import RecordingException


class RecordingVoiceClient(VoiceClient):
    def __init__(self, client, channel, server_id, sink, callback):
        super().__init__(client, channel)
        self.server_id = server_id
        self.sink = sink
        self.callback = callback

    async def connect(self, *args, **kwargs):
        # 60 sec timeout is too long
        kwargs['timeout'] = 30.0

        print(f"Attempting connection to voice channel - Server ID: {self.server_id}")
        try:
            await super().connect(*args, **kwargs)
            if self.is_connected():
                print(f"Starting recording in voice channel - Server ID: {self.server_id}")
                if not self.recording:
                    self.start_recording(self.sink, self.callback, self.channel)
            else:
                print("Connection attempted but bot is still not connected to voice channel. Disconnecting...")
                await self.disconnect(force=True)
        except ClientException as e:
            print(f"ClientException during connection (possibly reconnection). {e} - Server ID: {self.server_id}")

            if self.recording:
                self.stop_recording()
            await self.disconnect(force=True)
        except RecordingException as e:
            print(f"RecordingException during connection (possibly reconnection). {e} - Server ID: {self.server_id}")
        except TimeoutError as e:
            print(f"TimeoutError during connection (possibly reconnection). {e} - Server ID: {self.server_id}")
            if self.recording:
                self.stop_recording()
            await self.disconnect(force=True)
        except Exception as e:
            stack_trace = traceback.format_exc()
            print(f"Failed to connect to voice channel in RecordingVoiceClient: {type(e).__name__} - {e}\nStack trace:\n{stack_trace} - Server ID: {self.server_id}")
            if self.recording:
                self.stop_recording()
            await self.disconnect(force=True)

    async def edit(self, **kwargs):
        return await super().edit(**kwargs)
