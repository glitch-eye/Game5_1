"""
    Network Manager for Game03
    Integrates networking into the game loop
"""

import time
from network_protocol import (
    NetworkMessage,
    MessageType,
    PlayerStateData,
    EnemyStateData,
    ProjectileStateData,
    ParticleStateData,
    MapStateData
)
from network_client import NetworkClient


class NetworkManager:
    """Manages networking for single game instance"""
    
    def __init__(self, is_client=True, host='localhost', port=5000):
        self.is_client = is_client
        self.host = host
        self.port = port
        
        # Client connection
        self.client = None
        self.connected = False
        
        # Multiplayer data
        self.remote_players = {}  # {player_id: player_data}
        self.remote_enemies = {}  # {enemy_id: enemy_data}
        self.remote_projectiles = {}  # {projectile_id: projectile_data}
        self.remote_projectile_timestamps = {}
        self.remote_enemy_particles = {}
        self.remote_enemy_particle_timestamps = {}
        self.remote_map_state = {}
        self.remote_map_version = 0
        self.world_owner_id = None
        self.remote_projectiles_by_owner = {}
        self.remote_shared_state = {}
        
        # Sync timing
        self.last_player_update_time = time.time()
        self.last_world_update_time = time.time()
        self.last_projectile_update_time = time.time()
        self.update_interval = 0.033  # ~30 updates per second
        
        # Heartbeat
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 5.0
        
        # Settings
        self.network_enabled = True
        self.debug_mode = False
        
        if self.is_client:
            self.connect_to_server()
    
    def connect_to_server(self):
        """Initialize client connection"""
        self.client = NetworkClient(self.host, self.port)
        self.connected = self.client.connect()
        
        if self.connected:
            print("[NETWORK] Client connected successfully")
            # Request initial state sync
            self.client.request_full_state()
        else:
            print("[NETWORK] Failed to connect to server")
        
        return self.connected
    
    def disconnect(self):
        """Disconnect from server"""
        if self.client:
            self.client.disconnect()
        self.connected = False
    
    def update(self, delta_time):
        """Update network - process incoming messages, send updates"""
        if not self.is_client or not self.client:
            return
        
        # Check if we've lost connection
        if self.connected and not self.client.is_connected():
            print("[NETWORK] ❌ Connection to server lost!")
            print("     ➜ Server may have crashed or network interrupted")
            print("     ➜ Running in offline mode until reconnection")
            self.connected = False
            return
        
        if not self.connected:
            return
        
        # Process incoming messages
        self._process_messages()
        
        # Send heartbeat
        current_time = time.time()
        if current_time - self.last_heartbeat > self.heartbeat_interval:
            if not self.client.send_heartbeat():
                print("[NETWORK] ⚠️  Failed to send heartbeat - connection may be unstable")
                self.connected = False
            self.last_heartbeat = current_time
    
    def _process_messages(self):
        """Process all pending messages from server"""
        while True:
            msg = self.client.get_message(timeout=0)
            if not msg:
                break
            
            self._handle_message(msg)
    
    def _handle_message(self, msg):
        """Handle a single network message"""
        if msg.msg_type == MessageType.PLAYER_MOVE:
            player_id = msg.player_id
            if player_id in self.remote_players:
                self.remote_players[player_id].update(msg.data)
            else:
                self.remote_players[player_id] = msg.data
            if self.debug_mode:
                print(f"[NETWORK] Remote move update for {player_id}: {msg.data}")
        
        elif msg.msg_type == MessageType.PLAYER_STATE:
            player_id = msg.player_id
            if player_id in self.remote_players:
                self.remote_players[player_id].update(msg.data)
            else:
                self.remote_players[player_id] = msg.data
            if self.debug_mode:
                print(f"[NETWORK] Remote state update for {player_id}: {msg.data}")
        
        elif msg.msg_type == MessageType.PLAYER_ATTACK:
            # Handle remote player attack
            if self.debug_mode:
                print(f"[NETWORK] Remote attack from {msg.player_id}: {msg.data}")
        
        elif msg.msg_type == MessageType.ENEMY_MOVE:
            enemy_id = msg.data.get('enemy_id')
            if enemy_id:
                self.remote_enemies[enemy_id] = msg.data

        elif msg.msg_type == MessageType.WORLD_STATE:
            state = msg.data
            self.remote_players.update(state.get('players', {}))
            self.remote_enemies = state.get('enemies', {}).copy()
            self.remote_projectiles = state.get('projectiles', {}).copy()
            now = time.time()
            self.remote_projectile_timestamps = {
                projectile_id: now for projectile_id in self.remote_projectiles.keys()
            }
            self.remote_enemy_particles = state.get('enemy_particles', {}).copy()
            self.remote_enemy_particle_timestamps = {
                particle_id: now for particle_id in self.remote_enemy_particles.keys()
            }
            self.remote_map_state = state.get('map', self.remote_map_state)
            self.remote_map_version = self.remote_map_state.get('version', self.remote_map_version)
            self.world_owner_id = state.get('world_owner_id', self.world_owner_id)
            self.remote_shared_state = state.get('shared', self.remote_shared_state)
            if self.debug_mode:
                print(f"[NETWORK] Received world state - players={len(self.remote_players)}, "
                      f"enemies={len(self.remote_enemies)}, projectiles={len(self.remote_projectiles)}, "
                      f"enemy_particles={len(self.remote_enemy_particles)}: {list(self.remote_enemy_particles.keys())}")

        elif msg.msg_type == MessageType.PROJECTILE_SPAWN:
            owner_id = msg.data.get('owner_id')
            projectiles = msg.data.get('projectiles', {})
            if owner_id:
                stale_ids = self.remote_projectiles_by_owner.get(owner_id, set())
                for projectile_id in stale_ids:
                    self.remote_projectiles.pop(projectile_id, None)

                current_ids = set(projectiles.keys())
                self.remote_projectiles_by_owner[owner_id] = current_ids

                for projectile_id, projectile_data in projectiles.items():
                    projectile_data['owner_id'] = owner_id
                    self.remote_projectiles[projectile_id] = projectile_data
                    self.remote_projectile_timestamps[projectile_id] = time.time()

                active_projectile_ids = set(self.remote_projectiles.keys())
                stale_timestamp_ids = [
                    projectile_id for projectile_id in self.remote_projectile_timestamps.keys()
                    if projectile_id not in active_projectile_ids
                ]
                for projectile_id in stale_timestamp_ids:
                    del self.remote_projectile_timestamps[projectile_id]

        elif msg.msg_type == MessageType.PROJECTILE_DESTROY:
            owner_id = msg.data.get('owner_id')
            destroyed_ids = msg.data.get('projectile_ids', [])
            for projectile_id in destroyed_ids:
                self.remote_projectiles.pop(projectile_id, None)
                self.remote_projectile_timestamps.pop(projectile_id, None)

            if owner_id and owner_id in self.remote_projectiles_by_owner:
                self.remote_projectiles_by_owner[owner_id] -= set(destroyed_ids)

        elif msg.msg_type == MessageType.MAP_UPDATE:
            self.remote_map_state = msg.data
            self.remote_map_version = msg.data.get('version', self.remote_map_version)
            self.world_owner_id = msg.data.get('world_owner_id', self.world_owner_id)
            if self.debug_mode:
                print(f"[NETWORK] Remote map update: {msg.data}")

        elif msg.msg_type == MessageType.FULL_STATE:
            # Complete state synchronization
            self._sync_full_state(msg.data)

        elif msg.msg_type == MessageType.PLAYER_DIE:
            player_id = msg.data.get('player_id')
            if player_id:
                self.remote_players.pop(player_id, None)
        
        elif msg.msg_type == MessageType.HEARTBEAT:
            # Heartbeat response - calculate ping
            pass
        
        elif msg.msg_type == MessageType.ERROR:
            print(f"[NETWORK] Server error: {msg.data.get('error')}")
    
    def _sync_full_state(self, state):
        """Apply full game state from server"""
        self.remote_players = state.get('players', {})
        self.remote_enemies = state.get('enemies', {})
        self.remote_projectiles = state.get('projectiles', {})
        now = time.time()
        self.remote_projectile_timestamps = {
            projectile_id: now for projectile_id in self.remote_projectiles.keys()
        }
        self.remote_enemy_particles = state.get('enemy_particles', {}).copy()
        now = time.time()
        self.remote_enemy_particle_timestamps = {
            particle_id: now for particle_id in self.remote_enemy_particles.keys()
        }
        self.remote_map_state = state.get('map', {})
        self.remote_map_version = self.remote_map_state.get('version', 0)
        self.world_owner_id = state.get('world_owner_id')
        self.remote_shared_state = state.get('shared', {})
        
        if self.debug_mode:
            print(f"[NETWORK] Full state sync - Players: {len(self.remote_players)}, "
                  f"Enemies: {len(self.remote_enemies)}")
    
    def send_player_state(self, player):
        """Send local player state to server"""
        if not self.is_client or not self.connected:
            return
        
        current_time = time.time()
        if current_time - self.last_player_update_time < self.update_interval:
            return
        
        self.last_player_update_time = current_time
        self.client.send_message(
            NetworkMessage(
                MessageType.PLAYER_STATE,
                PlayerStateData.serialize(player)
            )
        )

    def send_world_state(self, enemies, projectiles, enemy_particles, map_obj=None, shared_state=None):
        """Send the current local world state for remote clients"""
        if not self.is_client or not self.connected:
            return

        current_time = time.time()
        if current_time - self.last_world_update_time < self.update_interval:
            return

        self.last_world_update_time = current_time

        enemy_states = {
            enemy.enemy_id: EnemyStateData.serialize(enemy)
            for enemy in enemies if hasattr(enemy, 'enemy_id')
        }
        projectile_states = {
            projectile.projectile_id: ProjectileStateData.serialize(projectile)
            for projectile in projectiles if hasattr(projectile, 'projectile_id')
        }
        enemy_particle_states = {
            p.particle_id: ParticleStateData.serialize(p)
            for p in enemy_particles if hasattr(p, 'particle_id')
        }

        if self.debug_mode:
            print(f"[NETWORK] Sending world state - enemy_particles: {list(enemy_particle_states.keys())}")

        payload = {
            'enemies': enemy_states,
            'projectiles': projectile_states,
            'enemy_particles': enemy_particle_states,
            'map': MapStateData.serialize(map_obj) if map_obj is not None else {},
            'shared': shared_state or {},
        }

        self.client.send_message(
            NetworkMessage(
                MessageType.WORLD_STATE,
                payload
            )
        )

    def send_player_projectiles(self, projectiles):
        """Send locally-owned projectiles such as player knives"""
        if not self.is_client or not self.connected or not self.client:
            return

        current_time = time.time()
        if current_time - self.last_projectile_update_time < self.update_interval:
            return

        self.last_projectile_update_time = current_time
        payload = {
            'owner_id': self.client.player_id,
            'projectiles': {
                projectile.projectile_id: {
                    **ProjectileStateData.serialize(projectile),
                    'owner_id': self.client.player_id,
                }
                for projectile in projectiles if hasattr(projectile, 'projectile_id')
            }
        }
        self.client.send_message(
            NetworkMessage(
                MessageType.PROJECTILE_SPAWN,
                payload
            )
        )

    def send_map_state(self, map_obj):
        """Send a map update to the server"""
        if not self.is_client or not self.connected:
            return

        payload = MapStateData.serialize(map_obj)
        payload['version'] = self.remote_map_version
        self.client.send_message(
            NetworkMessage(
                MessageType.MAP_UPDATE,
                payload
            )
        )

    def send_projectile_destroyed(self, projectile_ids):
        """Notify server that local projectiles have been removed"""
        if not self.is_client or not self.connected or not self.client or not projectile_ids:
            return

        self.client.send_message(
            NetworkMessage(
                MessageType.PROJECTILE_DESTROY,
                {
                    'owner_id': self.client.player_id,
                    'projectile_ids': list(projectile_ids),
                }
            )
        )
    
    def send_player_attack(self, player, attack_type='slash'):
        """Send player attack to server"""
        if not self.is_client or not self.connected:
            return
        
        self.client.send_player_attack(
            attack_type,
            player._pos.x,
            player._pos.y
        )
    
    def send_player_jump(self, jump_type='single'):
        """Send player jump to server"""
        if not self.is_client or not self.connected:
            return
        
        self.client.send_player_jump(jump_type)
    
    def send_player_dash(self, direction):
        """Send player dash to server"""
        if not self.is_client or not self.connected:
            return
        
        self.client.send_player_dash(direction)
    
    def get_remote_player(self, player_id):
        """Get remote player data"""
        return self.remote_players.get(player_id)
    
    def get_remote_players(self):
        """Get all remote players"""
        player_id = getattr(self.client, 'player_id', None) if self.client else None
        return {
            remote_id: remote_data
            for remote_id, remote_data in self.remote_players.items()
            if remote_id != player_id
        }
    
    def get_remote_enemies(self):
        """Get all remote enemies"""
        return self.remote_enemies.copy()

    def get_remote_projectiles(self):
        """Get all remote projectiles"""
        now = time.time()
        stale_ids = [
            projectile_id
            for projectile_id, timestamp in self.remote_projectile_timestamps.items()
            if now - timestamp > 0.25
        ]

        for projectile_id in stale_ids:
            self.remote_projectiles.pop(projectile_id, None)
            self.remote_projectile_timestamps.pop(projectile_id, None)

        return self.remote_projectiles.copy()

    def get_remote_map_state(self):
        """Get last remote map state received"""
        return self.remote_map_state.copy()

    def get_remote_map_version(self):
        """Get current authoritative map version"""
        return self.remote_map_version

    def get_remote_shared_state(self):
        """Get shared multiplayer state such as room-wide time stop"""
        return self.remote_shared_state.copy()

    def apply_remote_map_state(self, map_obj):
        """Apply remote map state to the local map object"""
        if not map_obj or not self.remote_map_state:
            return

        changed = False
        black = self.remote_map_state.get('black')
        incoming_signal = self.remote_map_state.get('incoming_signal')

        if black is not None and getattr(map_obj, 'black', None) != black:
            map_obj.black = black
            changed = True

        if incoming_signal is not None and getattr(map_obj, 'incoming_signal', None) != incoming_signal:
            map_obj.incoming_signal = incoming_signal
            changed = True

        if changed and hasattr(map_obj, 'set_collision_by_condition'):
            map_obj.set_collision_by_condition()

    def is_multiplayer_enabled(self):
        """Check if multiplayer is enabled"""
        return self.is_client and self.connected

    def is_world_authority(self):
        """True if this client currently owns shared world simulation"""
        if not self.client or not self.client.player_id:
            return False
        return self.client.player_id == self.world_owner_id
    
    def get_player_count(self):
        """Get number of connected players"""
        return len(self.get_remote_players())
    
    def enable_debug(self, enabled=True):
        """Enable debug logging"""
        self.debug_mode = enabled

    def get_remote_enemy_particles(self):
        now = time.time()

        stale_ids = [
            particle_id
            for particle_id, timestamp in self.remote_enemy_particle_timestamps.items()
            if now - timestamp > 2.0
        ]

        for particle_id in stale_ids:
            self.remote_enemy_particles.pop(particle_id, None)
            self.remote_enemy_particle_timestamps.pop(particle_id, None)

        return self.remote_enemy_particles.copy()


class LocalNetworkManager(NetworkManager):
    """Network manager for offline/single-player mode"""
    
    def __init__(self):
        self.is_client = False
        self.connected = False
        self.network_enabled = False
        self.remote_players = {}
        self.remote_enemies = {}
        self.remote_projectiles = {}
        self.remote_enemy_particles = {} 
    
    def update(self, delta_time):
        """No-op for offline mode"""
        pass
    
    def is_multiplayer_enabled(self):
        """Always false for offline mode"""
        return False
