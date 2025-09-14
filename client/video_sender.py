import cv2
import socket
import numpy as np
import time

from utils.codec import encode_frame
from utils.config import VIDEO_PORT, MAX_PACKET_SIZE, FRAME_WIDTH, FRAME_HEIGHT

class VideoSender:
    def __init__(self, remote_ip):
        self.remote_ip = remote_ip
        self.port = VIDEO_PORT
        self.cap = cv2.VideoCapture(0) # 0 for default webcam
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False

    def start(self):
        self.running = True
        print(f"Video sender started, sending to {self.remote_ip}:{self.port}")
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            encoded_frame = encode_frame(frame)
            if encoded_frame is None:
                continue

            # Split the frame into chunks if it's too large for a single UDP packet
            for i in range(0, len(encoded_frame), MAX_PACKET_SIZE):
                chunk = encoded_frame[i:i + MAX_PACKET_SIZE]
                self.sock.sendto(chunk, (self.remote_ip, self.port))
            
            # Small delay to prevent overwhelming the network and CPU
            time.sleep(0.01) 

    def stop(self):
        self.running = False
        self.cap.release()
        self.sock.close()
        print("Video sender stopped")

if __name__ == '__main__':
    # Example usage: replace with actual remote IP
    REMOTE_IP = "127.0.0.1" 
    sender = VideoSender(REMOTE_IP)
    try:
        sender.start()
    except KeyboardInterrupt:
        sender.stop()
