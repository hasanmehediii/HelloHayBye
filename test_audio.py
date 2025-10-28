import pyaudio
import time

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 5

def test_pyaudio():
    p = pyaudio.PyAudio()

    print("--- Testing Microphone Input ---")
    try:
        stream_input = p.open(format=FORMAT,
                              channels=CHANNELS,
                              rate=RATE,
                              input=True,
                              frames_per_buffer=CHUNK)
        print("Microphone stream opened successfully.")
        print(f"Recording for {RECORD_SECONDS} seconds...")
        frames = []
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)): # Corrected calculation
            data = stream_input.read(CHUNK)
            frames.append(data)
        print("Recording finished.")
        stream_input.stop_stream()
        stream_input.close()
        print("Microphone stream closed.")
    except Exception as e:
        print(f"Error opening or reading from microphone: {e}")

    print("\n--- Testing Speaker Output ---")
    try:
        stream_output = p.open(format=FORMAT,
                               channels=CHANNELS,
                               rate=RATE,
                               output=True,
                               frames_per_buffer=CHUNK)
        print("Speaker stream opened successfully.")
        # Play silence for a short period
        print(f"Playing silence for {RECORD_SECONDS} seconds...")
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)): # Corrected calculation
            stream_output.write(b'\x00' * CHUNK * CHANNELS * 2) # 2 bytes per sample for paInt16
        print("Playing finished.")
        stream_output.stop_stream()
        stream_output.close()
        print("Speaker stream closed.")
    except Exception as e:
        print(f"Error opening or writing to speaker: {e}")

    p.terminate()
    print("\nPyAudio terminated.")

if __name__ == '__main__':
    test_pyaudio()
