import customtkinter as ctk
from PIL import Image, ImageTk
import threading
from typing import Optional
from AdminNetwork import RemoteDesktopClient

class ScreenDisplay(ctk.CTkFrame):
    def __init__(self, master, user: RemoteDesktopClient, width=800, height=600, **kwargs):
        super().__init__(master, width=width, height=height,corner_radius=10,fg_color="#FFCC70",**kwargs)

        self.user = user
        self.running = True

        # Create canvas to display the screen
        self.canvas = ctk.CTkCanvas(self, width=width, height=height)
        self.canvas.pack(fill="both",padx=15,pady=15)

        # Store dimensions
        self.frame_width = width
        self.frame_height = height

        self.screen_width = width
        self.screen_height = height

        # Initialize image reference
        self.image_ref: Optional[ImageTk.PhotoImage] = None
        self.update_thread = None

    def enable_panel(self):
        """Start the screen update thread when enabling the panel."""
        self.canvas.configure(state="normal")
        if self.update_thread is None or not self.update_thread.is_alive():
            # Start the update thread if it isn't already running
            self.running = True
            self.update_thread = threading.Thread(target=self.screen_update_loop, daemon=True)
            self.update_thread.start()

    def disable_panel(self):
        """Stop the screen update thread when disabling the panel."""
        self.canvas.configure(state="disabled")
        self.stop()

    def screen_update_loop(self):
        """Background thread to fetch screen updates from queue"""
        while self.running:
            try:
                pixels = self.user.screen_queue.get()
                if pixels:
                    # Schedule GUI update on main thread
                    self.after(1, lambda p=pixels: self.update_screen(p))
            except Exception as e:
                print(f"Error in screen update loop: {e}")
                continue

    def update_screen(self, pixels):
        """Update the screen with new pixel data (called on main thread)"""
        try:
            # Convert pixels to PIL Image
            image = Image.frombytes('RGB', (self.screen_width, self.screen_height), pixels)

            # Resize if necessary
            if image.size != (self.frame_width, self.frame_height):
                image = image.resize((self.frame_width, self.frame_height))

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)

            # Update canvas
            self.image_ref = photo
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=photo)

        except Exception as e:
            print(f"Error updating screen: {e}")

    def stop(self):
        """Stop the update thread cleanly"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=0.5)
