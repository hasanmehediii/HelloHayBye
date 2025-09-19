import tkinter as tk
from tkinter import ttk
import threading
import socket
import json
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2

from utils.network import get_local_ip, scan_network, start_discovery_server
from utils.config import SIGNALING_PORT
from client.video_sender import VideoSender
from client.video_receiver import VideoReceiver
from client.audio_sender import AudioSender
from client.audio_receiver import AudioReceiver

class CallWindow(tk.Toplevel):
    def __init__(self, parent, remote_ip, signaling_socket):
        super().__init__(parent)
        self.title(f"Call with {remote_ip}")
        self.geometry("800x600")

        self.remote_ip = remote_ip
        self.parent = parent
        self.signaling_socket = signaling_socket

        # Main frame
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Paned window to separate video and chat
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Video frame
        self.video_frame = ttk.Frame(self.paned_window, width=640)
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        self.paned_window.add(self.video_frame, weight=3)

        # Chat frame
        self.chat_frame = ttk.Frame(self.paned_window, width=200)
        self.chat_display = tk.Text(self.chat_frame, state='disabled', height=15)
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_input = ttk.Entry(self.chat_frame)
        self.chat_input.pack(fill=tk.X, padx=5, pady=5)
        self.chat_input.bind("<Return>", self.send_message)

        self.send_button = ttk.Button(self.chat_frame, text="Send", command=self.send_message)
        self.send_button.pack(anchor=tk.E, padx=5, pady=5)
        self.paned_window.add(self.chat_frame, weight=1)

        self.hangup_button = ttk.Button(self.main_frame, text="Hang Up", command=self.stop_call)
        self.hangup_button.pack(pady=10)

        self.video_sender = None
        self.video_receiver = None
        self.audio_sender = None
        self.audio_receiver = None
        self.running = True
        self.protocol("WM_DELETE_WINDOW", self.stop_call)

    def start_call(self):
        # Start listening for signaling messages
        threading.Thread(target=self._listen_for_messages, daemon=True).start()

        # Start video sending
        self.video_sender = VideoSender(self.remote_ip)
        threading.Thread(target=self.video_sender.start, daemon=True).start()

        # Start video receiving
        self.video_receiver = VideoReceiver(frame_callback=self.update_frame)
        threading.Thread(target=self.video_receiver.start, daemon=True).start()

        # Start audio sending
        self.audio_sender = AudioSender(self.remote_ip)
        threading.Thread(target=self.audio_sender.start, daemon=True).start()

        # Start audio receiving
        self.audio_receiver = AudioReceiver()
        threading.Thread(target=self.audio_receiver.start, daemon=True).start()

    def stop_call(self):
        if not self.running: return
        self.running = False

        if self.video_sender: self.video_sender.stop()
        if self.video_receiver: self.video_receiver.stop()
        if self.audio_sender: self.audio_sender.stop()
        if self.audio_receiver: self.audio_receiver.stop()

        try:
            hang_up_msg = {"type": "hang_up"}
            self.signaling_socket.sendall(json.dumps(hang_up_msg).encode('utf-8'))
        except (BrokenPipeError, OSError):
            pass # Socket might already be closed
        finally:
            self.signaling_socket.close()
        
        self.parent.end_call(self.remote_ip)
        self.destroy()

    def update_frame(self, frame):
        if self.running and frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

    def send_message(self, event=None):
        message_text = self.chat_input.get()
        if message_text:
            self.chat_input.delete(0, tk.END)
            self.display_message(f"Me: {message_text}")
            
            chat_message = {
                "type": "chat_message",
                "content": message_text
            }
            try:
                self.signaling_socket.sendall(json.dumps(chat_message).encode('utf-8'))
            except (BrokenPipeError, OSError) as e:
                self.display_message("System: Connection lost.")
                self.stop_call()

    def display_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def _listen_for_messages(self):
        while self.running:
            try:
                data = self.signaling_socket.recv(1024)
                if not data:
                    # Socket closed by remote peer
                    self.after(0, self.stop_call)
                    break
                
                message = json.loads(data.decode('utf-8'))
                msg_type = message.get("type")

                if msg_type == "chat_message":
                    content = message.get("content", "")
                    self.after(0, self.display_message, f"{self.remote_ip}: {content}")
                elif msg_type == "hang_up":
                    self.after(0, self.stop_call)
                    break

            except (json.JSONDecodeError, ConnectionResetError, BrokenPipeError, OSError):
                if self.running:
                    self.after(0, self.stop_call)
                break

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("LAN Video Chat")
        self.geometry("400x600")

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.users_label = ttk.Label(self.main_frame, text="Online Users")
        self.users_label.pack(anchor=tk.W)

        self.users_listbox = tk.Listbox(self.main_frame)
        self.users_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        self.call_button = ttk.Button(self.main_frame, text="Call", command=self.initiate_call)
        self.call_button.pack(anchor=tk.E, pady=5)

        self.refresh_button = ttk.Button(self.main_frame, text="Refresh", command=self.discover_users)
        self.refresh_button.pack(anchor=tk.E, pady=5)

        self.local_ip = get_local_ip()
        self.hostname = socket.gethostname()
        self.active_calls = {}

        start_discovery_server()
        self.start_signaling_server()
        self.discover_users()

    def discover_users(self):
        self.users_listbox.delete(0, tk.END)
        self.users_listbox.insert(tk.END, "Discovering users...")
        threading.Thread(target=self._discover_users_thread, daemon=True).start()

    def _discover_users_thread(self):
        online_users = scan_network(self.local_ip)
        self.after(0, self._update_users_list, online_users)

    def _update_users_list(self, online_users):
        self.users_listbox.delete(0, tk.END)
        if not online_users:
            self.users_listbox.insert(tk.END, "No online users found.")
            return

        for user in online_users:
            self.users_listbox.insert(tk.END, f"\u25CF {user['hostname']} ({user['ip']})")

    def initiate_call(self):
        selected_index = self.users_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("No User Selected", "Please select a user to call.")
            return

        selected_user_str = self.users_listbox.get(selected_index)
        target_ip = selected_user_str.split('(')[-1][:-1]

        threading.Thread(target=self._initiate_call_thread, args=(target_ip,), daemon=True).start()

    def _initiate_call_thread(self, target_ip):
        call_request = {
            "type": "call_request",
            "from_ip": self.local_ip,
            "from_hostname": self.hostname
        }
        
        signaling_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            signaling_socket.connect((target_ip, SIGNALING_PORT))
            signaling_socket.sendall(json.dumps(call_request).encode('utf-8'))
            
            data = signaling_socket.recv(1024)
            if data:
                response = json.loads(data.decode('utf-8'))
                if response.get("type") == "call_accepted":
                    self.after(0, self.start_call_window, target_ip, signaling_socket)
                else:
                    self.after(0, lambda: messagebox.showinfo("Call Declined", f"{target_ip} declined the call."))
                    signaling_socket.close()
            else:
                self.after(0, lambda: messagebox.showerror("No Response", f"No response from {target_ip}."))
                signaling_socket.close()

        except (ConnectionRefusedError, json.JSONDecodeError, OSError) as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Could not complete call setup: {e}"))
            signaling_socket.close()

    def start_signaling_server(self):
        def signaling_server():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("0.0.0.0", SIGNALING_PORT))
                s.listen()
                while True:
                    conn, addr = s.accept()
                    # Handle new connection in a new thread to not block the server
                    threading.Thread(target=self.handle_incoming_connection, args=(conn, addr), daemon=True).start()

        threading.Thread(target=signaling_server, daemon=True).start()

    def handle_incoming_connection(self, conn, addr):
        try:
            data = conn.recv(1024)
            if not data: return

            message = json.loads(data.decode('utf-8'))
            msg_type = message.get("type")
            remote_ip = addr[0]

            if msg_type == "call_request":
                from_hostname = message.get("from_hostname", remote_ip)
                # We must handle the UI part in the main thread
                self.after(0, self.show_incoming_call, from_hostname, remote_ip, conn)
            else:
                # If it's not a call request, we don't know what to do with this connection
                conn.close()

        except (json.JSONDecodeError, OSError):
            conn.close()

    def show_incoming_call(self, from_hostname, remote_ip, conn):
        response = {"from_ip": self.local_ip}
        if messagebox.askyesno("Incoming Call", f"Incoming call from {from_hostname}.\n\nAccept?"):
            response["type"] = "call_accepted"
            try:
                conn.sendall(json.dumps(response).encode('utf-8'))
                # The connection is kept alive and passed to the call window
                self.start_call_window(remote_ip, conn)
            except (BrokenPipeError, OSError):
                conn.close()
        else:
            response["type"] = "call_declined"
            try:
                conn.sendall(json.dumps(response).encode('utf-8'))
            except (BrokenPipeError, OSError):
                pass
            finally:
                conn.close()

    def start_call_window(self, remote_ip, signaling_socket):
        if remote_ip in self.active_calls:
            self.active_calls[remote_ip].lift()
            # Don't start a new call, but we need to close the new socket
            signaling_socket.close()
            return

        call_window = CallWindow(self, remote_ip, signaling_socket)
        call_window.start_call()
        self.active_calls[remote_ip] = call_window

    def end_call(self, remote_ip):
        if remote_ip in self.active_calls:
            # The call window's stop_call method handles destroying the window
            del self.active_calls[remote_ip]

if __name__ == "__main__":
    app = App()
    app.mainloop()