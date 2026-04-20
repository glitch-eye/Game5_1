"""
    Character build
"""
import pygame
from pygame.locals import *
from settings import *
from utils import *
from knife import *
from build import *
import random

class Character:
    def __init__(self, loader, game, player_no = 1):
        #keyboard control
        self._keys = {
            "jump": K_SPACE,
            "left": K_a,
            "right": K_d,
            "up": K_w,
            "down": K_s,
            "dash": K_LSHIFT,
            "attack": K_j,          #also slows (implement later)
            "stop": K_k,
        }

        self.game = game
        self.loader = loader
        self.map = None
        self.player_no = player_no

        #stats
        self._pos = PLAYER_INIT_POS
        self._hurtbox = pygame.Vector2(PLAYER_HURTBOX_WIDTH, PLAYER_HURTBOX_HEIGHT)
        self._vel = pygame.Vector2(0, 0)
        self._moveSpeed = PLAYER_SPEED
        self._jumpforce = PLAYER_JUMPSTRENGTH
        self._doublejumpForce = PLAYER_DOUBLEJUMPSTRENGTH
        self._jumpPressedLastFrame = False
        self._jumpholdDuration = PLAYER_JUMPHOLDTIME
        self._doublejumpholdDuration = PLAYER_DOUBLEJUMPHOLDTIME

        self._jumpBufferTime = 0.12     # seconds allowed to buffer
        self._jumpBufferTimer = 0

        # HP
        self.hp = 100
        self.hp_max = 100

        # MP
        self.mp = 100
        self.mp_max = 100
        self.mp_regen_rate = 3.0
        self.mp_attack_cost = 5.0

        # state
        self._jumpTimes = 0
        self._grounded = True
        self._curJumpHold = 0.0
        self._jumpHolding = False
        self._jumpMaxHold = self._jumpholdDuration
        self._wasMoving = False
        self._crouching = False
        self._turning = False
        self._dead = False

        # dash placeholder    
        self._dashCD = 0.0
        self._dashCDStat = PLAYER_DASHCOOLDOWN
        self._dash = False
        self._dashSpeed = PLAYER_DASHSPEED

        # slide
        self.player_sliding = False
        self.slide_timer = 0
        self.slide_duration = PLAYER_SLIDE_DURATION
        self.slide_speed = PLAYER_SLIDE_SPEED

        # coyote time
        self._coyoteTime = 0.2
        self._coyoteTimer = 0

        # sprite
        if player_no == 1:
            self.animations = {
                "idle": loader.get_animation("player_idle"),
                "jump": loader.get_animation("player_jump"),
                "fall": loader.get_animation("player_fall"),
                "double_jump": loader.get_animation("player_2ndjump"),
                "glide": loader.get_animation("player_gliding"),
                "run": loader.get_animation("player_run"),
                "run_start": loader.get_animation("player_run_start"),
                "run_stop": loader.get_animation("player_run_stop"),
                "run_back": loader.get_animation("player_run_back"),
                "crouch": loader.get_animation("player_down"),
                "action1": loader.get_animation("player_action1"),
                "action2": loader.get_animation("player_action2"),
                "action3": loader.get_animation("player_action3"),
                "action4": loader.get_animation("player_action4"),
                "run_attack1": loader.get_animation("player_run_attack1"),
                "run_attack2": loader.get_animation("player_run_attack2"),
                "run_attack3": loader.get_animation("player_run_attack3"),
                "run_attack4": loader.get_animation("player_run_attack4"),
                "jump_attack": loader.get_animation("player_jump_attack"),
                "up_shot": loader.get_animation("player_up_shot"),
                "up_shot2": loader.get_animation("player_up_shot2"),
                "up_shot_air": loader.get_animation("player_up_shot_air"),
                "up_shot_run": loader.get_animation("player_up_shot_run"),
                "under_attack": loader.get_animation("player_under_attack"),
                "slide": loader.get_animation("player_sliding"),
                "time_stop": trim_top(loader.get_animation("player_time_stop")),
                "time_stop_air": loader.get_animation("player_time_stop_air"),
                "player_damage": loader.get_animation("player_damage"),
                "player_fall_down": loader.get_animation("player_fall_down"),
                "player_des": loader.get_animation("player_des"),
            }
        else:
            self.animations = {
                "idle": loader.get_animation("player_idle_2"),
                "jump": loader.get_animation("player_jump_2"),
                "fall": loader.get_animation("player_fall_2"),
                "double_jump": loader.get_animation("player_2ndjump_2"),
                "glide": loader.get_animation("player_gliding_2"),
                "run": loader.get_animation("player_run_2"),
                "run_start": loader.get_animation("player_run_start_2"),
                "run_stop": loader.get_animation("player_run_stop_2"),
                "run_back": loader.get_animation("player_run_back_2"),
                "crouch": loader.get_animation("player_down_2"),
                "action1": loader.get_animation("player_action1_2"),
                "action2": loader.get_animation("player_action2_2"),
                "action3": loader.get_animation("player_action3_2"),
                "action4": loader.get_animation("player_action4_2"),
                "run_attack1": loader.get_animation("player_run_attack1_2"),
                "run_attack2": loader.get_animation("player_run_attack2_2"),
                "run_attack3": loader.get_animation("player_run_attack3_2"),
                "run_attack4": loader.get_animation("player_run_attack4_2"),
                "jump_attack": loader.get_animation("player_jump_attack_2"),
                "up_shot": loader.get_animation("player_up_shot_2"),
                "up_shot2": loader.get_animation("player_up_shot2_2"),
                "up_shot_air": loader.get_animation("player_up_shot_air_2"),
                "up_shot_run": loader.get_animation("player_up_shot_run_2"),
                "under_attack": loader.get_animation("player_under_attack_2"),
                "slide": loader.get_animation("player_sliding_2"),
                "time_stop": trim_top(loader.get_animation("player_time_stop_2")),
                "time_stop_air": loader.get_animation("player_time_stop_air_2"),
                "player_damage": loader.get_animation("player_damage"),
                "player_fall_down": loader.get_animation("player_fall_down"),
                "player_des": loader.get_animation("player_des_2"),
            }


        self.anim_speeds = {
            "run": 0.04,
            "idle": 0.08,
            "jump": 0.08,
            "fall": 0.08,
            "glide": 0.08,
        }

        # special effects
        self.double_jump_effects = []
        self.arrow_ring_sprite = loader.get_animation("arrow_ring_sprite")
        self.double_jump_effect_sprite = self.jump_effect_frames = loader.get_animation("player_jump_effect")
        self.double_jump_trail_active = False
        self.trail_spawned = 0
        self.trail_timer = 0
        self.trail_interval = 0.05

        self.current_anim = "idle"
        self.frames = self.animations[self.current_anim]

        self.frame_index = 0
        self.frame_timer = 0
        self.frame_speed = 0.04

        self._image = self.frames[0]

        # collision box
        self._rect = pygame.Rect(0, 0, PLAYER_COLLISION_WIDTH, PLAYER_COLLISION_HEIGHT)
        self._rect.midtop = (int(self._pos.x), int(self._pos.y))

        # facing
        self._facingRight = True

        # gliding
        self._gliding = False
        self._glideGravity = GAME_GRAVITY * 0.25
        self._maxGlideFallSpeed = 120
        self._jumpHeld = False          

        # attack
        self.attack_duration = 0.25
        self.attack_frame_speed = 0.050
        self.upshot_frame_speed = 0.030
        self._attackPressedLastFrame = False
        self._attackQueued = False
        self._attacking = False
        self.attack_effects = []

        self._knifeCooldown = 0
        self._knifeCooldownTime = 0.30

        self._turnHoldTimer = 0.0
        self._turnHoldDuration = 0.35

        self.combos = {
            "ground": ["action1","action2","action3","action4"],
            "run": ["run_attack1","run_attack2","run_attack3","run_attack4"],
            "ground_up": ["up_shot","up_shot2"],
            "run_up": ["up_shot_run"],
            "air": ["jump_attack"],
            "air_up": ["up_shot_air"],
            "air_down": ["under_attack"]
        }
        self._currentCombo = None
        self._comboIndex = 0

        # time stop
        self.time_stop = False
        self.time_stop_frame_speed = 0.1
        self.time_stop_duration = 100.0   # max active time
        self.time_stop_timer = 0.0        # active timer
        self.time_stop_ending = False
        self.time_stop_ending_timer = 0.0

        self.time_stop_startup = False    # animation lock phase
        self.time_stop_startup_timer = 0.0

        self._stopPressedLastFrame = False
        self.time_stop_toggle_lock = 0.0
        self.time_stop_toggle_delay = 1.0

        self.anim_offsets = {
            "time_stop":        {"right": (0, -3),   "left": (0, -3)},
            "time_stop_air":    {"right": (-10, 0),  "left": (10, 0)},

            # ground combo
            "action1": {"right": (-5, 0), "left": (5, 0)},
            "action2": {"right": (13, 0), "left": (-13, 0)},
            "action3": {"right": (11, 0), "left": (-11, 0)},
            "action4": {"right": (16, 0), "left": (-16, 0)},

            # running combo
            "run_attack1": {"right": (0, 0), "left": (0, 0)},
            "run_attack2": {"right": (22, 0), "left": (-16, 0)},
            "run_attack3": {"right": (24, 0), "left": (-18, 0)},
            "run_attack4": {"right": (22, 0), "left": (-16, 0)},

            # air combo
            "jump_attack": {"right": (-5, 0), "left": (5, 0)},
        }

        self.time_energy = 100.0
        self.time_energy_max = 100.0

        self.time_regen_rate = 5.0       
        self.time_drain_base = 2.0        
        self.time_drain_move = 4.0
        self.time_doublejump_cost = 10.0        

        self.time_attack_cost = 10.0

        self._moving_timer = 0.0 

        # time stop efect
        self.time_stop_wave_active = False
        self.time_stop_wave_timer = 0.0
        self.time_stop_wave_duration = 0.4 
        self.time_stop_wave_max_radius = 1000 

        self.time_stop_wave_reverse = False 

        # taking damage
        self._takingDamage = False
        self._damageDuration = 0.5
        self._maxDamageDuration = 0.5
        self._tinted_lastframe = False
        self._inSmoke = False
        self._damageLock = False  
        self._knockbackVel = pygame.Vector2(0, 0)

        # fire upgrade
        self.fire_immune = False

    # -----------------------
    # INPUT
    # -----------------------

    def handleInput(self, keys):
        if self._dead:
            return
        # if self._damageLock:
        #     return

        # time stop
        stopPressed = keys[self._keys["stop"]]
        stopJustPressed = stopPressed and not self._stopPressedLastFrame

        if stopJustPressed and self.time_stop_toggle_lock <= 0:
            if getattr(self.game, "shared_time_stop_active", False):
                self.end_time_stop()
                self.time_stop_toggle_lock = 0.5
            elif self.time_energy > 0:
                self.start_time_stop()
                self.time_stop_toggle_lock = 0.5

        self._stopPressedLastFrame = stopPressed

        if self.player_sliding or self.time_stop_startup:
            return

        # crouch input (only allowed on ground)
        self._crouching = keys[K_s] and self._grounded and not self.player_sliding

        # horizontal input
        self._inputDir = (keys[self._keys["right"]] - keys[self._keys["left"]])
        self._inputDown = keys[self._keys["down"]]
        self._inputUp = keys[self._keys["up"]]

        # prevent movement while crouching
        if self._crouching or self.player_sliding:
            self._vel.x = 0
        else:
            self._vel.x = self._inputDir * self._moveSpeed

        jumpPressed = keys[K_SPACE]
        jumpJustPressed = jumpPressed and not self._jumpPressedLastFrame
        self._jumpHeld = jumpPressed

        # store jump request
        if jumpJustPressed:
            self._jumpBufferTimer = self._jumpBufferTime

        # release jump
        if not jumpPressed:
            self._jumpHolding = False
            self._curJumpHold = 0

        self._jumpPressedLastFrame = jumpPressed

        # attack
        attackPressed = keys[self._keys["attack"]]
        attackJustPressed = attackPressed and not self._attackPressedLastFrame

        if attackJustPressed and not self._attacking:
            if not self.can_pay_attack_cost():
                return
            self.pay_attack_cost()            

            if not self._grounded and self._coyoteTimer == 0:
                if self._inputUp:
                    self.start_attack("air_up")
                elif self._inputDown:
                    self.start_attack("air_down")
                else:
                    self.start_attack("air")
            else:
                if self._inputUp and abs(self._vel.x) > 0:
                    self.start_attack("run_up")
                elif self._inputUp:
                    self.start_attack("ground_up")
                elif abs(self._vel.x) > 0:
                    self.start_attack("run")
                else:
                    self.start_attack("ground")

        elif attackJustPressed:
            if self.can_pay_attack_cost():
                self._attackQueued = True

        self._attackPressedLastFrame = attackPressed

    # -----------------------
    # ANIMATION SWITCHING
    # -----------------------

    def set_animation(self, name, restart=False):
        self._knifeSpawned = False

        if self.current_anim != name or restart:

            self.current_anim = name
            self.frames = self.animations[name]

            self.frame_index = 0
            self.frame_timer = 0

            # immediately update the sprite
            self._image = self.frames[self.frame_index]

        # auto-set frame speed by animation
        if name in self.anim_speeds:
            self.frame_speed = self.anim_speeds[name]
        else:
            self.frame_speed = 0.04  # default speed

        self._image = self.frames[self.frame_index]

    # -----------------------
    # UPDATE
    # -----------------------

    def update(self, dt):
        self._inSmoke = False
        # hitbox update
        if self.player_sliding or self._crouching:
            self._hurtbox.x = PLAYER_CROUCH_HURTBOX_WIDTH
            self._hurtbox.y = PLAYER_CROUCH_HURTBOX_HEIGHT
        else:
            self._hurtbox.x = PLAYER_HURTBOX_WIDTH
            self._hurtbox.y = PLAYER_HURTBOX_HEIGHT


        # 2nd jump effect 2
        for effect in self.double_jump_effects[:]:
            effect["timer"] += dt
            if effect["timer"] >= effect["speed"]:
                effect["timer"] = 0
                effect["frame"] += 1
            if effect["frame"] >= len(effect["frames"]):
                self.double_jump_effects.remove(effect) 

        # attack effect
        for effect in self.attack_effects[:]:
            effect["timer"] += dt
            if effect["timer"] >= effect["speed"]:
                effect["timer"] = 0
                effect["frame"] += 1

            if effect["frame"] >= len(effect["frames"]):
                self.attack_effects.remove(effect)

        if self._dead and not self._takingDamage:
            self.update_death(dt)
            return
        if self._takingDamage:
            self.update_damage(dt)
            # return

        if self.time_stop_toggle_lock > 0:
            self.time_stop_toggle_lock -= dt

        # MP regen
        self.mp += self.mp_regen_rate * dt
        if self.mp > self.mp_max:
            self.mp = self.mp_max

        if self._knifeCooldown > 0:
            self._knifeCooldown -= dt

        # time stop wave update
        if self.time_stop_wave_active:
            self.time_stop_wave_timer += dt

            if self.time_stop_wave_timer >= self.time_stop_wave_duration:
                self.time_stop_wave_active = False
                self.time_stop_wave_reverse = False

        # time stop wind up
        if self.time_stop_startup:
            self.time_stop_startup_timer -= dt

            if self.double_jump_trail_active:
                self.double_jump_trail_active = False

            # lock player completely
            self._vel.x = 0
            self._vel.y = 0

            # animate
            self.frame_timer += dt
            if self.frame_timer >= self.frame_speed:
                self.frame_timer = 0
                if self.frame_index < len(self.frames) - 1:
                    self.frame_index += 1

            self._image = self.frames[self.frame_index]

            # when animation finishes → enter real timestop
            if self.time_stop_startup_timer <= 0:
                self.time_stop_startup = False
                self.time_stop = True
                self.time_stop_timer = self.time_stop_duration

            return
        
        # time stop ending (cancel animation)
        if self.time_stop_ending:
            self.time_stop_ending_timer -= dt
            if self.double_jump_trail_active:
                self.double_jump_trail_active = False

            # lock player
            self._vel.x = 0
            self._vel.y = 0

            # animate
            self.frame_timer += dt
            if self.frame_timer >= self.frame_speed:
                self.frame_timer = 0
                if self.frame_index < len(self.frames) - 1:
                    self.frame_index += 1

            self._image = self.frames[self.frame_index]

            if self.time_stop_ending_timer <= 0:
                self.time_stop_ending = False
                self.game.time_stop = False   # unfreeze world

            return

        # time stop freeze
        if self.time_stop:
            # --- energy drain ---
            drain = self.time_drain_base

            # moving drain
            if abs(self._vel.x) > 0:
                drain += self.time_drain_move

            self.time_energy -= drain * dt

            # auto stop if empty
            if self.time_energy <= 0:
                self.time_energy = 0
                self.time_stop = False
                self.game.time_stop = False

            self.time_stop_timer -= dt

            if self.time_stop_timer <= 0:
                self.time_stop = False
                self.game.time_stop = False
        
        if not self.time_stop:
            self.time_energy = min(self.time_energy_max, self.time_energy + self.time_regen_rate * dt)
            if self.time_energy > self.time_energy_max:
                self.time_energy = self.time_energy_max

        was_grounded = self._grounded

        # update jump buffer timer
        if self._jumpBufferTimer > 0:
            self._jumpBufferTimer -= dt

        # dash cooldown
        if self._dashCD > 0.0:
            self._dashCD -= dt

        if self._attacking:

            # detect opposite direction
            if (self._inputDir > 0 and not self._facingRight) or \
            (self._inputDir < 0 and self._facingRight):

                self._turnHoldTimer += dt

                if self._turnHoldTimer >= self._turnHoldDuration:
                    self._facingRight = self._inputDir > 0
                    self._turnHoldTimer = 0

            else:
                # reset if player releases or matches direction
                self._turnHoldTimer = 0

        # Note: collision check moved to AFTER position update (see below)

        #  (coyote timer and just_landed will be calculated after position update & collision check)

        # execute buffered jump if possible
        if self._jumpBufferTimer > 0: # Remove later when couch+jump allows sliding

            if self._grounded or self._coyoteTimer > 0:

                if self._inputDown and not self.player_sliding:

                    if self._inputDir != 0:
                        self._facingRight = self._inputDir > 0

                    # cancel attack
                    self._attacking = False
                    self._attackQueued = False
                    self._comboIndex = 0

                    self.player_sliding = True
                    self.slide_timer = self.slide_duration
                    self._jumpBufferTimer = 0
                    return

                self._vel.y = -self._jumpforce
                self._jumpMaxHold = self._jumpholdDuration

                self._jumpHolding = True
                self._grounded = False
                self._jumpTimes = 1

                self._coyoteTimer = 0
                self._jumpBufferTimer = 0


            elif self._jumpTimes < 2:

                if self.time_stop:
                    # CHECK ENERGY FIRST
                    if self.time_energy < self.time_doublejump_cost:
                        self._jumpBufferTimer = 0
                        return

                    # APPLY COST
                    self.time_energy -= self.time_doublejump_cost

                    # auto cancel timestop if empty
                    if self.time_energy <= 0:
                        self.time_energy = 0
                        self.time_stop = False
                        self.game.time_stop = False

                self._vel.y = -self._doublejumpForce
                self._jumpMaxHold = self._doublejumpholdDuration

                self._curJumpHold = 0
                self._jumpTimes = 2
                self.spawn_downward_knives()
                self._jumpHolding = True

                self.double_jump_trail_active = True
                self.trail_spawned = 0
                self.trail_timer = 0

                frames = self.arrow_ring_sprite
                effect = {
                    "frames": frames,
                    "frame": 0,
                    "timer": 0,
                    "speed": 0.015,
                    "scale": 0.8,
                    "x": int(self._pos.x),
                    "y": int(self._pos.y + self._rect.height + 4),
                    "rotate": 90
                }
                self.double_jump_effects.append(effect)

                self._jumpBufferTimer = 0

        self.frame_timer += dt

        # slide
        if self.player_sliding:

            self.slide_timer -= dt

            direction = 1 if self._facingRight else -1
            self._vel.x = direction * self.slide_speed

            if self.slide_timer <= 0:
                self.player_sliding = False

                # execute buffered jump after slide ends
                if self._jumpBufferTimer > 0:
                    self._vel.y = -self._jumpforce
                    self._jumpHolding = True
                    self._grounded = False
                    self._jumpTimes = 1
                    self._jumpBufferTimer = 0

        # glide detection - MOVED to after collision check (see below)
        # Will be recalculated after position update and collision check

        if self._dash:

            self._pos.x += self._dashSpeed * dt * (self._vel.x / abs(self._vel.x))
            self._dash = False
        else:
            self._pos.x += self._vel.x * dt
        self._pos.y += self._vel.y * dt

        # ===== COLLISION CHECK AFTER POSITION UPDATE =====
        self._rect.midtop = (int(self._pos.x), int(self._pos.y))
        self.check_collision()
        
        # Update coyote and just_landed after collision check
        if self._grounded:
            self._coyoteTimer = self._coyoteTime
        else:
            self._coyoteTimer = max(0, self._coyoteTimer - dt)
        
        just_landed = not was_grounded and self._grounded

        # ===== GLIDE DETECTION (after collision check with updated _grounded) =====
        self._gliding = False
        if not self._grounded and self._vel.y > 0 and self._jumpHeld and self._coyoteTimer <= 0:
            self._gliding = True

        # gravity
        if self._gliding:
            self._vel.y += self._glideGravity * dt

            # optional fall speed cap
            if self._vel.y > self._maxGlideFallSpeed:
                self._vel.y = self._maxGlideFallSpeed
        else:
            if not self._grounded:
                self._vel.y += GAME_GRAVITY * dt
        
         # variable jump height
        if not self._jumpHolding and self._vel.y < 0:
            self._vel.y = 0

        # 2nd jump effect 1
        if self.double_jump_trail_active:
            self.trail_timer += dt
            if self.trail_timer >= self.trail_interval:
                self.trail_timer = 0
                frames = self.double_jump_effect_sprite
                scale = random.uniform(0.3, 0.6)
                effect = {
                    "frames": frames,
                    "frame": 0,
                    "timer": 0,
                    "speed": 0.015,
                    "scale": scale,
                    "x": int(self._pos.x),
                    "y": int(self._pos.y + self._rect.height),
                }

                self.double_jump_effects.append(effect)

                self.trail_spawned += 1

                if self.trail_spawned >= 4 or self._vel.y > 0:
                    self.double_jump_trail_active = False

        # jump hold
        if self._jumpHolding:
            self._curJumpHold += dt
            if self._curJumpHold >= self._jumpMaxHold:
                self._jumpHolding = False

        # move
        isMoving = abs(self._vel.x) > 0
        turning = False

        if isMoving:
            if self._vel.x > 0 and not self._facingRight:
                turning = True
            elif self._vel.x < 0 and self._facingRight:
                turning = True
        if not self._grounded:
            if self._inputDir > 0:
                self._facingRight = True
            elif self._inputDir < 0:
                self._facingRight = False

        # state change
        if self._attacking:
            # --- dynamic attack animation correction ---
            isMoving = abs(self._vel.x) > 0
            if self.current_anim.startswith("run_attack") and not isMoving:
                old_frame = self.frame_index
                new_anim = self.current_anim.replace("run_attack", "action")
                self.set_animation(new_anim)
                self.frame_index = min(old_frame, len(self.frames) - 1)
            elif self.current_anim.startswith("action") and isMoving:
                old_frame = self.frame_index
                new_anim = self.current_anim.replace("action", "run_attack")
                self.set_animation(new_anim)
                self.frame_index = min(old_frame, len(self.frames) - 1)

        if not self._attacking:
            if just_landed:
                if self._vel.x != 0:
                    self.set_animation("run")
                else:
                    self.set_animation("idle")

            elif self._gliding:
                self.set_animation("glide")

            elif self.player_sliding:
                self.set_animation("slide")

            elif self._crouching:
                self.set_animation("crouch")

            elif self._grounded:

                isMoving = abs(self._vel.x) > 0

                turning = False
                if isMoving:
                    if self._inputDir > 0 and not self._facingRight:
                        turning = True
                    elif self._inputDir < 0 and self._facingRight:
                        turning = True

                if turning and self._grounded:
                    # flip immediately
                    if self._inputDir > 0:
                        self._facingRight = True
                    elif self._inputDir < 0:
                        self._facingRight = False
                    self.set_animation("run_back", True)

                elif not self._wasMoving and isMoving:
                    self.set_animation("run_start")

                elif self._wasMoving and not isMoving:
                    self.set_animation("run_stop")

                elif isMoving:
                    if self.current_anim not in ("run_start", "run_stop", "run_back"):
                        self.set_animation("run")

                else:
                    if self.current_anim not in ("run_stop",):
                        self.set_animation("idle")

                self._wasMoving = isMoving

            else:
                if self._vel.y < 0:
                    if self._jumpTimes == 2:
                        self.set_animation("double_jump")
                    else:
                        self.set_animation("jump")
                else:
                    self.set_animation("fall")

        # update animation frames
        if self.frame_timer >= self.frame_speed:
            self.frame_timer = 0

            if self.current_anim == "fall":
                self._curJumpHold += dt
                # loop last 2 frames
                if self.frame_index < len(self.frames) - 2:
                    self.frame_index += 1
                else:
                    if self.frame_index == len(self.frames) - 1:
                        self.frame_index = len(self.frames) - 2
                    else:
                        self.frame_index = len(self.frames) - 1

            elif self.current_anim == "glide":
                # loop last 3 frames
                if self.frame_index < len(self.frames) - 3:
                    self.frame_index += 1
                else:
                    if self.frame_index == len(self.frames) - 1:
                        self.frame_index = len(self.frames) - 3
                    else:
                        self.frame_index += 1

            elif self.current_anim == "run_start":
                if self.frame_index < len(self.frames) - 1:
                    self.frame_index += 1
                else:
                    self.set_animation("run")

            elif self.current_anim == "run_stop":
                if self.frame_index < len(self.frames) - 1:
                    self.frame_index += 1
                else:
                    self.set_animation("idle")

            elif self.current_anim == "run_back":
                if self.frame_index < len(self.frames) - 1:
                    self.frame_index += 1
                else:
                    self._turning = False
                    self.set_animation("run")

            elif self.current_anim == "slide":
                if self.frame_index < len(self.frames) - 1:
                    self.frame_index += 1
                else:
                    # animation finished → stop sliding
                    self.player_sliding = False
                    if self._grounded:
                        if self._inputDown:
                            self.set_animation("crouch")
                        else:
                            self.set_animation("idle")
                    else:
                        if self._keys["jump"]:
                            self.set_animation("glide")
                        else:    
                            self.set_animation("falling")

            elif (
                self.current_anim.startswith(("action", "run_attack"))
                or self.current_anim in ("jump_attack","under_attack","up_shot","up_shot2","up_shot_air","up_shot_run")
            ):      
                if self.frame_index >= 1 and not self._knifeSpawned and self._knifeCooldown <= 0:
                    self.spawn_knives()
                    self._knifeSpawned = True
                if self.frame_index < len(self.frames) - 1:
                    self.frame_index += 1

                else:
                    # attack combo logic
                    if self._attackQueued and self._currentCombo:
                        self._attackQueued = False
                        if not self.can_pay_attack_cost():
                            self._attacking = False
                            self._comboIndex = 0
                            return

                        self.pay_attack_cost()

                        self._comboIndex += 1
                        if self._comboIndex >= len(self._currentCombo):
                            self._comboIndex = 0

                        # determine combo type dynamically
                        if not self._grounded:
                            if self._inputUp:
                                combo = self.combos["air_up"]
                            elif self._inputDown:
                                combo = self.combos["air_down"]
                            else:
                                combo = self.combos["air"]
                        else:
                            if self._inputUp and abs(self._vel.x) > 0:
                                combo = self.combos["run_up"]
                            elif self._inputUp:
                                combo = self.combos["ground_up"]
                            elif abs(self._vel.x) > 0:
                                combo = self.combos["run"]
                            else:
                                combo = self.combos["ground"]

                        self._currentCombo = combo
                        self._comboIndex = self._comboIndex % len(combo)
                        next_anim = combo[self._comboIndex]

                        self.set_animation(next_anim, True)
                        self.frame_speed = self.attack_duration / len(self.frames)
                        self.spawn_attack_effect()

                    else:

                        self._attackQueued = False
                        self._attacking = False
                        self._comboIndex = 0

                        if not self._grounded:
                            if self._gliding:
                                self.set_animation("glide")
                            elif self._vel.y < 0:
                                self.set_animation("jump")
                            else:
                                self.set_animation("fall")
                        else:
                            isMoving = abs(self._vel.x) > 0
                            if isMoving:
                                self.set_animation("run")
                            elif self._wasMoving:
                                self.set_animation("run_stop")
                            else:
                                self.set_animation("idle")

                        self._wasMoving = abs(self._vel.x) > 0

            else:
                # normal looping animation
                self.frame_index = (self.frame_index + 1) % len(self.frames)

        self._image = self.frames[self.frame_index]

        # sync rect AGAIN after collision fix
        self._rect.midtop = (int(self._pos.x), int(self._pos.y))

    # -----------------------
    # COLLISION
    # -----------------------

    def check_collision(self):
        self._grounded = False

        # 1. Đồng bộ rect từ vị trí midtop hiện tại
        self._rect.midtop = (int(self._pos.x), int(self._pos.y))
        
        # 2. Lấy vị trí top-left để đưa vào hệ thống va chạm
        collision_pos = pygame.Vector2(self._rect.topleft)
        # 3. Gọi hàm va chạm → hàm này sẽ sửa collision_pos và self._vel
        rect = self._rect
        if self.player_sliding:
            collision_pos = pygame.Vector2(collision_pos.x, collision_pos.y + self._rect.height/2)
            rect = pygame.Rect(collision_pos.x, collision_pos.y, rect.width, self._rect.height/2)
        self._grounded, _ = self.map.update_position(collision_pos, rect, self._vel)
        self.map.check_pressing(collision_pos, rect)

        # 4. Cập nhật lại _pos (midtop) từ kết quả top-left đã được điều chỉnh
        self._pos.x = collision_pos.x + self._rect.width / 2
        self._pos.y = collision_pos.y if not self.player_sliding else collision_pos.y - self._rect.height / 2         # ← điểm midtop.y = top.y (vì midtop)

        # 5. Đồng bộ lại rect từ midtop (để vẽ / camera dùng)
        self._rect.midtop = (int(self._pos.x), int(self._pos.y))

        # 6. Xử lý logic khi chạm đất
        if self._grounded:
            self._vel.y = 0
            self._jumpTimes = 0

    # -----------------------
    # DRAW
    # -----------------------

    def load(self):
        """Load character stats from saved progress"""
        pass

    def save(self):
        """save current character stats"""
        pass

    def draw(self, screen):

        image = self._image

        if not self._facingRight:
            image = pygame.transform.flip(self._image, True, False)

        draw_pos = self._rect.midtop

        # offset taller up-shot sprites
        if self.current_anim in ("up_shot", "up_shot2", "up_shot_air", "up_shot_run"):
            draw_pos = (draw_pos[0], draw_pos[1] - 32)

        offset = self.anim_offsets.get(self.current_anim, (0,0))

        if isinstance(offset, dict):
            if self._facingRight:
                offset_x, offset_y = offset["right"]
            else:
                offset_x, offset_y = offset["left"]
        else:
            offset_x, offset_y = offset
            if not self._facingRight:
                offset_x = -offset_x
        
        draw_rect = image.get_rect(midtop=(
            draw_pos[0] + offset_x,
            draw_pos[1] + offset_y 
        ))

        map_width  = MAP_NUMS[0] * TILE_SIZE
        map_height = MAP_NUMS[1] * TILE_SIZE

        camera_x = self._pos.x - SCREEN_WIDTH // 2
        camera_y = self._pos.y - SCREEN_HEIGHT // 2

        camera_x = max(0, min(camera_x, map_width  - SCREEN_WIDTH))
        camera_y = max(0, min(camera_y, map_height - SCREEN_HEIGHT))
        # convert world → screen while preserving anchor
        screen_rect = draw_rect.move(-camera_x, -camera_y)

        # debug hit box
        hurtbox = self.get_hurtbox_rect()

        pygame.draw.rect(
            screen,
            (0, 255, 0),
            hurtbox.move(int(-camera_x), int(-camera_y)),
            2
        )

        # draw sprite
        if self._dead or self._inSmoke or self._takingDamage and not self._tinted_lastframe:
            self._tinted_lastframe = True
            tinted = image.copy()

            overlay = pygame.Surface(image.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 0, 0, 120))

            tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            screen.blit(tinted, screen_rect)
        else:
            self._tinted_lastframe = False
            # Draw normal sprite
            screen.blit(image, screen_rect)

        for effect in self.double_jump_effects:

            frame = effect["frames"][effect["frame"]]

            # apply random scale
            scale = effect["scale"]
            new_size = (
                int(frame.get_width() * scale),
                int(frame.get_height() * scale)
            )
            frame = pygame.transform.scale(frame, new_size)

            if "rotate" in effect:
                frame = pygame.transform.rotate(frame, effect["rotate"])

            rect = frame.get_rect(center=(
                int(effect["x"] - camera_x),
                int(effect["y"] - camera_y)
            ))
            screen.blit(frame, rect)

        for effect in self.attack_effects:

            frame = effect["frames"][effect["frame"]]

            scale = effect["scale"]
            new_size = (
                int(frame.get_width() * scale),
                int(frame.get_height() * scale)
            )

            frame = pygame.transform.scale(frame, new_size)

            if "rotate" in effect:
                frame = pygame.transform.rotate(frame, effect["rotate"])

            if not self._facingRight:
                frame = pygame.transform.flip(frame, True, False)

            x = self._pos.x + effect["offset_x"] 
            y = self._pos.y + self._rect.height // 2 + effect["offset_y"]

            rect = frame.get_rect(center=(
                int(x - camera_x),
                int(y - camera_y)
            ))
            screen.blit(frame, rect)

        # --- time stop wave ---
        if self.time_stop_wave_active:
            t = self.time_stop_wave_timer / self.time_stop_wave_duration
            t = min(t, 1.0)

            # smoother easing
            progress = 1 - (1 - t) ** 3

            if self.time_stop_wave_reverse:
                progress = 1 - progress

            radius = int(self.time_stop_wave_max_radius * progress)

            center = (
                int(self._pos.x - camera_x),
                int(self._pos.y + self._rect.height // 2 - camera_y)
            )

            # slower fade for visibility
            alpha = int(255 * (1 - t * 0.4))   # was (1 - t)

            surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

            main_color = (255, 0, 0)
            outer_color = (255, 0, 0)
            inner_color = (255, 0, 0)

            pygame.draw.circle(surf, (*main_color, alpha), center, radius, width=28)
            pygame.draw.circle(surf, (*outer_color, alpha // 2), center, radius, width=42)
            pygame.draw.circle(surf, (*inner_color, alpha // 4), center, radius, width=16)

            screen.blit(surf, (0, 0))

    def start_attack(self, combo_type):
        self._attacking = True
        self._attackQueued = False
        self._currentCombo = self.combos[combo_type]
        self._comboIndex = 0
        anim = self._currentCombo[self._comboIndex]
        self.set_animation(anim, True)
        self.frame_speed = self.attack_duration / len(self.frames)
        self.spawn_attack_effect()

    def spawn_attack_effect(self):

        frames = self.arrow_ring_sprite

        x = self._pos.x
        y = self._pos.y + self._rect.height // 2

        rotate = 0
        offset_x = 0
        offset_y = 0

        # horizontal attacks
        if self.current_anim.startswith(("action", "run_attack")):
            if self._facingRight:
                rotate = 0
                offset_x = 35
                offset_y = 2
            else:
                rotate = 0
                offset_x = -35
                offset_y = 2

        # up shot
        elif self.current_anim in ("up_shot", "up_shot2", "up_shot_run", "up_shot_air"):
            if self._facingRight:
                rotate = 90
                offset_x = 3
                offset_y = -40
            else:
                rotate = -90
                offset_x = -3
                offset_y = -40

        # air downward shot (45°)
        elif self.current_anim == "under_attack":
            if self._facingRight:
                rotate = -45
                offset_x = 30
                offset_y = 30
            else:
                rotate = -45
                offset_x = -30
                offset_y = 30

        # jump attack
        elif self.current_anim == "jump_attack":
            if self._facingRight:
                rotate = 0
                offset_x = 35
                offset_y = 2
            else:
                rotate = 0
                offset_x = -35
                offset_y = 2

        effect = {
            "frames": frames,
            "frame": 0,
            "timer": 0,
            "speed": 0.015,
            "scale": 0.75,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "rotate": rotate
        }
        self.attack_effects.append(effect)

    def start_time_stop(self):
        if self.time_stop:
            return
        
        # start red wave effect
        self.time_stop_wave_active = True
        self.time_stop_wave_timer = 0.0

        self.game.time_stop = True

        # FORCE CANCEL ATTACK
        self._attacking = False
        self._attackQueued = False
        self._comboIndex = 0

        # reset knife spawn so it doesn't fire mid-cancel
        self._knifeSpawned = False

        # STARTUP phase only
        self.time_stop = False
        self.time_stop_startup = True

        anim = "time_stop" if self._grounded else "time_stop_air"
        self.set_animation(anim, True)

        self.frame_speed = self.time_stop_frame_speed
        frames = self.animations[anim]
        self.time_stop_startup_timer = len(frames) * self.frame_speed


    def end_time_stop(self):
        if not self.time_stop and not getattr(self.game, "shared_time_stop_active", False):
            return
        self._begin_time_stop_end_sequence()

    def force_end_time_stop(self):
        """Force shared timestop to end locally, even if this player did not initiate it."""
        if self.time_stop_ending:
            return
        if not self.time_stop and not self.time_stop_startup:
            return

        if self.time_stop_startup:
            self.time_stop_startup = False

        self._begin_time_stop_end_sequence()

    def _begin_time_stop_end_sequence(self):
        # start reverse wave
        self.time_stop_wave_active = True
        self.time_stop_wave_reverse = True
        self.time_stop_wave_timer = 0.0

        self.time_stop = False
        self.time_stop_ending = True

        # FORCE CANCEL ATTACK
        self._attacking = False
        self._attackQueued = False
        self._comboIndex = 0

        # reset to a safe animation immediately
        if not self._grounded and self._coyoteTimer <= 0:
            if self._vel.y < 0:
                self.set_animation("jump", True)
            else:
                self.set_animation("fall", True)
        else:
            if abs(self._vel.x) > 0:
                self.set_animation("run", True)
            else:
                self.set_animation("idle", True)

        anim = "time_stop" if self._grounded else "time_stop_air"
        self.set_animation(anim, True)

        self.frame_speed = self.time_stop_frame_speed
        frames = self.animations[anim]
        self.time_stop_ending_timer = len(frames) * self.frame_speed

    def spawn_knives(self):
        self._knifeCooldown = self._knifeCooldownTime
        direction = 1 if self._facingRight else -1

        center_x = self._pos.x
        center_y = self._pos.y + self._rect.height // 2
        offset = 16
        dx, dy = 0, 0
        # --- determine direction based on animation ---
        if self.current_anim in ("up_shot", "up_shot2", "up_shot_run", "up_shot_air"):
            dx = 0
            dy = -offset
        elif self.current_anim == "under_attack":
            dx = direction * offset
            dy = offset   # 45° down
        else:
            # default horizontal
            dx = direction * offset
            dy = 0
        offset_range = 5
        rand_x = random.randint(-offset_range, offset_range)
        rand_y = random.randint(-offset_range, offset_range)

        base_pos = (center_x + dx + rand_x, center_y + dy + rand_y)
        knives = [
            Knife(base_pos, direction, self.loader,
                attack_type=self.current_anim, y_offset=-15, forward_offset=5),

            Knife(base_pos, direction, self.loader,
                attack_type=self.current_anim, y_offset=0, forward_offset=15),

            Knife(base_pos, direction, self.loader,
                attack_type=self.current_anim, y_offset=15, forward_offset=-5),
        ]
        self.game.knives.extend(knives)

    def spawn_downward_knives(self):
        offset_range = 5
        rand_x = random.randint(-offset_range, offset_range)
        rand_y = random.randint(-offset_range, offset_range)

        base_pos = (
            self._rect.centerx + rand_x,
            self._rect.centery + rand_y
        )
        knives = [
            Knife(base_pos, 1, self.loader, attack_type="down_shot",
                y_offset=-15, forward_offset=5),
            Knife(base_pos, 1, self.loader, attack_type="down_shot",
                y_offset=0, forward_offset=15),
            Knife(base_pos, 1, self.loader, attack_type="down_shot",
                y_offset=15, forward_offset=-5),
        ]
        self.game.knives.extend(knives)

    def can_pay_attack_cost(self):
        if self.time_stop:
            return self.time_energy >= self.time_attack_cost
        else:
            return self.mp >= self.mp_attack_cost

    def pay_attack_cost(self):
        if self.time_stop:
            self.time_energy -= self.time_attack_cost

            if self.time_energy <= 0:
                self.time_energy = 0
                self.time_stop = False
                self.game.time_stop = False

        else:
            self.mp -= self.mp_attack_cost

    def take_damage(self, attacker_x):
        if self._takingDamage:
            return

        self._takingDamage = True
        self._damageLock = True

        # cancel combat
        self._attacking = False
        self._attackQueued = False
        self._currentCombo = None
        self._comboIndex = 0

        # dx = self._pos.x - attacker_x
        # direction = 1 if dx > 0 else -1

        # self._knockbackVel.x = 150 * direction
        # self._knockbackVel.y = -300

        # self._grounded = False 

        # self.set_animation("player_damage", True)

    def update_damage(self, dt):

        was_grounded = self._grounded

        # # apply gravity to knockback
        # self._knockbackVel.y += GAME_GRAVITY * dt

        # # move using knockback ONLY
        # self._pos.x += self._knockbackVel.x * dt
        # self._pos.y += self._knockbackVel.y * dt

        # update rect
        self._rect.midtop = (int(self._pos.x), int(self._pos.y))

        # collision
        self.check_collision()

        # just_landed = not was_grounded and self._grounded

        # if just_landed:
        #     self._knockbackVel.x = 0

        # self.frame_timer += dt

        # # --- DAMAGE ANIMATION ---
        # if self.current_anim == "player_damage":

        #     if self.frame_timer >= self.frame_speed:
        #         self.frame_timer = 0

        #         # advance until last frame
        #         if self.frame_index < len(self.frames) - 1:
        #             self.frame_index += 1

        #         # STAY on last frame
        #         else:
        #             # self.frame_index = len(self.frames) - 1
        #             self.set_animation("player_fall_down", True)

        #     # # when hit ground → switch animation
        #     # if self._grounded:
        #     #     self.set_animation("player_fall_down", True)

        # # --- FALL DOWN ANIMATION ---
        # elif self.current_anim == "player_fall_down":

        #     if self.frame_timer >= self.frame_speed:
        #         self.frame_timer = 0

        #         if self.frame_index < len(self.frames) - 1:
        #             self.frame_index += 1
        #         else:
        #             # CHECK DEATH HERE
        #             if self.hp <= 0:
        #                 self.set_animation("player_des", True)
        #                 self.frame_speed = 0.04
        #                 self._takingDamage = False
        #                 return
        #             else:
        #                 # normal recovery
        #                 self._takingDamage = False
        #                 self._damageLock = False

        #                 if self._grounded:
        #                     self.set_animation("idle", True)
        #                 else:
        #                     self.set_animation("fall", True)
        self._damageDuration -= dt
        if self._damageDuration <= 0:
            self._takingDamage = False
            self._damageDuration = self._maxDamageDuration

        self._image = self.frames[self.frame_index]

    def apply_damage(self, damage, attacker_x):
        # prevent damage spam
        if self._takingDamage:
            return
        if self._dead:
            return
        # reduce HP
        self.hp -= damage
        if self.hp < 0:
            self.hp = 0

        if self.hp <= 0:
            self._dead = True
            self.set_animation("player_des", True)
            self.frame_speed = 0.04
            self._takingDamage = False
            return

        # call existing damage logic
        self.take_damage(attacker_x)

    def update_death(self, dt):
        self.frame_timer += dt

        if self.frame_timer >= self.frame_speed:
            self.frame_timer = 0

            if self.frame_index < len(self.frames) - 1:
                self.frame_index += 1
            else:
                # stay on last frame (dead)
                self.frame_index = len(self.frames) - 1

        self._image = self.frames[self.frame_index]

    def set_map(self, map: Map):
        self.map = map

    def fire_upgrade(self):
        self.fire_immune = True

    def get_fire(self):
        return self.fire_immune
    
    def get_hurtbox_rect(self):
        rect = pygame.Rect(0, 0, self._hurtbox.x, self._hurtbox.y)
        rect.midbottom = self._rect.midbottom
        return rect
