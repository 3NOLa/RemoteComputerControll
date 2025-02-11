from socket import *
import json
from dataclasses import dataclass
import threading
import logging
from typing import Optional, Dict, List
from Myprotocol import Myprotocol


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 7000
    buffer_size: int = 4096
    admin_code: str = ""


class Server_between:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.protocol = Myprotocol()
        self.host = self.config.host
        self.base_port = self.config.port
        self.admin_code = config.admin_code
        self.admin: List[socket] = []
        self.clients: Dict[str, socket] = {}
        self.rooms: Dict[str, str] = {}

        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ChatServer")
        self.lock = threading.Lock()

    def handle_admin(self, admin_socket: socket, address: tuple):
        room = False
        client_socket: Optional[socket] = None

        try:
            while True:
                try:
                    header, payload = self.protocol.recive_message(admin_socket)
                    command = header["thing"]

                    if not room:
                        if command == "get clients":
                            with self.lock:
                                valid_clients = {}
                                for addr, client_socket in self.clients.items():
                                    try:
                                        self.protocol.send_message(client_socket,"Ping","continue")
                                        header, resp = self.protocol.recive_message(client_socket)
                                        print(header)
                                        if header["thing"] == 'PONG':
                                            valid_clients[addr] = client_socket
                                    except:
                                        self.logger.info(f"Client {addr} disconnected.")

                            self.clients = valid_clients
                            result = ', '.join(f"{addr}" for addr in self.clients.keys())
                            self.protocol.send_message(admin_socket, "get clients", "success", result)

                        elif command == "choose client":
                            client_ip = payload
                            if client_ip in self.clients:
                                self.rooms[f"{address[0]}:{address[1]},"] = client_ip
                                client_socket = self.clients[client_ip]
                                room = True
                                self.protocol.send_message(admin_socket, "choose client", "success")

                                threading.Thread(
                                    target=self._forward_messages,
                                    args=(client_socket, admin_socket),
                                    daemon=True
                                ).start()
                            else:
                                self.protocol.send_message(admin_socket, "choose client", "error", "Client not found")
                    else:
                        if command == "exit room":
                            room = False
                            self.rooms.pop(f"{address[0]}:{address[1]}", None)
                            client_socket = None
                            self.protocol.send_message(admin_socket, "exit room", "success")
                        else:
                            self.protocol.send_message(client_socket, header["thing"], header["action"], payload)

                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error from {address}: {e}")
                    self.protocol.send_message(admin_socket, "error", "error", "Invalid JSON format")

        except Exception as e:
            self.logger.error(f"Error handling admin {address}: {e}")
        finally:
            self.admin_cleanup_connection(admin_socket, address)

    def _forward_messages(self, source: socket, target: socket):
        try:
            while True:
                header, payload = self.protocol.recive_message(source)
                self.protocol.send_message(target, header["thing"], header["action"], payload)
        except Exception as e:
            self.protocol.send_message(target, "error", "stop")
            self.client_cleanup_connection(source,source.getpeername())

    def client_cleanup_connection(self, sock: socket, address: tuple):
        try:
            addr_str = f"{address[0]}:{address[1]}"
            if addr_str in self.clients:
                del self.clients[addr_str]
            if addr_str in self.rooms.values():
                del self.rooms[addr_str]
            sock.close()
        except Exception as e:
            self.logger.error(f"Error in client cleanup: {e}")

    def admin_cleanup_connection(self, sock: socket, address: tuple):
        try:
            addr_str = f"{address[0]}:{address[1]}"
            if sock in self.admin:
                self.admin.remove(sock)
            if addr_str in self.rooms.keys():
                del self.rooms[addr_str]
            sock.close()
        except Exception as e:
            self.logger.error(f"Error in admin cleanup: {e}")

    def start(self):
        try:
            self.server_socket.bind((self.host, self.base_port))
            self.server_socket.listen()
            self.logger.info(f"Server listening on {self.host}:{self.base_port}")

            while True:
                client_socket, address = self.server_socket.accept()

                try:
                    header, payload = self.protocol.recive_message(client_socket)
                    client_type = header["thing"]

                    if client_type == "Admin":
                        self.logger.info(f"New Admin connection from {address}")
                        self.admin.append(client_socket)
                        threading.Thread(
                            target=self.handle_admin,
                            args=(client_socket, address),
                            daemon=True
                        ).start()
                    else:
                        self.logger.info(f"New client connection from {address}")
                        addr_str = f"{address[0]}:{address[1]}"
                        self.clients[addr_str] = client_socket
                except Exception as e:
                    self.logger.error(f"Error handling new connection from {address}: {e}")
                    client_socket.close()

        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.server_socket.close()


if __name__ == "__main__":
    config = ServerConfig()
    server = Server_between(config)
    try:
        server.start()
    except KeyboardInterrupt:
        server.logger.info("Shutting down the server.")