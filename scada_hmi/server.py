"""
Simple HTTP Web Server for 220kV SCADA HMI Dashboard
Run: python3 scada_hmi/server.py
Author: Tejanshu Dabariya
"""

import http.server
import socketserver
import os
import webbrowser

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def start_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"===========================================================")
        print(f"  220kV SWITCHYARD DIGITAL-TWIN SCADA DASHBOARD ONLINE")
        print(f"  Access URL: http://localhost:{PORT}")
        print(f"===========================================================")
        httpd.serve_forever()

if __name__ == "__main__":
    start_server()
