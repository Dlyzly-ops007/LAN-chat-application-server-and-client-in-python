"""LAN chat relay server.

Broadcasts every chat message to all connected clients. Messages on the wire
are newline-delimited JSON: each is a single JSON object followed by "\n",
which gives TCP's byte stream a boundary to split on (a bare recv() can
return partial or merged messages under load).
"""

import socket
import threading
import json
from datetime import datetime

HOST = "0.0.0.0"  # bind on all interfaces so other machines on the LAN can reach it
PORT = 9999

clients = []  # list of (socket, nickname) tuples
clients_lock = threading.Lock()


def send_json(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))


def recv_json_lines(sock):
    # Yields one parsed JSON object per line. Buffering here because a
    # single recv() might give us zero, one, or several messages at once.
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


def current_time():
    return datetime.now().strftime("%H:%M:%S")


def system_message(text):
    return {"type": "system", "text": text, "time": current_time()}


def broadcast(obj):
    with clients_lock:
        for sock, _nick in clients:
            try:
                send_json(sock, obj)
            except OSError:
                pass  # dead socket, its own handle_client thread will clean it up


def handle_client(client_socket, nickname, msg_stream):
    try:
        for msg in msg_stream:
            if msg.get("type") == "chat":
                text = msg.get("text", "")
                print(f"{nickname}: {text}")
                broadcast({
                    "type": "chat",
                    "nick": nickname,
                    "text": text,
                    "time": current_time(),
                })
    except (OSError, json.JSONDecodeError):
        pass
    finally:
        with clients_lock:
            clients[:] = [(s, n) for s, n in clients if s is not client_socket]
        broadcast(system_message(f"{nickname} left the chat"))
        client_socket.close()


def setup_client(client_socket, address):
    # Handshake happens on its own thread per connection now, so a client
    # sitting at the nickname prompt can't block accept_loop from accepting
    # anyone else. This used to run inline in accept_loop, which serialized
    # every incoming connection behind whoever was currently typing a name.
    msg_stream = recv_json_lines(client_socket)
    try:
        send_json(client_socket, {"type": "nick_request"})
        nick_msg = next(msg_stream)
        nickname = nick_msg.get("nick", "unknown")
    except (OSError, StopIteration, json.JSONDecodeError):
        client_socket.close()
        return

    with clients_lock:
        clients.append((client_socket, nickname))

    print(f"[+] Nickname is {nickname}")
    broadcast(system_message(f"{nickname} joined the chat"))

    handle_client(client_socket, nickname, msg_stream)


def get_lan_ip():
    # returns 127.0.1.1 on Linux.
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def accept_loop(server_socket):
    while True:
        client_socket, address = server_socket.accept()
        print(f"[+] Connected with {address}")
        threading.Thread(
            target=setup_client, args=(client_socket, address), daemon=True
        ).start()


def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[+] Server listening on {HOST}:{PORT}")
    print(f"[+] LAN IP: {get_lan_ip()}")
    accept_loop(server_socket)


if __name__ == "__main__":
    main()
