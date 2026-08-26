# lan-chat-app

A real-time LAN group chat: a threaded TCP relay server and a tkinter GUI client. Run the server on one machine, run the client on that machine (or any other machine on the same network) as many times as you have users.

## Architecture

**Server (`server.py`)** is a plain relay hub — it doesn't store any chat history, it just broadcasts every message it receives to every connected client. It:
- Binds to `0.0.0.0` (all network interfaces) so other devices on the LAN can actually reach it — not just `localhost`
- Runs one thread per connected client (`handle_client`), so a slow or dead connection on one client doesn't block anyone else
- Keeps the connected-client list behind a `threading.Lock`, since multiple client threads can connect or disconnect at the same instant
- Prints its own LAN IP on startup (via a UDP "connect" probe to 8.8.8.8 — no actual traffic sent, it's just a trick to ask the OS which local interface would be used) so you know what to type into a client on another machine

**Client (`client.py`)** is a single file — run it once per user. On launch it asks for the server IP, port, and your nickname, then opens the chat window. No hardcoded connection details.

### Wire protocol

Every message sent over the socket is a single JSON object followed by `\n`. This fixes a real limitation of raw TCP: `recv()` can return partial or merged messages under load, since TCP is just a byte stream with no built-in message boundaries — the newline gives both sides a place to split.

```json
{"type": "chat", "nick": "Dly", "text": "hey", "time": "14:32:05"}
{"type": "system", "text": "Dly joined the chat", "time": "14:32:00"}
{"type": "nick_request"}
{"type": "nick_response", "nick": "Dly"}
```

Timestamps are generated server-side, so everyone's chat log stays consistent even if individual machines' clocks are off.

## Features

- Real LAN chat — no hardcoded server address, prompted on client launch
- Per-user colored message bubbles (deterministic — same nickname always gets the same color, computed independently by every client, no server coordination needed)
- Timestamps on every message
- Dark/light theme toggle
- Auto-scroll that respects manual scrolling — if you've scrolled up to read history, new messages won't yank the view back down
- Clean disconnect handling — join/leave system messages, graceful error dialogs on failed connections instead of crashes

## Setup

No external dependencies — pure Python standard library (`socket`, `threading`, `json`, `tkinter`, `datetime`).

Start the server:
```bash
python server.py
```

Start one or more clients (same machine or any other machine on the LAN):
```bash
python client.py
```
Enter the server's IP (shown in the server's terminal output) and port when prompted, then your nickname.

## Scope

This is a single shared group chat — no rooms, no private messages, no authentication, no persisted chat history, and no file transfer. Intentionally kept simple.

## License

PolyForm Noncommercial 1.0.0 — see [LICENSE](LICENSE). Free for personal, educational, and noncommercial use.
