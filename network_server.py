"""
    Network Server for Game03 Multiplayer
    Manages game sessions and player connections
"""

import socket
import threading
import time
import uuid
from network_protocol import NetworkMessage, MessageType
from collections import defaultdict


class NetworkServer:
    """Game server that manages player connections and game state"""
    
    def __init__(self, host='localhost', port=5000, max_players=4):
        self.host = host
        self.port = port
        self.max_players = max_players
        
        self.socket = None
        self.running = False
        self.server_thread = None
        
        # Client management
        self.clients = {}  # {player_id: client_handler}
        self.players_lock = threading.Lock()
        
        # Game state
        self.game_state = {
            'started': False,
            'paused': False,
            'world_owner_id': None,
            'players': {},
            'enemies': {},
            'projectiles': {},
            'enemy_particles': {},
            'shared': {},
            'map': {
                'black': True,
                'incoming_signal': False,
                'version': 0
            },
            'time': 0.0
        }
        self.state_lock = threading.Lock()
        
        # Message queue for broadcasting
        self.broadcast_queue = []
        self.broadcast_lock = threading.Lock()
        
        print(f"[SERVER] Initialized on {host}:{port} with max players: {max_players}")
    
    def start(self):
        """Start the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.max_players)
            self.running = True
            
            self.server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self.server_thread.start()
            
            print(f"[SERVER] Started listening on {self.host}:{self.port}")
        except OSError as e:
            print(f"[SERVER] Failed to start: {e}")
            self.running = False
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        with self.players_lock:
            for player_id, handler in list(self.clients.items()):
                handler.disconnect()
        
        if self.socket:
            self.socket.close()
        
        print("[SERVER] Stopped")
    
    def _server_loop(self):
        """Main server loop - accepts connections"""
        while self.running:
            try:
                client_socket, address = self.socket.accept()
                player_id = str(uuid.uuid4())[:8]
                with self.players_lock:
                    if len(self.clients) >= self.max_players:
                        msg = NetworkMessage(MessageType.ERROR, {'error': 'Server full'})
                        client_socket.send(msg.to_bytes())
                        client_socket.close()
                        continue
                
                handler = ClientHandler(self, client_socket, address, player_id)
                
                with self.players_lock:
                    self.clients[player_id] = handler

                with self.state_lock:
                    if self.game_state['world_owner_id'] is None:
                        self.game_state['world_owner_id'] = player_id
                
                print(f"[SERVER] Player {player_id} connected from {address}")
                
                handler.start()
            
            except OSError:
                if self.running:
                    print("[SERVER] Socket error in accept loop")
            except Exception as e:
                print(f"[SERVER] Error accepting connection: {e}")
    
    def handle_message(self, player_id, message):
        """Process a message from a client"""
        if not message:
            return
        
        if message.msg_type in (MessageType.PLAYER_MOVE, MessageType.PLAYER_STATE):
            with self.state_lock:
                if player_id not in self.game_state['players']:
                    self.game_state['players'][player_id] = {}
                self.game_state['players'][player_id].update(message.data)

            # Forward local player updates to all other clients so remote players move in real time
            self.broadcast_to_all(message, exclude_player=player_id)
        
        elif message.msg_type == MessageType.PLAYER_ATTACK:
            self.broadcast_to_all(message)
        
        elif message.msg_type == MessageType.WORLD_STATE:
            with self.state_lock:
                world_owner_id = self.game_state.get('world_owner_id')

            if player_id != world_owner_id:
                return

            with self.state_lock:
                self.game_state['enemies'].update(message.data.get('enemies', {}))
                self.game_state['projectiles'] = message.data.get('projectiles', {}).copy()
                self.game_state['enemy_particles'] = message.data.get('enemy_particles', {}).copy()
                self.game_state['shared'] = message.data.get('shared', self.game_state.get('shared', {}))
                payload = {
                    'players': self.game_state['players'].copy(),
                    'enemies': self.game_state['enemies'].copy(),
                    'projectiles': self.game_state['projectiles'].copy(),
                    'enemy_particles': self.game_state['enemy_particles'].copy(),
                    'map': self.game_state['map'].copy(),
                    'shared': self.game_state['shared'].copy(),
                    'world_owner_id': world_owner_id,
                }

            world_state = NetworkMessage(
                MessageType.WORLD_STATE,
                payload,
                player_id
            )
            self.broadcast_to_all(world_state, exclude_player=player_id)

        elif message.msg_type == MessageType.MAP_UPDATE:
            with self.state_lock:
                world_owner_id = self.game_state.get('world_owner_id')
                current_version = self.game_state['map'].get('version', 0)
                client_version = message.data.get('version', current_version)

                if client_version == current_version:
                    self.game_state['map']['black'] = message.data.get(
                        'black',
                        self.game_state['map'].get('black', True)
                    )
                    self.game_state['map']['incoming_signal'] = message.data.get(
                        'incoming_signal',
                        self.game_state['map'].get('incoming_signal', False)
                    )
                    self.game_state['map']['version'] = current_version + 1

                payload = {
                    **self.game_state['map'],
                    'world_owner_id': world_owner_id,
                }

            map_update = NetworkMessage(
                MessageType.MAP_UPDATE,
                payload,
                player_id
            )
            if client_version == current_version:
                self.broadcast_to_all(map_update)
            else:
                self.send_to_player(player_id, map_update)

        elif message.msg_type == MessageType.PROJECTILE_SPAWN:
            owner_id = message.data.get('owner_id', player_id)
            projectiles = message.data.get('projectiles', {})

            with self.state_lock:
                stale_ids = [
                    projectile_id
                    for projectile_id, projectile_data in self.game_state['projectiles'].items()
                    if projectile_data.get('owner_id') == owner_id
                ]
                for projectile_id in stale_ids:
                    del self.game_state['projectiles'][projectile_id]
                self.game_state['projectiles'].update(projectiles)

            projectile_update = NetworkMessage(
                MessageType.PROJECTILE_SPAWN,
                {
                    'owner_id': owner_id,
                    'projectiles': projectiles,
                },
                player_id
            )
            self.broadcast_to_all(projectile_update, exclude_player=player_id)

        elif message.msg_type == MessageType.PROJECTILE_DESTROY:
            owner_id = message.data.get('owner_id', player_id)
            destroyed_ids = message.data.get('projectile_ids', [])

            with self.state_lock:
                for projectile_id in destroyed_ids:
                    self.game_state['projectiles'].pop(projectile_id, None)

            projectile_destroy = NetworkMessage(
                MessageType.PROJECTILE_DESTROY,
                {
                    'owner_id': owner_id,
                    'projectile_ids': destroyed_ids,
                },
                player_id
            )
            self.broadcast_to_all(projectile_destroy, exclude_player=player_id)

        elif message.msg_type == MessageType.SYNC_REQUEST:
            self.send_full_state(player_id)
        
        else:
            self.broadcast_to_all(message)
    
    def broadcast_to_all(self, message, exclude_player=None):
        """Send message to all connected clients"""
        with self.players_lock:
            for player_id, handler in list(self.clients.items()):
                if exclude_player and player_id == exclude_player:
                    continue
                handler.send_message(message)

    def send_to_player(self, player_id, message):
        """Send message to a single connected client"""
        with self.players_lock:
            handler = self.clients.get(player_id)
            if handler:
                handler.send_message(message)
    
    def send_full_state(self, player_id):
        """Send complete game state to a player"""
        with self.state_lock:
            payload = {
                'started': self.game_state['started'],
                'paused': self.game_state['paused'],
                'world_owner_id': self.game_state['world_owner_id'],
                'players': self.game_state['players'].copy(),
                'enemies': self.game_state['enemies'].copy(),
                'projectiles': self.game_state['projectiles'].copy(),
                'enemy_particles': self.game_state['enemy_particles'].copy(),
                'map': self.game_state['map'].copy(),
                'shared': self.game_state.get('shared', {}).copy() if isinstance(self.game_state.get('shared'), dict) else {},
                'time': self.game_state['time'],
            }
            msg = NetworkMessage(
                MessageType.FULL_STATE,
                payload,
                player_id
            )
        
        with self.players_lock:
            if player_id in self.clients:
                self.clients[player_id].send_message(msg)
    
    def update_game_state(self, delta_time):
        """Update server-side game state (called from game loop if server mode)"""
        with self.state_lock:
            self.game_state['time'] += delta_time
    
    def player_disconnected(self, player_id):
        """Handle player disconnection"""
        with self.players_lock:
            if player_id in self.clients:
                del self.clients[player_id]

        with self.players_lock:
            next_owner = next(iter(self.clients.keys()), None)
        
        with self.state_lock:
            if player_id in self.game_state['players']:
                del self.game_state['players'][player_id]
            if self.game_state.get('world_owner_id') == player_id:
                self.game_state['world_owner_id'] = next_owner
        
        # Notify other players
        msg = NetworkMessage(
            MessageType.PLAYER_DIE,
            {'player_id': player_id}
        )
        self.broadcast_to_all(msg)

        if next_owner:
            with self.players_lock:
                remaining_players = list(self.clients.keys())
            for remaining_player in remaining_players:
                self.send_full_state(remaining_player)
        
        print(f"[SERVER] Player {player_id} disconnected")


class ClientHandler(threading.Thread):
    """Handles communication with a single client"""
    
    def __init__(self, server, client_socket, address, player_id):
        super().__init__(daemon=True)
        self.server = server
        self.socket = client_socket
        self.socket.settimeout(30.0)  # 30 second socket timeout
        self.address = address
        self.player_id = player_id
        self.connected = True
        self.receive_buffer = b''
        self.last_heartbeat = time.time()
        self.message_count = 0
    
    def run(self):
        """Main thread loop for client communication"""
        print(f"[SERVER] Starting handler thread for {self.player_id}")
        
        try:
            # Send welcome message
            welcome_msg = NetworkMessage(
                MessageType.CONNECT,
                {'player_id': self.player_id, 'message': 'Welcome to Game03 Server'},
                self.player_id
            )
            self.send_message(welcome_msg)
            print(f"[SERVER] Sent welcome message to {self.player_id}")
            
            # Request full state sync
            self.server.send_full_state(self.player_id)
            print(f"[SERVER] Sent full state to {self.player_id}")
            
            print(f"[SERVER] Handler thread for {self.player_id} ready to receive")
            
            while self.connected:
                try:
                    # Receive data with timeout
                    data = self.socket.recv(4096)
                    
                    if not data:
                        print(f"[SERVER] Client {self.player_id} closed connection gracefully")
                        break
                    
                    self.receive_buffer += data
                    
                    # Process complete messages
                    while True:
                        message, self.receive_buffer = NetworkMessage.from_bytes(self.receive_buffer)
                        
                        if not message:
                            break
                        
                        message.player_id = self.player_id
                        self.server.handle_message(self.player_id, message)
                        self.last_heartbeat = time.time()
                        self.message_count += 1
                
                except socket.timeout:
                    # No data received for 30 seconds - client is idle
                    continue
                except Exception as e:
                    print(f"[SERVER] ❌ Error receiving from {self.player_id}: {type(e).__name__}: {e}")
                    break
        
        except Exception as e:
            print(f"[SERVER] ❌ Critical error in handler for {self.player_id}: {type(e).__name__}: {e}")
        
        finally:
            print(f"[SERVER] Closing handler for {self.player_id} (processed {self.message_count} messages)")
            self.disconnect()
    
    def send_message(self, message):
        """Send a message to the client"""
        try:
            if not self.connected:
                print(f"[SERVER] Skipping send to {self.player_id} - not connected")
                return False
            
            if message.player_id is None:
                message.player_id = self.player_id
            
            msg_bytes = message.to_bytes()
            print(f"[SERVER] 📤 Sending {len(msg_bytes)} bytes ({message.msg_type.value}) to {self.player_id}")
            self.socket.send(msg_bytes)
            print(f"[SERVER] ✅ Sent successfully to {self.player_id}")
            return True
        
        except BrokenPipeError:
            print(f"[SERVER] ❌ Broken pipe to {self.player_id} - client disconnected")
            self.connected = False
            return False
        except ConnectionResetError:
            print(f"[SERVER] ❌ Connection reset to {self.player_id}")
            self.connected = False
            return False
        except OSError as e:
            print(f"[SERVER] ❌ Failed to send to {self.player_id}: {e}")
            self.connected = False
            return False
        except Exception as e:
            print(f"[SERVER] ❌ Unexpected error sending to {self.player_id}: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect the client"""
        if self.connected:
            self.connected = False
            try:
                self.socket.close()
            except:
                pass
            self.server.player_disconnected(self.player_id)
