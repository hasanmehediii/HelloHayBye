import cv2
import socket
import numpy as np

from utils.codec import decode_frame
from utils.config import VIDEO_PORT, MAX_PACKET_SIZE

class VideoReceiver:
    def __init__(self, frame_callback):
        self.port = VIDEO_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('0.0.0.0', self.port))
        self.running = False
        self.frame_buffer = {} # To reassemble fragmented frames
        self.frame_callback = frame_callback

    def start(self):
        self.running = True
        print(f"Video receiver started, listening on port {self.port}")

        while self.running:
            try:
                packet, addr = self.sock.recvfrom(MAX_PACKET_SIZE)
                
                sender_ip = addr[0]
                if sender_ip not in self.frame_buffer:
                    self.frame_buffer[sender_ip] = b''
                
                self.frame_buffer[sender_ip] += packet

                if len(packet) < MAX_PACKET_SIZE:
                    full_frame_bytes = self.frame_buffer.pop(sender_ip, None)
                    if full_frame_bytes:
                        frame = decode_frame(full_frame_bytes)
                        if frame is not None and self.frame_callback:
                            self.frame_callback(frame)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error in video receiver: {e}")
                break

    def stop(self):
        self.running = False
        self.sock.close()
        print("Video receiver stopped")

if __name__ == '__main__':
    # Example usage (for testing, not part of the main app)
    def display_frame(frame):
        cv2.imshow("Remote Video", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            receiver.stop()

    receiver = VideoReceiver(frame_callback=display_frame)
    try:
        receiver.start()
    except KeyboardInterrupt:
        receiver.stop()
    finally:
        cv2.destroyAllWindows()
