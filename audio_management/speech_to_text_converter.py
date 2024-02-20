from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from deepgram import PrerecordedOptions, AsyncPreRecordedClient, DeepgramClientOptions, \
    BufferSource
from deepgram.clients.prerecorded.errors import DeepgramTypeError

NO_SPEECH_FROM_TEXT = "<<Issue getting speech from the text>>"
DEEPGRAM_API_KEY = "API_KEY"


class SpeechToTextManager:
    def __init__(self, guild, audio_cost_calculator):
        self.guild = guild
        self.audio_cost_calculator = audio_cost_calculator
        self.deepgram_client = AsyncPreRecordedClient(DeepgramClientOptions(api_key=DEEPGRAM_API_KEY))
        self.executor = ThreadPoolExecutor()

    async def print_speech(self, user_audio_segment, user_id):
        """
        Adds the passed audio to the transcript as text if it has detectable speech in it
        :param user_audio_segment: The audio to try to detect speech in
        :param user_id: The user the audio is associated with
        """
        speech_as_text = await self.audio_has_speech(user_audio_segment, user_id)
        print(speech_as_text)

    async def audio_has_speech(self, user_audio_segment, user_id):
        """
        Determines if the passed audio segment has speech. Sends it to the VAD first, if the VAD detects speech, then it
        send it to the API. Also calculates the cost of the API call.
        :param user_audio_segment: The audio to try to detect speech in
        :param user_id: The user the audio is associated with
        :return: The speech converted to text if both the VAD and the S2T API found speech. None if one of those failed
        to find speech
        """
        # This entire functionality with the Silero VAD is commented out because it uses up way too much memory.
        # If I want to reintegrate this in the future, I have to either a) Increase my RAM to at least 3 GB (probably 4),
        # or b) Move this to its own server with additional RAM and create a REST API for it.
        # Please for the love of god don't forget to use the combined_speech_segment instead of the original audio if i reintegrate this

        # combined_speech_segment = await asyncio.get_event_loop().run_in_executor(
        #     self.executor, speech_detector.get_speech_from_audio, user_audio_segment
        # )
        # if combined_speech_segment and combined_speech_segment.duration_seconds < 1:
        #     logging_helper.log_message(LogLevel.INFO,
        #                                f"Speech length too short. Rejecting it. {utils.get_username_from_id(self.guild, user_id)}: {combined_speech_segment.duration_seconds}",
        #                                self.guild.id)
        #     self.audio_cost_calculator.add_rejected_short_audio_request(combined_speech_segment.duration_seconds)
        # elif combined_speech_segment:
        self.audio_cost_calculator.calculate_cost(user_audio_segment.duration_seconds, user_id)
        speech_as_text = await self.get_speech_as_text(user_audio_segment, self.guild.id)
        if speech_as_text and speech_as_text != NO_SPEECH_FROM_TEXT:
            return speech_as_text
        self.audio_cost_calculator.increment_failed_requests()
        print("Tried to convert speech to text but no speech was detected")
        return None

    async def get_speech_as_text(self, user_audio_segment, server_id):
        # Set options for Deepgram
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True
        )

        # TODO: Should I use the WaveSink's format audio method?
        # Create a BytesIO object from the AudioSegment
        buffer = BytesIO()
        user_audio_segment.export(buffer, format="wav")
        buffer.seek(0)  # Reset buffer's pointer to the beginning

        try:
            url_response = await self.deepgram_client.transcribe_file(BufferSource(buffer=buffer.getvalue()), options)
        except DeepgramTypeError as e:
            print(f"Error from the Deepgram API while getting the S2T: {e}")
            return NO_SPEECH_FROM_TEXT
        except Exception as e:
            error_type = e.__class__.__name__
            print(f"An error occurred while trying to get the S2T: {error_type}: {e}")
            return NO_SPEECH_FROM_TEXT

        if not url_response or not url_response.results or not url_response.results.channels:
            print("Something went wrong getting the S2T")
            return NO_SPEECH_FROM_TEXT
        return url_response.results.channels[0].alternatives[0].transcript
