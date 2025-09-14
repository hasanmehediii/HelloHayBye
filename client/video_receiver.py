import cv2
import socket
import numpy as np

from utils.codec import decode_frame
from utils.config import VIDEO_PORT, MAX_PACKET_SIZE

class VideoReceiver:
    def __init__(self):
        self.port = VIDEO_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.running = False
        self.frame_buffer = {} # To reassemble fragmented frames

    def start(self):
        self.running = True
        print(f"Video receiver started, listening on port {self.port}")
        cv2.namedWindow("Remote Video", cv2.WINDOW_NORMAL)

        while self.running:
            try:
                packet, addr = self.sock.recvfrom(MAX_PACKET_SIZE)
                
                # Simple fragmentation handling: assuming each packet is a full frame for now
                # or that the sender sends chunks sequentially and we can reassemble.
                # A more robust solution would involve sequence numbers and a proper reassembly buffer.
                
                # For now, let's assume a simple case where a new packet means a new frame
                # or that the sender sends full frames if they fit, or multiple packets for one frame.
                # The current sender sends chunks, so we need to buffer.

                # This is a very basic reassembly. In a real-world scenario, you'd need
                # sequence numbers and a more sophisticated buffer to handle out-of-order
                # packets and packet loss.
                
                # Let's use the sender's IP as a key for the buffer
                sender_ip = addr[0]
                if sender_ip not in self.frame_buffer:
                    self.frame_buffer[sender_ip] = b''
                
                self.frame_buffer[sender_ip] += packet

                # Heuristic: if the packet size is less than MAX_PACKET_SIZE, assume it's the last chunk
                # This is a simplification and might not always be true.
                if len(packet) < MAX_PACKET_SIZE:
                    full_frame_bytes = self.frame_buffer.pop(sender_ip)
                    frame = decode_frame(full_frame_bytes)
                    if frame is not None:
                        cv2.imshow("Remote Video", frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.stop()

            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error in video receiver: {e}")
                break

    def stop(self):
        self.running = False
        self.sock.close()
        cv2.destroyAllWindows()
        print("Video receiver stopped")

if __name__ == '__main__':
    receiver = VideoReceiver()
    try:
        receiver.start()
    except KeyboardInterrupt:
        receiver.stop()
