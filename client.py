"""LAN chat client (tkinter GUI).

Run this file once per user to test a multi-person chat against server.py.
Uses the same newline-delimited JSON protocol as the server: every message
on the wire is one JSON object followed by "\n".
"""

import socket
import threading
import json
import sys
import tkinter
from tkinter import simpledialog, messagebox

PALETTE = ["#e8ff48", "#4fffb0", "#ff4f6b", "#5aa9ff", "#ff9f4f", "#c58fff"]

DARK = {"bg": "#0f0f11", "bg2": "#1a1a20", "txt": "#e8e8ec", "dim": "#555560"}
LIGHT = {"bg": "#f5f5f7", "bg2": "#ffffff", "txt": "#1a1a20", "dim": "#8a8a90"}


def send_json(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))


def recv_json_lines(sock):
    # Yields one parsed JSON object per line, same idea as the server side.
    buffer = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            return
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            if line.strip():
                yield json.loads(line.decode("utf-8"))


def color_for(nick):
    # Using sum-of-ordinals instead of hash() because hash() on strings is
    # salted per process (PYTHONHASHSEED), so the same nickname would get a
    # different color every run otherwise.
    return PALETTE[sum(ord(c) for c in nick) % len(PALETTE)]


class Client:
    def __init__(self):
        self.sock = None
        self.nickname = None
        self.win = None
        self.running = True
        self.theme = DARK
        self.themed = []  # widgets we need to re-color when the theme toggles
        self.gui_ready = threading.Event()

        self.connect()
        self.handshake_nickname()

        threading.Thread(target=self.build_gui).start()
        threading.Thread(target=self.receive_loop).start()

    # startup: get server details, connect, then swap nicknames with the server

    def connect(self):
        self.root = tkinter.Tk()
        self.root.withdraw()

        ip = simpledialog.askstring("Server", "Server IP:", initialvalue="0.0.0.0", parent=self.root)
        if not ip:
            self.root.destroy()
            sys.exit()

        port_str = simpledialog.askstring("Server", "Port:", initialvalue="9999", parent=self.root)
        if not port_str:
            self.root.destroy()
            sys.exit()

        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Invalid port", f"'{port_str}' is not a valid port number.")
            self.root.destroy()
            sys.exit()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((ip, port))
        except OSError as e:
            messagebox.showerror("Connection failed", f"Could not connect to {ip}:{port}\n({e})")
            self.root.destroy()
            sys.exit()

    def handshake_nickname(self):
        self.msg_stream = recv_json_lines(self.sock)
        try:
            next(self.msg_stream)  # expecting {"type": "nick_request"}
        except (StopIteration, OSError):
            messagebox.showerror("Connection error", "Server closed the connection unexpectedly.")
            self.root.destroy()
            sys.exit()

        self.nickname = simpledialog.askstring("Nickname", "Enter your name:", parent=self.root) or "Anonymous"

        try:
            send_json(self.sock, {"type": "nick_response", "nick": self.nickname})
        except OSError:
            messagebox.showerror("Connection error", "Lost connection to the server.")
            self.root.destroy()
            sys.exit()

        self.root.destroy()

    # building the actual chat window

    def build_gui(self):
        self._build_widgets()
        self.gui_ready.set()
        self.win.mainloop()

    def _build_widgets(self):
        self.win = tkinter.Tk()
        self.win.title(f"LAN Chat - {self.nickname}")
        self.win.geometry("520x640")
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

        top_bar = tkinter.Frame(self.win)
        top_bar.pack(fill="x")
        self.register_themed(top_bar, bg="bg")

        chat_label = tkinter.Label(top_bar, text="LAN Chat", font=("Arial", 18, "bold"))
        chat_label.pack(side="left", padx=16, pady=10)
        self.register_themed(chat_label, bg="bg", fg="txt")

        theme_button = tkinter.Button(top_bar, text="Toggle theme", relief="flat", bd=0, command=self.toggle_theme)
        theme_button.pack(side="right", padx=16, pady=10)
        self.register_themed(theme_button, bg="bg2", fg="txt")

        # the message list is a Frame inside a Canvas so it can scroll -
        # tkinter doesn't have a native scrollable frame widget
        canvas_frame = tkinter.Frame(self.win)
        canvas_frame.pack(fill="both", expand=True, padx=8, pady=4)
        self.register_themed(canvas_frame, bg="bg")

        self.canvas = tkinter.Canvas(canvas_frame, highlightthickness=0)
        self.scrollbar = tkinter.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.messages_frame = tkinter.Frame(self.canvas)

        self.messages_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.messages_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind_all("<Button-4>", self.on_mousewheel)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.register_themed(self.canvas, bg="bg")
        self.register_themed(self.messages_frame, bg="bg")

        input_frame = tkinter.Frame(self.win)
        input_frame.pack(fill="x", padx=8, pady=8)
        self.register_themed(input_frame, bg="bg")

        self.input_area = tkinter.Text(input_frame, height=3, wrap="word", font=("Arial", 11))
        self.input_area.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.input_area.bind("<Return>", self.on_return)
        self.input_area.bind("<Shift-Return>", self.on_shift_return)
        self.register_themed(self.input_area, bg="bg2", fg="txt")

        self.send_button = tkinter.Button(input_frame, text="Send", font=("Arial", 12), command=self.write)
        self.send_button.pack(side="right")
        self.register_themed(self.send_button, bg="bg2", fg="txt")

        self.apply_theme()

    # theming - just tracks widgets we've styled so we can restyle them on toggle

    def register_themed(self, widget, bg=None, fg=None):
        self.themed.append((widget, bg, fg))
        if bg:
            widget.config(bg=self.theme[bg])
        if fg:
            widget.config(fg=self.theme[fg])

    def apply_theme(self):
        for widget, bg_role, fg_role in self.themed:
            if bg_role:
                widget.config(bg=self.theme[bg_role])
            if fg_role:
                widget.config(fg=self.theme[fg_role])
        self.win.config(bg=self.theme["bg"])
        self.input_area.config(insertbackground=self.theme["txt"])
        self.scrollbar.config(bg=self.theme["bg2"], troughcolor=self.theme["bg"])

    def toggle_theme(self):
        self.theme = LIGHT if self.theme is DARK else DARK
        self.apply_theme()

    # receiving messages from the server

    def receive_loop(self):
        self.gui_ready.wait()
        try:
            for msg in self.msg_stream:
                if not self.running:
                    break
                # hop back onto the GUI thread before touching any widgets,
                # tkinter isn't thread-safe
                self.win.after(0, self.handle_incoming, msg)
        except Exception:
            pass
        if self.running:
            self.running = False
            self.win.after(0, self.handle_disconnect)

    def handle_incoming(self, msg):
        msg_type = msg.get("type")
        if msg_type == "chat":
            self.render_chat_message(msg.get("nick", "?"), msg.get("text", ""), msg.get("time", ""))
        elif msg_type == "system":
            self.render_system_message(msg.get("text", ""))

    def handle_disconnect(self):
        self.render_system_message("Disconnected from server.")
        self.send_button.config(state="disabled")
        self.input_area.config(state="disabled")

    # rendering messages as bubbles

    def render_chat_message(self, nick, text, time_str):
        was_at_bottom = self.is_scrolled_to_bottom()
        is_own = nick == self.nickname
        bubble_color = color_for(nick)
        anchor = "e" if is_own else "w"

        row = tkinter.Frame(self.messages_frame)
        row.pack(fill="x", pady=4, padx=8)
        self.register_themed(row, bg="bg")

        inner = tkinter.Frame(row)
        inner.pack(anchor=anchor)
        self.register_themed(inner, bg="bg")

        if not is_own:
            name_label = tkinter.Label(inner, text=nick, font=("Arial", 9, "bold"), fg=bubble_color)
            name_label.pack(anchor="w")
            self.register_themed(name_label, bg="bg")

        bubble = tkinter.Label(
            inner, text=text, bg=bubble_color, fg="#1a1a20",
            font=("Arial", 11), wraplength=320, justify="left", padx=10, pady=6,
        )
        bubble.pack(anchor=anchor)

        time_label = tkinter.Label(inner, text=time_str, font=("Arial", 8))
        time_label.pack(anchor=anchor)
        self.register_themed(time_label, bg="bg", fg="dim")

        self.finish_new_message(was_at_bottom)

    def render_system_message(self, text):
        was_at_bottom = self.is_scrolled_to_bottom()

        row = tkinter.Frame(self.messages_frame)
        row.pack(fill="x", pady=6)
        self.register_themed(row, bg="bg")

        label = tkinter.Label(row, text=text, font=("Arial", 9, "italic"))
        label.pack()
        self.register_themed(label, bg="bg", fg="dim")

        self.finish_new_message(was_at_bottom)

    def finish_new_message(self, was_at_bottom):
        self.messages_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if was_at_bottom:
            self.canvas.yview_moveto(1.0)

    def is_scrolled_to_bottom(self):
        _top, bottom = self.canvas.yview()
        return bottom >= 0.999

    # sending

    def write(self):
        text = self.input_area.get("1.0", "end").strip()
        if not text:
            return
        self.input_area.delete("1.0", "end")
        try:
            send_json(self.sock, {"type": "chat", "nick": self.nickname, "text": text})
        except OSError:
            if self.running:
                self.running = False
                self.handle_disconnect()

    def on_return(self, _event):
        self.write()
        return "break"

    def on_shift_return(self, _event):
        self.input_area.insert(tkinter.INSERT, "\n")
        return "break"

    # misc UI events

    def on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_close(self):
        self.running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
        self.win.destroy()


if __name__ == "__main__":
    Client()
