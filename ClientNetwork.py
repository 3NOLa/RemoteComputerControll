import socket
import threading
from zlib import compress
from mss import mss
import pynput
from pynput.keyboard import Listener, Controller as KeyboardController
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Key
from Myprotocol import Myprotocol
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Dict, Optional
from enum import Enum
import json
from StopAbleThread import StoppableThread

class ActionType(Enum):
    CONTINUOUS = "continuous"
    SINGLE = "single"


@dataclass
class ClientConfig:
    host: str = "127.0.0.1"
    port: int = 7000
    width: int = None
    height: int = None

    def __post_init__(self):
        root = tk.Tk()
        self.width = root.winfo_screenwidth() if self.width is None else self.width
        self.height = root.winfo_screenheight() if self.height is None else self.height
        root.destroy()


class RemoteDesktopServer:
    def __init__(self, config: ClientConfig = None):
        if config is None:
            config = ClientConfig()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((config.host, config.port))
        self.protocol = Myprotocol()
        self.protocol.send_message(self.sock, "client")

        self.WIDTH = config.width
        self.HEIGHT = config.height

        self.mouse = MouseController()
        self.keyboard = KeyboardController()

        self.watching = False
        self.capturing = threading.Event()

        self.actions: Dict[str, tuple[Callable, ActionType]] = {}
        self._register_actions()

        self.active_threads: Dict[str, StoppableThread] = {}
        self.active_lisnener : Dict = {}

    def _register_actions(self):
        self.actions.update({
            'retrieve_screenshot': (self.retrieve_screenshot, ActionType.CONTINUOUS),
            'Change_Mouse': (self.Change_Mouse_Pos, ActionType.SINGLE),
            'click_mouse': (self.click_mouse, ActionType.SINGLE),
            "block_mouse" : (self.block_mouse,ActionType.CONTINUOUS),
            "Click_mouse" : (self.click_mouse,ActionType.SINGLE),
            'start_keyboard_listener': (self.start_keyboard_listener, ActionType.CONTINUOUS),
            "send_writing_client" : (self.admin_writing_client,ActionType.SINGLE),
            "block_keyboard_client" : (self.block_keyboard,ActionType.CONTINUOUS),
            "Ping" : (self.check_alive,ActionType.SINGLE)
        })

    def check_alive(self,payload = None):
        self.protocol.send_message(self.sock,"PONG","sucsses")

    def start_action(self, method_name: str, payload: Optional[dict] = None):
        if method_name not in self.actions:
            raise ValueError(f"Unknown action: {method_name}")

        method, action_type = self.actions[method_name]

        if action_type == ActionType.CONTINUOUS:
            self.stop_action(method_name)
            if not payload:
                thread = StoppableThread(target=method,args=())
            else:
                thread = StoppableThread(target=method,args=(payload,))
            self.active_threads[method_name] = thread
            thread.start()
        else:
            method(payload) if payload else method()

    def stop_action(self, method_name: str):
        if method_name in self.active_threads:
            if hasattr(self.active_threads[method_name], 'stop') and callable(getattr(self.active_threads[method_name], 'stop')):
                self.active_threads[method_name].stop()
            else:
                self.active_threads[method_name].join(timeout=1.0)

            self.active_threads.pop(method_name)

    def retrieve_screenshot(self):
        import tkinter
        app = tkinter.Tk()
        width = app.winfo_screenwidth()
        height = app.winfo_screenheight()
        size = {"width" : width,
                "height" : height}
        self.protocol.send_message(self.sock,"screen_info",action="start",data=json.dumps(size))
        with mss() as sct:
            rect = {'top': 0, 'left': 0, 'width': self.WIDTH, 'height': self.HEIGHT}
            try:
                while self.active_threads["retrieve_screenshot"].should_stop():
                    img = sct.grab(rect)
                    pixels = compress(img.rgb, 6)
                    self.protocol.send_message(self.sock, "screen", "continue", pixels)
            except Exception as e:
                print(f"Error in retrieve_screenshot: {e}")
            finally:
                self.watching = False

    def Change_Mouse_Pos(self, payload):
        try:
            data = json.loads(payload)
            self.mouse.position = data["position"]
        except Exception as e:
            print(f"Error moving mouse: {e}")

    def block_mouse(self):
        mouse_blocker = pynput.mouse.Listener(suppress=True,on_click=self.on_block)
        mouse_blocker.start()
        self.active_threads["block_mouse"] = mouse_blocker

    def on_block(self,x, y, mouse, pressed):
        pass

    def click_mouse(self, payload):
        try:
            self.stop_action("block_mouse")
            payload = json.loads(payload)
            button = payload["button"]
            print(button)

            if button == 1:
                self.mouse.press(Button.left)
                self.mouse.release(Button.left)
            elif button == 3:
                self.mouse.press(Button.right)
                self.mouse.release(Button.right)
            elif button == 2:
                self.mouse.press(Button.middle)
            else:
                pass
            self.start_action("block_mouse")
        except Exception as e:
            print(f"Error clicking mouse: {e}")

    def start_keyboard_listener(self):
        self.keyboard_listener = Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()
        self.active_threads["start_keyboard_listener"] = self.keyboard_listener

    # In the on_key_press function, handle special keys like space, enter, etc.
    def on_key_press(self, key):
        try:
            if isinstance(key, Key):  # Special key (like space, enter)
                if key == Key.space:
                    key_char = " "
                elif key == Key.enter:
                    key_char = "\n"
                else:
                    key_char = str(key)  # For other special keys (e.g. Key.esc)
            else:
                key_char = key.char  # Regular key (like 'a', 'b', etc.)

            self.protocol.send_message(self.sock, "keyboard listener", "continue", key_char)
        except Exception as e:
            print(f"Error in keyboard listener: {e}")

    def admin_writing_client(self,text):
        try:
            self.stop_action("block_keyboard")
            for char in text:
                print(char)
                self.keyboard.press(char)
                self.keyboard.release(char)
            self.start_action("block_keyboard_client")
        except Exception as e:
            print(f"Error wrtinig key: {e}")

    def block_keyboard(self):
        self.keyboard_blocker = pynput.keyboard.Listener(suppress=True)
        self.keyboard_blocker.start()
        self.active_threads["block_keyboard"] = self.keyboard_blocker

    def run(self):
        try:
            while True:
                header, payload = self.protocol.recive_message(self.sock)
                method = header["thing"]
                action = header["action"]
                print(method + action)

                if not method or not action:
                    continue

                try:
                    if action == "start":
                        self.start_action(method,payload=payload)
                        print("started" + method)
                    elif action == "stop":
                        self.stop_action(method)
                    elif action == "continue":
                        self.actions[method][0](payload)
                        print("still " + method)
                except Exception as e:
                    print(f"Error handling {method} with action {action}: {e}")

        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            for method in list(self.active_threads.keys()):
                self.stop_action(method)
            self.sock.close()


if __name__ == '__main__':
    config = ClientConfig()
    client = RemoteDesktopServer(config)
    client.run()