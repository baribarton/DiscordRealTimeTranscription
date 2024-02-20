import asyncio
import time

from audio_management import audio_queue


class AudioProcessor:
    def __init__(self, guild, audio_buffer_manager, speech_to_text_converter, audio_cost_calculator):
        self.guild = guild
        self.is_running = False
        self.audio_buffer_manager = audio_buffer_manager
        self.speech_to_text_converter = speech_to_text_converter
        self.audio_queue = audio_queue.AudioQueue(guild.id, self.audio_buffer_manager, speech_to_text_converter)
        self.audio_cost_calculator = audio_cost_calculator

    def start_speech_checker(self):
        self.is_running = True
        asyncio.create_task(self.continuous_speech_checker())

    def stop_speech_checker(self):
        self.is_running = False

    async def continuous_speech_checker(self):
        """
        Continuous loop that determines when to add the user's audio to a queue that finds speech in the audio
        """
        while self.is_running:
            try:
                await asyncio.sleep(0.5)  # Heartbeat interval
                for user_id in self.audio_buffer_manager.last_write_times:
                    last_speech_time = self.audio_buffer_manager.last_write_times.get(user_id, 0)
                    if time.time() - last_speech_time > 1:  # Check if speech ended at least 1 second ago
                        await self.audio_buffer_manager.trim_leading_silence_from_user_audio(user_id)
                        if self.has_unprocessed_audio(user_id):
                            await self.audio_queue.enqueue_audio(user_id)
                    elif await self.audio_duration_exceeds_threshold(user_id, 60):
                        print(f"User {user_id}-{user_id} was talking for a while")
                        await self.audio_queue.enqueue_audio(user_id)
            except Exception as e:
                error_type = e.__class__.__name__
                print(f"An error got raised while running speech checker task: {error_type}: {e}")
                await asyncio.sleep(5)

    async def audio_duration_exceeds_threshold(self, user_id, threshold_in_seconds):
        """
        Checks if the buffer contains audio exceeding the passed duration in seconds
        :param user_id: the user speaking
        :param threshold_in_seconds: The threshold
        :return: True if the audio duration exceeds the threshold. False if not
        """
        if user_id in self.audio_buffer_manager.audio_buffers:
            await self.audio_buffer_manager.trim_leading_silence_from_user_audio(user_id)
            audio_duration_seconds = self.get_user_audio_duration(user_id)
            # print(f"user: {user_id} talked for {audio_duration_seconds} seconds")
            return audio_duration_seconds > threshold_in_seconds
        return False

    def has_unprocessed_audio(self, user_id):
        """
        Determines if there is audio in the buffer that should be processed.
        :param user_id:
        :return: True if there is audio in the buffer that is 1 second or longer. False if otherwise
        """
        if user_id in self.audio_buffer_manager.audio_buffers:
            # Get the raw audio buffer for the user
            audio_duration_seconds = self.get_user_audio_duration(user_id)

            # If the audio is less than 1 second, it is too short
            # Note: You can remove this part if you want. I just didn't care about audio less than a second long
            if audio_duration_seconds < 1:
                if audio_duration_seconds > 0:
                    print(f"Speech length too short. Rejecting it before speech recognition. Length: {audio_duration_seconds:.2f}")
                    self.audio_cost_calculator.add_rejected_short_audio_request(audio_duration_seconds)
                self.audio_buffer_manager.empty_buffer(user_id)
            else:
                return True
        return False

    def get_user_audio_duration(self, user_id):
        return self.get_audio_duration(self.audio_buffer_manager.audio_buffers[user_id])

    def get_audio_duration(self, raw_audio_data):
        sample_rate = 48000  # Samples per second
        bit_depth = 16  # Bits per sample
        bytes_per_sample = bit_depth // 8
        channel_count = 2  # Stereo audio

        # Calculate the total number of bytes per frame (sample pair for stereo)
        bytes_per_frame = bytes_per_sample * channel_count

        # Calculate the number of frames in the buffer
        number_of_frames = len(raw_audio_data) / bytes_per_frame

        # Calculate the duration in seconds
        duration_seconds = number_of_frames / sample_rate

        return duration_seconds

    async def process_unempty_buffers(self):
        for user_id, audio_buffer in self.audio_buffer_manager.audio_buffers.items():
            if len(audio_buffer) > 0:
                await self.audio_queue.enqueue_audio(user_id)
