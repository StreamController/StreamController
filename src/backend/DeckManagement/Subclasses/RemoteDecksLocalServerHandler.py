from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
from datetime import datetime
import base64
from io import BytesIO

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.DeckManagement.Subclasses.RemoteDeckManager import RemoteDeckManager
    from PIL import Image

def create_handler(remote_deck_manager: "RemoteDeckManager"):
    """Factory function to create a handler class with access to RemoteDeckManager."""
    
    class RemoteDecksLocalServerHandler(BaseHTTPRequestHandler):
        """Handle HTTP requests from the Next.js client."""
        
        # Store the manager as a class variable
        manager = remote_deck_manager
        
        # Dictionary to store button images {button_id: base64_image_data}
        button_images = {}

        def _set_cors_headers(self):
            """Set CORS headers to allow cross-origin requests."""
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        def _send_json_response(self, status_code, data):
            """Send a JSON response."""
            self.send_response(status_code)
            self._set_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        
        @classmethod
        def send_button_image(cls, button_id: int, image: "Image.Image"):
            """
            Store a PIL image for a specific button to be sent to the browser.
            
            Args:
                button_id: The button identifier (e.g., row * 5 + col)
                image: PIL Image object
            """
            # Convert PIL image to base64-encoded JPEG
            buffered = BytesIO()
            image.save(buffered, format="JPEG")
            img_bytes = buffered.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Store the image data
            cls.button_images[button_id] = {
                'data': f"data:image/jpeg;base64,{img_base64}",
                'timestamp': int(time.time())
            }

        def do_OPTIONS(self):
            """Handle preflight OPTIONS request."""
            self.send_response(200)
            self._set_cors_headers()
            self.end_headers()

        def do_GET(self):
            """Handle GET requests."""
            if self.path == '/status':
                response_data = {
                    'status': 'online',
                    'message': 'Python server is running',
                    'timestamp': int(time.time()),
                    'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                self._send_json_response(200, response_data)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Status check received")
            elif self.path == '/images':
                # Return all button images
                response_data = {
                    'status': 'ok',
                    'images': self.button_images,
                    'timestamp': int(time.time())
                }
                self._send_json_response(200, response_data)
            elif self.path.startswith('/images/'):
                print("/images/")
                # Return a specific button image
                try:
                    button_id = int(self.path.split('/')[-1])
                    if button_id in self.button_images:
                        response_data = {
                            'status': 'ok',
                            'button_id': button_id,
                            'image': self.button_images[button_id],
                            'timestamp': int(time.time())
                        }
                        self._send_json_response(200, response_data)
                    else:
                        self._send_json_response(404, {'error': f'No image found for button {button_id}'})
                except (ValueError, IndexError):
                    self._send_json_response(400, {'error': 'Invalid button ID'})
            else:
                self._send_json_response(404, {'error': 'Not found'})

        def do_POST(self):
            """Handle POST requests."""
            if self.path == '/message':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)

                try:
                    data = json.loads(post_data.decode('utf-8'))
                    received_message = data.get('message', '')

                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Received message: {received_message}")

                    response_text = f"Echo: {received_message} | Received at {datetime.now().strftime('%H:%M:%S')}"

                    response_data = {
                        'status': 'success',
                        'response': response_text,
                        'timestamp': int(time.time())
                    }

                    self._send_json_response(200, response_data)

                except json.JSONDecodeError:
                    self._send_json_response(400, {'error': 'Invalid JSON'})
                except Exception as e:
                    self._send_json_response(500, {'error': str(e)})
            elif self.path == '/button':
                # Handle button press/release events from the client UI
                content_length = int(self.headers.get('Content-Length', '0'))
                post_data = self.rfile.read(content_length)

                try:
                    data = json.loads(post_data.decode('utf-8'))
                    event_type = data.get('type')  # expected: "down" | "up"
                    row = data.get('row')
                    col = data.get('col')

                    # Validate payload
                    if event_type not in {"down", "up"}:
                        self._send_json_response(400, {'error': 'Invalid or missing "type" (use "down" or "up")'})
                        return

                    if not isinstance(row, int) or not isinstance(col, int):
                        self._send_json_response(400, {'error': '"row" and "col" must be integers'})
                        return

                    # Compute a stable button id for convenience (5 columns layout)
                    button_id = row * 5 + col

                    # Log the event to the server console
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Button event: type={event_type} row={row} col={col} id={button_id}")

                    self.manager.on_key_event(button_id, event_type == "down")

                    response_data = {
                        'status': 'ok',
                        'received': {
                            'type': event_type,
                            'row': row,
                            'col': col,
                            'id': button_id,
                        },
                        'timestamp': int(time.time()),
                    }

                    self._send_json_response(200, response_data)

                except json.JSONDecodeError:
                    self._send_json_response(400, {'error': 'Invalid JSON'})
                except Exception as e:
                    self._send_json_response(500, {'error': str(e)})
            else:
                self._send_json_response(404, {'error': 'Not found'})

        def log_message(self, format, *args):
            """Override to customize logging."""
            pass
    
    return RemoteDecksLocalServerHandler