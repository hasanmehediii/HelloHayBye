import socket
import threading
import time
import unittest

from utils.config import VIDEO_PORT # Using an arbitrary port for testing

class TestConnection(unittest.TestCase):

    def test_udp_connection(self):
        # Receiver setup
        receiver_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver_sock.bind(('127.0.0.1', VIDEO_PORT))
        receiver_sock.settimeout(5) # 5 second timeout

        received_data = None
        def receive_func():
            nonlocal received_data
            try:
                data, addr = receiver_sock.recvfrom(1024)
                received_data = data.decode('utf-8')
            except socket.timeout:
                pass
            finally:
                receiver_sock.close()

        receiver_thread = threading.Thread(target=receive_func)
        receiver_thread.start()

        # Sender setup
        sender_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        message = "test_ping"
        sender_sock.sendto(message.encode('utf-8'), ('127.0.0.1', VIDEO_PORT))
        sender_sock.close()

        receiver_thread.join()

        self.assertEqual(received_data, message, "UDP message not received or corrupted")

if __name__ == '__main__':
    unittest.main()
