
# 🗨️ LAN Chat App (Python)

A simple LAN-based chat application built in Python.  
It uses **socket** and **threading** for server-client communication and **Tkinter** for the graphical user interface.

This project lets multiple clients on the same network chat with each other via a central server.

---

## 🚀 Features
- Multiple clients can connect to a single server.
- Real-time messaging between clients.
- GUI built with Tkinter.
- Easy to configure for LAN use.

---

## 📦 Requirements
This app uses only Python’s standard libraries except for Tkinter (which comes bundled with most Python installations).

- Python 3.x
- `tkinter` (usually preinstalled)
- No third-party modules required.

Check if Tkinter is installed by running:
bash
`python -m tkinter`

🌐 Using Over a LAN

To use across multiple devices on the same network:

Find the Server Machine’s Local IP
On the server machine:

`ipconfig`   # Windows
`ifconfig`   # Linux/Mac


Look for an address like 192.168.x.x.

Update HOST in All Files
Open server_chat.py, client1_chat.py, and client2_chat.py and change:

HOST = '127.0.0.1'
to:
HOST = '192.168.x.x'   # your server machine’s IP

Run the Server and Clients
Start the server on the host machine.
Start the client scripts on other machines.
Make sure all machines are on the same Wi-Fi/LAN.
You’re now chatting over the network!
