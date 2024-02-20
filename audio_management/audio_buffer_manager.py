import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from pydub import AudioSegment
from pydub.silence import detect_leading_silence


class AudioBufferManager:
    def __init__(self, guild):
        self.guild = guild
        self.audio_buffers = {}
        self.last_write_times = {}
        self.is_audio_trimmed_dict = {}

    def update_buffers_and_time(self, raw_audio_data, user_id):
        current_time = time.time()
        self.create_buffer(user_id)

        # Add the speech segment to the buffer
        self.audio_buffers[user_id] += raw_audio_data
        self.last_write_times[user_id] = current_time

    def create_buffer(self, user_id):
        """
        Initialiizes a new buffer for the user passed if they don't have one already.
        :param user_id: The user to create the buffer for
        """
        if user_id not in self.audio_buffers:
            self.audio_buffers[user_id] = b''
            self.set_audio_is_trimmed(user_id)

    def empty_buffer(self, user_id):
        """
        Empties the buffer for the user passed. Doesn't clear it. sets it to an empty AudioSegment
        :param user_id: The user to empty the buffer for
        """
        if user_id in self.audio_buffers:
            self.audio_buffers[user_id] = b''
            self.set_audio_is_trimmed(user_id)

    def clear_buffers_and_write_times(self):
        # Clear the buffers
        self.audio_buffers.clear()
        self.last_write_times.clear()

    async def trim_leading_silence_from_user_audio(self, user_id):
        # Check if the audio buffer for the user is empty
        if len(self.audio_buffers[user_id]) == 0:
            return

        # Check if the audio for this user has already been trimmed
        if not self.is_audio_trimmed(user_id):
            # Detect the index where leading silence ends
            audio_segment = AudioSegment(
                data=self.audio_buffers[user_id],
                sample_width=2,
                frame_rate=48000,
                channels=2
            )

            start_trim = await self.detect_leading_silence_async(audio_segment)

            # Trim the leading silence from the audio buffer
            audio_segment = audio_segment[start_trim:]

            self.audio_buffers[user_id] = audio_segment.raw_data

            # Update the status to indicate that this audio has been trimmed
            self.set_audio_is_trimmed(user_id, True)

    def is_audio_trimmed(self, user_id):
        if user_id not in self.is_audio_trimmed_dict:
            self.is_audio_trimmed_dict[user_id] = False
        return self.is_audio_trimmed_dict[user_id]

    def set_audio_is_trimmed(self, user_id, is_trimmed=False):
        self.is_audio_trimmed_dict[user_id] = is_trimmed

    async def detect_leading_silence_async(self, audio_segment):
        # Create a partial function with the specific audio_segment argument
        func = partial(detect_leading_silence, audio_segment)

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            # Execute the partial function in the thread pool
            start_trim = await loop.run_in_executor(pool, func)
            return start_trim
