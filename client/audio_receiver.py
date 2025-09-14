import pyaudio
import socket

from utils.codec import decode_audio
from utils.config import AUDIO_PORT, FORMAT, CHANNELS, RATE, CHUNK

class AudioReceiver:
    def __init__(self):
        self.port = AUDIO_PORT
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16, # Using paInt16 as per config
                                  channels=CHANNELS,
                                  rate=RATE,
                                  output=True,
                                  frames_per_buffer=CHUNK)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.port))
        self.running = False

    def start(self):
        self.running = True
        print(f"Audio receiver started, listening on port {self.port}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(CHUNK * CHANNELS * 2) # 2 bytes per sample for paInt16
                decoded_data = decode_audio(data)
                self.stream.write(decoded_data)
            except Exception as e:
                print(f"Error in audio receiver: {e}")
                break

    def stop(self):
        self.running = False
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        self.sock.close()
        print("Audio receiver stopped")

if __name__ == '__main__':
    receiver = AudioReceiver()
    try:
        receiver.start()
    except KeyboardInterrupt:
        receiver.stop()
