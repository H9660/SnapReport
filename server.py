#!/usr/bin/env python3
"""
SnapReport Backend Server
Serves the React SPA and handles PDF generation requests.
"""
import os
import sys
import json
import tempfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Add our directory to path
sys.path.insert(0, os.path.dirname(__file__))
from generate_report import generate_pdf

HTML_FILE = os.path.join(os.path.dirname(__file__), "index.html")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.serve_file(HTML_FILE, "text/html")
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/generate":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            zip_code   = (body.get("zip_code") or "").strip()
            agent_name = (body.get("agent_name") or "").strip() or "Your Agent"
            month      = (body.get("month") or "").strip() or None

            if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
                self.send_json({"error": "Please enter a valid 5-digit ZIP code."}, 400)
                return

            try:
                out_path = os.path.join(tempfile.gettempdir(),
                                        f"snapreport_{zip_code}.pdf")
                generate_pdf(zip_code, agent_name, out_path, month)
                with open(out_path, "rb") as f:
                    pdf_bytes = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="SnapReport_{zip_code}.pdf"')
                self.send_header("Content-Length", str(len(pdf_bytes)))
                self.end_headers()
                self.wfile.write(pdf_bytes)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
        else:
            self.send_error(404)

    def serve_file(self, path, mime):
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)

    def send_json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7654))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"SnapReport server running on http://localhost:{port}")
    server.serve_forever()
