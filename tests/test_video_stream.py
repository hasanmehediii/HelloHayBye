import unittest
import threading
import time
import cv2
import numpy as np
import socket
from unittest.mock import patch

from client.video_sender import VideoSender
from client.video_receiver import VideoReceiver
from utils.codec import encode_frame, decode_frame
from utils.config import VIDEO_PORT, FRAME_WIDTH, FRAME_HEIGHT

class TestVideoStream(unittest.TestCase):

    def setUp(self):
        # Create a dummy frame for testing
        self.dummy_frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
        cv2.putText(self.dummy_frame, "Test", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    @patch('cv2.imshow')
    @patch('cv2.waitKey', return_value=ord('q')) # Mock waitKey to quit immediately
    @patch('cv2.VideoCapture')
    def test_video_send_receive(self, mock_video_capture, mock_wait_key, mock_imshow):
        # Mock VideoCapture to return our dummy frame
        mock_video_capture_instance = mock_video_capture.return_value
        mock_video_capture_instance.read.return_value = (True, self.dummy_frame)
        mock_video_capture_instance.set.return_value = True

        # Start receiver in a separate thread
        receiver = VideoReceiver()
        receiver_thread = threading.Thread(target=receiver.start)
        receiver_thread.daemon = True # Allow main thread to exit even if this is running
        receiver_thread.start()

        # Give receiver a moment to bind
        time.sleep(0.5)

        # Start sender in a separate thread
        sender = VideoSender('127.0.0.1')
        sender_thread = threading.Thread(target=sender.start)
        sender_thread.daemon = True
        sender_thread.start()

        # Let it run for a short period to send/receive some frames
        time.sleep(2)

        # Stop sender and receiver
        sender.stop()
        receiver.stop()

        # Wait for threads to finish
        sender_thread.join(timeout=1)
        receiver_thread.join(timeout=1)

        # Assertions
        # Check if imshow was called, indicating a frame was processed
        self.assertTrue(mock_imshow.called, "cv2.imshow was not called, indicating no frames were received/displayed")
        
        # Optionally, check the content of the displayed frame if needed
        # For example, you could capture the argument passed to mock_imshow
        # and decode it to compare with the original dummy_frame.
        # This would require more sophisticated mocking or a custom mock object.
        
        # For now, just checking if it was called is a good start.

if __name__ == '__main__':
    unittest.main()
