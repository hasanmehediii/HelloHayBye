import socket
import threading
from .config import DISCOVERY_PORT

def get_local_ip():
    """Gets the local IP address of the machine."""
    try:
        # Create a dummy socket to connect to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('10.254.254.254', 1)) # Doesn't have to be reachable
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def scan_network(local_ip):
    """Scans the local network for other clients running the application."""
    subnet = '.'.join(local_ip.split('.')[:-1])
    online_users = []
    threads = []

    def check_host(ip):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1) # Quick timeout for non-responsive hosts
                if s.connect_ex((ip, DISCOVERY_PORT)) == 0:
                    hostname = socket.gethostbyaddr(ip)[0]
                    online_users.append({"ip": ip, "hostname": hostname})
        except (socket.herror, socket.timeout):
            # Hostname could not be resolved or host timed out
            pass

    for i in range(1, 255):
        ip_to_check = f"{subnet}.{i}"
        if ip_to_check != local_ip:
            thread = threading.Thread(target=check_host, args=(ip_to_check,))
            threads.append(thread)
            thread.start()

    for thread in threads:
        thread.join()

    return online_users

def start_discovery_server():
    """Starts a server to listen for discovery probes."""
    def discovery_server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", DISCOVERY_PORT))
                s.listen()
                while True:
                    conn, addr = s.accept()
                    conn.close()
            except OSError as e:
                print(f"Error starting discovery server: {e}")

    thread = threading.Thread(target=discovery_server, daemon=True)
    thread.start()
