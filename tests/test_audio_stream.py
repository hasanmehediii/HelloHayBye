import unittest
import threading
import time
import socket
from unittest.mock import patch, MagicMock

from client.audio_sender import AudioSender
from client.audio_receiver import AudioReceiver
from utils.config import AUDIO_PORT, CHUNK, CHANNELS, RATE

class TestAudioStream(unittest.TestCase):

    def setUp(self):
        # Create dummy audio data
        self.dummy_audio_data = b'\x00' * (CHUNK * CHANNELS * 2) # 2 bytes per sample for paInt16

    @patch('pyaudio.PyAudio')
    def test_audio_send_receive(self, mock_pyaudio):
        # Mock PyAudio stream objects
        mock_pyaudio_instance = mock_pyaudio.return_value
        mock_input_stream = MagicMock()
        mock_output_stream = MagicMock()

        mock_pyaudio_instance.open.side_effect = [mock_input_stream, mock_output_stream]
        mock_input_stream.read.return_value = self.dummy_audio_data

        # Start receiver in a separate thread
        receiver = AudioReceiver()
        receiver_thread = threading.Thread(target=receiver.start)
        receiver_thread.daemon = True
        receiver_thread.start()

        # Give receiver a moment to bind
        time.sleep(0.5)

        # Start sender in a separate thread
        sender = AudioSender('127.0.0.1')
        sender_thread = threading.Thread(target=sender.start)
        sender_thread.daemon = True
        sender_thread.start()

        # Let it run for a short period to send/receive some audio
        time.sleep(2)

        # Stop sender and receiver
        sender.stop()
        receiver.stop()

        # Wait for threads to finish
        sender_thread.join(timeout=1)
        receiver_thread.join(timeout=1)

        # Assertions
        # Check if the input stream was read from (sender)
        self.assertTrue(mock_input_stream.read.called, "Audio sender did not read from input stream")
        # Check if the output stream was written to (receiver)
        self.assertTrue(mock_output_stream.write.called, "Audio receiver did not write to output stream")

        # Optionally, you could check the arguments passed to write if you want to verify data integrity
        # For example: mock_output_stream.write.assert_called_with(self.dummy_audio_data)

if __name__ == '__main__':
    unittest.main()
