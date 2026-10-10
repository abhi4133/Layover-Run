import pygame
import random
import sys
import os
import math

pygame.init()

# Window setup
WIDTH, HEIGHT = 1000, 600
is_fullscreen = True
try:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
except pygame.error:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    is_fullscreen = False
pygame.display.set_caption("Layover Run")

# Parallax background setup
base_dir = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()

def load_parallax_layer(filename):
    candidates = [
        os.path.join(base_dir, "Assets", filename),
        os.path.join(base_dir, "Hackathon", "Assets", filename),
        os.path.join("Assets", filename),
        os.path.join("Hackathon", "Assets", filename),
    ]
    path = next((p for p in candidates if os.path.exists(p)), candidates[0])
    raw = pygame.image.load(path).convert_alpha()
    scale = HEIGHT / raw.get_height()
    width = int(raw.get_width() * scale)
    return pygame.transform.smoothscale(raw, (width, HEIGHT)), width

bg_img, bg_width = load_parallax_layer("BG.png")
mid_img, _ = load_parallax_layer("Mid.png")
floor_img, _ = load_parallax_layer("Floor.png")

# Parallax layers from back to front with their speed multipliers
parallax_layers = [
    {"surf": bg_img, "speed": 0.20},    # Distant sunset sky, tarmac & planes
    {"surf": mid_img, "speed": 0.55},   # Airport concourse windows, pillars & seating
    {"surf": floor_img, "speed": 1.00}, # Foreground moving walkway railing & floor
]

# Avatar animation frames setup
PLAYER_W = 48
PLAYER_H = 70

def load_avatar_frame(filename):
    candidates = [
        os.path.join(base_dir, "Assets", "Avatar", filename),
        os.path.join(base_dir, "Hackathon", "Assets", "Avatar", filename),
        os.path.join("Assets", "Avatar", filename),
        os.path.join("Hackathon", "Assets", "Avatar", filename),
    ]
    path = next((p for p in candidates if os.path.exists(p)), candidates[0])
    raw = pygame.image.load(path).convert_alpha()
    bbox = raw.get_bounding_rect()
    return raw.subsurface(bbox).copy()

avatar_raw_1 = load_avatar_frame("AA1.png")
avatar_raw_2 = load_avatar_frame("AA2.png")
avatar_raw_3 = load_avatar_frame("AA3.png")

avatar_frame_1 = pygame.transform.smoothscale(avatar_raw_1, (PLAYER_W, PLAYER_H))
avatar_frame_2 = pygame.transform.smoothscale(avatar_raw_2, (PLAYER_W, PLAYER_H))
avatar_frame_3 = pygame.transform.smoothscale(avatar_raw_3, (PLAYER_W, PLAYER_H))

avatar_run_frames = [
    avatar_frame_1,
    avatar_frame_3,
    avatar_frame_2,
    avatar_frame_3,
]

# Slide frame: tilted running frame fitting slide height
slide_rot = pygame.transform.rotozoom(avatar_run_frames[0], -40, 1.0)
slide_h = 42
slide_w = int(slide_rot.get_width() * (slide_h / slide_rot.get_height()))
avatar_slide_frame = pygame.transform.smoothscale(slide_rot, (slide_w, slide_h))

