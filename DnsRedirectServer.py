from http.server import HTTPServer, BaseHTTPRequestHandler
import ssl
import threading
import os
class RedirectHandler(BaseHTTPRequestHandler):
    def handle_request(self):
        try:
            print(f"\n=== Incoming Request ===")
            print(f"Client Address: {self.client_address}")
            print(f"Request Path: {self.path}")
            print(f"Headers: {self.headers}")

            # Send a basic response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Connection', 'close')  # Important for some clients
            self.end_headers()

            response = """
            <html>
                <head><title>Connection Successful</title></head>
                <style>
                        body {
                            font-family: Arial, sans-serif;
                            margin: 0;
                            padding: 0;
                            background-color: #f4f4f9;
                            color: #333;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                        }
                        div {
                            padding: 20px;
                            text-align: center;
                        }
                        h1 {
                            color: #4CAF50;
                            font-size: 2em;
                        }
                        p {
                            font-size: 1.2em;
                        }
                    </style>
                <body>
                    <div><h1>Connection Established</h1></div>
                    <div><p>The DNS redirection was successful!</p></div>
                    <a href="/download" class="download-button">Download File</a>
                </body>
            </html>
            """
            self.wfile.write(response.encode('utf-8'))
            print("Response sent successfully")

        except Exception as e:
            print(f"Error handling request: {e}")
            # Try to send an error response if possible
            try:
                self.send_error(500, str(e))
            except:
                pass

    def do_GET(self):
        if self.path == "/download":
            file_path = "C:\\Users\\keyna\\PycharmProjects\\pythonProject1\\update\\lastMAIN.py"
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="lastMAIN.py"')
                self.end_headers()
                with open(file_path, 'rb') as file:
                    self.wfile.write(file.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File not found.")
        else:
            self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_HEAD(self):
        self.handle_request()


class RedirectServer:
    def __init__(self, host='0.0.0.0', port=80):
        self.host = host
        # Remove port from host if accidentally included
        if ':' in str(host):
            self.host = host.split(':')[0]
        self.port = port
        self.server = None
        self.server_thread = None
        print(f"Initializing server on {self.host}:{self.port}")

    def start(self):
        try:
            # Try port 80 first
            try:
                self.server = HTTPServer((self.host, self.port), RedirectHandler)
                print(f"Server started on port {self.port}")
            except (PermissionError, OSError):
                # If port 80 fails, try 8080
                self.port = 8080
                print("Port 80 not available, trying 8080...")
                self.server = HTTPServer((self.host, self.port), RedirectHandler)
                print("Server started on port 8080")

            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

        except Exception as e:
            print(f"Failed to start server: {e}")
            # Don't raise the exception, just log it
            return False
        return True

    def stop(self):
        try:
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                print("Redirect server stopped")
        except Exception as e:
            print(f"Error stopping server: {e}")

    def test_server(self):
        """Test if the server is responding"""
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))
            print(f"Server test successful - listening on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Server test failed: {e}")
            return False
        finally:
            sock.close()