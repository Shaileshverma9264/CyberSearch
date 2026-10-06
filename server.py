#!/usr/bin/env python3
import json
import os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib import parse, request, error

HOST = "0.0.0.0"
PORT = 8000
ROOT = os.path.dirname(os.path.abspath(__file__))
REMOTE_API = "https://deeposint.felixrdx.xyz/api/developer/Cyb3rB4nn3r/"
API_KEY = "58c49cb2dbbf8dc53009705ecd7c4132"


class ProxyHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/search"):
            self.handle_search()
            return
        super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/search"):
            self.handle_search()
            return
        super().do_POST()

    def handle_search(self):
        query = None
        if "?" in self.path:
            parsed = parse.urlsplit(self.path)
            params = parse.parse_qs(parsed.query)
            query = params.get("query", [None])[0]
            api_key = params.get("key", [API_KEY])[0]
        else:
            api_key = API_KEY

        if not query:
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": False, "message": "Missing query"}).encode("utf-8"))
            return

        target_url = f"{REMOTE_API}?{parse.urlencode({'key': api_key, 'query': query})}"
        try:
            req = request.Request(target_url, headers={"User-Agent": "CyberSearch-Proxy/1.0", "Accept": "application/json"})
            with request.urlopen(req, timeout=25) as resp:
                payload = resp.read()
            body = payload.decode("utf-8", errors="replace")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        except Exception as exc:
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            message = {"status": False, "message": f"Proxy request failed: {exc}"}
            self.wfile.write(json.dumps(message).encode("utf-8"))

    def _serve_static(self):
        os.chdir(ROOT)
        return SimpleHTTPRequestHandler.do_GET(self)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer((HOST, PORT), ProxyHandler)
    print(f"CyberSearch server running at http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        httpd.server_close()
