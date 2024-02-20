import discord.sinks

from audio_management import audio_buffer_manager
from audio_management.audio_cost_calculator import AudioCostCalculator
from audio_management.audio_processor import AudioProcessor
from audio_management.speech_to_text_converter import SpeechToTextManager


class RealTimeTranscriptionSink(discord.sinks.WaveSink):
    def __init__(self, guild, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_cost_calculator = AudioCostCalculator(guild)
        self.speech_to_text_converter = SpeechToTextManager(guild, self.audio_cost_calculator)
        self.audio_buffer_manager = audio_buffer_manager.AudioBufferManager(guild)
        self.audio_processor = AudioProcessor(guild, self.audio_buffer_manager, self.speech_to_text_converter,
                                              self.audio_cost_calculator)
        self.cleanup_is_done = False

    def write(self, data, user_id):
        self.audio_buffer_manager.update_buffers_and_time(data, user_id)

    def start_transcription_tasks(self):
        """
        Starts the async tasks necessary to process audio
        """
        self.audio_processor.start_speech_checker()
        self.audio_processor.audio_queue.start_queue()

    async def stop_transcription_tasks(self):
        """
        Finishes processing any remaining audio and stops the async tasks that process audio. Nothing should be getting processed after this is done executing
        """
        self.audio_processor.stop_speech_checker()  # Stops processing any incoming audio
        await self.audio_processor.process_unempty_buffers()
        await self.audio_processor.audio_queue.terminate_task()
        await self.audio_processor.audio_queue.wait_for_queue()
        self.cleanup_is_done = True

    def cleanup(self):
        print("Cleaning up audio")
        self.audio_buffer_manager.clear_buffers_and_write_times()
        super().cleanup()
