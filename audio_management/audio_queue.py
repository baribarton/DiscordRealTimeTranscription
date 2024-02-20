import asyncio
import traceback

from pydub import AudioSegment


class AudioQueue:
    TERMINATION_SIGNAL = "TERMINATE_WORKER"

    def __init__(self, server_id, audio_buffer_manager, speech_to_text_converter):
        self.server_id = server_id
        self.audio_buffer_manager = audio_buffer_manager
        self.speech_to_text_converter = speech_to_text_converter
        self.audio_queue = asyncio.Queue()
        self.is_running = False

    def start_queue(self):
        asyncio.create_task(self.process_audio_queue())
        self.is_running = True

    def queue_is_running(self):
        return self.is_running

    async def terminate_task(self):
        await self.audio_queue.put((None, self.TERMINATION_SIGNAL))

    async def process_audio_queue(self):
        while True:
            try:
                audio_segment, user_id = await self.audio_queue.get()
                if user_id == self.TERMINATION_SIGNAL:
                    self.is_running = False
                    break

                await self.speech_to_text_converter.print_speech(audio_segment, user_id)
                self.audio_queue.task_done()
            except Exception as e:
                stack_trace = traceback.format_exc()
                print(f"An error occurred in the audio queue: {type(e).__name__} - {e}\nStack trace:\n{stack_trace}")
                await asyncio.sleep(5)

    async def enqueue_audio(self, user_id):
        """
        Enqueues the audio associated with the passed user. Empties the buffer to process new data
        :param user_id: the userID associated with the audio
        """
        audio_segment = AudioSegment(
            data=self.audio_buffer_manager.audio_buffers[user_id],
            sample_width=2,
            frame_rate=48000,
            channels=2
        )

        self.audio_buffer_manager.empty_buffer(user_id)
        await self.audio_queue.put((audio_segment, user_id))

    async def wait_for_queue(self):
        try:
            await asyncio.wait_for(self._queue_finish_check(), timeout=30)
        except asyncio.TimeoutError as e:
            print(f"The audio queue task timed out: {e}.")

    async def _queue_finish_check(self):
        # Continue to check if the worker is running
        while self.queue_is_running():
            await asyncio.sleep(1)
