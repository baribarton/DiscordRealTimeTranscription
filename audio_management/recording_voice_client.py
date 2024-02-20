from discord import VoiceClient


class RecordingVoiceClient(VoiceClient):
    def __init__(self, client, channel, server_id, sink, callback):
        super().__init__(client, channel)
        self.server_id = server_id
        self.sink = sink
        self.callback = callback

    async def connect(self, *args, **kwargs):
        # Await the original connect method from the parent class
        voice_client = await super().connect(*args, **kwargs)
        print("Starting recording in voice channel")
        self.start_recording(self.sink, self.callback, self.channel)

        return voice_client
