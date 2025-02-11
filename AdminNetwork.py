import socket
from zlib import decompress
from pynput import keyboard
from pynput.keyboard import Key
import threading
import json
import queue
from Myprotocol import Myprotocol


class RemoteDesktopClient:
    def __init__(self, ip, port, frames):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((ip, port))
        self.protocol = Myprotocol()

        # Send initial admin connection message
        self.protocol.send_message(self.sock, "Admin", "connect")

        self.active = []
        self.frames = frames

        # Initialize queues
        self.screen_queue = queue.Queue()
        # self.camera_queue = queue.Queue()

        # Start receive thread
        self.receive_thread = threading.Thread(target=self.main_receive_data, daemon=True)
        self.receive_thread.start()

        # Keyboard mapping
        self.lastkey = None
        self.num_to_symbol = {
            '1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
            '6': '^', '7': '&', '8': '*', '9': '(', '0': ')'
        }
        self.sym_to_symbol = {
            '`': '~', ',': '<', '.': '>', '/': '?', '\'': '\"', '\\': '|',
            ';': ':', '[': '{', ']': '}', '-': '_', '=': '+'
        }

    def main_receive_data(self):
        try:
            while True:
                header, payload = self.protocol.recive_message(self.sock)

                if header["thing"] == "screen":
                    pixels = decompress(payload.encode()) if isinstance(payload, str) else decompress(payload)
                    self.screen_queue.put(pixels)

                elif header["thing"] == "camera":
                    pixels = decompress(payload.encode()) if isinstance(payload, str) else decompress(payload)
                    self.camera_queue.put(pixels)

                elif header["thing"] == "keyboard listener":
                        self.frames["ConnectTarget"].keys_panel.enter_new_text(text=payload)

                elif header["thing"] == "get clients":
                    home_page = self.frames["HomePage"]

                    if home_page:
                        count = 0
                        # Clear existing buttons first
                        home_page.server_canvas.delete("all")
                        for entity in payload.split(","):
                            if entity.strip():  # Only process non-empty entities
                                home_page.create_entity_button_server(entity.strip(), count)
                                count += 1
                    else:
                        print("HomePage frame not found")

                elif header["thing"] == "screen_info":
                    info = json.loads(payload)
                    self.frames["ConnectTarget"].screen_panel.screen_width = info["width"]
                    self.frames["ConnectTarget"].screen_panel.screen_height = info["height"]


        except Exception as e:
            print(f"Error in receive thread: {e}")

    def start_screen_capture(self):
        self.protocol.send_message(self.sock, "retrieve_screenshot", "start")

    def stop_screen_capture(self):
        self.protocol.send_message(self.sock, "retrieve_screenshot", "stop")

    def start_client_keys_listener(self):
        self.protocol.send_message(self.sock,"start_keyboard_listener","start")

    def stop_client_keys_listener(self):
        self.protocol.send_message(self.sock, "start_keyboard_listener", "stop")

    def start_mouse_control(self):
        self.protocol.send_message(self.sock, "block_mouse", "start")

    def stop_mouse_control(self):
        self.protocol.send_message(self.sock, "block_mouse", "stop")

    def send_mouse_pos(self,position):
        message = {"position" : position}
        self.protocol.send_message(self.sock, "Change_Mouse", "continue",json.dumps(message))

    def send_mouse_clicks(self,click):
        message = {"button" : click.num}
        self.protocol.send_message(self.sock, "Click_mouse", "continue",json.dumps(message))

    def start_keyboard_control(self):
        self.protocol.send_message(self.sock, "block_keyboard_client", "start")

    def stop_keyboard_control(self):
        self.protocol.send_message(self.sock, "block_keyboard_client", "stop")

    def send_writing_client(self,text : str):
        self.protocol.send_message(self.sock,"send_writing_client","start",text)


    #def start_camera(self):
    #    self.protocol.send_message(self.sock, "camera_feature", "start")
    #    threading.Thread(target=self.display_camera, daemon=True).start()
    def return_home(self):
        self.protocol.send_message(self.sock,"exit room")

    def close(self):
        self.stop_screen_capture()
        #self.stop_camera()
        self.stop_keyboard_control()
        self.stop_mouse_control()
        self.sock.close()

