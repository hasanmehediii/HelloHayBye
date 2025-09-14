import pyaudio
import socket
import time

from utils.codec import encode_audio
from utils.config import AUDIO_PORT, FORMAT, CHANNELS, RATE, CHUNK

class AudioSender:
    def __init__(self, remote_ip):
        self.remote_ip = remote_ip
        self.port = AUDIO_PORT
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, # Using paInt16 as per config
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False

    def start(self):
        self.running = True
        print(f"Audio sender started, sending to {self.remote_ip}:{self.port}")
        while self.running:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                encoded_data = encode_audio(data)
                self.sock.sendto(encoded_data, (self.remote_ip, self.port))
            except Exception as e:
                print(f"Error in audio sender: {e}")
                break
            # Small delay to prevent overwhelming the network and CPU
            time.sleep(0.001) # Adjust as needed

    def stop(self):
        self.running = False
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        self.sock.close()
        print("Audio sender stopped")

if __name__ == '__main__':
    # Example usage: replace with actual remote IP
    REMOTE_IP = "127.0.0.1"
    sender = AudioSender(REMOTE_IP)
    try:
        sender.start()
    except KeyboardInterrupt:
        sender.stop()
