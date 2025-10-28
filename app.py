import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import socket
import json
import os
import asyncio
import websockets
import random
import time

from PIL import Image, ImageTk
import cv2

from utils.network import get_local_ip
from utils.config import SIGNALING_PORT
from client.video_sender import VideoSender
from client.video_receiver import VideoReceiver
from client.file_sender import FileSender
from client.file_receiver import FileReceiver

class CallWindow(tk.Toplevel):
    def __init__(self, parent, remote_ip, remote_hostname, signaling_websocket, loop):
        super().__init__(parent)
        self.title(f"Call with {remote_hostname}")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.stop_call)

        self.remote_ip = remote_ip
        self.remote_hostname = remote_hostname
        self.parent = parent
        self.signaling_websocket = signaling_websocket
        self.loop = loop
        self.remote_file_port = None
        self.remote_video_port = None
        self.remote_ports_ready = threading.Event()

        # Apply styling
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#2e2e2e')
        self.style.configure('TButton', 
                             background='#007bff', 
                             foreground='white', 
                             font=('Arial', 10, 'bold'),
                             borderwidth=0)
        self.style.map('TButton', 
                       background=[('active', '#0056b3')],
                       foreground=[('active', 'white')])
        self.style.configure('TLabel', background='#2e2e2e', foreground='#ffffff')
        self.style.configure('TText', background='#3c3c3c', foreground='#ffffff', borderwidth=1)
        self.style.configure('TEntry', fieldbackground='#3c3c3c', foreground='#ffffff', borderwidth=1)

        # Main frame
        self.main_frame = ttk.Frame(self, style='TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Paned window to separate video and chat
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Video frame
        self.video_frame = ttk.Frame(self.paned_window, width=640, style='TFrame')
        self.video_label = ttk.Label(self.video_frame, style='TLabel')
        self.video_label.pack(fill=tk.BOTH, expand=True)
        self.paned_window.add(self.video_frame, weight=4)

        self.self_view_label = ttk.Label(self.video_frame, style='TLabel')
        self.self_view_label.place(relx=0.05, rely=0.05, relwidth=0.3, relheight=0.3)

        # Chat and File Transfer Frame
        self.chat_file_frame = ttk.Frame(self.paned_window, width=200, style='TFrame')
        self.paned_window.add(self.chat_file_frame, weight=1)

        # Chat frame
        self.chat_frame = ttk.Frame(self.chat_file_frame, style='TFrame')
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_display = tk.Text(self.chat_frame, state='disabled', height=15, bg='#3c3c3c', fg='#ffffff', borderwidth=0)
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_input = ttk.Entry(self.chat_frame, style='TEntry')
        self.chat_input.pack(fill=tk.X, padx=5, pady=5)
        self.chat_input.bind("<Return>", self.send_message)

        self.send_button = ttk.Button(self.chat_frame, text="Send", command=self.send_message, style='TButton')
        if hasattr(self, 'send_icon'):
            self.send_button.config(image=self.send_icon, compound=tk.LEFT)
        self.send_button.pack(anchor=tk.E, padx=5, pady=5)

        # File Transfer Frame
        self.file_transfer_frame = ttk.Frame(self.chat_file_frame, style='TFrame')
        self.file_transfer_frame.pack(fill=tk.X, padx=5, pady=5)

        self.file_path_label = ttk.Label(self.file_transfer_frame, text="No file selected", style='TLabel')
        self.file_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.browse_file_button = ttk.Button(self.file_transfer_frame, text="Browse", command=self.browse_file, style='TButton')
        if hasattr(self, 'browse_icon'):
            self.browse_file_button.config(image=self.browse_icon, compound=tk.LEFT)
        self.browse_file_button.pack(side=tk.LEFT, padx=(5, 0))

        self.send_file_button = ttk.Button(self.file_transfer_frame, text="Send File", command=self.send_file, style='TButton')
        if hasattr(self, 'send_file_icon'):
            self.send_file_button.config(image=self.send_file_icon, compound=tk.LEFT)
        self.send_file_button.pack(side=tk.RIGHT)

        self.hangup_button = ttk.Button(self.main_frame, text="Hang Up", command=self.stop_call, style='TButton')
        try:
            self.hangup_icon = ImageTk.PhotoImage(Image.open("assets/icons/end-call.png").resize((20, 20)))
            self.hangup_button.config(image=self.hangup_icon, compound=tk.LEFT)
        except FileNotFoundError:
            print("Hang up icon not found.")
        self.hangup_button.pack(pady=10)

        self.video_sender = None
        self.video_receiver = None
        self.file_sender = None
        self.file_receiver = None
        self.running = True
        self.selected_file = None

        # Load icons for other buttons
        try:
            self.send_icon = ImageTk.PhotoImage(Image.open("assets/icons/bubble-chat.png").resize((20, 20)))
            self.browse_icon = ImageTk.PhotoImage(Image.open("assets/icons/add-group.png").resize((20, 20)))
            self.send_file_icon = ImageTk.PhotoImage(Image.open("assets/icons/add-group.png").resize((20, 20)))
        except FileNotFoundError:
            print("One or more icons not found.")

    def start_call(self):
        # Start video receiving
        print("Starting video receiver...")
        self.video_receiver = VideoReceiver(frame_callback=self.update_frame)
        self.video_receiver_thread = threading.Thread(target=self.video_receiver.start)
        self.video_receiver_thread.start()
        self.video_receiver.port_ready.wait()
        print(f"Video receiver started on port {self.video_receiver.port}")

        # Start file receiver
        print("Starting file receiver...")
        self.file_receiver = FileReceiver(self.remote_ip, self.display_message)
        self.file_receiver_thread = threading.Thread(target=self.file_receiver.start)
        self.file_receiver_thread.start()
        self.file_receiver.port_ready.wait()
        print(f"File receiver started on port {self.file_receiver.port}")

        # Send port information to the other client
        print("Sending video port info...")
        port_info_message = {
            "type": "video_port_info",
            "to_hostname": self.remote_hostname,
            "from_hostname": self.parent.hostname,
            "port": self.video_receiver.port
        }
        self.parent.run_async_task(self.signaling_websocket.send(json.dumps(port_info_message)))

        print("Sending file transfer port info...")
        port_info_message = {
            "type": "file_transfer_port",
            "to_hostname": self.remote_hostname,
            "from_hostname": self.parent.hostname,
            "port": self.file_receiver.port
        }
        self.parent.run_async_task(self.signaling_websocket.send(json.dumps(port_info_message)))

        # Wait for remote ports to be received (Indentation fix attempt)
        def wait_for_ports():
            print("Waiting for remote ports to be ready...")
            self.remote_ports_ready.wait() # Wait until the event is set
            print("Remote ports ready. Starting senders...")

            # Start video sending
            print(f"Instantiating VideoSender with remote_ip={self.remote_ip}, remote_video_port={self.remote_video_port}")
            self.video_sender = VideoSender(self.remote_ip, self.remote_video_port, self.update_self_view_frame)
            self.video_sender_thread = threading.Thread(target=self.video_sender.start)
            self.video_sender_thread.start()
            print("Video sender started.")

            # Start file sending (if a file is selected)
            if self.selected_file:
                self.display_message(f"Me: Sending file {os.path.basename(self.selected_file)}...")
                self.file_sender = FileSender(self.remote_ip, self.selected_file, self.display_message, self.remote_file_port)
                self.file_sender_thread = threading.Thread(target=self.file_sender.start)
                self.file_sender_thread.start()
                self.selected_file = None
                self.file_path_label.config(text="No file selected")

        self.wait_for_ports_thread = threading.Thread(target=wait_for_ports)
        self.wait_for_ports_thread.start()

    def stop_call(self):
        if not self.running: return
        self.running = False

        if self.video_sender: self.video_sender.stop()
        if self.video_receiver: self.video_receiver.stop()
        if self.file_sender: self.file_sender.stop()
        if self.file_receiver: self.file_receiver.stop()

        # Join all threads to ensure they finish cleanly
        if hasattr(self, 'video_receiver_thread') and self.video_receiver_thread and self.video_receiver_thread.is_alive():
            self.video_receiver_thread.join(timeout=1)
        if hasattr(self, 'file_receiver_thread') and self.file_receiver_thread and self.file_receiver_thread.is_alive():
            self.file_receiver_thread.join(timeout=1)
        if hasattr(self, 'video_sender_thread') and self.video_sender_thread and self.video_sender_thread.is_alive():
            self.video_sender_thread.join(timeout=1)
        if hasattr(self, 'file_sender_thread') and self.file_sender_thread and self.file_sender_thread.is_alive():
            self.file_sender_thread.join(timeout=1)

        try:
            hang_up_msg = {"type": "hang_up", "from_hostname": self.parent.hostname, "to_hostname": self.remote_hostname}
            self.parent.run_async_task(self.signaling_websocket.send(json.dumps(hang_up_msg)))
        except Exception as e:
            print(f"Error sending hang up message: {e}")
        
        self.parent.end_call(self.remote_hostname)
        self.destroy()

    def check_remote_ports(self):
        print(f"Checking remote ports: video={self.remote_video_port}")
        if self.remote_video_port is not None:
            self.remote_ports_ready.set()
            print("Remote ports ready event set.")



    def update_self_view_frame(self, frame):
        if self.running and frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (160, 120)) # Smaller size for self-view
            img = Image.fromarray(frame)
            imgtk = ImageTk.PhotoImage(image=img)
            self.self_view_label.imgtk = imgtk
            self.self_view_label.configure(image=imgtk)

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
                "content": message_text,
                "from_hostname": self.parent.hostname,
                "to_hostname": self.remote_hostname
            }
            try:
                self.parent.run_async_task(self.signaling_websocket.send(json.dumps(chat_message)))
            except Exception as e:
                self.display_message("System: Connection lost.")
                print(f"Error sending chat message: {e}")
                self.stop_call()

    def browse_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.selected_file = file_path
            self.file_path_label.config(text=os.path.basename(file_path))

    def send_file(self):
        if self.selected_file:
            if self.remote_file_port:
                self.display_message(f"Me: Sending file {os.path.basename(self.selected_file)}...")
                self.file_sender = FileSender(self.remote_ip, self.selected_file, self.display_message, self.remote_file_port)
                threading.Thread(target=self.file_sender.start, daemon=True).start()
                self.selected_file = None
                self.file_path_label.config(text="No file selected")
            else:
                messagebox.showwarning("File Transfer Not Ready", "The other client is not ready to receive files yet.")
        else:
            messagebox.showwarning("No File Selected", "Please select a file to send.")

    def display_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)



