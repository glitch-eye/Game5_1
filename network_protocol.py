"""
    Network Protocol for Game03 Multiplayer
    Handles message serialization and deserialization
"""

import json
import struct
from enum import Enum


class MessageType(Enum):
    """Message types for network communication"""
    # Connection management
    CONNECT = "CONNECT"
    DISCONNECT = "DISCONNECT"
    HEARTBEAT = "HEARTBEAT"
    
    # Player state
    PLAYER_MOVE = "PLAYER_MOVE"
    PLAYER_ATTACK = "PLAYER_ATTACK"
    PLAYER_JUMP = "PLAYER_JUMP"
    PLAYER_DASH = "PLAYER_DASH"
    PLAYER_STATE = "PLAYER_STATE"
    PLAYER_HEALTH = "PLAYER_HEALTH"
    PLAYER_SPAWN = "PLAYER_SPAWN"
    PLAYER_DIE = "PLAYER_DIE"
    
    # Projectile events
    PROJECTILE_SPAWN = "PROJECTILE_SPAWN"
    PROJECTILE_DESTROY = "PROJECTILE_DESTROY"
    
    # Enemy events
    ENEMY_MOVE = "ENEMY_MOVE"
    ENEMY_ATTACK = "ENEMY_ATTACK"
    ENEMY_SPAWN = "ENEMY_SPAWN"
    ENEMY_DIE = "ENEMY_DIE"
    
    # World synchronization
    WORLD_STATE = "WORLD_STATE"
    MAP_UPDATE = "MAP_UPDATE"
    
    # Game events
    GAME_START = "GAME_START"
    GAME_PAUSE = "GAME_PAUSE"
    GAME_RESUME = "GAME_RESUME"
    GAME_END = "GAME_END"
    
    # Server info
    SYNC_REQUEST = "SYNC_REQUEST"
    FULL_STATE = "FULL_STATE"
    ERROR = "ERROR"


class NetworkMessage:
    """Represents a network message"""
    
    def __init__(self, msg_type, data=None, player_id=None):
        self.msg_type = msg_type
        self.data = data or {}
        self.player_id = player_id
        self.timestamp = 0
    
    def to_json(self):
        """Convert message to JSON string"""
        return json.dumps({
            'type': self.msg_type.value,
            'data': self.data,
            'player_id': self.player_id,
            'timestamp': self.timestamp
        })
    
    @staticmethod
    def from_json(json_str):
        """Create message from JSON string"""
        try:
            parsed = json.loads(json_str)
            msg = NetworkMessage(
                MessageType(parsed['type']),
                parsed.get('data', {}),
                parsed.get('player_id')
            )
            msg.timestamp = parsed.get('timestamp', 0)
            return msg
        except (json.JSONDecodeError, ValueError) as e:
            return None
    
    def to_bytes(self):
        """Convert to bytes with length prefix"""
        json_str = self.to_json()
        json_bytes = json_str.encode('utf-8')
        length = struct.pack('>I', len(json_bytes))
        return length + json_bytes
    
    @staticmethod
    def from_bytes(data):
        """Extract message from bytes"""
        if len(data) < 4:
            return None, data
        
        length = struct.unpack('>I', data[:4])[0]
        
        if len(data) < 4 + length:
            return None, data
        
        json_bytes = data[4:4 + length]
        remaining = data[4 + length:]
        
        try:
            json_str = json_bytes.decode('utf-8')
            msg = NetworkMessage.from_json(json_str)
            return msg, remaining
        except UnicodeDecodeError:
            return None, remaining


