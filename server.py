import http.server
import socketserver

PORT = 8159  # Changed from 8158
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"🔄 Serving frontend at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    httpd.serve_forever()