# Luggage and obstacle sprites loaded from layover_run_luggage_sprites
def load_luggage_sprites():
    candidates = [
        os.path.join(base_dir, "Assets", "layover_run_luggage_sprites"),
        os.path.join(base_dir, "Assets", "layover_run_luggage_sprits"),
        os.path.join(base_dir, "Hackathon", "Assets", "layover_run_luggage_sprites"),
        os.path.join(base_dir, "Hackathon", "Assets", "layover_run_luggage_sprits"),
        os.path.join("Assets", "layover_run_luggage_sprites"),
        os.path.join("Assets", "layover_run_luggage_sprits"),
        os.path.join("Hackathon", "Assets", "layover_run_luggage_sprites"),
        os.path.join("Hackathon", "Assets", "layover_run_luggage_sprits"),
        os.path.join(base_dir, "layover_run_luggage_sprites"),
        os.path.join(base_dir, "layover_run_luggage_sprits"),
    ]
    folder = next((p for p in candidates if os.path.exists(p) and os.path.isdir(p)), None)
    if not folder:
        return [], [], []

    def scale_sprite(img, target_h, max_w):
        bbox = img.get_bounding_rect()
        if bbox.w > 0 and bbox.h > 0:
            cropped = img.subsurface(bbox).copy()
        else:
            cropped = img.copy()
        cw, ch = cropped.get_size()
        aspect = cw / max(1, ch)
        tw = max(16, int(target_h * aspect))
        th = target_h
        if max_w and tw > max_w:
            tw = max_w
            th = max(16, int(tw / aspect))
        return pygame.transform.smoothscale(cropped, (tw, th))

    cart_sprites = []
    tall_sprites = []
    regular_sprites = []

    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith(".png"):
            continue
        fpath = os.path.join(folder, fname)
        try:
            raw = pygame.image.load(fpath).convert_alpha()
        except pygame.error:
            continue

        name = fname.lower()
        if any(k in name for k in ["cart", "trolley", "trailer", "flatbed"]):
            scaled = scale_sprite(raw, 56, 92)
            cart_sprites.append(scaled)
        elif name.startswith("suitcase") and "darkblue" not in name:
            scaled = scale_sprite(raw, 78, 62)
            tall_sprites.append(scaled)
        else:
            scaled = scale_sprite(raw, 44, 66)
            regular_sprites.append(scaled)

    all_sprites = cart_sprites + tall_sprites + regular_sprites
    if not cart_sprites and all_sprites:
        cart_sprites = list(all_sprites)
    if not tall_sprites and all_sprites:
        tall_sprites = list(all_sprites)
    if not regular_sprites and all_sprites:
        regular_sprites = list(all_sprites)

    return cart_sprites, regular_sprites, tall_sprites

cart_sprites, luggage_sprites, tall_luggage_sprites = load_luggage_sprites()



clock = pygame.time.Clock()

# System font loader with modern typography fallbacks
def get_font(names, size, bold=False):
    for name in names:
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("arial", size, bold=bold)

font_title = get_font(["bahnschrift", "segoeui", "helvetica", "arial"], 24, bold=True)
font_large = get_font(["bahnschrift", "segoeui", "helvetica", "arial"], 20, bold=True)
font_mid = get_font(["segoeui", "bahnschrift", "helvetica", "arial"], 15, bold=True)
font_body = get_font(["segoeui", "helvetica", "arial"], 13)
font_tiny = get_font(["segoeui", "helvetica", "arial"], 10, bold=True)
font = font_mid
big_font = font_title

# Clean minimal UI palette
WHITE = (248, 250, 252)
BLACK = (15, 23, 42)
BLUE = (56, 189, 248)
RED = (244, 63, 94)
GREEN = (52, 211, 153)
GRAY = (148, 163, 184)
YELLOW = (251, 191, 36)

C_WHITE = WHITE
C_MUTED = (148, 163, 184)
C_EMERALD = GREEN
C_ROSE = RED
C_AMBER = YELLOW
C_CYAN = BLUE

GROUND = 516
PLAYER_X = 130

def reset_game():
    return {
        "player_y": float(GROUND - 70),
        "velocity_y": 0.0,
        "jumping": False,
        "sliding_until": 0,
        "obstacles": [],
        "boosts": [],
        "spawn_timer": 0,
        "boost_timer": 0,
        "speed": 350.0,
        "top_speed": 350.0,
        "score": 0,
        "start_time": pygame.time.get_ticks(),
        "game_over": False,
        "won": False,
        "bg_scroll": 0.0,
        "anim_timer": 0.0,
    }

game = reset_game()

def draw_text(text, x, y, color=BLACK, font_obj=font):
    image = font_obj.render(text, True, color)
    screen.blit(image, (x, y))

def draw_glass_pill(surf, rect, bg_alpha=200, border_alpha=35, radius=12):
    pill = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(pill, (15, 23, 42, bg_alpha), (0, 0, rect.width, rect.height), border_radius=radius)
    pygame.draw.rect(pill, (255, 255, 255, border_alpha), (0, 0, rect.width, rect.height), width=1, border_radius=radius)
    surf.blit(pill, rect.topleft)

