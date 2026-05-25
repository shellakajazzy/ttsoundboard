[![Entangled badge](https://img.shields.io/badge/entangled-Use%20the%20source!-%2300aeff)](https://entangled.github.io/)

# TTSoundboard
My TTS and soundboard solution.

It uses a server at the core that accepts HTTP API calls and clients will connect to through a TCP socket that will stream the generated TTS or soundboard audio realtime.
Although this means that any client can make an API call to the server, I am only planning it to use on my private Tailscale meshnet VPN.
I may or may not make the server require an API key to respond to requests to further address this, but for the scope of this project I doubt I will have to until I have implemented the features I want.

In this repo, I have provided an example Discord client for both making API calls and playing back the generated audio in a VC.

## TTSoundboard Server
This is the server that will receive HTTP API calls and from which clients will connect to have audio streamed to them.

[`./ttsoundboard_server.py`](./ttsoundboard_server.py):
``` {.python #ttsoundboard-server file="ttsoundboard_server.py"}
<<ttsoundboard-imports>>
<<ttsoundboard-globals>>
<<ttsoundboard-classes>>
```

### Globals
I might change these, so I put them here to be easily accessible.

`ttsoundboard-globals`:
```{.python #ttsoundboard-globals}
HTTP_PORT = 6973
TCP_PORT = 5212
```

### API Handler
The API is handled through an HTTP server that queues.

This requires the `http` module to start the server and the `json` module to encode and decode requests and responses.

`ttsoundboard-imports`:
``` {.python #ttsoundboard-imports}
import http
import http.server
import json
```

Next, the `APIHandler` class needs to be setup to handle

`ttsoundboard-classes`:
``` {.python #ttsoundboard-classes}
class APIHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        match self.path:
            <<ttsoundboard-api-cases>>
            case _: self.send_error(400)
    def respond(self, response, obj = {}):
        data = json.dumps(obj).encode()
        self.send_response(response)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
```

### TCP Audio Streamer
The TCP server is running asynchronously from how API requests are processed.

This requires the following modules.

`ttsoundboard-imports`:
``` {.python #ttsoundboard-imports}
import socket
import threading
```

Additionally, in order to save clients and prepare them, we need some global variables.

`ttsoundboard-globals`:
``` {.python #ttsoundboard-globals}
clients = []
clients_lock = threading.Lock()
```

Finally, the server needs to be defined.

`ttsoundboard-classes`:
``` {.python #ttsoundboard-classes}
class TCPServer(threading.Thread):
    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", TCP_PORT))
        s.listen()
        print(f"TCP server started on 0.0.0.0:{TCP_PORT}")

        while True:
            conn, addr = s.accept()
            print(f"Client connected: {addr}")
            with clients_lock: clients.append(conn)
```

### Audio Thread
This class is what generates and streams audio over to the clients.

It needs a queue to handle the arguments sent to generate the audio, which is handled through a subprocess.

`ttsoundboard-imports`:
``` {.python #ttsoundboard-imports}
import queue
import subprocess
```

Additionally, events need to be created that will tell the thread to pause, resume, or stop and clear the playback of audio.

`ttsoundboard-globals`:
``` {.python #ttsoundboard-globals}
audio_arg_queue = queue.Queue()
stop_event = threading.Event()
stop_event.clear()
pause_event = threading.Event()
pause_event.set()
```

`ttsoundboard-classes`:
``` {.python #ttsoundboard-classes}
class AudioThread(threading.Thread):
    def run(self):
        while True:
            audio_arg = audio_arg_queue.get()
            if audio_arg is None: continue
            stop_event.clear()
            self.stream_audio_arg(audio_arg)
    <<ttsoundboard-audiothread>>
```

This class provides the method to stream audio to all the clients as chunks.

`ttsoundboard-audiothread`:
``` {.python #ttsoundboard-audiothread}
def broadcast(self, chunk):
    with clients_lock:
        dead = []
        for c in clients:
            try: c.sendall(chunk)
            except: dead.append(c)
        for d in dead: clients.remove(d)
```

Then, there needs to be a method to process the audio argument, generate the audio to stream, and then also process if the audio generation should be stopped or paused.

`ttsoundboard-audiothread`:
``` {.python #ttsoundboard-audiothread}
def stream_audio_arg(self, audio_arg):
    proc = subprocess.Popen(
        [
            "espeak-ng",
            "--stdout",
            audio_arg
        ],
        stdout = subprocess.PIPE,
        stderr = subprocess.DEVNULL
    )

    try:
        while True:
            if stop_event.is_set():
                proc.kill()
                break

            pause_event.wait()

            chunk = proc.stdout.read(1024)
            if not chunk: break

            self.broadcast(chunk)
    finally:
        proc.stdout.close()
        proc.wait()
```

### Start Server
Finally, these methods need to be run.

`ttsoundboard-server`:
``` {.python #ttsoundboard-server}
if __name__ == "__main__":
    AudioThread(daemon=True).start()
    TCPServer(daemon=True).start()

    api_server = http.server.HTTPServer(("0.0.0.0", HTTP_PORT), APIHandler)
    print(f"HTTP API server on 0.0.0.0:{HTTP_PORT}")
    api_server.serve_forever()
```

### Pause Command

`ttsoundboard-api-cases`:
``` {.python #ttsoundboard-api-cases}
case "/pause":
    pause_event.set()
    self.respond(200, {"status": "paused"})
```

### Pause Command

`ttsoundboard-api-cases`:
``` {.python #ttsoundboard-api-cases}
case "/resume":
    pause_event.clear()
    self.respond(200, {"status": "playing"})
```

### Stop Command

`ttsoundboard-api-cases`:
``` {.python #ttsoundboard-api-cases}
case "/stop":
    stop_event.set()
    while not audio_arg_queue.empty():
        try: audio_arg_queue.get_nowait()
        except queue.Empty: break
    self.respond(200, {"status": "stopped"})
```

### Speak Command

`ttsoundboard-api-cases`:
``` {.python #ttsoundboard-api-cases}
case "/speak":
    audio_arg = body.decode()
    audio_arg_queue.put(audio_arg)
    self.respond(200, {"status": "queued", "audio_arg": audio_arg})
```
