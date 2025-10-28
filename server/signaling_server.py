import asyncio
import websockets
import json

from utils.config import SIGNALING_PORT

class SignalingServer:
    def __init__(self):
        self.clients = {}
        self.port = SIGNALING_PORT

    async def register(self, websocket, message):
        self.clients[websocket] = {"ip": message["ip"], "hostname": message["hostname"]}
        print(f"Client connected: {websocket.remote_address[0]} ({message["hostname"]}). Total clients: {len(self.clients)}")
        await self.send_client_list()

    async def unregister(self, websocket):
        if websocket in self.clients:
            hostname = self.clients[websocket]["hostname"]
            del self.clients[websocket]
            print(f"Client disconnected: {websocket.remote_address[0]} ({hostname}). Total clients: {len(self.clients)}")
            await self.send_client_list()

    async def send_client_list(self):
        client_infos = [{
            "ip": client_info["ip"],
            "hostname": client_info["hostname"]
        } for client_info in self.clients.values()]
        message = json.dumps({"type": "client_list", "clients": client_infos})
        await asyncio.gather(*[client.send(message) for client in self.clients])

    async def handler(self, websocket):
        # The first message from a new client should be a 'register' message
        try:
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "register":
                    await self.register(websocket, data)
                elif msg_type == "request_call":
                    target_hostname = data["target_hostname"]
                    caller_ip = data["from_ip"]
                    caller_hostname = data["from_hostname"]
                    print(f"Call request from {caller_hostname} ({caller_ip}) to {target_hostname}")
                    
                    target_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["hostname"] == target_hostname:
                            target_websocket = client_ws
                            break
                    
                    if target_websocket:
                        await target_websocket.send(json.dumps({"type": "incoming_call", "from_ip": caller_ip, "from_hostname": caller_hostname}))
                    else:
                        await websocket.send(json.dumps({"type": "call_declined", "peer_hostname": target_hostname, "message": f"Client {target_hostname} not found"}))
                
                elif msg_type == "accept_call":
                    caller_hostname = data["caller_hostname"]
                    accepter_ip = data["accepter_ip"]
                    accepter_hostname = data["accepter_hostname"]
                    print(f"Call from {caller_hostname} accepted by {accepter_hostname}")

                    caller_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["hostname"] == caller_hostname:
                            caller_websocket = client_ws
                            break
                    
                    if caller_websocket:
                        await caller_websocket.send(json.dumps({"type": "call_accepted", "peer_ip": accepter_ip, "peer_hostname": accepter_hostname}))
                    else:
                        await websocket.send(json.dumps({"type": "error", "message": f"Caller {caller_hostname} not found"}))

                elif msg_type == "decline_call":
                    caller_hostname = data["caller_hostname"]
                    decliner_hostname = data["decliner_hostname"]
                    print(f"Call from {caller_hostname} declined by {decliner_hostname}")

                    caller_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["hostname"] == caller_hostname:
                            caller_websocket = client_ws
                            break
                    
                    if caller_websocket:
                        await caller_websocket.send(json.dumps({"type": "call_declined", "peer_hostname": decliner_hostname}))
                    else:
                        await websocket.send(json.dumps({"type": "error", "message": f"Caller {caller_hostname} not found"}))

                elif msg_type == "chat_message":
                    to_hostname = data["to_hostname"]
                    from_hostname = data["from_hostname"]
                    content = data["content"]

                    target_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["hostname"] == to_hostname:
                            target_websocket = client_ws
                            break
                    
                    if target_websocket:
                        await target_websocket.send(json.dumps({"type": "chat_message", "from_hostname": from_hostname, "content": content}))
                    else:
                        print(f"Target {to_hostname} for chat message not found.")

                elif msg_type == "hang_up":
                    to_hostname = data["to_hostname"]
                    from_hostname = data["from_hostname"]

                    target_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["hostname"] == to_hostname:
                            target_websocket = client_ws
                            break
                    
                    if target_websocket:
                        await target_websocket.send(json.dumps({"type": "hang_up", "from_hostname": from_hostname}))
                    else:
                        print(f"Target {to_hostname} for hang up not found.")

                elif msg_type == "file_transfer_port":
                    to_hostname = data["to_hostname"]
                    target_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["hostname"] == to_hostname:
                            target_websocket = client_ws
                            break
                    
                    if target_websocket:
                        await target_websocket.send(json.dumps(data))

                elif msg_type in ["video_port_info", "audio_port_info"]:
                    to_hostname = data["to_hostname"]
                    target_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["hostname"] == to_hostname:
                            target_websocket = client_ws
                            break
                    
                    if target_websocket:
                        await target_websocket.send(json.dumps(data))

        except websockets.exceptions.ConnectionClosedOK:
            pass
        except Exception as e:
            print(f"Error in signaling handler: {e}")
        finally:
            await self.unregister(websocket)

    async def start_server(self):
        print(f"Signaling server starting on ws://0.0.0.0:{self.port}")
        async with websockets.serve(self.handler, "0.0.0.0", self.port):
            await asyncio.Future()  # Run forever

if __name__ == '__main__':
    server = SignalingServer()
    asyncio.run(server.start_server())