class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("LAN Video Chat")
        self.geometry("400x600")
        self.resizable(False, False)

        # Apply a modern theme
        self.style = ttk.Style(self)
        self.style.theme_use('clam') # 'clam', 'alt', 'default', 'classic'

        # Configure styles for a modern look
        self.style.configure('TFrame', background='#2e2e2e')
        self.style.configure('TButton', 
                             background='#007bff', 
                             foreground='white', 
                             font=('Arial', 10, 'bold'),
                             borderwidth=0)
        self.style.map('TButton', 
                       background=[('active', '#0056b3')],
                       foreground=[('active', 'white')])
        self.style.configure('TLabel', background='#2e2e2e', foreground='#ffffff')
        self.style.configure('Treeview', background='#3c3c3c', foreground='#ffffff', fieldbackground='#3c3c3c')
        self.style.map('Treeview', background=[('selected', '#007bff')])
        self.style.configure('TEntry', fieldbackground='#3c3c3c', foreground='#ffffff', borderwidth=1)
        self.style.configure('TText', background='#3c3c3c', foreground='#ffffff', borderwidth=1)

        self.main_frame = ttk.Frame(self, style='TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.users_label = ttk.Label(self.main_frame, text="Online Users", style='TLabel')
        self.users_label.pack(anchor=tk.W, pady=(0, 5))

        self.users_listbox = tk.Listbox(self.main_frame, 
                                        bg='#3c3c3c', 
                                        fg='#ffffff', 
                                        selectbackground='#007bff', 
                                        selectforeground='white',
                                        borderwidth=0, 
                                        highlightthickness=0)
        self.users_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        self.call_button = ttk.Button(self.main_frame, text="Call", command=self.initiate_call, style='TButton')
        try:
            self.call_icon = ImageTk.PhotoImage(Image.open("assets/icons/phone-call.png").resize((20, 20)))
            self.call_button.config(image=self.call_icon, compound=tk.LEFT)
        except FileNotFoundError:
            print("Call icon not found.")
        self.call_button.pack(anchor=tk.E, pady=5)

        self.refresh_button = ttk.Button(self.main_frame, text="Refresh", command=self.discover_users, style='TButton')
        try:
            self.refresh_icon = ImageTk.PhotoImage(Image.open("assets/icons/search-profile.png").resize((20, 20)))
            self.refresh_button.config(image=self.refresh_icon, compound=tk.LEFT)
        except FileNotFoundError:
            print("Refresh icon not found.")
        self.refresh_button.pack(anchor=tk.E, pady=5)

        self.local_ip = get_local_ip()
        self.hostname = f"{socket.gethostname()}-{random.randint(1000, 9999)}"
        self.active_calls = {}
        self.signaling_websocket = None
        self.online = False

        # UI for online/offline status and toggle
        self.status_frame = ttk.Frame(self.main_frame, style='TFrame')
        self.status_frame.pack(fill=tk.X, pady=5)

        self.status_label = ttk.Label(self.status_frame, text="Status: Offline", foreground="red", style='TLabel')
        self.status_label.pack(side=tk.LEFT)

        self.toggle_online_button = ttk.Button(self.status_frame, text="Go Online", command=self.toggle_online_status, style='TButton')
        self.toggle_online_button.pack(side=tk.RIGHT)

        # New asyncio integration
        self.asyncio_loop = asyncio.new_event_loop()
        self.asyncio_thread = threading.Thread(target=self._run_asyncio_loop, args=(self.asyncio_loop,), daemon=True)
        self.asyncio_thread.start()
        self.after(100, self._check_asyncio_tasks, self.asyncio_loop) # Periodically check for completed asyncio tasks

        self.discover_users()

    def _run_asyncio_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def _check_asyncio_tasks(self, loop):
        # This method is called periodically by Tkinter's main loop
        # It ensures that any callbacks scheduled from the asyncio thread are processed
        loop.call_soon_threadsafe(lambda: None) # A no-op to wake up the asyncio loop if it's idle
        self.after(100, self._check_asyncio_tasks, loop) # Schedule itself again

    def run_async_task(self, coro):
        # Helper to run an asyncio coroutine from the Tkinter thread
        return asyncio.run_coroutine_threadsafe(coro, self.asyncio_loop)


    def toggle_online_status(self):
        if self.online:
            self.go_offline()
        else:
            self.go_online()

    def go_online(self):
        self.run_async_task(self._connect_to_signaling_server())
        self.status_label.config(text="Status: Online", foreground="green")
        self.toggle_online_button.config(text="Go Offline")
        self.online = True
        self.discover_users()

    def go_offline(self):
        if self.signaling_websocket:
            self.run_async_task(self.signaling_websocket.close())
            self.signaling_websocket = None
        self.status_label.config(text="Status: Offline", foreground="red")
        self.toggle_online_button.config(text="Go Online")
        self.online = False
        self.users_listbox.delete(0, tk.END)
        self.users_listbox.insert(tk.END, "Go online to see other users.")

    async def _connect_to_signaling_server(self):
        try:
            self.signaling_websocket = await websockets.connect(f"ws://{self.local_ip}:{SIGNALING_PORT}")
            print("Connected to signaling server.")
            # Start listening for messages from the signaling server
            self.run_async_task(self._listen_to_signaling_server())
            await self.signaling_websocket.send(json.dumps({"type": "register", "ip": self.local_ip, "hostname": self.hostname}))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Connection Error", f"Could not connect to signaling server: {e}"))
            self.go_offline()

    async def _listen_to_signaling_server(self):
        while self.online and self.signaling_websocket:
            try:
                message = await self.signaling_websocket.recv()
                data = json.loads(message)
                self.after(0, self._handle_signaling_message, data)
            except websockets.exceptions.ConnectionClosedOK:
                print("Signaling connection closed gracefully.")
                break
            except Exception as e:
                print(f"Error listening to signaling server: {e}")
                self.after(0, self.go_offline)
                break

    def _handle_signaling_message(self, message):
        msg_type = message.get("type")

        if msg_type == "client_list":
            self._update_users_list(message.get("clients", []))
        elif msg_type == "incoming_call":
            from_ip = message.get("from_ip")
            from_hostname = message.get("from_hostname", from_ip)
            self.show_incoming_call(from_hostname, from_ip)
        elif msg_type == "call_accepted":
            peer_ip = message.get("peer_ip")
            peer_hostname = message.get("peer_hostname")
            self.start_call_window(peer_ip, peer_hostname)
        elif msg_type == "call_declined":
            peer_hostname = message.get("peer_hostname")
            messagebox.showinfo("Call Declined", f"{peer_hostname} declined the call.")
        elif msg_type == "error":
            messagebox.showerror("Signaling Error", message.get("message", "An unknown error occurred."))
        elif msg_type == "chat_message":
            from_hostname = message.get("from_hostname")
            if from_hostname in self.active_calls:
                self.active_calls[from_hostname].display_message(f"{from_hostname}: {message.get('content')}")
        elif msg_type == "hang_up":
            from_hostname = message.get("from_hostname")
            if from_hostname in self.active_calls:
                self.active_calls[from_hostname].stop_call()
        elif msg_type == "file_transfer_port":
            from_hostname = message.get("from_hostname")
            port = message.get("port")
            if from_hostname in self.active_calls:
                self.active_calls[from_hostname].remote_file_port = port
                print(f"Received file transfer port {port} from {from_hostname}")
        elif msg_type == "video_port_info":
            from_hostname = message.get("from_hostname")
            port = message.get("port")
            if from_hostname in self.active_calls:
                self.active_calls[from_hostname].remote_video_port = port
                self.active_calls[from_hostname].check_remote_ports()
                print(f"Received video port {port} from {from_hostname}")


    def discover_users(self):
        self.users_listbox.delete(0, tk.END)
        if not self.online:
            self.users_listbox.insert(tk.END, "Go online to see other users.")
            return
        self.users_listbox.insert(tk.END, "Fetching online users...")
        # The client list will be sent by the signaling server

    def _update_users_list(self, online_clients):
        self.users_listbox.delete(0, tk.END)
        if not online_clients:
            self.users_listbox.insert(tk.END, "No other online users found.")
            return

        for client in online_clients:
            if client["hostname"] != self.hostname: # Don't list self
                self.users_listbox.insert(tk.END, f"● {client['hostname']} ({client['ip']})")

    def initiate_call(self):
        selected_index = self.users_listbox.curselection()
        if not selected_index:
            messagebox.showwarning("No User Selected", "Please select a user to call.")
            return

        selected_user_str = self.users_listbox.get(selected_index)
        target_hostname = selected_user_str.split(' ')[1]
        target_ip = selected_user_str.split('(')[-1][:-1]

        if self.signaling_websocket and self.online:
            call_request = {
                "type": "request_call",
                "target_hostname": target_hostname,
                "from_ip": self.local_ip,
                "from_hostname": self.hostname
            }
            self.run_async_task(self.signaling_websocket.send(json.dumps(call_request)))
        else:
            messagebox.showerror("Not Online", "You must be online to initiate a call.")

    def show_incoming_call(self, from_hostname, remote_ip):
        if messagebox.askyesno("Incoming Call", f"Incoming call from {from_hostname}.\n\nAccept?"):
            response = {
                "type": "accept_call",
                "caller_hostname": from_hostname,
                "accepter_ip": self.local_ip,
                "accepter_hostname": self.hostname
            }
            self.run_async_task(self.signaling_websocket.send(json.dumps(response)))
            self.start_call_window(remote_ip, from_hostname)
        else:
            response = {
                "type": "decline_call",
                "caller_hostname": from_hostname,
                "decliner_hostname": self.hostname
            }
            self.run_async_task(self.signaling_websocket.send(json.dumps(response)))

    def start_call_window(self, remote_ip, remote_hostname):
        if remote_hostname in self.active_calls:
            self.active_calls[remote_hostname].lift()
            return

        call_window = CallWindow(self, remote_ip, remote_hostname, self.signaling_websocket, self.asyncio_loop)
        call_window.start_call()
        self.active_calls[remote_hostname] = call_window

    def end_call(self, remote_hostname):
        if remote_hostname in self.active_calls:
            del self.active_calls[remote_hostname]

if __name__ == "__main__":
    app = App()
    app.mainloop()