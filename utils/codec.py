import cv2
import numpy as np

from .config import JPEG_QUALITY

def encode_frame(frame):
    """
    Encodes a video frame (numpy array) into JPEG bytes.
    """
    if frame is None:
        return None
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return buffer.tobytes()

def decode_frame(jpeg_bytes):
    """
    Decodes JPEG bytes into a video frame (numpy array).
    """
    if jpeg_bytes is None:
        return None
    np_arr = np.frombuffer(jpeg_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame

def encode_audio(audio_data):
    """
    Encodes audio data (bytes) for transmission.
    (Currently, just returns the raw bytes as PyAudio handles raw bytes)
    """
    return audio_data

def decode_audio(audio_bytes):
    """
    Decodes audio bytes for playback.
    (Currently, just returns the raw bytes as PyAudio handles raw bytes)
    """
    return audio_bytes
