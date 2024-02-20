# Finds speech in audio segments
# WARNING: This uses a lot of RAM (Maybe about 250 MB to compile and import torch)
# I had to remove this from my project because the cost savings were not justified (yet)
# It blocked about 10% more requests from being sent to the API due to it not recognizing any speech in it
import numpy as np
import torch
from pydub import AudioSegment

torch.set_grad_enabled(False)


class SileroVADModel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SileroVADModel, cls).__new__(cls)

            cls._instance.model, cls._instance.utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad'
            )
            cls._instance.get_speech_timestamps, cls._instance.save_audio, _, _, cls._instance.collect_chunks = cls._instance.utils
        return cls._instance

    @staticmethod
    def get_model():
        return SileroVADModel()._instance.model

    @staticmethod
    def get_utils():
        return SileroVADModel()._instance.utils


def get_speech_from_audio(user_audio_segment):
    model = SileroVADModel.get_model()
    get_speech_timestamps, save_audio, _, _, collect_chunks = SileroVADModel.get_utils()

    samples = np.array(user_audio_segment.get_array_of_samples(), dtype=np.float32)
    # Normalize and convert to tensor using Int2Float
    audio_tensor = int2float(samples)

    # Process this tensor with your VAD
    speech_timestamps = get_speech_timestamps(audio_tensor, model)
    speech_segment = None
    if len(speech_timestamps) > 0:
        chunks = collect_chunks(speech_timestamps, audio_tensor)
        speech_segment = tensor_to_audio_segment(chunks, 16000)
    return speech_segment


def tensor_to_audio_segment(tensor, sample_rate=16000):
    # save_audio('only_speech.wav',
    #                 tensor, sampling_rate=sample_rate)

    # Move the tensor to CPU and convert to NumPy array
    tensor = tensor.detach().cpu()
    audio_numpy = tensor.numpy()

    # Scale the data to the 16-bit integer range
    audio_int16 = np.int16(audio_numpy * 32767)

    # Create an AudioSegment
    audio_segment = AudioSegment(
        audio_int16.tobytes(),
        frame_rate=sample_rate,
        sample_width=2,  # 2 bytes for int16
        channels=1
    )

    return audio_segment


def int2float(sound):
    _sound = np.copy(sound)
    abs_max = np.abs(_sound).max()
    _sound = _sound.astype('float32')
    if abs_max > 0:
        _sound *= 1 / abs_max
    audio_float32 = torch.from_numpy(_sound.squeeze())
    return audio_float32


def convert_to_vad_compatible(audio_segment):
    """
    Converts an audio segment to a format compatible with the silero VAD.
    Parameters:
        audio_segment (AudioSegment): The audio segment to be converted.
    Returns:
        AudioSegment: VAD compatible audio segment.
    """
    return audio_segment.set_channels(1).set_frame_rate(16000)
