import socket
import threading

# Server setup
HOST = '127.0.0.1'
PORT = 9999

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

clients = []
nicknames = []

def broadcast(message):
    for client in clients:
        client.send(message)

def handle_client(client):
    while True:
        try:
            message = client.recv(1024)
            nickname = nicknames[clients.index(client)]
            print(f"{nickname}: {message.decode('utf-8')}")
            broadcast(message)
        except:
            index = clients.index(client)
            client.close()
            nickname = nicknames[index]
            clients.remove(client)
            nicknames.remove(nickname)
            broadcast(f"{nickname} left the chat.\n".encode('utf-8'))
            break

def receive():
    print(f"[+] Server listening on {HOST}:{PORT}")
    while True:
        client, address = server.accept()
        print(f"[+] Connected with {address}")

        client.send("NICK".encode('utf-8'))
        nickname = client.recv(1024).decode('utf-8')

        nicknames.append(nickname)
        clients.append(client)

        print(f"[+] Nickname is {nickname}")
        broadcast(f"{nickname} joined the chat!\n".encode('utf-8'))
        client.send("Connected to server!\n".encode('utf-8'))

        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()

receive()

