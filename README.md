# HelloHayBye

This project implements a real-time video and audio streaming application designed for multiple clients to communicate within the same local area network (LAN).

## Features

-   **Real-time Video Streaming:** Capture webcam feed, compress it using JPEG, and stream it over UDP.
-   **Real-time Audio Streaming:** Capture microphone audio and stream it over UDP.
-   **Multi-client Support:** Designed to allow multiple participants in a call.
-   **Signaling Server:** A central server to help clients discover each other and manage connection information without directly relaying media.
-   **Modular Design:** Separated concerns for video/audio sending/receiving, utility functions, and server logic.
-   **Testing Suite:** Includes unit tests for connection, video, and audio streaming to aid in debugging and development.

## Project Structure

-   `requirements.txt`: Lists all Python dependencies.
-   `README.md`: This project description and guide.
-   `server/`:
    -   `signaling_server.py`: Coordinates client connections. It does not handle audio/video data.
-   `client/`:
    -   `main.py`: The entry point for the client application, launching video and audio senders/receivers in parallel threads.
    -   `video_sender.py`: Captures video from the webcam, encodes it, and sends it via UDP.
    -   `video_receiver.py`: Receives UDP video packets, decodes them, and displays the video.
    -   `audio_sender.py`: Captures audio from the microphone and sends it via UDP.
    -   `audio_receiver.py`: Receives UDP audio packets and plays them.
-   `utils/`:
    -   `config.py`: Stores global configuration settings like IP addresses, ports, and media parameters.
    -   `codec.py`: Handles encoding and decoding of video frames (JPEG) and audio data.
-   `tests/`:
    -   `test_connection.py`: Verifies basic UDP network connectivity.
    -   `test_video_stream.py`: Tests video sending and receiving functionality.
    -   `test_audio_stream.py`: Tests audio sending and receiving functionality.

## Setup Guide

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd LAN-Video-Streaming
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

    *Note: PyAudio might require additional system-level dependencies depending on your OS. Refer to PyAudio documentation for details if you encounter installation issues.*

## How to Run

### 1. Start the Signaling Server

Open a terminal and run:

```bash
python server/signaling_server.py
```

The server will start listening for client connections on the configured `SIGNALING_PORT` (default: 5000).

### 2. Start Client(s)

Open a separate terminal for each client you want to run. For each client, execute:

```bash
python client/main.py
```

You will be prompted to enter the remote IP address. This is the IP address of the client you wish to connect to. If you are testing with two clients on the same machine, you can use `127.0.0.1` for the remote IP. If you are connecting to another machine on your LAN, enter that machine's IP address.

**Example Workflow:**

1.  Start `signaling_server.py`.
2.  Start `client/main.py` on Machine A. It will connect to the signaling server.
3.  Start `client/main.py` on Machine B. It will also connect to the signaling server.
4.  On Machine A's client, enter Machine B's IP address when prompted.
5.  On Machine B's client, enter Machine A's IP address when prompted.

    *Note: The current signaling implementation is basic. For a full multi-client call, you would need to implement call request/acceptance logic within the client based on the signaling messages.*

### 3. Running Tests

To run the test suite, navigate to the project root directory and execute:

```bash
python -m unittest discover tests
```

This will run all tests in the `tests/` directory.

## Configuration

Edit `utils/config.py` to modify network settings, video resolution, audio parameters, and JPEG quality.

```python
# utils/config.py
SERVER_IP = "127.0.0.1"  # Replace with your server's IP address
SIGNALING_PORT = 5000
VIDEO_PORT = 5001
AUDIO_PORT = 5002
MAX_PACKET_SIZE = 65507

FRAME_WIDTH = 640
FRAME_HEIGHT = 480
JPEG_QUALITY = 80

FORMAT = "pyaudio.paInt16"
CHANNELS = 1
RATE = 44100
CHUNK = 1024
```

## Limitations and Future Improvements

-   **UDP Reliability:** UDP is connectionless and unreliable. This implementation does not include mechanisms for packet loss recovery, reordering, or congestion control, which can lead to dropped frames or audio glitches.
-   **Signaling Logic:** The signaling server provides basic client discovery. Advanced features like group calls, call rejection, or NAT traversal are not implemented.
-   **Error Handling:** Basic error handling is present, but more robust error management and logging would improve stability.
-   **Security:** No encryption or authentication is implemented, making the communication insecure.
-   **Video/Audio Synchronization:** There is no explicit synchronization mechanism between video and audio streams, which might lead to A/V desync over time.
-   **Dynamic Peer Discovery:** Currently, clients need to manually enter the remote IP. Implementing mDNS or a more sophisticated discovery mechanism would enhance usability.
