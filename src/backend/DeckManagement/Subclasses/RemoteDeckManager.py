from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import threading
from datetime import datetime

from src.backend.DeckManagement.DeckController import DeckController
from src.backend.DeckManagement.Subclasses.RemoteDeck import RemoteDeck
from src.backend.DeckManagement.Subclasses.RemoteDecksLocalServerHandler import create_handler

PORT = 8765
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckManager import DeckManager

class RemoteDeckManager:
    def __init__(self, deck_manager: "DeckManager"):
        self.deck_manager = deck_manager
        self.deck_controllers = []
        self.httpd = None
        self.server_thread = None
        self.handler_class = None
        self._is_running = False

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        # Start the webserver
        self.start_server()

        deck = RemoteDeck(self, serial_number="remote-deck-1", deck_type="Remote Deck 1")
        self.deck_controllers.append(DeckController(self.deck_manager, deck))

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        # Stop the webserver
        self.stop_server()

        self.deck_controllers.clear()
    

    def start_server(self):
        """Start the HTTP server in a separate thread."""
        server_address = ('0.0.0.0', PORT)
        # Create a handler class with access to this RemoteDeckManager instance
        self.handler_class = create_handler(self)
        self.httpd = HTTPServer(server_address, self.handler_class)

        print("=" * 60)
        print("Local Network Python Server")
        print("=" * 60)
        print(f"Server started on port {PORT}")
        print(f"Server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nEndpoints:")
        print(f"  GET  http://localhost:{PORT}/status")
        print(f"  GET  http://localhost:{PORT}/images")
        print(f"  GET  http://localhost:{PORT}/images/{{button_id}}")
        print(f"  POST http://localhost:{PORT}/message")
        print(f"  POST http://localhost:{PORT}/button")
        print("\nWaiting for connections from Next.js web app...")
        print("Press Ctrl+C to stop the server")
        print("=" * 60)
        print()

        # Run server in a separate thread so it doesn't block
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

    def stop_server(self):
        """Stop the HTTP server."""
        if self.httpd:
            print("\n\nStopping Remote Deck Server...")
            self.httpd.shutdown()
            self.httpd = None
            if self.server_thread:
                self.server_thread.join(timeout=5)
                self.server_thread = None

    def on_key_event(self, key: int, state: bool):
        print(f"Remote Deck Manager: Key event: {key}, {state}")
        print(self.deck_controllers)
        for deck_controller in self.deck_controllers:
            deck_controller.deck.deck.key_callback(deck_controller.deck.deck, key, state)
    
    def send_button_image(self, button_id: int, image):
        """
        Send a PIL image for a specific button to the browser.
        
        Args:
            button_id: The button identifier (e.g., row * 5 + col)
            image: PIL Image object
        """
        if self.handler_class:
            self.handler_class.send_button_image(button_id, image)