import pygame
from settings import *
from boss_projectile import *
import random
import math

class Boss:
    def __init__(self, loader, game, character):

        self.game = game
        self.player = character

        self.animations = {
            "stand": loader.get_animation("marisa_idle"),
            "sit": loader.get_animation("marisa_down"),
            "stop": loader.get_animation("marisa_stop"),
            "sit_down": loader.get_animation("marisa_up_to_down"),
            "stand_up": loader.get_animation("marisa_down_to_up"),
            "standing_turn": loader.get_animation("marisa_dir_change"),
            "sitting_turn": loader.get_animation("marisa_dira_down_change"),
            "dash": loader.get_animation("marisa_dash"),
            "undershot": loader.get_animation("marisa_undershot"),
            "shot": loader.get_animation("marisa_shot"),
            "supershot": loader.get_animation("marisa_supershot"),
            "ded": loader.get_animation("marisa_des"),
            "dying": loader.get_animation("marisa_dying"),
        }

        self.timeshot = loader.get_animation("marisa_timeshot")
        self.undershot = loader.get_animation("marisa_undershot_a")
        self.laser = loader.get_animation("marisa_laser")
        self.after_effect = loader.get_animation("marisa_after_effect")
        self.after_effect_s = loader.get_animation("marisa_after_effect_s")
        self.shot = loader.get_animation("marisa_shot_a")
        self.zangai_frames = loader.get_animation("marisa_zangai")

        self._ded_frames = loader.get_animation("bomb_effect")
        self._explosions = []          # active explosions
        self._explosion_timer = 0
        self._explosion_interval = 0.12
        self._explosion_duration = 1.8
        self._explosion_total_time = 0

        self.supershot = {
            "a": loader.get_animation("marisa_supershot_a"),
            "b": loader.get_animation("marisa_supershot_b"),
            "c": loader.get_animation("marisa_supershot_c"),
            "d": loader.get_animation("marisa_supershot_d"),
        }

        self._pattern = [
            "timeshot_rl",
            "timeshot_lr",
            "shot_rl",
            "undershot_lr",
            "timeshot_rl",
            "dash_fake_lr",
            "dash_real_rl",
            "supershot_lr",
        ]

        self.height_levels = {
            "high": 810,
            "mid": 870,
            "low": 930,
            "dash": 960,
        }
        
        self.arena = BOSS_ARENA

        self.fast_anims = {
            "standing_turn",
            "sitting_turn",
            "stand_up",
            "sit_down",
        }
        # -----------------------
        # ANIMATION SYSTEM
        # -----------------------
        self.current_anim = "stop"
        self.frames = self.animations[self.current_anim]

        self.frame_index = 0
        self.frame_timer = 0
        self.frame_speed = 0.08

        self.image = self.frames[0]

        # Afterimage system
        self.afterimages = []
        self.afterimage_timer = 0

        # -----------------------
        # POSITION
        # -----------------------
        self.pos = pygame.Vector2(3436, 324)  # offscreen top-left
        self.rect = self.image.get_rect(midtop=(int(self.pos.x), int(self.pos.y)))

        # -----------------------
        # STATE MACHINE
        # -----------------------
        self.state = "intro_fly"
        self.hold_timer = 0
        self.transition_state = None

        # Facing: sprites look RIGHT by default
        self.facing_right = True

        self.pattern_index = 0
        self.pattern_loop_flipped = False

        # attack state machine
        self.attack_state = None
        self.attack_repeat = 0

        # movement targets
        self.target_x = 0

        # visibility
        self.visible = False

        # timeshot
        self.timeshot_drop_timer = 0
        self.timeshot_drop_interval = 0.25

        # shot
        self.burst_count = 0
        self.burst_timer = 0

        # undershot
        self.undershot_fire_timer = 0
        self.undershot_fire_interval = 0.35

        # dash
        self.dash_particles = []

        self.trail_timer_big = 0
        self.trail_timer_small = 0

        self.prev_pos = self.pos.copy()
        self.speed = 0

        # HP
        self.hp = 1000
        self.max_hp = 1000
        self.prev_hp = self.hp
        self._dead = False
        # hurt flash system
        self._hit = False
        self._shake_timer = 0
        self._shake_duration = 8
        # dead
        self._dying = False 
        self._dead_anim_done = False
        # MASTER SPARKSSSSSSSSSSSSS
        self.master_spark_proj = None

    def arena_left(self):  return self.arena.left
    def arena_right(self): return self.arena.right
    def arena_top(self):   return self.arena.top
    def arena_bottom(self):return self.arena.bottom

    # -----------------------
    # ANIMATION SWITCH
    # -----------------------
    def set_animation(self, name, restart=False):
        if self.current_anim != name or restart:
            self.current_anim = name
            self.frames = self.animations[name]
            self.frame_index = 0
            self.frame_timer = 0
            self.image = self.frames[0]

            # Faster playback for certain animations
            if name in self.fast_anims:
                self.frame_speed = 0.06
            else:
                self.frame_speed = 0.08

    # -----------------------
    # INTRO PATTERN
    # -----------------------
    def update_intro(self, dt):
        player_x = self.player._pos.x
        target_x = player_x + 250
        target_y = self.height_levels["high"]
        low_y = self.height_levels["low"]

        # --- FLY IN ---
        if self.state == "intro_fly":
            dx = target_x - self.pos.x
            dy = target_y - self.pos.y
            dist = math.hypot(dx, dy)

            if dist > 4:
                speed = 260
                self.pos.x += dx / dist * speed * dt
                self.pos.y += dy / dist * speed * dt
                self.set_animation("stop")
            else:
                self.pos.x = target_x
                self.pos.y = target_y
                self.state = "intro_turn"
                self.set_animation("standing_turn")

        # --- TURN (RIGHT → LEFT) ---
        elif self.state == "intro_turn":
            if self.frame_index >= len(self.frames) - 1:
                self.facing_right = False  # now face player
                self.state = "intro_hold"
                self.set_animation("stand")
                self.hold_timer = 0.2

        # --- HOLD STAND ---
        elif self.state == "intro_hold":
            self.hold_timer -= dt
            if self.hold_timer <= 0:
                self.state = "intro_descend"
                self.set_animation("sit_down")

        # --- DESCEND ---
        elif self.state == "intro_descend":
            if abs(self.pos.y - low_y) > 3:
                self.pos.y += 325 * dt
            else:
                self.pos.y = low_y

            if self.pos.y > low_y:
                self.pos.y = low_y

            if self.frame_index >= len(self.frames) - 1:
                self.state = "intro_done"
                self.set_animation("sit")

    # -----------------------
    # ANIMATION UPDATE
    # -----------------------
    def update_animation(self, dt):
        self.frame_timer += dt
        if self.frame_timer >= self.frame_speed:
            self.frame_timer = 0
            self.frame_index += 1

            # --- DYING ANIMATION ---
            if self._dying:
                if self.frame_index >= len(self.frames):
                    self._dying = False
                    self._dead = True
                    self.set_animation("ded", restart=True)
                    return

            # --- DEAD LOOP ---
            if self._dead:
                if self.frame_index >= len(self.frames):
                    self.frame_index = len(self.frames) - 1  # freeze last frame
                self.image = self.frames[self.frame_index]
                return

            # --- NORMAL LOOP ---
            if self.frame_index >= len(self.frames):
                self.frame_index = 0

        self.image = self.frames[self.frame_index]

    # -----------------------
    # UPDATE
    # -----------------------
    def update(self, dt, player_pos, knives):
        self.player_pos = player_pos

        # --- Calculate boss movement speed ---
        movement = self.pos - self.prev_pos
        if dt > 0:
            self.speed = movement.length() / dt
        else:
            self.speed = 0
        self.prev_pos = self.pos.copy()

        # -----------------------
        # DEATH FREEZE
        # -----------------------
        if self._dying or self._dead:
            self.update_animation(dt)
            self.rect.midtop = (int(self.pos.x), int(self.pos.y))
            self.update_hurtbox()

            # still update explosions
            self.update_explosions(dt)
            return

        # Detect HP decrease for remote damage flash
        if self.hp < self.prev_hp:
            self._hit = True
            self._shake_timer = 0

        self.update_intro(dt)
        if self.state == "intro_done":
            self.update_pattern(dt)
        elif self.state == "post_dash_recover" and self.hp > (self.max_hp/2):
            self.update_post_dash_recover(dt)
        elif self.state == "post_dash_recover":
            self.update_master_spark(dt)
        self.update_animation(dt)
        self.rect.midtop = (int(self.pos.x), int(self.pos.y))
        self.update_hurtbox()

        player_hurtbox = self.player.get_hurtbox_rect()

        if self.hurtbox.colliderect(player_hurtbox):
            self.player.apply_damage(10, self.hurtbox.centerx)

        if self.is_hit(knives):
            self._hit_flash = True

        # --- hurt flash update ---
        if self._hit:
            self._shake_timer += dt
            if self._shake_timer >= 1 / self._shake_duration:
                self._shake_timer = 0
                self._hit = False

        # -----------------------
        # BOSS AFTERIMAGES
        # -----------------------
        if not self._dying and not self._dead:
            self.afterimage_timer += dt

            # --- NORMAL SPEED TRAIL ---
            if self.speed < 600:
                if self.afterimage_timer >= 0.175:
                    self.afterimage_timer = 0

                    self.afterimages.append({
                        "pos": self.pos.copy(),
                        "frame": self.image.copy(),
                        "life": 0.35,
                        "type": "normal"
                    })

            # --- HIGH SPEED TRAIL ---
            else:
                if self.afterimage_timer >= 0.045:  # MUCH faster spawn
                    self.afterimage_timer = 0

                    self.afterimages.append({
                        "pos": self.pos.copy(),
                        "frame": self.image.copy(),
                        "life": 0.22,  # shorter life = sharper streak feel
                        "type": "fast"
                    })

            # Fade & cleanup
            for img in self.afterimages:
                img["life"] -= dt

            self.afterimages = [img for img in self.afterimages if img["life"] > 0]

        for p in self.dash_particles:
            p.update(dt)

        self.dash_particles = [p for p in self.dash_particles if p.alive]

        # Update prev_hp for damage detection
        self.prev_hp = self.hp

    # -----------------------
    # DRAW
    # -----------------------
    def draw(self, screen, camera_x, camera_y):
        if not self.visible:
            return
        image = self.image

        if not self.facing_right:
            image = pygame.transform.flip(image, True, False)
        
        # apply red flash if hit
        if self._hit:
            image = self.apply_flash_to(image)

        # -----------------------
        # DRAW AFTERIMAGES
        # -----------------------
        for img in self.afterimages:
            ghost = img["frame"].copy()

            if img["type"] == "normal":
                alpha = int(255 * (img["life"] / 0.35))
            else:  # fast trail
                alpha = int(200 * (img["life"] / 0.22))  # brighter & sharper

            ghost.set_alpha(alpha)

            rect = ghost.get_rect(midtop=(int(img["pos"].x-camera_x), int(img["pos"].y-camera_y)))

            if not self.facing_right:
                ghost = pygame.transform.flip(ghost, True, False)

            screen.blit(ghost, rect)

        # Build mask from current sprite frame
        mask = pygame.mask.from_surface(image)
        bbox = mask.get_bounding_rects()

        if bbox:
            # mask may return multiple regions; use largest
            largest = max(bbox, key=lambda r: r.width * r.height)

            tight_rect = pygame.Rect(
                self.rect.left + largest.left,
                self.rect.top + largest.top,
                largest.width,
                largest.height
            )

            pygame.draw.rect(
                screen,
                (0, 0, 255),
                tight_rect.move(int(-camera_x), int(-camera_y)),
                2
            ) # debug hitbox
        screen.blit(image, self.rect.move(int(-camera_x), int(-camera_y)))

        for p in self.dash_particles:
            p.draw(screen, camera_x, camera_y)

        # -----------------------
        # DRAW MULTI EXPLOSIONS
        # -----------------------
        for e in self._explosions:
            frame = self._ded_frames[e["frame"]]
            rect = frame.get_rect(center=(int(e["pos"].x), int(e["pos"].y)))
            screen.blit(frame, rect.move(int(-camera_x), int(-camera_y)))

    def update_pattern(self, dt):
        if self.state != "intro_done":
            return

        current = self._pattern[self.pattern_index]

        # flip meaning of directions after loop
        if self.pattern_loop_flipped:
            current = current.replace("_rl", "_tmp").replace("_lr", "_rl").replace("_tmp", "_lr")

        if self.transition_state:
            self.update_transition(dt)
            return

        if current.startswith("timeshot"):
            self.update_timeshot(dt)
        elif current.startswith("shot"):
            self.update_shot(dt)
        elif current.startswith("undershot"):
            self.update_undershot(dt)
        elif current.startswith("dash_fake"):
            self.update_dash_fake(dt)
        elif current.startswith("dash_real"):
            self.update_dash_real(dt)
            return

    def advance_pattern(self):
        prev = self._pattern[self.pattern_index]

        self.pattern_index += 1
        if self.pattern_index >= len(self._pattern):
            self.pattern_index = 0
            self.pattern_loop_flipped = not self.pattern_loop_flipped

        next_attack = self._pattern[self.pattern_index]

        # If undershot → timeshot, add descent transition
        if prev.startswith("undershot") and next_attack.startswith("timeshot"):
            self.transition_state = "descend_to_sit"

    def update_timeshot(self, dt):
        if self.attack_state in (None, "adjust", "dash"):
            self.set_animation("sit")

        # -----------------------
        # START
        # -----------------------
        if self.attack_state is None:
            self.attack_state = "adjust"
            self.adjust_target_x = None
            self.dash_target_x = None

        # -----------------------
        # ADJUST (move to 400px from player)
        # -----------------------
        if self.attack_state == "adjust":

            if self.adjust_target_x is None:
                player_x = self.player._pos.x
                offset = 350 if (self.pos.x - player_x) > 0 else -350
                self.adjust_target_x = player_x + offset

            dx = self.adjust_target_x - self.pos.x

            if abs(dx) > 4:
                direction = 1 if dx > 0 else -1
                self.pos.x += direction * 325 * dt
            else:
                self.pos.x = self.adjust_target_x
                self.adjust_target_x = None
                self.attack_state = "dash"

                # decide dash side ONCE
                player_x = self.player_pos.x
                boss_on_right = self.pos.x > player_x
                self.dash_to_right = not boss_on_right

        # -----------------------
        # DASH ACROSS PLAYER
        # -----------------------
        elif self.attack_state == "dash":
            # Drop projectiles periodically while dashing
            self.timeshot_drop_timer -= dt
            if self.timeshot_drop_timer <= 0:
                self.timeshot_drop_timer = self.timeshot_drop_interval 

                proj = TimeShotProjectile(self.pos, self.facing_right, self.game.loader)
                self.game.enemy_projectiles.append(proj)

            player_x = self.player_pos.x

            # Target opposite side, but relative to player's CURRENT position
            if self.dash_to_right:
                desired_x = player_x + 350
            else:
                desired_x = player_x - 350

            dx = desired_x - self.pos.x

            if abs(dx) > 8:
                direction = 1 if dx > 0 else -1
                self.pos.x += direction * 350 * dt
            else:
                self.attack_state = "turn"
                self.set_animation("sitting_turn")

        # -----------------------
        # SIT TURN → END ATTACK
        # -----------------------
        elif self.attack_state == "turn":
            # wait for sit turn animation to finish
            if self.frame_index >= len(self.frames) - 1:
                self.facing_right = not self.facing_right
                self.set_animation("sit")
                self.attack_state = "end"

        # -----------------------
        # CLEAN END STATE
        # -----------------------
        elif self.attack_state == "end":
            # small buffer so animation visibly settles
            self.attack_state = None
            self.advance_pattern()

    def fire_shot(self):
        self.set_animation("shot",restart=True)

        if self.facing_right:
            spawn_x = self.rect.right - 10
        else:
            spawn_x = self.rect.left + 10

        spawn_y = self.rect.centery

        start = (spawn_x, spawn_y - 5)
        target = (
            self.player_pos.x + 16,  # half width
            self.player_pos.y + 32   # half height
        )

        proj = ShotProjectile(
            start,
            target,
            self.shot,              # projectile animation
            self.facing_right,      # boss direction
            self.after_effect,
            self.after_effect_s,     # trail animation
            scale_frames(self.zangai_frames, 0.6667)
        )
        self.game.enemy_projectiles.append(proj)

    def update_shot(self, dt):

        # -----------------------
        # START
        # -----------------------
        if self.attack_state is None:
            self.attack_state = "standup"
            self.set_animation("stand_up")

        # -----------------------
        # STAND UP ANIMATION
        # -----------------------
        elif self.attack_state == "standup":
            if self.frame_index >= len(self.frames) - 1:
                self.attack_state = "stand_hold"
                self.set_animation("stand")
                self.shot_timer = 2.0  # how long boss stands

        # -----------------------
        # STAND & FIRE (later)
        # -----------------------
        elif self.attack_state == "stand_hold":

            self.burst_timer -= dt

            if self.burst_timer <= 0 and self.burst_count < 3:
                self.fire_shot()
                self.burst_count += 1
                self.burst_timer = 0.5   # delay between shots

            if self.burst_count >= 3:
                self.attack_state = None
                self.burst_count = 0
                self.advance_pattern()

    def update_undershot(self, dt):

        # -----------------------
        # START
        # -----------------------
        if self.attack_state is None:
            self.attack_state = "rise"
            self.set_animation("stand")

            # Decide target side ONCE
            player_x = self.player_pos.x
            boss_on_right = self.pos.x > player_x
            self.rise_to_right = not boss_on_right

        # -----------------------
        # PHASE 1 — DIAGONAL RISE
        # -----------------------
        elif self.attack_state == "rise":

            player_x = self.player_pos.x
            target_y = self.height_levels["high"]

            if self.rise_to_right:
                target_x = player_x + 300
            else:
                target_x = player_x - 300

            dx = target_x - self.pos.x
            dy = target_y - self.pos.y
            dist = math.hypot(dx, dy)

            if dist > 5:
                speed = 375
                self.pos.x += dx / dist * speed * dt
                self.pos.y += dy / dist * speed * dt
            else:
                self.attack_state = "turn"
                self.set_animation("standing_turn")

        # -----------------------
        # PHASE 2 — MID-AIR TURN
        # -----------------------
        elif self.attack_state == "turn":
            if self.frame_index >= len(self.frames) - 1:
                self.facing_right = not self.facing_right
                self.set_animation("stand")
                self.attack_state = "adjust"

        # -----------------------
        # PHASE 3 — HORIZONTAL ADJUST
        # -----------------------
        elif self.attack_state == "adjust":

            player_x = self.player_pos.x
            dx = self.pos.x - player_x
            desired_gap = 350

            if abs(abs(dx) - desired_gap) > 5:
                direction = 1 if dx > 0 else -1
                target_x = player_x + direction * desired_gap
                move_dir = 1 if target_x > self.pos.x else -1
                self.pos.x += move_dir * 325 * dt
            else:
                boss_on_right = dx > 0
                self.dash_to_right = not boss_on_right

                self.attack_state = "dash"
                self.set_animation("undershot", restart=True)

        # -----------------------
        # PHASE 4 — UNDERSHOT DASH
        # -----------------------
        elif self.attack_state == "dash":

            self.facing_right = self.dash_to_right

            player_x = self.player_pos.x

            # Desired final spacing on opposite side
            if self.dash_to_right:
                desired_x = player_x + 350
            else:
                desired_x = player_x - 350

            dx = desired_x - self.pos.x

            self.undershot_fire_timer -= dt
            if self.undershot_fire_timer <= 0:
                self.undershot_fire_timer = self.undershot_fire_interval

                spawn_x = self.rect.centerx
                spawn_y = self.rect.centery + 24

                proj = UndershotProjectile(
                    spawn_x,
                    spawn_y,
                    self.undershot,
                    self.laser,
                    scale_frames(self.zangai_frames, 1.5)
                )

                self.game.enemy_projectiles.append(proj)

            # Move toward dynamic target
            if abs(dx) > 10:
                direction = 1 if dx > 0 else -1
                self.pos.x += direction * 350 * dt
            else:
                self.pos.x = desired_x
                self.attack_state = "end_turn"
                self.set_animation("standing_turn")
        # -----------------------
        # PHASE 5 — END TURN
        # -----------------------
        elif self.attack_state == "end_turn":
            if self.frame_index >= len(self.frames) - 1:
                self.facing_right = not self.facing_right
                self.set_animation("stand")
                self.attack_state = "recover"

        # -----------------------
        # PHASE 6 — RECOVER
        # -----------------------
        elif self.attack_state == "recover":
            self.set_animation("stand")
            self.attack_state = None
            self.advance_pattern()

    def update_transition(self, dt):

        # Descend while playing sit_down
        if self.transition_state == "descend_to_sit":

            self.set_animation("sit_down")

            target_y = self.height_levels["low"]

            if abs(self.pos.y - target_y) > 3:
                self.pos.y += 225 * dt
            else:
                self.pos.y = target_y

            # When animation finishes, enter sit idle and resume pattern
            if self.frame_index >= len(self.frames) - 1:
                self.set_animation("sit")
                self.transition_state = None

    def update_dash_fake(self, dt):

        # -----------------------
        # START
        # -----------------------
        if self.attack_state is None:
            self.attack_state = "standup"
            self.set_animation("stand_up")

        # -----------------------
        # STAND UP AND ASCEND
        # -----------------------
        elif self.attack_state == "standup":

            # ascend during stand-up animation
            target_y = self.height_levels["mid"]

            if abs(self.pos.y - target_y) > 4:
                self.pos.y -= 325 * dt
            else:
                self.pos.y = target_y

            # when stand-up animation finishes → dash
            if self.frame_index >= len(self.frames) - 1:

                # Decide dash direction (opposite side of player)
                player_x = self.player_pos.x
                boss_on_right = self.pos.x > player_x
                self.dash_to_right = not boss_on_right

                self.attack_state = "dash"
                self.set_animation("stand")

        # -----------------------
        # RAPID DASH OFFSCREEN
        # -----------------------
        elif self.attack_state == "dash":

            direction = 1 if self.dash_to_right else -1
            self.fake_dash_dir = direction
            self.pos.x += direction * 800 * dt

            # Offscreen bounds (extra margin)
            cam_left  = self.game.camera_x
            cam_right = self.game.camera_x + SCREEN_WIDTH
            margin = 360

            if self.pos.x < cam_left - margin or self.pos.x > cam_right + margin:
                self.attack_state = "vanish"

        # -----------------------
        # VANISH
        # -----------------------
        elif self.attack_state == "vanish":
            # Move fully offscreen and stop drawing
            self.visible = False
            self.attack_state = None
            self.advance_pattern()

    def update_dash_real(self, dt):

        # -----------------------
        # START — SPAWN OFFSCREEN
        # -----------------------
        if self.attack_state is None:
            self.attack_state = "dash"

            # Mirror fake dash direction
            self.real_dash_dir = -self.fake_dash_dir

            margin = 220

            cam_left  = self.game.camera_x
            cam_right = self.game.camera_x + SCREEN_WIDTH
            margin = 220

            if self.real_dash_dir > 0:  # entering from left → moving right
                self.pos.x = cam_left - margin
                self.facing_right = True
            else:                      # entering from right → moving left
                self.pos.x = cam_right + margin
                self.facing_right = False

            # Force DASH HEIGHT
            self.pos.y = self.height_levels["dash"]

            self.visible = True
            self.set_animation("dash", restart=True)

        # -----------------------
        # DASH ACROSS SCREEN
        # -----------------------
        elif self.attack_state == "dash":

            # --- Spawn trail particles ---
            self.trail_timer_big += dt
            if self.trail_timer_big >= 0.07:
                self.trail_timer_big = 0

                x_jitter = random.randint(-30, 30)     # MUCH wider sideways spread
                y_jitter = random.randint(10, 70)     # Tall vertical spread

                spawn_pos = pygame.Vector2(
                    self.pos.x + x_jitter,
                    self.pos.y + y_jitter
                )

                self.dash_particles.append(
                    DashTrail(spawn_pos, self.after_effect, self.facing_right)
                )

            self.trail_timer_small += dt
            if self.trail_timer_small >= 0.025:
                self.trail_timer_small = 0

                x_jitter = random.randint(-45, 45)    # even wider
                y_jitter = random.randint(0, 90)      # fills whole column

                spawn_pos = pygame.Vector2(
                    self.pos.x + x_jitter,
                    self.pos.y + y_jitter
                )

                self.dash_particles.append(
                    DashTrail(spawn_pos, self.after_effect_s, self.facing_right)
                )

            self.pos.x += self.real_dash_dir * 1100 * dt

            # Exit screen
            cam_left  = self.game.camera_x
            cam_right = self.game.camera_x + SCREEN_WIDTH
            margin = 360

            if self.pos.x < cam_left - margin or self.pos.x > cam_right + margin:
                self.visible = False
                self.attack_state = None
                self.transition_state = None
                self.state = "post_dash_recover"

    def update_post_dash_recover(self, dt):

        player_x = self.player_pos.x

        # -----------------------
        # PHASE 1 — FLY IN (STOP ANIM)
        # -----------------------
        if self.attack_state is None:
            self.attack_state = "fly_in"
            self.visible = True
            self.set_animation("stop")

            cam_left  = self.game.camera_x
            cam_right = self.game.camera_x + SCREEN_WIDTH

            margin = 80          # MUCH closer
            top_y = cam_left  # temp placeholder to keep structure
            top_y = -120

            if self.real_dash_dir < 0:  # exited left
                self.pos.x = cam_left - margin
                self.facing_right = True
            else:                       # exited right
                self.pos.x = cam_right + margin
                self.facing_right = False

            self.pos.y = top_y

        elif self.attack_state == "fly_in":

            side = -1 if self.pattern_loop_flipped else 1
            target_x = player_x + 225 * side
            target_y = self.height_levels["high"]

            dx = target_x - self.pos.x
            dy = target_y - self.pos.y
            dist = math.hypot(dx, dy)

            if dist > 5:
                speed = 600
                self.pos.x += dx / dist * speed * dt
                self.pos.y += dy / dist * speed * dt
            else:
                self.attack_state = "turn1"
                self.set_animation("standing_turn")

        # -----------------------
        # PHASE 2 — TURN TOWARD PLAYER
        # -----------------------
        elif self.attack_state == "turn1":
            if self.frame_index >= len(self.frames) - 1:
                self.facing_right = not self.facing_right
                self.set_animation("stand")
                self.attack_state = "move_across"

        # -----------------------
        # PHASE 3 — MOVE TO OTHER SIDE
        # -----------------------
        elif self.attack_state == "move_across":

            side = -1 if self.pattern_loop_flipped else 1
            target_x = player_x - 300 * side
            dx = target_x - self.pos.x

            if abs(dx) > 4:
                direction = 1 if dx > 0 else -1
                self.pos.x += direction * 360 * dt
            else:
                self.attack_state = "turn2"
                self.set_animation("standing_turn")

        # -----------------------
        # PHASE 4 — TURN AGAIN
        # -----------------------
        elif self.attack_state == "turn2":
            if self.frame_index >= len(self.frames) - 1:
                self.facing_right = not self.facing_right
                self.attack_state = "descend"
                self.set_animation("sit_down")

        # -----------------------
        # PHASE 5 — DESCEND TO LOW HEIGHT
        # -----------------------
        elif self.attack_state == "descend":

            low_y = self.height_levels["low"]

            if abs(self.pos.y - low_y) > 3:
                self.pos.y += 325 * dt
            else:
                self.pos.y = low_y

            if self.pos.y > low_y:
                self.pos.y = low_y

            if self.frame_index >= len(self.frames) - 1:
                # Sit idle
                self.set_animation("sit")
                self.attack_state = None

                # Flip attack directions only
                self.pattern_loop_flipped = not self.pattern_loop_flipped

                # Restart pattern from beginning
                self.pattern_index = 0
                self.attack_state = None
                self.transition_state = None

                self.state = "intro_done"

    def update_master_spark(self, dt):

        player_x = self.player_pos.x

        # -----------------------
        # PHASE 1 — FLY IN (STOP ANIM)
        # -----------------------
        if self.attack_state is None:
            self.attack_state = "fly_in"
            self.visible = True
            self.set_animation("stop")

            cam_left  = self.game.camera_x
            cam_right = self.game.camera_x + SCREEN_WIDTH

            margin = 80          # MUCH closer
            top_y = cam_left  # temp placeholder to keep structure
            top_y = -120

            if self.real_dash_dir < 0:  # exited left
                self.pos.x = cam_left - margin
                self.facing_right = True
            else:                       # exited right
                self.pos.x = cam_right + margin
                self.facing_right = False

            self.pos.y = top_y

        elif self.attack_state == "fly_in":

            side = -1 if self.pattern_loop_flipped else 1
            target_x = player_x + 225 * side
            target_y = self.height_levels["high"]

            dx = target_x - self.pos.x
            dy = target_y - self.pos.y
            dist = math.hypot(dx, dy)

            if dist > 5:
                speed = 600
                self.pos.x += dx / dist * speed * dt
                self.pos.y += dy / dist * speed * dt
            else:
                self.attack_state = "turn1"
                self.set_animation("standing_turn")

        # -----------------------
        # PHASE 2 — TURN TOWARD PLAYER AND PREPARE SHOT
        # -----------------------
        elif self.attack_state == "turn1":
            if self.frame_index >= len(self.frames) - 1:
                self.facing_right = not self.facing_right
                self.set_animation("undershot")
                self.attack_state = "prepare_spark"

        # -----------------------
        # PHASE 3 - PREPARE TO FIRE
        # -----------------------
        elif self.attack_state == "prepare_spark":
            if self.frame_index >= len(self.frames) - 1:
                self.set_animation("supershot")
                self.attack_state = "master_spark"

        # -----------------------
        # PHASE 4 — FIRE AND MOVE ACROSS UNTIL COVER 500 PIXELS
        # -----------------------
        elif self.attack_state == "master_spark":

            if self.master_spark_proj is None:
                self.master_spark_proj = MasterSparkProjectile(
                    self,
                    self.supershot,
                    1080
                )
                self.game.enemy_projectiles.append(self.master_spark_proj)
            
            if not hasattr(self, "spark_start_x"):
                self.spark_start_x = self.pos.x
                self.spark_dir = 1 if self.facing_right else -1

            # Move in locked direction
            speed = 225  # pixels per second
            self.pos.x += self.spark_dir * speed * dt

            # Check distance traveled
            if abs(self.pos.x - self.spark_start_x) >= 600:
                del self.spark_start_x
                del self.spark_dir

                self.attack_state = "recovery"
                self.set_animation("undershot")

        # -----------------------
        # PHASE 5 — RECOVERY
        # -----------------------
        elif self.attack_state == "recovery":
            self.master_spark_proj = None
            if self.frame_index >= len(self.frames) - 1:
                self.set_animation("stand")
                self.attack_state = "stand_up"

        # -----------------------
        # PHASE 6 — BACK TO STAND
        # -----------------------
        elif self.attack_state == "stand_up":
            if self.frame_index >= len(self.frames) - 1:
                self.set_animation("standing_turn")
                self.attack_state = "turn2"      

        # -----------------------
        # PHASE 7 — TURN AROUND
        # -----------------------
        elif self.attack_state == "turn2":
            if self.frame_index >= len(self.frames) - 1:
                self.facing_right = not self.facing_right
                self.set_animation("sit_down")
                self.attack_state = "descend" 

        # -----------------------
        # PHASE 8 — SIT DOWN AND DESCEND TO LOW HEIGHT
        # -----------------------
        elif self.attack_state == "descend":

            low_y = self.height_levels["low"]

            if abs(self.pos.y - low_y) > 3:
                self.pos.y += 325 * dt
            else:
                self.pos.y = low_y

            if self.pos.y > low_y:
                self.pos.y = low_y

            if self.frame_index >= len(self.frames) - 1:
                # Sit idle
                self.set_animation("sit")
                self.attack_state = None

                # Flip attack directions only
                self.pattern_loop_flipped = not self.pattern_loop_flipped

                # Restart pattern from beginning
                self.pattern_index = 0
                self.attack_state = None
                self.transition_state = None

                self.state = "intro_done"

    def update_hurtbox(self):
        mask = pygame.mask.from_surface(self.image)
        rects = mask.get_bounding_rects()

        if rects:
            largest = max(rects, key=lambda r: r.width * r.height)

            self.hurtbox = pygame.Rect(
                self.rect.left + largest.left,
                self.rect.top + largest.top,
                largest.width,
                largest.height
            )
        else:
            self.hurtbox = self.rect.copy()

    def is_hit(self, knives):
        # group knives in batches of 3 (same as your enemies)
        for i in range(0, len(knives), 3):
            group = knives[i:i+3]

            rect_left   = min(k.rect.left   for k in group)
            rect_top    = min(k.rect.top    for k in group)
            rect_right  = max(k.rect.right  for k in group)
            rect_bottom = max(k.rect.bottom for k in group)

            # check overlap with boss HURTBOX (not body rect)
            if (rect_left <= self.hurtbox.right and rect_right >= self.hurtbox.left
                and rect_top <= self.hurtbox.bottom and rect_bottom >= self.hurtbox.top):

                # kill knives
                for k in group:
                    k.alive = False

                # damage boss (15 per knife × knives in group)
                self.take_damage(5 * len(group))

                return True

        return False
    
    def take_damage(self, amount):
        if self._dead or self._dying:
            return

        self.hp -= amount

        # trigger red flash
        self._hit = True
        self._shake_timer = 0

        if self.hp <= 0:
            self.hp = 0
            self._hit = False
            self._dying = True
            self.set_animation("dying", restart=True)

            # FREEZE BOSS
            self.attack_state = None
            self.transition_state = None
            self.state = "dead"
            self.speed = 0

            # start explosions
            self._explosion_total_time = self._explosion_duration
            self._explosions.clear()
            self.afterimages.clear()
            self.dash_particles.clear()
        
    def apply_flash_to(self, surface, color=(255, 0, 0), alpha=120):
        flash_img = surface.copy()
        tint = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        tint.fill((*color, alpha))
        flash_img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return flash_img
    
    def update_explosions(self, dt):
        if self._explosion_total_time > 0:
            self._explosion_total_time -= dt
            self._explosion_timer -= dt

            if self._explosion_timer <= 0:
                self._explosion_timer = self._explosion_interval

                x = random.randint(self.hurtbox.left, self.hurtbox.right)
                y = random.randint(self.hurtbox.top, self.hurtbox.bottom)

                self._explosions.append({
                    "pos": pygame.Vector2(x, y),
                    "frame": 0,
                    "timer": 0
                })

        for e in self._explosions:
            e["timer"] += dt
            if e["timer"] >= 0.05:
                e["timer"] = 0
                e["frame"] += 1

        self._explosions = [
            e for e in self._explosions
            if e["frame"] < len(self._ded_frames)
        ]
    
def scale_frames(frames, scale):
    scaled = []
    for f in frames:
        w, h = f.get_size()
        scaled.append(pygame.transform.scale(f, (int(w*scale), int(h*scale))))
    return scaled

