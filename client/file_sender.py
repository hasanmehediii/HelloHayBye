import socket
import threading
import os

from utils.config import FILE_TRANSFER_PORT

class FileSender:
    def __init__(self, remote_ip, file_path, display_message_callback, port):
        self.remote_ip = remote_ip
        self.port = port
        self.file_path = file_path
        self.display_message_callback = display_message_callback
        self.running = False

    def start(self):
        self.running = True
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.remote_ip, self.port))
                
                filename = os.path.basename(self.file_path)
                filesize = os.path.getsize(self.file_path)
                
                # Send filename and filesize
                header = f"{filename}|{filesize}".encode('utf-8')
                s.sendall(header + b'\n') # Use a newline as a delimiter

                with open(self.file_path, 'rb') as f:
                    while True:
                        bytes_read = f.read(4096)
                        if not bytes_read:
                            break
                        s.sendall(bytes_read)
                
                self.display_message_callback(f"System: Successfully sent {filename}.")

        except Exception as e:
            self.display_message_callback(f"System: Error sending file: {e}")
        finally:
            self.running = False

    def stop(self):
        self.running = False
