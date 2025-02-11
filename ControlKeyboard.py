from AdminNetwork import RemoteDesktopClient
import customtkinter as ctk

class KeyboardSendFrame(ctk.CTkFrame):
    def __init__(self,master, user : RemoteDesktopClient, width=350, height=150, **kwargs):
        super().__init__(master, width=width, height=height,border_width=3,border_color="#FFCC70",corner_radius=10 ,**kwargs)
        self.user = user

        self.text_feild = ctk.CTkEntry(self,width=250,height=50,corner_radius=3)
        self.text_feild.grid(row=0,column=0,padx=5,pady=10)

        self.send_button = ctk.CTkButton(self,width=75,height=50,corner_radius=3,text="send",command=self.Send_Text_Client)
        self.send_button.grid(row=0, column=1,padx=5,pady=10)

    def enable_panel(self):
        for widget in self.winfo_children():
            if hasattr(widget, 'configure'):
                widget.configure(state="normal")

    def disable_panel(self):
        for widget in self.winfo_children():
            if hasattr(widget, 'configure'):
                widget.configure(state="disabled")
        self.stop()

    def Send_Text_Client(self):
        text = self.text_feild.get()

        self.user.send_writing_client(text)

        self.text_feild.delete(0,ctk.END)

    def stop(self):
        self.text_feild.delete(0,ctk.END)