# ~/~ begin <<README.md#ttsoundboard-server>>[init]
# ~/~ begin <<README.md#ttsoundboard-imports>>[init]
import http
import http.server
import json
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-imports>>[1]
import socket
import threading
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-imports>>[2]
import queue
import subprocess
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-globals>>[init]
HTTP_PORT = 6973
TCP_PORT = 5212
FRAME_SIZE = 3840
TTS_VOICE = "en+m1"
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-globals>>[1]
clients = []
clients_lock = threading.Lock()
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-globals>>[2]
audio_arg_queue = queue.Queue()
pause_event = threading.Event()
pause_event.set()
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-classes>>[init]
class APIHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        match self.path:
            # ~/~ begin <<README.md#ttsoundboard-api-cases>>[init]
            case "/pause":
                pause_event.clear()
                self.respond(200, {"status": "paused"})
            # ~/~ end
            # ~/~ begin <<README.md#ttsoundboard-api-cases>>[1]
            case "/resume":
                pause_event.set()
                self.respond(200, {"status": "playing"})
            # ~/~ end
            # ~/~ begin <<README.md#ttsoundboard-api-cases>>[2]
            case "/stop":
                pause_event.clear()
                while not audio_arg_queue.empty():
                    try: audio_arg_queue.get_nowait()
                    except queue.Empty: break
                pause_event.set()
                self.respond(200, {"status": "stopped"})
            # ~/~ end
            # ~/~ begin <<README.md#ttsoundboard-api-cases>>[3]
            case "/speak":
                audio_arg = body.decode()
                audio_arg_queue.put(audio_arg)
                self.respond(200, {"status": "queued", "audio_arg": audio_arg})
            # ~/~ end
            # ~/~ begin <<README.md#ttsoundboard-api-cases>>[4]
            case "/voice":
                global TTS_VOICE
                TTS_VOICE = body.decode()
                self.respond(200, {"status": "voice changed", "voice": TTS_VOICE})
            # ~/~ end
            case _: self.send_error(400)
    def respond(self, response, obj = {}):
        data = json.dumps(obj).encode()
        self.send_response(response)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-classes>>[1]
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
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-classes>>[2]
class AudioThread(threading.Thread):
    def run(self):
        while True:
            audio_arg = audio_arg_queue.get()
            if audio_arg is None: continue
            self.stream_audio_arg(audio_arg)
    # ~/~ begin <<README.md#ttsoundboard-audiothread>>[init]
    def broadcast(self, chunk):
        with clients_lock:
            dead = []
            for c in clients:
                print(f"Sending information to client {c}")
                try: c.sendall(chunk)
                except Exception as e:
                    dead.append(c)
                    print(f"Could not send to client {c} because {str(e)}")
    # ~/~ end
    # ~/~ begin <<README.md#ttsoundboard-audiothread>>[1]
    def stream_audio_arg(self, audio_arg):
        global TTS_VOICE
        proc = subprocess.Popen(
            [
                "espeak-ng",
                "-v", TTS_VOICE,
                "--stdout",
                audio_arg
            ],
            stdout = subprocess.PIPE,
            stderr = subprocess.DEVNULL
        )
    
        try:
            while True:
                pause_event.wait()
    
                chunk = proc.stdout.read(FRAME_SIZE)
                if not chunk: break
    
                self.broadcast(chunk)
        finally:
            proc.stdout.close()
            proc.wait()
    # ~/~ end
# ~/~ end
# ~/~ end
# ~/~ begin <<README.md#ttsoundboard-server>>[1]
if __name__ == "__main__":
    AudioThread(daemon=True).start()
    TCPServer(daemon=True).start()

    api_server = http.server.HTTPServer(("0.0.0.0", HTTP_PORT), APIHandler)
    print(f"HTTP API server on 0.0.0.0:{HTTP_PORT}")
    api_server.serve_forever()
# ~/~ end