class PlayerStateData:
    """Serializes player state for network transmission"""
    
    @staticmethod
    def serialize(player):
        """Convert player to network format"""
        return {
            'pos_x': float(player._pos.x),
            'pos_y': float(player._pos.y),
            'vel_x': float(player._vel.x),
            'vel_y': float(player._vel.y),
            'hp': player.hp,
            'mp': player.mp,
            'time_energy': getattr(player, 'time_energy', 0.0),
            'grounded': player._grounded,
            'facing_right': player._facingRight if hasattr(player, '_facingRight') else True,
            'animation_state': player.current_anim if hasattr(player, 'current_anim') else 'idle',
            'current_anim': player.current_anim if hasattr(player, 'current_anim') else 'idle',
            'time_stop': getattr(player, 'time_stop', False),
            'time_stop_startup': getattr(player, 'time_stop_startup', False),
            'time_stop_ending': getattr(player, 'time_stop_ending', False),
            'time_stop_wave_active': getattr(player, 'time_stop_wave_active', False),
            'time_stop_wave_reverse': getattr(player, 'time_stop_wave_reverse', False),
            'frame_index': getattr(player, 'frame_index', 0),
            'dead': player._dead,
            'player_no': getattr(player, 'player_no', 1),
        }
    
    @staticmethod
    def deserialize(data, player):
        """Apply network data to player"""
        player._pos.x = data.get('pos_x', player._pos.x)
        player._pos.y = data.get('pos_y', player._pos.y)
        player._vel.x = data.get('vel_x', player._vel.x)
        player._vel.y = data.get('vel_y', player._vel.y)
        player.hp = data.get('hp', player.hp)
        player.mp = data.get('mp', player.mp)
        if hasattr(player, 'time_energy'):
            player.time_energy = data.get('time_energy', player.time_energy)
        player._grounded = data.get('grounded', player._grounded)
        player._dead = data.get('dead', player._dead)
        if hasattr(player, '_facingRight'):
            player._facingRight = data.get('facing_right', player._facingRight)
        if hasattr(player, 'current_anim'):
            player.current_anim = data.get('current_anim', player.current_anim)
        if hasattr(player, 'frame_index'):
            player.frame_index = data.get('frame_index', player.frame_index)
        if hasattr(player, 'time_stop'):
            player.time_stop = data.get('time_stop', player.time_stop)
        if hasattr(player, 'time_stop_startup'):
            player.time_stop_startup = data.get('time_stop_startup', player.time_stop_startup)
        if hasattr(player, 'time_stop_ending'):
            player.time_stop_ending = data.get('time_stop_ending', player.time_stop_ending)
        if hasattr(player, 'player_no'):
            player.player_no = data.get('player_no', player.player_no)


