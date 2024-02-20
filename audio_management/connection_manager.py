import time
import discord
from audio_management.recording_voice_client import RecordingVoiceClient
from audio_management.real_time_transcription_sink import RealTimeTranscriptionSink

voice_connections = {}


class VoiceConnection:
    def __init__(self, sink, voice_client, active_voice_channel):
        self.sink = sink
        self.voice_client = voice_client
        self.active_voice_channel = active_voice_channel
        self.deleting = False   # True if this connection is in the process of getting deleted

    def is_connected(self):
        """Check if the voice client is connected."""
        return self.voice_client and self.voice_client.is_connected()

    def is_recording(self):
        """Check if the transcription sink is actively recording."""
        return self.sink and self.sink.is_recording()

    def mark_for_deletion(self):
        self.deleting = True


async def audio_callback(sink, channel: discord.TextChannel, *args):
    await sink.vc.disconnect()  # Disconnect from voice channel


async def connect_to_voice_channel(guild, voice_channel):
    server_id = guild.id

    # Check if the bot is already connected and recording in the channel
    if server_id in voice_connections:
        voice_connection = voice_connections[server_id]
        if voice_connection.is_connected() and voice_connection.is_recording():
            print("Already connected and recording")
            return

    # Check if a new transcription sink needs to be created or get the existing one
    if server_id in voice_connections:
        print("Using existing transcription sink")
        sink = voice_connections[server_id].sink
    else:
        print("Creating a new transcription sink")
        sink = RealTimeTranscriptionSink(guild)
        sink.start_transcription_tasks()
        sink.speech_to_text_converter.audio_cost_calculator.session_start_time = time.time()

    # Connect to the voice channel
    print("Connecting to a voice channel")
    voice_client = await voice_channel.connect(
        cls=lambda client, channel: RecordingVoiceClient(client, channel, server_id, sink, audio_callback))

    # Update or create the VoiceConnection object
    voice_connections[server_id] = VoiceConnection(sink, voice_client, voice_channel)
