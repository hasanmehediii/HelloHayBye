import socket
import threading
import os
from tkinter import filedialog

from utils.config import FILE_TRANSFER_PORT

class FileReceiver:
    def __init__(self, local_ip, display_message_callback):
        self.local_ip = local_ip
        self.display_message_callback = display_message_callback
        self.running = False
        self.server_socket = None
        self.port_ready = threading.Event()

    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', 0))
        _, self.port = self.server_socket.getsockname()
        self.port_ready.set()
        self.server_socket.listen(5)
        self.display_message_callback(f"System: File receiver listening on port {FILE_TRANSFER_PORT}")

        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except OSError as e:
                if self.running: # Only print error if it's not due to shutdown
                    print(f"FileReceiver accept error: {e}")
                break
            except Exception as e:
                print(f"FileReceiver error: {e}")
                break

    def _handle_client(self, conn, addr):
        try:
            self.display_message_callback(f"System: Incoming file transfer from {addr[0]}")
            
            # Receive header (filename|filesize)
            header_data = b''
            while not header_data.endswith(b'\n'):
                header_data += conn.recv(1)
            header = header_data.decode('utf-8').strip()
            filename, filesize_str = header.split('|')
            filesize = int(filesize_str)

            # Ask user where to save the file
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if not save_path:
                self.display_message_callback("System: File transfer cancelled by user.")
                conn.close()
                return

            with open(save_path, 'wb') as f:
                bytes_received = 0
                while bytes_received < filesize:
                    bytes_read = conn.recv(4096)
                    if not bytes_read:
                        break
                    f.write(bytes_read)
                    bytes_received += len(bytes_read)
            
            self.display_message_callback(f"System: Received file {filename} ({bytes_received} bytes) saved to {save_path}")

        except Exception as e:
            self.display_message_callback(f"System: Error receiving file: {e}")
        finally:
            conn.close()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
