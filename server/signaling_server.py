import asyncio
import websockets
import json

from utils.config import SIGNALING_PORT

class SignalingServer:
    def __init__(self):
        self.clients = {}
        self.port = SIGNALING_PORT

    async def register(self, websocket):
        # For simplicity, using websocket object as client ID. In a real app, use a unique ID.
        self.clients[websocket] = {"ip": websocket.remote_address[0]}
        print(f"Client connected: {websocket.remote_address[0]}. Total clients: {len(self.clients)}")
        await self.send_client_list()

    async def unregister(self, websocket):
        del self.clients[websocket]
        print(f"Client disconnected: {websocket.remote_address[0]}. Total clients: {len(self.clients)}")
        await self.send_client_list()

    async def send_client_list(self):
        client_ips = [client_info["ip"] for client_info in self.clients.values()]
        message = json.dumps({"type": "client_list", "clients": client_ips})
        await asyncio.gather(*[client.send(message) for client in self.clients])

    async def handler(self, websocket, path):
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                if data["type"] == "request_call":
                    target_ip = data["target_ip"]
                    caller_ip = websocket.remote_address[0]
                    print(f"Call request from {caller_ip} to {target_ip}")
                    
                    # Find the target client's websocket
                    target_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["ip"] == target_ip:
                            target_websocket = client_ws
                            break
                    
                    if target_websocket:
                        # Notify target client about incoming call
                        await target_websocket.send(json.dumps({"type": "incoming_call", "from_ip": caller_ip}))
                        # Notify caller that request was sent
                        await websocket.send(json.dumps({"type": "call_request_sent", "to_ip": target_ip}))
                    else:
                        await websocket.send(json.dumps({"type": "error", "message": f"Client {target_ip} not found"}))
                
                elif data["type"] == "accept_call":
                    caller_ip = data["caller_ip"]
                    accepter_ip = websocket.remote_address[0]
                    print(f"Call from {caller_ip} accepted by {accepter_ip}")

                    # Find the caller's websocket
                    caller_websocket = None
                    for client_ws, client_info in self.clients.items():
                        if client_info["ip"] == caller_ip:
                            caller_websocket = client_ws
                            break
                    
                    if caller_websocket:
                        # Inform both parties of the connection
                        await caller_websocket.send(json.dumps({"type": "call_accepted", "peer_ip": accepter_ip}))
                        await websocket.send(json.dumps({"type": "call_accepted", "peer_ip": caller_ip}))
                    else:
                        await websocket.send(json.dumps({"type": "error", "message": f"Caller {caller_ip} not found"}))

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