class EnemyStateData:
    """Serializes enemy state for network transmission"""
    
    @staticmethod
    def serialize(enemy):
        """Convert enemy to network format"""
        if hasattr(enemy, '_rect'):
            rect = enemy._rect
        elif hasattr(enemy, 'rect'):
            rect = enemy.rect
        else:
            rect = None

        pos_x = None
        pos_y = None
        if hasattr(enemy, '_pos'):
            pos_x = float(enemy._pos.x)
            pos_y = float(enemy._pos.y)
        elif hasattr(enemy, 'pos'):
            pos_x = float(enemy.pos.x)
            pos_y = float(enemy.pos.y)
        elif rect is not None:
            pos_x = float(rect.centerx)
            pos_y = float(rect.centery)

        return {
            'enemy_id': getattr(enemy, 'enemy_id', getattr(enemy, 'object_id', 'unknown')),
            'entity_type': enemy.__class__.__name__.lower(),
            'pos_x': pos_x or 0.0,
            'pos_y': pos_y or 0.0,
            'vel_x': float(getattr(enemy, '_vel', getattr(enemy, 'vel_x', 0)).x if hasattr(enemy, '_vel') else getattr(enemy, 'vel_x', 0)),
            'vel_y': float(getattr(enemy, '_vel', getattr(enemy, 'vel_y', 0)).y if hasattr(enemy, '_vel') else getattr(enemy, 'vel_y', 0)),
            'hp': getattr(enemy, '_health', getattr(enemy, 'hp', 100)),
            'max_hp': getattr(enemy, 'max_hp', getattr(enemy, '_max_health', None)),
            'animation_state': getattr(enemy, 'current_animation', 'idle'),
            'current_anim': getattr(enemy, 'current_anim', None),
            'state': getattr(enemy, 'state', None),
            'attack_state': getattr(enemy, 'attack_state', None),
            'visible': getattr(enemy, 'visible', True),
            'facing_right': getattr(enemy, 'facing_right', getattr(enemy, '_dir', 'right') != 'left'),
            'alive': getattr(enemy, '_alive', getattr(enemy, 'alive', not getattr(enemy, '_dead', False))),
            'dead': getattr(enemy, '_died', getattr(enemy, 'dead', getattr(enemy, '_dead', False))),
            'dying': getattr(enemy, '_dying', False),
            'item_shown': getattr(getattr(enemy, '_item', None), '_shown', None),
            'item_pop': getattr(getattr(enemy, '_item', None), '_pop', None),
            'frame_index': getattr(enemy, '_frame_index', getattr(enemy, 'frame_index', 0)),
            'attack': getattr(enemy, '_attack', False),
            'dir': getattr(enemy, '_dir', None),
            'hit': getattr(enemy, '_hit', False),
        }
    
    @staticmethod
    def deserialize(data, enemy):
        """Apply network data to enemy"""
        if hasattr(enemy, '_pos'):
            enemy._pos.x = data.get('pos_x', enemy._pos.x)
            enemy._pos.y = data.get('pos_y', enemy._pos.y)
        elif hasattr(enemy, 'pos'):
            enemy.pos.x = data.get('pos_x', enemy.pos.x)
            enemy.pos.y = data.get('pos_y', enemy.pos.y)
        elif hasattr(enemy, 'x'):
            enemy.x = data.get('pos_x', enemy.x)
            enemy.y = data.get('pos_y', enemy.y)

        if hasattr(enemy, '_vel'):
            enemy._vel.x = data.get('vel_x', enemy._vel.x)
            enemy._vel.y = data.get('vel_y', enemy._vel.y)
        else:
            enemy.vel_x = data.get('vel_x', getattr(enemy, 'vel_x', 0))
            enemy.vel_y = data.get('vel_y', getattr(enemy, 'vel_y', 0))

        if hasattr(enemy, '_health'):
            enemy._health = data.get('hp', enemy._health)
        else:
            enemy.hp = data.get('hp', getattr(enemy, 'hp', 100))

        if hasattr(enemy, 'max_hp') and data.get('max_hp') is not None:
            enemy.max_hp = data.get('max_hp', enemy.max_hp)

        if hasattr(enemy, '_died'):
            enemy._died = data.get('dead', enemy._died)
        else:
            enemy.dead = data.get('dead', getattr(enemy, 'dead', False))

        if hasattr(enemy, '_dead'):
            enemy._dead = data.get('dead', enemy._dead)

        if hasattr(enemy, '_dying'):
            enemy._dying = data.get('dying', enemy._dying)

        if hasattr(enemy, '_alive'):
            enemy._alive = data.get('alive', enemy._alive)
        elif hasattr(enemy, 'alive'):
            enemy.alive = data.get('alive', enemy.alive)

        if hasattr(enemy, 'visible'):
            enemy.visible = data.get('visible', enemy.visible)

        if hasattr(enemy, 'facing_right'):
            enemy.facing_right = data.get('facing_right', enemy.facing_right)

        if hasattr(enemy, '_dir'):
            enemy._dir = 'right' if data.get('facing_right', enemy._dir != 'left') else 'left'

        if data.get('state') is not None and hasattr(enemy, 'state'):
            enemy.state = data.get('state')

        if data.get('attack_state') is not None and hasattr(enemy, 'attack_state'):
            enemy.attack_state = data.get('attack_state')

        if data.get('current_anim') and hasattr(enemy, 'current_anim'):
            enemy.current_anim = data.get('current_anim')

        if hasattr(enemy, '_frame_index'):
            enemy._frame_index = data.get('frame_index', enemy._frame_index)
        elif hasattr(enemy, 'frame_index'):
            enemy.frame_index = data.get('frame_index', enemy.frame_index)

        if hasattr(enemy, '_attack'):
            enemy._attack = data.get('attack', enemy._attack)

        if data.get('dir') is not None and hasattr(enemy, '_dir'):
            enemy._dir = data.get('dir')

        if hasattr(enemy, '_hit'):
            enemy._hit = data.get('hit', enemy._hit)

        item = getattr(enemy, '_item', None)
        if item is not None:
            if data.get('item_shown') is not None:
                item._shown = data.get('item_shown')
            if data.get('item_pop') is not None:
                item._pop = data.get('item_pop')



