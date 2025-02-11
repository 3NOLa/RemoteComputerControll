from AdminNetwork import RemoteDesktopClient
import customtkinter as ctk

class KeysFrame(ctk.CTkFrame):
    def __init__(self,master, user : RemoteDesktopClient, width=250, height=350, **kwargs):
        super().__init__(master, width=width, height=height,corner_radius=10,fg_color="#6495ED" ,**kwargs)
        self.user = user

        self.text_feild = ctk.CTkTextbox(self,width=250,height=325,corner_radius=16,activate_scrollbars=True,scrollbar_button_color="#FFCC70",
                                         border_width=5,border_color="#FFCC70",fg_color="black",text_color="white")

        self.text_feild.place(relx=0.5,rely=0.5,anchor="center")
        self.text_feild.pack(expand=True,pady=10,padx=10)
        self.text_feild.insert("0.0","Client text Below\n")

    def enable_panel(self):
        for widget in self.winfo_children():
            if hasattr(widget, 'configure'):
                widget.configure(state="normal")

    def disable_panel(self):
        for widget in self.winfo_children():
            if hasattr(widget, 'configure'):
                widget.configure(state="disabled")
        self.stop()

    def enter_new_text(self,text : str):
        if text == "Key.backspace":
            self.text_feild.delete("insert -1 chars","end")
        else:
            self.text_feild.insert("end",text)

    def stop(self):
        self.text_feild.delete("0.0","end")