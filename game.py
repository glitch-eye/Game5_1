from settings import *
from character import *
from utils import *
from wisp import *
from menu import *
from boss import Boss
from boss_projectile import *
from fire_gate import *
from asset_loader import AssetLoader
import pygame
import subprocess
import sys
from build import *
from concurrent.futures import ThreadPoolExecutor

# Network support
from network_manager import NetworkManager, LocalNetworkManager
from network_protocol import EnemyStateData
from network_utils import NetworkStatistics

class Position:
    def __init__(self):
        self.x = 36*36
        self.y = 360

pos = Position()
class Game:

    def __init__(self, enable_multiplayer=False, server_host='localhost', server_port=5000):

        self.time_stop = False

        self._display = pygame.display.set_mode(
            (SCREEN_WIDTH * GAME_SCALE, SCREEN_HEIGHT * GAME_SCALE)
        )

        self._screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(GAME_NAME)

        self._clock = pygame.time.Clock()
        self._font = pygame.font.SysFont(None, FONT_SIZE)

        self.loader = AssetLoader()
        self.in_menu = True
        self.menu = None

        self.player = None
        self.wisp = None   # store animation frames
        self.goblin = None
        self.boss = None
        self.crystal = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.firegate = None

        self.boss_spawned = False
        self.boss_spawn_triggered = False
        self.boss_spawn_timer = 0
        self.boss_spawn_delay = 1.2 
        
        # ===== NETWORK INITIALIZATION =====
        self.enable_multiplayer = enable_multiplayer
        self.server_host = server_host
        self.server_port = server_port
        self.net_manager = None
        self.net_stats = None
        self.projectile_sequence = 0
        self.processed_remote_projectile_hits = set()
        self.consumed_remote_projectiles = set()
        self.shared_time_stop_active = False
        self.shared_time_stop_energy = 100.0
        self._prev_shared_time_stop_active = False
        self._last_sent_map_state = None
        self._last_local_knife_ids = set()
        self.load_assets()
    
    def _init_network(self):
        """Initialize network manager"""
        if self.enable_multiplayer:
            subprocess.Popen(["python3", "network_server_app.py"])
            print("[GAME] Starting in multiplayer mode...")
            self.net_manager = NetworkManager(
                is_client=True,
                host=self.server_host,
                port=self.server_port
            )
            
            if not self.net_manager.connected:
                print("[GAME] ⚠️  Failed to connect to server - falling back to offline")
                self.enable_multiplayer = False
                self.net_manager = LocalNetworkManager()
            else:
                print("[GAME] ✅ Connected to multiplayer server!")
                self.net_stats = NetworkStatistics()
        else:
            print("[GAME] Starting in single-player mode...")
            # self.net_manager = LocalNetworkManager() 

    # -----------------------
    # ASSET LOADING
    # -----------------------

    def load_assets(self):
        # menu
        self.loader.load_animation("start_screen", "assets/sprite/start_screen_sprite")
        self.loader.load_animation("taohao_font", "assets/sprite/toho_font_sprite")
        self.loader.load_animation("pause_screen", "assets/sprite/title_back")
        self.loader.load_animation("status_font", "assets/sprite/status_font")

        # player effect (shared)
        self.loader.load_animation("arrow_ring_sprite", "assets/sprite/arrow_ring_sprite")
        self.loader.load_animation("player_jump_effect", "assets/sprite/player_jump_effect")
        self.loader.load_animation("bullet_effect_sprite2", "assets/sprite/bullet_effect_sprite2")
        self.loader.load_animation("bullet_effect_sprite3", "assets/sprite/bullet_effect_sprite3")
        self.loader.load_animation("flying_knife", "assets/sprite/bullet_sprite3")

        self.loader.load_animation("player_damage", "assets/sprite/player_damage")
        self.loader.load_animation("player_fall_down", "assets/sprite/player_fall_down")

        # player 1
        self.loader.load_animation("player_idle", "assets/sprite/player_stop")
        self.loader.load_animation("player_jump", "assets/sprite/player_jump")
        self.loader.load_animation("player_fall", "assets/sprite/player_falling")
        self.loader.load_animation("player_2ndjump", "assets/sprite/player_2ndjump")
        self.loader.load_animation("player_gliding", "assets/sprite/player_gliding")
        self.loader.load_animation("player_run", "assets/sprite/player_run")
        self.loader.load_animation("player_run_start", "assets/sprite/player_run_start")
        self.loader.load_animation("player_run_stop", "assets/sprite/player_run_stop")
        self.loader.load_animation("player_run_back", "assets/sprite/player_run_back")
        self.loader.load_animation("player_down", "assets/sprite/player_down")
        self.loader.load_animation("player_action1", "assets/sprite/player_action")
        self.loader.load_animation("player_action2", "assets/sprite/player_action2")
        self.loader.load_animation("player_action3", "assets/sprite/player_action3")
        self.loader.load_animation("player_action4", "assets/sprite/player_action4")
        self.loader.load_animation("player_run_attack1", "assets/sprite/player_run_attack2")
        self.loader.load_animation("player_run_attack2", "assets/sprite/player_run_attack")
        self.loader.load_animation("player_run_attack3", "assets/sprite/player_run_attack3")
        self.loader.load_animation("player_run_attack4", "assets/sprite/player_run_attack4")
        self.loader.load_animation("player_jump_attack", "assets/sprite/player_jump_attack")
        self.loader.load_animation("player_up_shot","assets/sprite/player_up_shot")
        self.loader.load_animation("player_up_shot2","assets/sprite/player_up_shot2")
        self.loader.load_animation("player_up_shot_run","assets/sprite/player_up_shot_run")
        self.loader.load_animation("player_up_shot_air","assets/sprite/player_up_shot_air")
        self.loader.load_animation("player_under_attack","assets/sprite/player_under_attack")
        self.loader.load_animation("player_sliding","assets/sprite/player_sliding")
        self.loader.load_animation("player_time_stop", "assets/sprite/player_time_stop")
        self.loader.load_animation("player_time_stop_air", "assets/sprite/player_time_stop_air")
        self.loader.load_animation("player_des", "assets/sprite/player_des")
        # player 2
        self.loader.load_animation("player_idle_2", "assets/sprite/player_stop_2")
        self.loader.load_animation("player_jump_2", "assets/sprite/player_jump_2")
        self.loader.load_animation("player_fall_2", "assets/sprite/player_falling_2")
        self.loader.load_animation("player_2ndjump_2", "assets/sprite/player_2ndjump_2")
        self.loader.load_animation("player_gliding_2", "assets/sprite/player_gliding_2")
        self.loader.load_animation("player_run_2", "assets/sprite/player_run_2")
        self.loader.load_animation("player_run_start_2", "assets/sprite/player_run_start_2")
        self.loader.load_animation("player_run_stop_2", "assets/sprite/player_run_stop_2")
        self.loader.load_animation("player_run_back_2", "assets/sprite/player_run_back_2")
        self.loader.load_animation("player_down_2", "assets/sprite/player_down_2")
        self.loader.load_animation("player_action1_2", "assets/sprite/player_action_2")
        self.loader.load_animation("player_action2_2", "assets/sprite/player_action2_2")
        self.loader.load_animation("player_action3_2", "assets/sprite/player_action3_2")
        self.loader.load_animation("player_action4_2", "assets/sprite/player_action4_2")
        self.loader.load_animation("player_run_attack1_2", "assets/sprite/player_run_attack2_2")
        self.loader.load_animation("player_run_attack2_2", "assets/sprite/player_run_attack_2")
        self.loader.load_animation("player_run_attack3_2", "assets/sprite/player_run_attack3_2")
        self.loader.load_animation("player_run_attack4_2", "assets/sprite/player_run_attack4_2")
        self.loader.load_animation("player_jump_attack_2", "assets/sprite/player_jump_attack_2")
        self.loader.load_animation("player_up_shot_2","assets/sprite/player_up_shot_2")
        self.loader.load_animation("player_up_shot2_2","assets/sprite/player_up_shot2_2")
        self.loader.load_animation("player_up_shot_run_2","assets/sprite/player_up_shot_run_2")
        self.loader.load_animation("player_up_shot_air_2","assets/sprite/player_up_shot_air_2")
        self.loader.load_animation("player_under_attack_2","assets/sprite/player_under_attack_2")
        self.loader.load_animation("player_sliding_2","assets/sprite/player_sliding_2")
        self.loader.load_animation("player_time_stop_2", "assets/sprite/player_time_stop_2")
        self.loader.load_animation("player_time_stop_air_2", "assets/sprite/player_time_stop_air_2")
        self.loader.load_animation("player_des_2", "assets/sprite/player_des_2")
        # item and effect
        self.loader.load_animation("crystal", "assets/sprite/crystal_sprite")
        self.loader.load_animation("bomb_effect", "assets/sprite/bomb_effect")
        self.loader.load_animation("big_bomb_effect", "assets/sprite/big_bomb_effect")
        self.loader.load_image("mp_item", "assets/sprite/mpup_sprite/mpup_sprite_0.png")
        self.loader.load_image("hp_item", "assets/sprite/hpup_sprite/hpup_sprite_0.png")
        self.loader.load_animation("huda_fire", "assets/sprite/huda_fire")
        self.loader.load_image("magatama", "assets/sprite/item_magatama/item_magatama_0.png")

        # UI
        self.loader.load_image("gauge", "assets/sprite/gauge_sprite/gauge_sprite_1.png")
        for i in range(10):
            self.loader.load_image(
                f"time_number_sprite_{i}",
                f"assets/sprite/time_number_sprite/time_number_sprite_{i}.png"
            )
        self.loader.load_image("hp_bar", "assets/sprite/hpvar_sprite/hpvar_sprite_19.png")
        self.loader.load_image("mp_bar", "assets/sprite/mpvar_sprite/mpvar_sprite_19.png")

        # Boss
        self.loader.load_animation("marisa_idle", "assets/sprite/marisa")
        self.loader.load_animation("marisa_dir_change", "assets/sprite/marisa_dir_change")
        self.loader.load_animation("marisa_up_to_down", "assets/sprite/marisa_up_to_down")
        self.loader.load_animation("marisa_down", "assets/sprite/marisa_down")
        self.loader.load_animation("marisa_down_to_up", "assets/sprite/marisa_down_to_up")
        self.loader.load_animation("marisa_dira_down_change", "assets/sprite/marisa_dira_change_down")
        self.loader.load_animation("marisa_stop", "assets/sprite/marisa_stop")
        self.loader.load_animation("marisa_dash", "assets/sprite/marisa_dash")
        self.loader.load_animation("marisa_dash_zanzou", "assets/sprite/marisa_dash_zanzou")
        self.loader.load_animation("marisa_undershot", "assets/sprite/marisa_undershot")
        self.loader.load_animation("marisa_timeshot", "assets/sprite/marisa_timeshot")
        self.loader.load_animation("marisa_shot", "assets/sprite/marisa_shot")
        self.loader.load_animation("marisa_undershot_a", "assets/sprite/marisa_undershot_a")
        self.loader.load_animation("marisa_laser", "assets/sprite/marisa_laser")
        self.loader.load_animation("marisa_after_effect", "assets/sprite/marisa_after_effect")
        self.loader.load_animation("marisa_after_effect_s", "assets/sprite/marisa_after_effect_s")
        self.loader.load_animation("marisa_shot_a", "assets/sprite/marisa_shot_a")
        self.loader.load_animation("smoke", "assets/sprite/smoke")
        self.loader.load_animation("marisa_zangai", "assets/sprite/marisa_shot_effect_zangai")
        self.loader.load_animation("marisa_supershot", "assets/sprite/marisa_supershot")
        self.loader.load_animation("marisa_supershot_a", "assets/sprite/marisa_supershot_a")
        self.loader.load_animation("marisa_supershot_b", "assets/sprite/marisa_supershot_b")
        self.loader.load_animation("marisa_supershot_c", "assets/sprite/marisa_supershot_c")
        self.loader.load_animation("marisa_supershot_d", "assets/sprite/marisa_supershot_d")
        self.loader.load_animation("marisa_des", "assets/sprite/marisa_des")
        self.loader.load_animation("marisa_dying", "assets/sprite/marisa_dying")
        # sounds

        # enemies
        self.loader.load_animation("wisp","assets/sprite/will_o_wisp_sprite")

        self.loader.load_animation("goblin_attack", "assets/sprite/goblin_attack_sprite")
        self.loader.load_animation("goblin_run", "assets/sprite/goblin_run_sprite")
        self.loader.load_animation("goblin_idle", "assets/sprite/goblin_sprite")

        self.knives = []
        self.enemy_projectiles = []
        self.enemy_particles = []
        # music
        self.loader.load_music("Luna_Dial", "assets/music/Lunar Clock Lunar Dial.ogg")
        music_path = self.loader.get_music("Luna_Dial")
        pygame.mixer.music.load(music_path)

        # loading screen loop
        while not self.loader.done():

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self._screen.fill((0,0,0))

            text = self._font.render("Loading...", True, (255,255,255))
            rect = text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self._screen.blit(text, rect)

            pygame.display.flip()

        # finalize assets
        self.loader.finalize()

        # start music
        pygame.mixer.music.set_volume(GAME_VOLUME / 100)
        pygame.mixer.music.play(-1)   # -1 = loop forever
        self.menu = Menu(loader=self.loader)
        # retrieve animation frames
        self.wisp = list(self.executor.map(lambda x: Wisp(x, self.loader), WISP_POS))
        self.goblin = list(self.executor.map(lambda x: Goblin(self.loader, x), GOB_INIT_POS))

        self.crystal = list(self.executor.map(lambda x: Crystal(self.loader, x), CRYSTAL_POS))

        # prepare remote render templates for player sprites
        self.remote_player_templates = {
            1: Character(self.loader, self, 1),
            2: Character(self.loader, self, 2),
        }

        # prepare remote render templates for player sprites
        self.remote_player_templates = {
            1: Character(self.loader, self, 1),
            2: Character(self.loader, self, 2),
        }

        # initialize entity placeholders; actual player/boss creation happens once the game starts
        self.player = None
        self.boss = None
        self.fire_gate = None
        self.magatamas = []

        self.BG = build_background()
        self.INDEX_MAP = load_map_from_excel()
        self.collision_map = Map()
        self.map_tiles, self.collision_tiles = self.collision_map.build_map()
        self.collision_map.build_collision(self.INDEX_MAP, self.collision_tiles)
        self._last_sent_map_state = self._get_local_map_state()
        self._create_local_entities()

    def _create_local_entities(self, desired_player_no=None, force_recreate=False):
        """Create or update the local player and dependent entities."""
        if self.player is not None and not force_recreate:
            if desired_player_no is None or getattr(self.player, 'player_no', 1) == desired_player_no:
                return

        player_no = 1
        if desired_player_no is not None:
            player_no = desired_player_no
        elif self.enable_multiplayer and self.net_manager and self.net_manager.connected:
            import time
            start_time = time.time()
            while self.net_manager.world_owner_id is None and time.time() - start_time < 1.0:
                self.net_manager.update(0)
                time.sleep(0.01)

            player_no = 1 if self.net_manager.is_world_authority() else 2

        self.player = Character(self.loader, self, player_no)
        self.player.player_no = player_no
        self.player.set_map(self.collision_map)

        self.boss = Boss(self.loader, self, self.player)
        self.fire_gate = FireGate((3347.0, 470.0), self.loader)
        self.magatamas = [Magatama((2850, 680), self.loader)]

        self._assign_world_ids()
        self._last_sent_map_state = self._get_local_map_state()

    # -----------------------
    # INPUT
    # -----------------------

    def handleInput(self):

        for event in pygame.event.get():
            if self.in_menu:
                option = self.menu.handle_event(event)
                if option:
                    self.enable_multiplayer = self.menu.multi_mode
                    self._init_network()
                    self._create_local_entities(force_recreate=True)
                    self.in_menu = False
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and self.menu.game_start:
                    self.in_menu = not self.in_menu
                    self.menu.game_paused = not self.menu.game_paused

        keypressed = pygame.key.get_pressed()
        if self.time_stop:
            self.collision_map.time_stop()
        else:
            self.collision_map.time_go()
        
        self.player.handleInput(keypressed)
        

    # -----------------------
    # UPDATE
    # -----------------------

    def update(self, dt):
        global GAME_SCALE
        if self.menu.setting_options["GAME SCALE"] != GAME_SCALE:
            GAME_SCALE = self.menu.setting_options["GAME SCALE"]
            self._display = pygame.display.set_mode(
                (SCREEN_WIDTH * GAME_SCALE, SCREEN_HEIGHT * GAME_SCALE)
            )
        pygame.mixer.music.set_volume(self.menu.setting_options["VOLUME"] / 100)
        self.collision_map.update_position(pos, pygame.Rect(0,0,40,40), pygame.Vector2(10,10))
        self.player.update(dt)

        # -----------------------
        # BOSS SPAWN TRIGGER
        # -----------------------
        if not self.boss_spawned:

            # Player enters trigger → start countdown
            if not self.boss_spawn_triggered:
                if self.player._pos.x >= 3412 and self.player._pos.y >= 404:
                    self.boss_spawn_triggered = True
                    self.boss_spawn_timer = self.boss_spawn_delay

            # Countdown running
            else:
                self.boss_spawn_timer -= dt
                if self.boss_spawn_timer <= 0:
                    self.boss.visible = True
                    self.boss_spawned = True

        if self._is_world_authority():
            self.fire_gate.update(dt, self.player)

            if not self.time_stop:
                if self.boss_spawned:
                    self.boss.update(dt, self.player._pos, self.knives)
                if self.enable_multiplayer:
                    remote_players = self.net_manager.get_remote_players()
                    list(self.executor.map(lambda x: x.update(dt, self.player, self.knives, remote_players), self.wisp))
                    list(self.executor.map(lambda x: x.update(dt, self.player, self.knives, remote_players), self.goblin))
                    list(self.executor.map(lambda x: x.update(dt, self.player, self.knives, remote_players), self.crystal))
                else:
                    list(self.executor.map(lambda x: x.update(dt, self.player, self.knives), self.wisp))
                    list(self.executor.map(lambda x: x.update(dt, self.player, self.knives), self.goblin))
                    list(self.executor.map(lambda x: x.update(dt, self.player, self.knives), self.crystal))

                for m in self.magatamas:
                    m.update(dt, self.player)

                self.magatamas = [m for m in self.magatamas if m.alive]

                for p in self.enemy_particles:
                    p.update(dt, self.player)

                for proj in self.enemy_projectiles:
                    proj.update(dt, self.player, self.enemy_particles)

                self.enemy_particles = [p for p in self.enemy_particles if p.alive]
                self.enemy_projectiles = [p for p in self.enemy_projectiles if p.alive]
            else:
                [p.timestop_update(dt, self.player) for p in self.enemy_particles if isinstance(p, SmokeColumn)]
                [proj.timestop_update(dt, self.player) for proj in self.enemy_projectiles if isinstance(proj, UndershotProjectile) or isinstance(proj, ShotProjectile) or isinstance(proj,MasterSparkProjectile)]
        else:
            self._apply_remote_world_state()
            self._apply_remote_world_interactions(dt)

        if self.enable_multiplayer and self.net_manager:
            self._apply_remote_projectile_interactions()
            self._apply_remote_enemy_particles_interactions(dt)

        if not self.time_stop:
            for knife in self.knives:
                knife.update(dt)
            self.knives = [k for k in self.knives if k.alive]
        self._sync_destroyed_knives()

        self._assign_projectile_ids(self.knives)
        if self._is_world_authority():
            self._assign_projectile_ids(self.enemy_projectiles)
            self._assign_particle_ids(self.enemy_particles)

    # -----------------------
    # COLLISION
    # -----------------------

    def check_collision(self):

        self.player.check_collision()
        list(self.executor.map(lambda x: x.check_collision(), self.goblin))

    # -----------------------
    # DRAW
    # -----------------------

    def draw(self):
        self._screen.fill(COLOR_BLACK)
        self._screen.blit(self.BG, (0,0))
        
        if self.in_menu:
            self.menu.draw(self._screen)
            scaled = pygame.transform.scale(
                self._screen,
                (SCREEN_WIDTH * GAME_SCALE, SCREEN_HEIGHT * GAME_SCALE)
            )
        else:
            # Update camera position to follow player
            pos.x = self.player._pos.x
            pos.y = self.player._pos.y
            
            self.collision_map.load_map(self._screen, self.INDEX_MAP, self.map_tiles, pos)
            # self.collision_map.load_collision_map(self._screen, self.collision_tiles, pos)

            # camera_x = min(max(pos.x - SCREEN_WIDTH // 2, 0), MAP_NUMS[0]*TILE_SIZE - SCREEN_WIDTH)
            # camera_y = min(max(pos.y - SCREEN_HEIGHT // 2, 0), MAP_NUMS[1]*TILE_SIZE - SCREEN_HEIGHT)
            # x,y = SCREEN_WIDTH//2 , SCREEN_HEIGHT//2
            # if camera_x == 0:
            #     x = pos.x
            # if camera_x == MAP_NUMS[0]*TILE_SIZE - SCREEN_WIDTH:
            #     x = pos.x%SCREEN_WIDTH
            # if camera_y == 0:
            #     y = pos.y
            # if camera_y == MAP_NUMS[1]*TILE_SIZE - SCREEN_HEIGHT:
            #     y = pos.y%SCREEN_HEIGHT
            
            # pygame.draw.rect(self._screen, (255, 0, 0), (x, y, 40, 40))
            # -----------------------
            # DRAW WORLD (no player)
            # -----------------------
            map_width  = MAP_NUMS[0] * TILE_SIZE
            map_height = MAP_NUMS[1] * TILE_SIZE

            self.camera_x = self.player._pos.x - SCREEN_WIDTH // 2
            self.camera_y = self.player._pos.y - SCREEN_HEIGHT // 2

            self.camera_x = max(0, min(self.camera_x, map_width  - SCREEN_WIDTH))
            self.camera_y = max(0, min(self.camera_y, map_height - SCREEN_HEIGHT))

            list(self.executor.map(lambda x: x.draw(self._screen, pos), self.wisp))
            list(self.executor.map(lambda x: x.draw(self._screen, pos), self.goblin))
            list(self.executor.map(lambda x: x.draw(self._screen, pos), self.crystal))
            # draw fire gate
            self.fire_gate.draw(self._screen, self.camera_x, self.camera_y)
            for m in self.magatamas:
                m.draw(self._screen, self.camera_x, self.camera_y)

            # draw boss
            self.boss.draw(self._screen, self.camera_x, self.camera_y)

            for knife in self.knives:
                knife.draw(self._screen, self.camera_x, self.camera_y)
            for p in self.enemy_particles:
                p.draw(self._screen, self.camera_x, self.camera_y)
            for proj in self.enemy_projectiles:
                proj.draw(self._screen, self.camera_x, self.camera_y)

            # -----------------------
            # APPLY FILTER SAFELY
            # -----------------------
            if self.time_stop:
                filtered = apply_grayscale(self._screen.copy())
            else:
                filtered = self._screen

            # -----------------------
            # HP/MP bar
            # -----------------------
            hp_bar = self.loader.get_image("hp_bar")
            mp_bar = self.loader.get_image("mp_bar")

            # ratios
            hp_ratio = self.player.hp / self.player.hp_max
            mp_ratio = self.player.mp / self.player.mp_max

            # clamp
            hp_ratio = max(0, min(1, hp_ratio))
            mp_ratio = max(0, min(1, mp_ratio))

            # --- crop width ---
            hp_width = int(hp_bar.get_width() * hp_ratio)
            mp_width = int(mp_bar.get_width() * mp_ratio)

            # create cropped surfaces
            hp_crop = pygame.Surface((hp_width, hp_bar.get_height()), pygame.SRCALPHA)
            mp_crop = pygame.Surface((mp_width, mp_bar.get_height()), pygame.SRCALPHA)
            # --- position (under your gauge UI) ---
            base_x = SCREEN_WIDTH // 2 - 199   # tweak this
            base_y = 25                        # tweak this

            hp_crop.blit(hp_bar, (0, 0), (0, 0, hp_width, hp_bar.get_height()))
            mp_crop.blit(mp_bar, (0, 0), (0, 0, mp_width, mp_bar.get_height()))

            # draw HP (top)
            filtered.blit(hp_crop, (base_x, base_y))
            value = int(self.shared_time_stop_energy)
            digits = list(str(value))

            # -----------------------
            # BOSS HP BAR
            # -----------------------
            if self.boss and self.boss.hp > 0:

                base_bar = self.loader.get_image("hp_bar")
                boss_bar = recolor_red(base_bar)

                # --- Stretch horizontally ---
                stretch_w = int(boss_bar.get_width() * 1.7)   # widen boss bar
                stretch_h = boss_bar.get_height()

                boss_bar = pygame.transform.scale(boss_bar, (stretch_w, stretch_h))

                ratio = self.boss.hp / self.boss.max_hp
                ratio = max(0, min(1, ratio))

                width = int(stretch_w * ratio)

                crop = pygame.Surface((width, stretch_h), pygame.SRCALPHA)
                crop.blit(boss_bar, (0,0), (0,0,width,stretch_h))

                # centered top
                x = SCREEN_WIDTH//2 - stretch_w//2 + 160
                y = 25

                filtered.blit(crop, (x, y))
        
            # -----------------------
            # GAUGE
            # -----------------------
            gauge = self.loader.get_image("gauge")

            # draw MP (below HP)
            filtered.blit(mp_crop, (base_x, base_y + 12))

            value = int(self.shared_time_stop_energy)
            digits = list(str(value))
        
            # -----------------------
            # GAUGE
            # -----------------------
            gauge = self.loader.get_image("gauge")
            gauge_rect = gauge.get_rect(midtop=(
            SCREEN_WIDTH // 2 + OFFSET_X,
            -15  # small padding from top
        ))


            filtered.blit(gauge, gauge_rect)

            # -----------------------
            # TIME
            # -----------------------
            value = int(self.shared_time_stop_energy)
            value = max(0, min(999, value))  # clamp

            digits = list(str(value))

            digit_images = [
                self.loader.get_image(f"time_number_sprite_{d}")
                for d in digits
            ]

            spacing = 2
            # --- adjust these ---
            circle_center_x = SCREEN_WIDTH // 2 + OFFSET_X
            circle_center_y = 44
            # --------------------

            total_width = sum(img.get_width() for img in digit_images) + spacing * (len(digit_images) - 1)


            start_x = circle_center_x - total_width // 2

            x = start_x
            for img in digit_images:
                y = circle_center_y - img.get_height() // 2
                filtered.blit(img, (x, y))
                x += img.get_width() + spacing

            # -----------------------
            # DRAW PLAYER ON TOP (NOT FILTERED)
            # -----------------------
            self.player.draw(filtered)
            
            # ===== DRAW REMOTE PLAYERS =====
            self._draw_remote_players(filtered)
            if not self._using_local_world_sync():
                self._draw_remote_enemies(filtered)
            self._draw_remote_projectiles(filtered)
            self._draw_remote_enemy_particles(filtered)
            
            # ===== DRAW NETWORK STATUS =====
            self._draw_network_status(filtered)
            
            # -----------------------
            # SCALE + DISPLAY
            # -----------------------
            scaled = pygame.transform.scale(
                filtered,
                (SCREEN_WIDTH * GAME_SCALE, SCREEN_HEIGHT * GAME_SCALE)
            )
        
        self._display.blit(scaled, (0,0))
        pygame.display.flip()
    
    def _draw_remote_players(self, screen):
        """Draw remote players on screen"""
        if not self.enable_multiplayer or not self.net_manager:
            return
        
        remote_players = self.net_manager.get_remote_players()
        if not remote_players:
            return
        
        font = pygame.font.SysFont(None, 20)
        
        for player_id, player_data in remote_players.items():
            try:
                pos_x = player_data.get('pos_x', 0)
                pos_y = player_data.get('pos_y', 0)
                current_anim = player_data.get('current_anim', player_data.get('animation_state', 'idle'))
                facing_right = player_data.get('facing_right', True)
                
                # Adjust for camera
                screen_x = int(pos_x - self.camera_x)
                screen_y = int(pos_y - self.camera_y)
                
                # Only draw if on screen
                if -50 < screen_x < SCREEN_WIDTH + 50 and -50 < screen_y < SCREEN_HEIGHT + 50:
                    self._draw_remote_player_sprite(screen, player_data)
                    label = font.render(player_id[:6], True, (0, 255, 0))
                    screen.blit(label, (screen_x - 15, screen_y - 42))
            except (KeyError, TypeError):
                pass
    
    def _draw_remote_enemies(self, screen):
        """Draw remote enemies on screen"""
        if not self.enable_multiplayer or not self.net_manager:
            return

        remote_enemies = self.net_manager.get_remote_enemies()
        if not remote_enemies:
            return

        font = pygame.font.SysFont(None, 20)
        for enemy_id, enemy_data in remote_enemies.items():
            try:
                if not enemy_data.get('alive', True) or enemy_data.get('dead', False):
                    continue
                entity_type = enemy_data.get('entity_type', '')
                if entity_type == 'boss':
                    continue  # Boss is drawn separately
                pos_x = enemy_data.get('pos_x', 0)
                pos_y = enemy_data.get('pos_y', 0)
                screen_x = int(pos_x - self.camera_x)
                screen_y = int(pos_y - self.camera_y)
                if -50 < screen_x < SCREEN_WIDTH + 50 and -50 < screen_y < SCREEN_HEIGHT + 50:
                    pygame.draw.circle(screen, (255, 100, 100), (screen_x, screen_y), 14)
                    label = font.render(enemy_id[:6], True, (255, 100, 100))
                    screen.blit(label, (screen_x - 15, screen_y - 30))
            except (KeyError, TypeError):
                pass

    def _draw_remote_projectiles(self, screen):
        """Draw remote projectiles on screen"""
        if not self.enable_multiplayer or not self.net_manager:
            return

        remote_projectiles = self.net_manager.get_remote_projectiles()
        if not remote_projectiles:
            return

        for projectile_data in remote_projectiles.values():
            try:
                if not projectile_data.get('alive', True):
                    continue
                if projectile_data.get('projectile_id') in self.consumed_remote_projectiles:
                    continue
                self._draw_remote_projectile_sprite(screen, projectile_data)
            except (KeyError, TypeError):
                pass

    def _draw_remote_enemy_particles(self, screen):
        """Draw remote enemy particles on screen"""
        if not self.enable_multiplayer or not self.net_manager:
            return

        remote_enemy_particles = self.net_manager.get_remote_enemy_particles()
        if not remote_enemy_particles:
            return

        print(f"[DEBUG] Drawing remote enemy particles: {list(remote_enemy_particles.keys())}")

        for particle_data in remote_enemy_particles.values():
            try:
                if not particle_data.get('alive', True):
                    continue
                
                class_name = particle_data.get('class_name')
                if class_name == "SmokeColumn":
                    # Special drawing for SmokeColumn
                    pos_x = particle_data.get('pos_x', 0)
                    pos_y = particle_data.get('pos_y', 0)
                    frame_index = particle_data.get('frame_index', 0)
                    
                    print(f"[DEBUG] Drawing SmokeColumn at {pos_x}, {pos_y}")
                    
                    frames = self.loader.get_animation("smoke")
                    if not frames:
                        continue
                    
                    # Tint frames red like local
                    tinted_frames = [tint_surface_red(f) for f in frames]
                    frame = tinted_frames[frame_index % len(tinted_frames)]
                    h = frame.get_height()
                    layers = 4  # Always 4 layers like local
                    overlap = h * 0.45
                    height = int(h + (layers - 1) * overlap)
                    
                    # Calculate bottom y from center y
                    bottom_y = pos_y + height // 2
                    
                    for i in range(layers):
                        # Fade higher layers slightly
                        alpha = int(255 * (1 - i * 0.18))
                        frame_copy = frame.copy()
                        frame_copy.set_alpha(alpha)
                        
                        rect = frame_copy.get_rect(midbottom=(pos_x, bottom_y - i * overlap))
                        screen.blit(frame_copy, rect.move(-self.camera_x, -self.camera_y))
                else:
                    # Draw enemy particles
                    image = self._get_enemy_particles_visual(particle_data)
                    if image is None:
                        continue
                    
                    pos_x = particle_data.get('pos_x', 0)
                    pos_y = particle_data.get('pos_y', 0)
                    
                    rect = image.get_rect(center=(int(pos_x), int(pos_y)))
                    screen.blit(image, rect.move(-self.camera_x, -self.camera_y))
                
            except (KeyError, TypeError):
                pass

    def _draw_network_status(self, screen):
        """Draw network status indicator"""
        font = pygame.font.SysFont(None, 24)
        font_small = pygame.font.SysFont(None, 18)
        
        if self.enable_multiplayer and self.net_manager:
            if self.net_manager.is_multiplayer_enabled():
                player_count = self.net_manager.get_player_count() + 1
                status_text = f"🟢 ONLINE"
                detail_text = f"({player_count} player{'s' if player_count != 1 else ''})"
                color = (0, 255, 0)
            else:
                status_text = "🔴 OFFLINE"
                detail_text = "No connection"
                color = (255, 100, 100)
        else:
            status_text = "OFFLINE"
            detail_text = "Single-player"
            color = (200, 200, 200)
        
        # Draw status
        text_surface = font.render(status_text, True, color)
        screen.blit(text_surface, (10, 10))
        
        # Draw detail
        detail_surface = font_small.render(detail_text, True, color)
        screen.blit(detail_surface, (10, 35))

    def _assign_world_ids(self):
        for index, enemy in enumerate(self.wisp):
            enemy.enemy_id = f"wisp_{index}"
        for index, enemy in enumerate(self.goblin):
            enemy.enemy_id = f"goblin_{index}"
        for index, crystal in enumerate(self.crystal):
            crystal.enemy_id = f"crystal_{index}"
        for index, magatama in enumerate(self.magatamas):
            magatama.enemy_id = f"magatama_{index}"
        if self.fire_gate:
            self.fire_gate.enemy_id = "fire_gate_0"
        if self.boss:
            self.boss.enemy_id = "boss_main"

    def _assign_projectile_ids(self, projectiles):
        owner = "offline"
        if self.net_manager and getattr(self.net_manager, "client", None):
            owner = self.net_manager.client.player_id or owner

        for projectile in projectiles:
            if not hasattr(projectile, "projectile_id"):
                projectile.projectile_id = f"{owner}_proj_{self.projectile_sequence}"
                self.projectile_sequence += 1

    def _assign_particle_ids(self, particles):
        """Assign network IDs to particles (like projectiles)"""
        owner = "offline"
        if self.net_manager and getattr(self.net_manager, "client", None):
            owner = self.net_manager.client.player_id or owner

        for particle in particles:
            if not hasattr(particle, "projectile_id"):
                particle.projectile_id = f"{owner}_particle_{self.projectile_sequence}"
                self.projectile_sequence += 1

    def _get_local_map_state(self):
        if not hasattr(self, "collision_map") or self.collision_map is None:
            return {'black': False, 'incoming_signal': False}
        return {
            'black': getattr(self.collision_map, 'black', False),
            'incoming_signal': getattr(self.collision_map, 'incoming_signal', False),
        }

    def _sync_map_interactions(self):
        current_state = self._get_local_map_state()

        if not self.enable_multiplayer or not self.net_manager or not self.net_manager.connected:
            self._last_sent_map_state = current_state.copy()
            return

        if self._last_sent_map_state != current_state:
            self.net_manager.send_map_state(self.collision_map)
            self._last_sent_map_state = current_state.copy()

    def _sync_destroyed_knives(self):
        current_ids = {
            knife.projectile_id
            for knife in self.knives
            if hasattr(knife, "projectile_id")
        }
        destroyed_ids = self._last_local_knife_ids - current_ids

        if self.enable_multiplayer and self.net_manager and self.net_manager.connected and destroyed_ids:
            self.net_manager.send_projectile_destroyed(destroyed_ids)

        self._last_local_knife_ids = current_ids

    def _draw_remote_player_sprite(self, screen, player_data):
        player_no = int(player_data.get('player_no', 1)) if player_data.get('player_no') is not None else 1
        template = self.remote_player_templates.get(player_no, self.remote_player_templates[1])
        current_anim = player_data.get('current_anim', player_data.get('animation_state', 'idle'))
        frames = template.animations.get(current_anim) or template.animations.get("idle")
        if not frames:
            return

        image = frames[0]
        if len(frames) > 1:
            frame_index = player_data.get('frame_index', 0)
            image = frames[frame_index % len(frames)]

        facing_right = player_data.get('facing_right', True)
        if not facing_right:
            image = pygame.transform.flip(image, True, False)

        draw_pos = (int(player_data.get('pos_x', 0)), int(player_data.get('pos_y', 0)))
        if current_anim in ("up_shot", "up_shot2", "up_shot_air", "up_shot_run"):
            draw_pos = (draw_pos[0], draw_pos[1] - 32)

        offset = template.anim_offsets.get(current_anim, (0, 0))
        if isinstance(offset, dict):
            offset_x, offset_y = offset["right"] if facing_right else offset["left"]
        else:
            offset_x, offset_y = offset
            if not facing_right:
                offset_x = -offset_x

        world_rect = image.get_rect(midtop=(
            draw_pos[0] + offset_x,
            draw_pos[1] + offset_y
        ))
        screen.blit(image, world_rect.move(-self.camera_x, -self.camera_y))

    def _draw_remote_projectile_sprite(self, screen, projectile_data):
        class_name = projectile_data.get('class_name')
        if class_name == "MasterSparkProjectile":
            self._draw_remote_master_spark(screen, projectile_data)
            return        
        image = self._get_projectile_visual(projectile_data)
        if image is None:
            return

        if not projectile_data.get('facing_right', True):
            image = pygame.transform.flip(image, True, False)

        pos_x = projectile_data.get('pos_x', 0)
        pos_y = projectile_data.get('pos_y', 0)

        if class_name == "Knife":
            vel = pygame.Vector2(projectile_data.get('vel_x', 0), projectile_data.get('vel_y', 0))
            if vel.length_squared() > 0:
                angle = vel.angle_to(pygame.Vector2(1, 0))
                image = pygame.transform.rotate(image, angle)

        if class_name == "UndershotProjectile" and projectile_data.get('state') == "laser":
            rect = image.get_rect(midbottom=(int(pos_x), BOSS_ARENA.bottom + 70))
        else:
            rect = image.get_rect(center=(int(pos_x), int(pos_y)))

        screen.blit(image, rect.move(-self.camera_x, -self.camera_y))

    def _draw_remote_master_spark(self, screen, projectile_data):
        boss_x = projectile_data.get('boss_x')
        boss_y = projectile_data.get('boss_y')
        if boss_x is None or boss_y is None:
            return

        anim_a = self.boss.supershot["a"]
        anim_b = self.boss.supershot["b"]
        anim_c = self.boss.supershot["c"]
        anim_d = self.boss.supershot["d"]
        frame = projectile_data.get('frame_index', 0)
        ground_y = projectile_data.get('ground_y', BOSS_ARENA.bottom + 70)
        start_y = boss_y + 20

        frame_a = anim_a[frame % len(anim_a)]
        rect_a = frame_a.get_rect(midtop=(boss_x, start_y))
        screen.blit(frame_a, rect_a.move(-self.camera_x, -self.camera_y))

        current_y = start_y + frame_a.get_height() - 24
        i = 0
        while current_y < ground_y:
            body = anim_b[frame % len(anim_b)] if i % 2 == 0 else anim_c[frame % len(anim_c)]
            seg_bottom = current_y + body.get_height()
            if seg_bottom > ground_y:
                visible_height = ground_y - current_y
                if visible_height <= 0:
                    break
                body = body.subsurface((0, 0, body.get_width(), visible_height))
            rect = body.get_rect(midtop=(boss_x, current_y))
            screen.blit(body, rect.move(-self.camera_x, -self.camera_y))
            if seg_bottom > ground_y:
                break
            current_y += body.get_height()
            i += 1

        frame_d = anim_d[frame % len(anim_d)]
        rect_d = frame_d.get_rect(midbottom=(boss_x, ground_y))
        screen.blit(frame_d, rect_d.move(-self.camera_x, -self.camera_y))

    def _get_shared_world_objects(self):
        objects = []
        objects.extend(self.wisp)
        objects.extend(self.goblin)
        objects.extend(self.crystal)
        objects.extend(self.magatamas)
        if self.fire_gate:
            objects.append(self.fire_gate)
        if self.boss:
            objects.append(self.boss)
        return objects

    def _is_world_authority(self):
        if not self.enable_multiplayer or not self.net_manager:
            return True
        return self.net_manager.is_world_authority()

    def _using_local_world_sync(self):
        return self.enable_multiplayer and self.net_manager and not self._is_world_authority()

    def _sync_global_time_stop_from_network(self):
        if self.player is None:
            return

        if not self.enable_multiplayer or not self.net_manager:
            self.shared_time_stop_active = self.player.time_stop or self.player.time_stop_startup or self.player.time_stop_ending
            self.shared_time_stop_energy = self.player.time_energy
            self.time_stop = self.shared_time_stop_active
            if self._prev_shared_time_stop_active and not self.shared_time_stop_active:
                self.player.force_end_time_stop()
            self._prev_shared_time_stop_active = self.shared_time_stop_active
            return

        if self._is_world_authority():
            active_states = []
            players = list(self.net_manager.get_remote_players().values())
            players.append({
                'time_stop': self.player.time_stop,
                'time_stop_startup': self.player.time_stop_startup,
                'time_stop_ending': self.player.time_stop_ending,
                'time_energy': self.player.time_energy,
            })
            ending = any(player_data.get('time_stop_ending') for player_data in players)
            active_states = [
                player_data for player_data in players
                if player_data.get('time_stop') or player_data.get('time_stop_startup')
            ]
            self.shared_time_stop_active = bool(active_states) and not ending
            if active_states:
                self.shared_time_stop_energy = min(
                    player_data.get('time_energy', self.shared_time_stop_energy)
                    for player_data in active_states
                )
            else:
                self.shared_time_stop_energy = self.player.time_energy
        else:
            shared_state = self.net_manager.get_remote_shared_state()
            self.shared_time_stop_active = shared_state.get('time_stop_active', False)
            self.shared_time_stop_energy = shared_state.get('time_stop_energy', self.player.time_energy)

        self.time_stop = self.shared_time_stop_active
        if self._prev_shared_time_stop_active and not self.shared_time_stop_active:
            self.player.force_end_time_stop()
        self._prev_shared_time_stop_active = self.shared_time_stop_active

    def _apply_remote_world_state(self):
        if not self.enable_multiplayer or not self.net_manager:
            return

        remote_enemies = self.net_manager.get_remote_enemies()
        if not remote_enemies:
            return

        local_objects = {
            getattr(obj, "enemy_id", None): obj
            for obj in self._get_shared_world_objects()
            if getattr(obj, "enemy_id", None)
        }

        for enemy_id, enemy_data in remote_enemies.items():
            local_obj = local_objects.get(enemy_id)
            if local_obj is None:
                continue
            EnemyStateData.deserialize(enemy_data, local_obj)
            self._apply_synced_object_visual_state(local_obj, enemy_data)
            self._realign_synced_object(local_obj)

        self.magatamas = [m for m in self.magatamas if getattr(m, "alive", True)]

        remote_projectiles = self.net_manager.get_remote_projectiles()
        active_ids = set(remote_projectiles.keys())
        self.enemy_projectiles = [
            projectile for projectile in self.enemy_projectiles
            if getattr(projectile, "projectile_id", None) in active_ids
        ]

    def _apply_synced_object_visual_state(self, obj, data):
        frame_index = data.get('frame_index', 0)

        if isinstance(obj, Wisp):
            if data.get('dead', False):
                obj._died = True
                if obj._ded_frames:
                    obj._frames = obj._ded_frames
                    obj._frame_index = min(frame_index, len(obj._frames) - 1)
                    obj._image = obj._frames[obj._frame_index]
            elif not data.get('alive', True):
                obj._died = False
                obj._alive = False
                obj._frames = obj._ded_frames
                obj._frame_index = min(frame_index, len(obj._frames) - 1)
                obj._image = obj._frames[obj._frame_index]
            else:
                obj._died = False
                obj._alive = True
                obj._frames = obj._normal_frames
                obj._frame_index = frame_index % len(obj._frames)
                obj._image = obj._frames[obj._frame_index]
        elif isinstance(obj, Goblin):
            if data.get('dead', False):
                obj._died = True
                obj._frames = obj._animations["die"]
            elif obj._health <= 0:
                obj._died = False
                obj._frames = obj._animations["die"]
            elif obj._attack:
                obj._died = False
                obj._frames = obj._animations["attack"]
            else:
                obj._died = False
                obj._frames = obj._animations["run"]
            obj._frame_index = min(frame_index, len(obj._frames) - 1)
            obj._image = obj._frames[obj._frame_index]
        elif isinstance(obj, Crystal):
            if data.get('dead', False):
                obj._died = True
                obj._alive = False
                obj._image_index = min(frame_index, len(obj._death_frames) - 1)
                obj._image = obj._death_frames[obj._image_index]
            elif obj._alive:
                obj._died = False
                obj._image = obj._frame[0]
            else:
                obj._died = False
                obj._image_index = min(frame_index, len(obj._death_frames) - 1)
                obj._image = obj._death_frames[obj._image_index]
        elif isinstance(obj, Boss):
            if data.get('dead', False):
                obj._dying = False
                obj._dead = True
                obj.set_animation("ded", restart=True)
            elif data.get('dying', False):
                obj._dead = False
                obj._dying = True
                obj.set_animation("dying", restart=True)
            elif obj.current_anim in obj.animations:
                obj._dead = False
                obj._dying = False
                frames = obj.animations[obj.current_anim]
                obj.frame_index = frame_index % len(frames)
                obj.frames = frames
                obj.image = frames[obj.frame_index]
        elif isinstance(obj, FireGate):
            obj.frame_index = frame_index % len(obj.frames)
            obj.image = obj.frames[int(obj.frame_index)]

    def _apply_remote_world_interactions(self, dt):
        player_hurtbox = self.player.get_hurtbox_rect()

        for wisp in self.wisp:
            if not getattr(wisp, "_alive", False) or getattr(wisp, "_died", False):
                continue
            if self.knives:
                wisp.is_hit(self.knives)
            if wisp._rect.colliderect(player_hurtbox):
                self.player.apply_damage(WISP_DAMAGE, wisp._pos.x)

        for goblin in self.goblin:
            if getattr(goblin, "_health", 0) <= 0 or getattr(goblin, "_died", False):
                continue
            if self.knives:
                goblin.is_hit(self.knives)
            goblin.update_hurtbox()
            if goblin._attack:
                if goblin.did_hit(self.player):
                    self.player.apply_damage(GOB_DAMAGE, goblin._pos.x)

        if self.boss and self.boss.visible and not self.boss._dead and not self.boss._dying:
            if self.knives:
                self.boss.is_hit(self.knives)
            self.boss.update_hurtbox()
            if self.boss.hurtbox.colliderect(player_hurtbox):
                self.player.apply_damage(10, self.boss.hurtbox.centerx)

        if self.fire_gate and self.fire_gate.rect.colliderect(player_hurtbox) and not self.player.get_fire():
            self.player.apply_damage(25, self.fire_gate.rect.centerx)

        for magatama in self.magatamas:
            if not magatama.alive:
                continue
            dx = abs(self.player._pos.x - magatama.pos.x)
            dy = abs(self.player._pos.y - magatama.pos.y)
            if dx < 20 and dy < 20:
                self.player.fire_upgrade()
                magatama.alive = False

        for crystal in self.crystal:
            if self.knives:
                crystal.is_hit(self.knives)
            item = getattr(crystal, "_item", None)
            if item:
                item.update(dt, self.player)

    def _get_projectile_visual(self, projectile_data):
        class_name = projectile_data.get('class_name')
        frame_index = projectile_data.get('frame_index', 0)

        if class_name == "Knife":
            frames = self.loader.get_animation("flying_knife")
            return frames[frame_index % len(frames)]
        if class_name == "TimeShotProjectile":
            frames = self.loader.get_animation("marisa_timeshot")
            return frames[frame_index % len(frames)]
        if class_name == "UndershotProjectile":
            if projectile_data.get('state') == "laser":
                frames = self.loader.get_animation("marisa_laser")
                frame = frames[frame_index % len(frames)]
                return pygame.transform.scale(frame, (frame.get_width(), SCREEN_HEIGHT))
            frames = self.loader.get_animation("marisa_undershot_a")
            return frames[frame_index % len(frames)]
        if class_name == "ShotProjectile":
            frames = self.loader.get_animation("marisa_shot_a")
            return frames[frame_index % len(frames)]
        return None

    def _get_enemy_particles_visual(self, particle_data):
        """Get visual representation for enemy particles"""
        class_name = particle_data.get('class_name')
        frame_index = particle_data.get('frame_index', 0)

        if class_name == "DashTrail":
            frames = self.loader.get_animation("marisa_after_effect_s")
            return frames[frame_index % len(frames)]
        if class_name == "ZangaiTrail":
            frames = self.loader.get_animation("marisa_zangai")
            return frames[frame_index % len(frames)]
        if class_name == "SmokeColumn":
            # SmokeColumn has special drawing logic, return single frame
            frames = self.loader.get_animation("smoke")
            return frames[frame_index % len(frames)]
        return None

    def _build_remote_projectile_hitbox(self, projectile_data):
        class_name = projectile_data.get('class_name')
        image = self._get_projectile_visual(projectile_data)

        if class_name == "MasterSparkProjectile":
            boss_x = projectile_data.get('boss_x')
            boss_y = projectile_data.get('boss_y')
            ground_y = projectile_data.get('ground_y', BOSS_ARENA.bottom + 70)
            if boss_x is None or boss_y is None:
                return None
            return pygame.Rect(int(boss_x - 28), int(boss_y + 20), 56, int(ground_y - (boss_y + 20)))

        if image is None:
            return None

        pos_x = projectile_data.get('pos_x', 0)
        pos_y = projectile_data.get('pos_y', 0)
        if class_name == "UndershotProjectile" and projectile_data.get('state') == "laser":
            rect = image.get_rect(midbottom=(int(pos_x), BOSS_ARENA.bottom + 70))
            return get_tight_hitbox(image, rect, "midbottom")

        rect = image.get_rect(center=(int(pos_x), int(pos_y)))
        return get_tight_hitbox(image, rect, "center")

    def _build_remote_enemy_particles_hitbox(self, particle_data):
        """Build hitbox for remote enemy particles"""
        class_name = particle_data.get('class_name')
        pos_x = particle_data.get('pos_x', 0)
        pos_y = particle_data.get('pos_y', 0)

        if class_name == "SmokeColumn":
            # SmokeColumn has a rect covering the stacked column
            frames = self.loader.get_animation("smoke")
            if frames:
                frame = frames[0]
                h = frame.get_height()
                layers = 4  # Always 4 layers
                overlap = h * 0.45
                height = int(h + (layers - 1) * overlap)
                width = frame.get_width()
                return pygame.Rect(int(pos_x - width//2), int(pos_y - height), width, height)
        else:
            pass
        return None

    def _damage_synced_object_from_remote_knife(self, projectile_id, hitbox):
        if projectile_id in self.processed_remote_projectile_hits:
            return

        for wisp in self.wisp:
            if not getattr(wisp, "_alive", False) or getattr(wisp, "_died", False):
                continue
            if hitbox.colliderect(wisp._rect):
                wisp._alive = False
                wisp._frames = wisp._ded_frames
                wisp._frame_index = 0
                wisp._anim_timer = 0
                wisp._image = wisp._frames[0]
                self.processed_remote_projectile_hits.add(projectile_id)
                self.consumed_remote_projectiles.add(projectile_id)
                return

        for goblin in self.goblin:
            if getattr(goblin, "_health", 0) <= 0 or getattr(goblin, "_died", False):
                continue
            goblin.update_hurtbox()
            if hitbox.colliderect(goblin._hurtbox):
                goblin._health -= 1
                goblin._hit = True
                goblin._shake_timer = 0
                if goblin._health <= 0:
                    goblin._health = 0
                    goblin._frames = goblin._animations["die"]
                    goblin._frame_index = 0
                    goblin._image = goblin._frames[0]
                self.processed_remote_projectile_hits.add(projectile_id)
                self.consumed_remote_projectiles.add(projectile_id)
                return

        for crystal in self.crystal:
            if getattr(crystal, "_died", False):
                continue
            crystal.update_hurtbox()
            if hitbox.colliderect(crystal._hurtbox):
                crystal._hit = True
                crystal._shake_timer = 0
                crystal._health -= 1
                if crystal._health <= 0 and crystal._alive:
                    crystal._alive = False
                    crystal._frame_timer = 0
                    crystal._image_index = 0
                    crystal._image = crystal._death_frames[0]
                    crystal._item._pop = True
                    crystal._item._shown = True
                self.processed_remote_projectile_hits.add(projectile_id)
                self.consumed_remote_projectiles.add(projectile_id)
                return

        if self.boss and self.boss.visible and not self.boss._dead and not self.boss._dying:
            self.boss.update_hurtbox()
            if hitbox.colliderect(self.boss.hurtbox):
                self.boss.take_damage(15)
                self.processed_remote_projectile_hits.add(projectile_id)
                self.consumed_remote_projectiles.add(projectile_id)
                return

    def _apply_remote_projectile_interactions(self):
        player_hurtbox = self.player.get_hurtbox_rect()
        remote_projectiles = self.net_manager.get_remote_projectiles()
        active_projectile_ids = {
            projectile_id
            for projectile_id, projectile_data in remote_projectiles.items()
            if projectile_data.get('alive', True)
        }
        self.processed_remote_projectile_hits &= active_projectile_ids
        self.consumed_remote_projectiles &= active_projectile_ids

        for projectile_id, projectile_data in remote_projectiles.items():
            if not projectile_data.get('alive', True):
                continue
            if projectile_id in self.consumed_remote_projectiles:
                continue
            hitbox = self._build_remote_projectile_hitbox(projectile_data)
            if not hitbox:
                continue

            class_name = projectile_data.get('class_name')
            owner_id = projectile_data.get('owner_id')
            local_player_id = self.net_manager.client.player_id if self.net_manager and self.net_manager.client else None

            if class_name == "Knife":
                if owner_id != local_player_id:
                    self._damage_synced_object_from_remote_knife(projectile_id, hitbox)
                continue

            if hitbox.colliderect(player_hurtbox):
                damage = 0
                if class_name == "UndershotProjectile":
                    damage = 10 if projectile_data.get('state') == "laser" else 20
                elif class_name == "ShotProjectile":
                    damage = 15
                elif class_name == "MasterSparkProjectile":
                    damage = 40
                if damage:
                    self.player.apply_damage(damage, hitbox.centerx)
                    if class_name in {"ShotProjectile", "UndershotProjectile"}:
                        self.consumed_remote_projectiles.add(projectile_id)

    def _apply_remote_enemy_particles_interactions(self, dt):
        """Apply interactions with remote enemy particles (e.g., smoke drains time energy)"""
        if not self.enable_multiplayer or not self.net_manager:
            return

        player_hurtbox = self.player.get_hurtbox_rect()
        remote_particles = self.net_manager.get_remote_enemy_particles()

        for particle_id, particle_data in remote_particles.items():
            if not particle_data.get('alive', True):
                continue

            class_name = particle_data.get('class_name')
            if class_name == "SmokeColumn":
                # SmokeColumn drains shared time energy when player is hit
                hitbox = self._build_remote_enemy_particles_hitbox(particle_data)
                if hitbox and hitbox.colliderect(player_hurtbox):
                    self.shared_time_stop_energy -= 50 * dt
                    self.player._inSmoke = True

    def _realign_synced_object(self, obj):
        if isinstance(obj, Wisp):
            obj._rect.center = (int(obj._pos.x), int(obj._pos.y))
        elif isinstance(obj, Goblin):
            obj._rect.topleft = (int(obj._pos.x), int(obj._pos.y))
            if hasattr(obj, "update_hurtbox"):
                obj.update_hurtbox()
        elif isinstance(obj, Crystal):
            obj._rect.midbottom = (int(obj._pos.x), int(obj._pos.y))
            if hasattr(obj, "update_hurtbox"):
                obj.update_hurtbox()
        elif isinstance(obj, Magatama):
            obj.rect.center = (int(obj.pos.x), int(obj.pos.y))
        elif isinstance(obj, FireGate):
            obj.rect.midbottom = (int(obj.pos.x), int(obj.pos.y))
        elif isinstance(obj, Boss):
            obj.rect.midtop = (int(obj.pos.x), int(obj.pos.y))
            if hasattr(obj, "update_hurtbox"):
                obj.update_hurtbox()
    

    def disconnect_network(self):
        """Cleanup network connection"""
        if self.net_manager and self.enable_multiplayer:
            self.net_manager.disconnect()
            print("[GAME] Disconnected from server")
    
    def save(self, savename=None):
        """Save current game progress to new save / override current save"""
        pass

    def load(self, savename):
        """Load saved progress"""
        pass

    # -----------------------
    # GAME LOOP
    # -----------------------

    def play(self):
        while True:
            dt = self._clock.tick(FPS) / 1000.0
            
            # ===== NETWORK UPDATE =====
            if self.net_manager:
                self.net_manager.update(dt)
                self.net_manager.apply_remote_map_state(self.collision_map)
                self._last_sent_map_state = self._get_local_map_state()
                if self._using_local_world_sync():
                    self._apply_remote_world_state()
            self._sync_global_time_stop_from_network()

            self.handleInput()
            if not self.in_menu:
                self.update(dt)
                self.check_collision()
                self._sync_map_interactions()
                
                # ===== SEND PLAYER STATE TO NETWORK =====
                if self.net_manager and self.enable_multiplayer:
                    self.net_manager.send_player_state(self.player)
                    if self._is_world_authority():
                        self.net_manager.send_world_state(
                            self._get_shared_world_objects(),
                            self.knives + self.enemy_projectiles,
                            self.enemy_particles,
                            self.collision_map,
                            {
                                'time_stop_active': self.shared_time_stop_active,
                                'time_stop_energy': self.shared_time_stop_energy,
                            }
                        )
                    else:
                        self.net_manager.send_player_projectiles(self.knives)

            self.draw()