def draw_hud(score, remaining, speed, total_time=60.0):
    progress = min(1.0, max(0.0, (total_time - remaining) / total_time))
    now = pygame.time.get_ticks()

    # 1. Left Pill: Gate B12 & Concourse Progress
    r_left = pygame.Rect(20, 16, 230, 52)
    draw_glass_pill(screen, r_left)

    t_gate = font_mid.render("GATE B12", True, C_WHITE)
    screen.blit(t_gate, (34, 23))

    badge_rect = pygame.Rect(142, 23, 94, 20)
    b_surf = pygame.Surface((badge_rect.width, badge_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(b_surf, (16, 185, 129, 45), (0, 0, badge_rect.width, badge_rect.height), border_radius=10)
    screen.blit(b_surf, badge_rect.topleft)

    pulse = 0.5 + 0.5 * math.sin(now * 0.005)
    dot_color = (int(52 + 40 * pulse), 211, 153)
    pygame.draw.circle(screen, dot_color, (153, 33), 4)
    t_board = font_tiny.render("BOARDING", True, C_EMERALD)
    screen.blit(t_board, (162, 27))

    # Concourse progress bar
    bar_w = 202
    bar_x = 34
    bar_y = 51
    pygame.draw.rect(screen, (255, 255, 255, 22), (bar_x, bar_y, bar_w, 4), border_radius=2)
    fill_w = max(4, int(bar_w * progress))
    pygame.draw.rect(screen, C_EMERALD, (bar_x, bar_y, fill_w, 4), border_radius=2)

    # 2. Center Pill: Countdown Timer
    r_mid = pygame.Rect(420, 16, 160, 52)
    draw_glass_pill(screen, r_mid)
    t_lbl = font_tiny.render("DEPARTURE IN", True, C_MUTED)
    screen.blit(t_lbl, (r_mid.centerx - t_lbl.get_width() // 2, 22))

    t_sec = f"{int(remaining):02d}s"
    time_color = C_ROSE if remaining < 12 else (C_AMBER if remaining < 20 else C_WHITE)
    t_val = font_large.render(t_sec, True, time_color)
    screen.blit(t_val, (r_mid.centerx - t_val.get_width() // 2, 38))

    # 3. Right Pill: Score & Speed
    r_right = pygame.Rect(750, 16, 230, 52)
    draw_glass_pill(screen, r_right)

    s_lbl = font_tiny.render("SCORE", True, C_MUTED)
    screen.blit(s_lbl, (766, 22))
    s_val = font_large.render(f"{score:,}", True, C_WHITE)
    screen.blit(s_val, (766, 38))

    pygame.draw.line(screen, (255, 255, 255, 25), (865, 24), (865, 60))

    sp_lbl = font_tiny.render("SPEED", True, C_MUTED)
    screen.blit(sp_lbl, (880, 22))
    sp_val = font_large.render(f"{int(speed)}", True, C_CYAN)
    screen.blit(sp_val, (880, 38))

def draw_controls_hint(elapsed):
    if elapsed > 10:
        return
    alpha = 180 if elapsed < 6 else int(180 * max(0.0, (10 - elapsed) / 4.0))
    if alpha <= 0:
        return
    r_hint = pygame.Rect(375, 565, 250, 24)
    pill = pygame.Surface((r_hint.width, r_hint.height), pygame.SRCALPHA)
    pygame.draw.rect(pill, (15, 23, 42, int(alpha * 0.8)), (0, 0, r_hint.width, r_hint.height), border_radius=12)
    pygame.draw.rect(pill, (255, 255, 255, int(alpha * 0.15)), (0, 0, r_hint.width, r_hint.height), width=1, border_radius=12)
    screen.blit(pill, r_hint.topleft)

    t_hint = font_tiny.render("SPACE / ↑  JUMP     •     S / ↓  SLIDE", True, (200, 215, 235))
    t_hint.set_alpha(alpha)
    screen.blit(t_hint, (r_hint.centerx - t_hint.get_width() // 2, r_hint.centery - t_hint.get_height() // 2))

def draw_boost(boost, now):
    bx, by = int(boost["x"]), int(boost["y"])
    bob = int(math.sin(now * 0.006 + (0 if boost["kind"] == "coffee" else 1.5)) * 3)
    cy = by + 15 + bob
    cx = bx + 15

    if boost["kind"] == "coffee":
        glow = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(glow, (251, 191, 36, 45), (22, 22), 20)
        screen.blit(glow, (cx - 22, cy - 22))

        pygame.draw.circle(screen, (245, 158, 11), (cx, cy), 15)
        pygame.draw.circle(screen, (254, 240, 138), (cx, cy), 15, width=1)

        pygame.draw.rect(screen, (255, 255, 255), (cx - 7, cy - 8, 14, 3), border_radius=1)
        pts = [(cx - 6, cy - 5), (cx + 6, cy - 5), (cx + 4, cy + 7), (cx - 4, cy + 7)]
        pygame.draw.polygon(screen, (255, 255, 255), pts)
        sleeve_pts = [(cx - 5, cy - 1), (cx + 5, cy - 1), (cx + 4, cy + 3), (cx - 4, cy + 3)]
        pygame.draw.polygon(screen, (180, 83, 9), sleeve_pts)
    else:
        glow = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(glow, (56, 189, 248, 45), (22, 22), 20)
        screen.blit(glow, (cx - 22, cy - 22))

        pygame.draw.circle(screen, (14, 165, 233), (cx, cy), 15)
        pygame.draw.circle(screen, (186, 230, 253), (cx, cy), 15, width=1)

        def chevron(surf, ox, oy):
            pts = [(ox - 3, oy - 6), (ox + 2, oy), (ox - 3, oy + 6), (ox - 1, oy + 6), (ox + 4, oy), (ox - 1, oy - 6)]
            pygame.draw.polygon(surf, (255, 255, 255), pts)
        chevron(screen, cx - 3, cy)
        chevron(screen, cx + 4, cy)

def draw_end_modal(won, score, top_speed, now):
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((10, 15, 26, 180))
    screen.blit(dim, (0, 0))

    mw, mh = 480, 270
    mx = (WIDTH - mw) // 2
    my = (HEIGHT - mh) // 2

    card = pygame.Surface((mw, mh), pygame.SRCALPHA)
    pygame.draw.rect(card, (15, 23, 42, 240), (0, 0, mw, mh), border_radius=18)
    pygame.draw.rect(card, (255, 255, 255, 35), (0, 0, mw, mh), width=1, border_radius=18)

    accent_color = C_EMERALD if won else C_ROSE
    pygame.draw.rect(card, accent_color, (mw // 2 - 24, 0, 48, 3), border_radius=2)
    screen.blit(card, (mx, my))

    badge_w, badge_h = 130, 24
    badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
    bg_color = (16, 185, 129, 35) if won else (244, 63, 94, 30)
    pygame.draw.rect(badge_surf, bg_color, (0, 0, badge_w, badge_h), border_radius=12)
    badge_x = mx + (mw - badge_w) // 2
    badge_y = my + 24
    screen.blit(badge_surf, (badge_x, badge_y))

    dot_x = badge_x + 18
    dot_y = badge_y + 12
    if won:
        pygame.draw.circle(screen, C_EMERALD, (dot_x, dot_y), 4)
        t_badge = font_tiny.render("FLIGHT CAUGHT", True, C_EMERALD)
    else:
        pygame.draw.line(screen, C_ROSE, (dot_x - 3, dot_y - 3), (dot_x + 3, dot_y + 3), 2)
        pygame.draw.line(screen, C_ROSE, (dot_x - 3, dot_y + 3), (dot_x + 3, dot_y - 3), 2)
        t_badge = font_tiny.render("FLIGHT MISSED", True, C_ROSE)
    screen.blit(t_badge, (badge_x + 28, badge_y + 5))

    title_text = "WELCOME ABOARD!" if won else "GATE B12 CLOSED"
    t_title = font_title.render(title_text, True, C_WHITE)
    screen.blit(t_title, (mx + (mw - t_title.get_width()) // 2, my + 60))

    sub_text = "You made it to your connecting gate just in time!" if won else "The final call has passed. Better luck next layover!"
    t_sub = font_body.render(sub_text, True, C_MUTED)
    screen.blit(t_sub, (mx + (mw - t_sub.get_width()) // 2, my + 96))

    cap_w, cap_h = 190, 56
    cap_y = my + 130

    c1_x = mx + 36
    c1_surf = pygame.Surface((cap_w, cap_h), pygame.SRCALPHA)
    pygame.draw.rect(c1_surf, (255, 255, 255, 12), (0, 0, cap_w, cap_h), border_radius=10)
    pygame.draw.rect(c1_surf, (255, 255, 255, 20), (0, 0, cap_w, cap_h), width=1, border_radius=10)
    screen.blit(c1_surf, (c1_x, cap_y))

    s_lbl = font_tiny.render("FINAL SCORE", True, C_MUTED)
    s_val = font_large.render(f"{score:,}", True, C_WHITE)
    screen.blit(s_lbl, (c1_x + (cap_w - s_lbl.get_width()) // 2, cap_y + 10))
    screen.blit(s_val, (c1_x + (cap_w - s_val.get_width()) // 2, cap_y + 26))

    c2_x = mx + mw - 36 - cap_w
    c2_surf = pygame.Surface((cap_w, cap_h), pygame.SRCALPHA)
    pygame.draw.rect(c2_surf, (255, 255, 255, 12), (0, 0, cap_w, cap_h), border_radius=10)
    pygame.draw.rect(c2_surf, (255, 255, 255, 20), (0, 0, cap_w, cap_h), width=1, border_radius=10)
    screen.blit(c2_surf, (c2_x, cap_y))

    sp_lbl = font_tiny.render("TOP SPEED", True, C_MUTED)
    sp_val = font_large.render(f"{int(top_speed)} km/h", True, C_CYAN)
    screen.blit(sp_lbl, (c2_x + (cap_w - sp_lbl.get_width()) // 2, cap_y + 10))
    screen.blit(sp_val, (c2_x + (cap_w - sp_val.get_width()) // 2, cap_y + 26))

    btn_w, btn_h = 240, 36
    btn_x = mx + (mw - btn_w) // 2
    btn_y = my + 208
    pulse = 0.5 + 0.5 * math.sin(now * 0.005)
    btn_border_alpha = int(35 + 25 * pulse)
    btn_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
    pygame.draw.rect(btn_surf, (255, 255, 255, 18), (0, 0, btn_w, btn_h), border_radius=18)
    pygame.draw.rect(btn_surf, (255, 255, 255, btn_border_alpha), (0, 0, btn_w, btn_h), width=1, border_radius=18)
    screen.blit(btn_surf, (btn_x, btn_y))

    t_btn = font_mid.render("PRESS [R] TO RETRY", True, C_WHITE)
    screen.blit(t_btn, (btn_x + (btn_w - t_btn.get_width()) // 2, btn_y + (btn_h - t_btn.get_height()) // 2))

def draw_player(rect, sliding, frame_idx=0):
    if sliding:
        surf = avatar_slide_frame
    else:
        surf = avatar_run_frames[frame_idx % len(avatar_run_frames)]
    surf_rect = surf.get_rect(midbottom=(rect.centerx, rect.bottom))
    screen.blit(surf, surf_rect)

def draw_background(offset):
    # Base dark fill
    screen.fill(BLACK)

    # Render each parallax layer from back to front
    for layer in parallax_layers:
        surf = layer["surf"]
        spd = layer["speed"]
        rel_x = -(int(offset * spd) % bg_width)
        x = rel_x
        while x < WIDTH:
            screen.blit(surf, (x, 0))
            x += bg_width

def add_obstacle():
    available_kinds = ["cart", "luggage", "tall_luggage"]
    if game["obstacles"]:
        prev_kind = game["obstacles"][-1]["kind"]
        available_kinds = [k for k in available_kinds if k != prev_kind]
    kind = random.choice(available_kinds)

    img = None
    if kind == "cart":
        if cart_sprites:
            img = random.choice(cart_sprites)
            cw, ch = img.get_size()
            rect = pygame.Rect(WIDTH, GROUND - ch, cw, ch)
        else:
            rect = pygame.Rect(WIDTH, GROUND - 58, 75, 58)
        color = RED
    elif kind == "luggage":
        if luggage_sprites:
            img = random.choice(luggage_sprites)
            lw, lh = img.get_size()
            rect = pygame.Rect(WIDTH, GROUND - lh, lw, lh)
        else:
            rect = pygame.Rect(WIDTH, GROUND - 45, 43, 45)
        color = (145, 90, 50)
    else:  # Tall luggage obstacle from luggage sprites folder
        if tall_luggage_sprites:
            img = random.choice(tall_luggage_sprites)
            tw, th = img.get_size()
            rect = pygame.Rect(WIDTH, GROUND - th, tw, th)
        else:
            rect = pygame.Rect(WIDTH, GROUND - 82, 38, 82)
        color = (230, 150, 45)

    game["obstacles"].append({
        "rect": rect,
        "color": color,
        "kind": kind,
        "x": float(WIDTH),
        "image": img,
    })

def add_boost():
    game["boosts"].append({
        "x": float(WIDTH),
        "y": GROUND - random.choice([100, 130, 160]),
        "kind": random.choice(["coffee", "walkway"]),
    })

def start_game():
    global game
    game = reset_game()

running = True

while running:
    dt = min(clock.tick(60) / 1000.0, 0.05)
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            if event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    try:
                        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
                    except pygame.error:
                        screen = pygame.display.set_mode((WIDTH, HEIGHT))
                        is_fullscreen = False
                else:
                    screen = pygame.display.set_mode((WIDTH, HEIGHT))

            if game["game_over"] or game["won"]:
                if event.key == pygame.K_r:
                    start_game()
                continue

            if event.key in (pygame.K_SPACE, pygame.K_UP):
                if not game["jumping"]:
                    game["velocity_y"] = -650
                    game["jumping"] = True

            if event.key in (pygame.K_DOWN, pygame.K_s):
                game["sliding_until"] = now + 550

    elapsed = (now - game["start_time"]) / 1000
    remaining = max(0, 60 - elapsed)

    # Calculate player position
    sliding = now < game["sliding_until"]

    if not game["game_over"] and not game["won"]:
        # Scroll background as player runs along
        game["bg_scroll"] += game["speed"] * dt

        # Animate running avatar
        anim_speed = 9.0 * (game["speed"] / 350.0)
        game["anim_timer"] += anim_speed * dt

        if game["jumping"]:
            game["velocity_y"] += 1700 * dt
            game["player_y"] += game["velocity_y"] * dt

            if game["player_y"] >= GROUND - 70:
                game["player_y"] = float(GROUND - 70)
                game["velocity_y"] = 0
                game["jumping"] = False

        # Speed increases over time
        game["speed"] = min(520, 350 + elapsed * 3)
        game["top_speed"] = max(game.get("top_speed", 350.0), game["speed"])

        game["spawn_timer"] -= dt
        if game["spawn_timer"] <= 0:
            add_obstacle()
            game["spawn_timer"] = random.uniform(1.0, 1.7)

        game["boost_timer"] -= dt
        if game["boost_timer"] <= 0:
            add_boost()
            game["boost_timer"] = random.uniform(3.5, 5.0)

        # Move obstacles
        for obstacle in game["obstacles"]:
            obstacle["x"] -= game["speed"] * dt
            obstacle["rect"].x = round(obstacle["x"])

        game["obstacles"] = [
            o for o in game["obstacles"]
            if o["rect"].right > 0
        ]

        # Move and collect boosts
        player_h = 42 if sliding else 70
        player_y = game["player_y"] + (28 if sliding else 0)

        player_rect = pygame.Rect(
            PLAYER_X, int(player_y), PLAYER_W, player_h
        )

        for boost in game["boosts"]:
            boost["x"] -= game["speed"] * dt
        game["boosts"] = [
            b for b in game["boosts"] if b["x"] > -40
        ]

        for boost in game["boosts"][:]:
            boost_rect = pygame.Rect(
                int(boost["x"]), int(boost["y"]), 30, 30
            )
            if player_rect.colliderect(boost_rect):
                game["speed"] = min(game["speed"] + 80, 600)
                game["score"] += 25
                game["boosts"].remove(boost)

        # Collision checks
        for obstacle in game["obstacles"]:
            hitbox = obstacle["rect"].inflate(
                -max(4, min(8, obstacle["rect"].w // 4)),
                -max(4, min(6, obstacle["rect"].h // 4))
            )

            if player_rect.colliderect(hitbox):
                game["game_over"] = True

        game["score"] += int(10 * dt)
        if remaining <= 0:
            game["won"] = True

    # Render
    draw_background(game["bg_scroll"])

    for obstacle in game["obstacles"]:
        r = obstacle["rect"]
        if obstacle.get("image"):
            screen.blit(obstacle["image"], r)
        else:
            pygame.draw.rect(
                screen, obstacle["color"], r, border_radius=5
            )
            if obstacle["kind"] == "cart":
                pygame.draw.circle(
                    screen, BLACK, (r.x + 15, r.bottom), 8
                )
                pygame.draw.circle(
                    screen, BLACK, (r.right - 15, r.bottom), 8
                )

    for boost in game["boosts"]:
        draw_boost(boost, now)

    sliding = now < game["sliding_until"]
    ph = 42 if sliding else 70
    py = game["player_y"] + (28 if sliding else 0)
    player_rect = pygame.Rect(PLAYER_X, int(py), PLAYER_W, ph)
    frame_idx = int(game["anim_timer"]) % len(avatar_run_frames)
    draw_player(player_rect, sliding, frame_idx)

    # Minimal floating HUD & control hints
    draw_hud(game["score"], remaining, game["speed"], total_time=60.0)
    draw_controls_hint(elapsed)

    if game["game_over"] or game["won"]:
        draw_end_modal(game["won"], game["score"], game.get("top_speed", game["speed"]), now)

    pygame.display.flip()

pygame.quit()
sys.exit()
