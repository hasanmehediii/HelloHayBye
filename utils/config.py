
SERVER_IP = "127.0.0.1"  # Replace with your server's IP address
SIGNALING_PORT = 5000
VIDEO_PORT = 5001
AUDIO_PORT = 5002
MAX_PACKET_SIZE = 65507  # Max UDP packet size

# Video settings
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
JPEG_QUALITY = 80 # 0-100

# Audio settings
FORMAT = "pyaudio.paInt16"
CHANNELS = 1
RATE = 44100
CHUNK = 1024
