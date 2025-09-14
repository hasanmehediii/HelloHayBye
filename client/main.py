import threading
import time

from client.video_sender import VideoSender
from client.video_receiver import VideoReceiver
from client.audio_sender import AudioSender
from client.audio_receiver import AudioReceiver
from utils.config import SERVER_IP

def main():
    remote_ip = input(f"Enter remote IP address (default: {SERVER_IP}): ")
    if not remote_ip:
        remote_ip = SERVER_IP

    print(f"Connecting to remote IP: {remote_ip}")

    # Initialize senders and receivers
    video_sender = VideoSender(remote_ip)
    video_receiver = VideoReceiver()
    audio_sender = AudioSender(remote_ip)
    audio_receiver = AudioReceiver()

    # Create threads
    video_sender_thread = threading.Thread(target=video_sender.start)
    video_receiver_thread = threading.Thread(target=video_receiver.start)
    audio_sender_thread = threading.Thread(target=audio_sender.start)
    audio_receiver_thread = threading.Thread(target=audio_receiver.start)

    # Start threads
    video_sender_thread.start()
    video_receiver_thread.start()
    audio_sender_thread.start()
    audio_receiver_thread.start()

    try:
        while True:
            time.sleep(1) # Keep main thread alive
    except KeyboardInterrupt:
        print("\nShutting down client...")
    finally:
        # Stop all components
        video_sender.stop()
        video_receiver.stop()
        audio_sender.stop()
        audio_receiver.stop()

        # Wait for threads to finish
        video_sender_thread.join()
        video_receiver_thread.join()
        audio_sender_thread.join()
        audio_receiver_thread.join()
        print("Client shutdown complete.")

if __name__ == '__main__':
    main()