class ProjectileStateData:
    """Serializes projectile state for network transmission"""

    @staticmethod
    def serialize(projectile):
        pos_x = None
        pos_y = None
        if hasattr(projectile, 'pos'):
            pos_x = float(projectile.pos.x)
            pos_y = float(projectile.pos.y)
        elif hasattr(projectile, 'rect'):
            pos_x = float(projectile.rect.centerx)
            pos_y = float(projectile.rect.centery)

        vel = getattr(projectile, 'vel', getattr(projectile, 'velocity', None))
        vel_x = vel.x if vel is not None and hasattr(vel, 'x') else getattr(projectile, 'vel_x', 0)
        vel_y = vel.y if vel is not None and hasattr(vel, 'y') else getattr(projectile, 'vel_y', 0)

        return {
            'projectile_id': getattr(projectile, 'projectile_id', 'unknown'),
            'type': getattr(projectile, 'attack_type', getattr(projectile, 'projectile_type', projectile.__class__.__name__.lower())),
            'class_name': projectile.__class__.__name__,
            'pos_x': pos_x or 0.0,
            'pos_y': pos_y or 0.0,
            'vel_x': float(vel_x),
            'vel_y': float(vel_y),
            'alive': getattr(projectile, 'alive', True),
            'facing_right': getattr(projectile, 'facing_right', True),
            'phase': getattr(projectile, 'phase', None),
            'state': getattr(projectile, 'state', None),
            'frame_index': getattr(projectile, 'frame_index', getattr(projectile, 'frame', 0)),
            'ground_y': getattr(projectile, 'ground_y', None),
            'boss_x': getattr(getattr(projectile, 'boss', None), 'rect', None).centerx if getattr(getattr(projectile, 'boss', None), 'rect', None) else None,
            'boss_y': getattr(getattr(projectile, 'boss', None), 'rect', None).centery if getattr(getattr(projectile, 'boss', None), 'rect', None) else None,
        }


class ParticleStateData:
    """Serializes particle state for network transmission"""

    @staticmethod
    def serialize(particle):
        """Convert particle to network format"""
        pos_x = None
        pos_y = None
        if hasattr(particle, 'pos'):
            pos_x = float(particle.pos.x)
            pos_y = float(particle.pos.y)
        elif hasattr(particle, 'rect'):
            pos_x = float(particle.rect.centerx)
            pos_y = float(particle.rect.centery)

        vel = getattr(particle, 'vel', getattr(particle, 'velocity', None))
        vel_x = vel.x if vel is not None and hasattr(vel, 'x') else getattr(particle, 'vel_x', 0)
        vel_y = vel.y if vel is not None and hasattr(vel, 'y') else getattr(particle, 'vel_y', 0)

        return {
            'particle_id': getattr(particle, 'particle_id', 'unknown'),
            'class_name': particle.__class__.__name__,
            'pos_x': pos_x or 0.0,
            'pos_y': pos_y or 0.0,
            'vel_x': float(vel_x),
            'vel_y': float(vel_y),
            'alive': getattr(particle, 'alive', True),
            'facing_right': getattr(particle, 'facing_right', True),
            'frame_index': getattr(particle, 'frame_index', getattr(particle, 'frame', 0)),
            'state': getattr(particle, 'state', None),
            'phase': getattr(particle, 'phase', None),
            'ground_y': getattr(particle, 'ground_y', None),
            'base_pos_y': getattr(particle, 'base_pos', None).y if hasattr(particle, 'base_pos') else None,
        }


class MapStateData:
    """Serializes map collision state for network transmission"""

    @staticmethod
    def serialize(map_obj):
        return {
            'black': getattr(map_obj, 'black', False),
            'incoming_signal': getattr(map_obj, 'incoming_signal', False)
        }
