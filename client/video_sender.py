import cv2
import socket
import numpy as np
import time

from utils.codec import encode_frame
from utils.config import VIDEO_PORT, MAX_PACKET_SIZE, FRAME_WIDTH, FRAME_HEIGHT

class VideoSender:
    def __init__(self, remote_ip, port, frame_callback=None):
        self.remote_ip = remote_ip
        self.port = port
        self.frame_callback = frame_callback
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2) # Try camera index 0
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(1, cv2.CAP_V4L2) # Fallback to camera index 1
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Initialize sock unconditionally

        self.running = True # Assume running until proven otherwise
        if not self.cap.isOpened():
            print("Error: Could not open video source. Please check if webcam is connected and not in use.")
            self.running = False
            return # Exit if camera cannot be opened
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    def start(self):
        if not self.running:
            print("Video sender cannot start: Camera not opened or initialized.")
            return
        self.running = True
        print(f"Video sender started, sending to {self.remote_ip}:{self.port}")
        # Give camera a moment to warm up
        time.sleep(0.5)
        while self.running:
            ret, frame = self.cap.read()
            if not self.running:
                break
            if not ret:
                print("Failed to grab frame")
                continue # Continue to the next iteration instead of breaking

            if self.frame_callback:
                self.frame_callback(frame)

            encoded_frame = encode_frame(frame)
            if encoded_frame is None:
                print("Failed to encode frame")
                continue

            # Split the frame into chunks if it's too large for a single UDP packet
            for i in range(0, len(encoded_frame), MAX_PACKET_SIZE):
                if not self.running: # Check if still running before sending each chunk
                    break
                chunk = encoded_frame[i:i + MAX_PACKET_SIZE]
                try:
                    self.sock.sendto(chunk, (self.remote_ip, self.port))
                    # print(f"Sent video chunk to {self.remote_ip}:{self.port}") # Too verbose, enable if needed
                except Exception as e:
                    print(f"Error sending video chunk: {e}")
                    if not self.running: # If error occurs during shutdown, it's expected
                        break
            
            # Small delay to prevent overwhelming the network and CPU
            time.sleep(0.01) 

    def stop(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.sock:
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
