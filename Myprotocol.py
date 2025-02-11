from socket import *
import json
from typing import Tuple, Any


class Myprotocol():
    def __init__(self, encryption: str = "utf-8", num_bytes: int = 16, buffer: int = 2048):
        self.encrypt = encryption
        self.num_bytes = num_bytes
        self.buffer = buffer

    def send_message(self, socket: socket, thing: str, action: str = "start", data: Any = "") -> None:
        try:
            if isinstance(data, str):
                data = data.encode(self.encrypt)
            elif isinstance(data, bytes):
                pass
            else:
                data = str(data).encode(self.encrypt)

            header = {
                "size": len(data),
                "thing": thing,
                "action": action,
            }

            json_header = json.dumps(header)
            header_bytes = json_header.encode(self.encrypt)

            size_header = str(len(header_bytes)).encode(self.encrypt)
            size_header = size_header.ljust(self.num_bytes, b'\0')

            socket.send(size_header)
            socket.send(header_bytes)
            socket.sendall(data)
        except Exception as e:
            raise RuntimeError(f"Error sending message: {e}")

    def recive_message(self, socket: socket) -> Tuple[dict, str]:
        try:
            size_header_raw = socket.recv(self.num_bytes)
            if not size_header_raw:
                raise ConnectionError("Connection closed by peer")

            size_header = int(size_header_raw.strip(b'\0').decode(self.encrypt))

            header_data = self.recvall(socket, size_header)
            if not header_data:
                raise ConnectionError("Connection closed while receiving header")

            header = json.loads(header_data.decode(self.encrypt))
            print("recive header: "+ header["thing"])

            payload_data = self.recvall(socket, header["size"])

            try:
                payload = payload_data.decode(self.encrypt)
            except:
                payload = payload_data
            return header, payload
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in header: {e}")
        except Exception as e:
            raise RuntimeError(f"Error receiving message: {e}")

    def recvall(self, socket: socket, size: int) -> bytes:
        data = bytearray()
        remaining = size

        while remaining > 0:
            chunk = socket.recv(min(remaining, self.buffer))
            if not chunk:
                return bytes(data)
            data.extend(chunk)
            remaining -= len(chunk)

        return bytes(data)