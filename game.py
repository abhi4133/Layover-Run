import pygame
import random
import sys
import os
import math

pygame.init()

# Window setup - initialized with SCALED so SDL2 can smoothly toggle to FULLSCREEN on demand
WIDTH, HEIGHT = 1000, 600
is_fullscreen = False
try:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
except pygame.error:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
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

# High-clarity typography with prioritized modern Windows antialiased fonts
def get_font(names, size, bold=False):
    for name in names:
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont("arial", size, bold=bold)

font_hero = get_font(["segoeui", "bahnschrift", "helvetica", "arial"], 40, bold=True)
font_title = get_font(["segoeui", "bahnschrift", "helvetica", "arial"], 26, bold=True)
font_large = get_font(["segoeui", "bahnschrift", "helvetica", "arial"], 21, bold=True)
font_mid = get_font(["segoeui", "bahnschrift", "helvetica", "arial"], 16, bold=True)
font_body = get_font(["segoeui", "helvetica", "arial"], 14)
font_tiny = get_font(["segoeui", "bahnschrift", "helvetica", "arial"], 12, bold=True)
font = font_mid
big_font = font_title

# High-contrast crisp UI palette
WHITE = (255, 255, 255)
BLACK = (11, 17, 32)
BLUE = (56, 189, 248)
RED = (244, 63, 94)
GREEN = (52, 211, 153)
GRAY = (148, 163, 184)
YELLOW = (251, 191, 36)

C_WHITE = (255, 255, 255)
C_MUTED = (203, 213, 225)       # High-contrast light slate (clear & readable)
C_EMERALD = (52, 211, 153)      # Crisp emerald
C_ROSE = (251, 113, 133)        # Crisp rose
C_AMBER = (251, 191, 36)        # Crisp gold
C_CYAN = (56, 189, 248)         # Crisp sky blue

GROUND = 516
PLAYER_X = 130

def load_high_score():
    try:
        hs_path = os.path.join(base_dir, "highscore.txt")
        if os.path.exists(hs_path):
            with open(hs_path, "r") as f:
                return int(f.read().strip())
    except Exception:
        pass
    return 0

def save_high_score(score):
    try:
        hs_path = os.path.join(base_dir, "highscore.txt")
        with open(hs_path, "w") as f:
            f.write(str(score))
    except Exception:
        pass

def toggle_fullscreen():
    global screen, is_fullscreen
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        try:
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        except pygame.error:
            try:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error:
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
                is_fullscreen = False
    else:
        try:
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
        except pygame.error:
            screen = pygame.display.set_mode((WIDTH, HEIGHT))

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

def draw_glass_pill(surf, rect, bg_alpha=220, border_alpha=40, radius=12):
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
    screen.blit(t_board, (162, 26))

    # Concourse progress bar
    bar_w = 202
    bar_x = 34
    bar_y = 51
    pygame.draw.rect(screen, (255, 255, 255, 30), (bar_x, bar_y, bar_w, 4), border_radius=2)
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

    pygame.draw.line(screen, (255, 255, 255, 30), (865, 24), (865, 60))

    sp_lbl = font_tiny.render("SPEED", True, C_MUTED)
    screen.blit(sp_lbl, (880, 22))
    sp_val = font_large.render(f"{int(speed)}", True, C_CYAN)
    screen.blit(sp_val, (880, 38))

def draw_controls_hint(elapsed):
    if elapsed > 10:
        return
    alpha = 220 if elapsed < 6 else int(220 * max(0.0, (10 - elapsed) / 4.0))
    if alpha <= 0:
        return
    r_hint = pygame.Rect(360, 560, 280, 28)
    pill = pygame.Surface((r_hint.width, r_hint.height), pygame.SRCALPHA)
    pygame.draw.rect(pill, (11, 17, 32, int(alpha * 0.9)), (0, 0, r_hint.width, r_hint.height), border_radius=14)
    pygame.draw.rect(pill, (255, 255, 255, int(alpha * 0.25)), (0, 0, r_hint.width, r_hint.height), width=1, border_radius=14)
    screen.blit(pill, r_hint.topleft)

    t_hint = font_tiny.render("SPACE / ↑  JUMP     •     S / ↓  SLIDE", True, C_WHITE)
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

def draw_end_modal(won, score, top_speed, now, is_new_record=False, mouse_pos=(0, 0)):
    dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    dim.fill((10, 15, 26, 190))
    screen.blit(dim, (0, 0))

    mw, mh = 500, 290
    mx = (WIDTH - mw) // 2
    my = (HEIGHT - mh) // 2

    # Drop shadow
    shadow_card = pygame.Rect(mx + 6, my + 6, mw, mh)
    pygame.draw.rect(screen, (5, 8, 18), shadow_card, border_radius=18)

    card = pygame.Surface((mw, mh), pygame.SRCALPHA)
    pygame.draw.rect(card, (15, 23, 42, 250), (0, 0, mw, mh), border_radius=18)
    pygame.draw.rect(card, (255, 255, 255, 35), (0, 0, mw, mh), width=1, border_radius=18)

    accent_color = C_EMERALD if won else C_ROSE
    pygame.draw.rect(card, accent_color, (mw // 2 - 28, 0, 56, 3), border_radius=2)
    screen.blit(card, (mx, my))

    badge_w, badge_h = 140, 24
    badge_surf = pygame.Surface((badge_w, badge_h), pygame.SRCALPHA)
    bg_color = (16, 185, 129, 35) if won else (244, 63, 94, 30)
    pygame.draw.rect(badge_surf, bg_color, (0, 0, badge_w, badge_h), border_radius=12)
    badge_x = mx + (mw - badge_w) // 2
    badge_y = my + 18
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
    screen.blit(t_badge, (badge_x + 28, badge_y + 4))

    title_text = "WELCOME ABOARD!" if won else "GATE B12 CLOSED"
    t_title = font_title.render(title_text, True, C_WHITE)
    screen.blit(t_title, (mx + (mw - t_title.get_width()) // 2, my + 48))

    sub_text = "You made it to your connecting gate just in time!" if won else "The final call has passed. Better luck next layover!"
    t_sub = font_body.render(sub_text, True, C_MUTED)
    screen.blit(t_sub, (mx + (mw - t_sub.get_width()) // 2, my + 80))

    if is_new_record:
        t_rec = font_tiny.render("★ NEW PERSONAL BEST RECORD! ★", True, C_AMBER)
        screen.blit(t_rec, (mx + (mw - t_rec.get_width()) // 2, my + 102))

    cap_w, cap_h = 190, 56
    cap_y = my + 124

    c1_x = mx + 40
    c1_surf = pygame.Surface((cap_w, cap_h), pygame.SRCALPHA)
    pygame.draw.rect(c1_surf, (255, 255, 255, 15), (0, 0, cap_w, cap_h), border_radius=10)
    pygame.draw.rect(c1_surf, (255, 255, 255, 25), (0, 0, cap_w, cap_h), width=1, border_radius=10)
    screen.blit(c1_surf, (c1_x, cap_y))

    s_lbl = font_tiny.render("FINAL SCORE", True, C_MUTED)
    s_val = font_large.render(f"{score:,}", True, C_WHITE)
    screen.blit(s_lbl, (c1_x + (cap_w - s_lbl.get_width()) // 2, cap_y + 8))
    screen.blit(s_val, (c1_x + (cap_w - s_val.get_width()) // 2, cap_y + 26))

    c2_x = mx + mw - 40 - cap_w
    c2_surf = pygame.Surface((cap_w, cap_h), pygame.SRCALPHA)
    pygame.draw.rect(c2_surf, (255, 255, 255, 15), (0, 0, cap_w, cap_h), border_radius=10)
    pygame.draw.rect(c2_surf, (255, 255, 255, 25), (0, 0, cap_w, cap_h), width=1, border_radius=10)
    screen.blit(c2_surf, (c2_x, cap_y))

    sp_lbl = font_tiny.render("TOP SPEED", True, C_MUTED)
    sp_val = font_large.render(f"{int(top_speed)} km/h", True, C_CYAN)
    screen.blit(sp_lbl, (c2_x + (cap_w - sp_lbl.get_width()) // 2, cap_y + 8))
    screen.blit(sp_val, (c2_x + (cap_w - sp_val.get_width()) // 2, cap_y + 26))

    # Action Buttons: [R] Retry and [M] Main Menu
    btn_w = 195
    btn_h = 42
    btn_y = my + 214

    btn_retry_rect = pygame.Rect(mx + 40, btn_y, btn_w, btn_h)
    btn_menu_rect = pygame.Rect(mx + mw - 40 - btn_w, btn_y, btn_w, btn_h)

    # Retry button
    r_hover = btn_retry_rect.collidepoint(mouse_pos)
    r_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
    pygame.draw.rect(r_surf, (255, 255, 255, 28 if r_hover else 16), (0, 0, btn_w, btn_h), border_radius=14)
    screen.blit(r_surf, btn_retry_rect.topleft)
    pygame.draw.rect(screen, C_EMERALD if r_hover else (255, 255, 255, 40), btn_retry_rect, width=2 if r_hover else 1, border_radius=14)
    t_r = font_mid.render("[R] RETRY SPRINT", True, C_WHITE)
    screen.blit(t_r, (btn_retry_rect.centerx - t_r.get_width() // 2, btn_retry_rect.centery - t_r.get_height() // 2))

    # Menu button
    m_hover = btn_menu_rect.collidepoint(mouse_pos)
    m_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
    pygame.draw.rect(m_surf, (255, 255, 255, 28 if m_hover else 16), (0, 0, btn_w, btn_h), border_radius=14)
    screen.blit(m_surf, btn_menu_rect.topleft)
    pygame.draw.rect(screen, C_CYAN if m_hover else (255, 255, 255, 40), btn_menu_rect, width=2 if m_hover else 1, border_radius=14)
    t_m = font_mid.render("[M] MAIN MENU", True, C_WHITE)
    screen.blit(t_m, (btn_menu_rect.centerx - t_m.get_width() // 2, btn_menu_rect.centery - t_m.get_height() // 2))

    return btn_retry_rect, btn_menu_rect

def draw_player(rect, sliding, frame_idx=0):
    if sliding:
        surf = avatar_slide_frame
    else:
        surf = avatar_run_frames[frame_idx % len(avatar_run_frames)]
    surf_rect = surf.get_rect(midbottom=(rect.centerx, rect.bottom))
    screen.blit(surf, surf_rect)

def draw_background(offset):
    screen.fill(BLACK)
    for layer in parallax_layers:
        surf = layer["surf"]
        spd = layer["speed"]
        rel_x = -(int(offset * spd) % bg_width)
        x = rel_x
        while x < WIDTH:
            screen.blit(surf, (x, 0))
            x += bg_width

def draw_start_menu(now, menu_scroll, anim_timer, selected_idx, high_score, mouse_pos):
    # 1. Background parallax layers
    draw_background(menu_scroll)

    # 2. Cinematic backdrop tint
    tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    tint.fill((11, 17, 32, 140))
    screen.blit(tint, (0, 0))

    # 3. Avatar running preview on the moving walkway
    runner_x = 760
    runner_y = GROUND - 70
    pygame.draw.ellipse(screen, (0, 0, 0, 90), (runner_x - 6, GROUND - 8, PLAYER_W + 12, 12))
    f_idx = int(anim_timer) % len(avatar_run_frames)
    screen.blit(avatar_run_frames[f_idx], (runner_x, runner_y))

    # Floating Gate badge above runner
    gate_badge = pygame.Rect(runner_x - 30, runner_y - 44, 112, 28)
    draw_glass_pill(screen, gate_badge, bg_alpha=240, border_alpha=40, radius=14)
    pulse = 0.5 + 0.5 * math.sin(now * 0.006)
    dot_color = (int(52 + 40 * pulse), 211, 153)
    pygame.draw.circle(screen, dot_color, (gate_badge.x + 16, gate_badge.centery), 4)
    t_gb = font_tiny.render("GATE B12", True, C_WHITE)
    screen.blit(t_gb, (gate_badge.x + 28, gate_badge.centery - t_gb.get_height() // 2))

    # 4. Main Menu Card with solid high-contrast dark fill & drop shadow
    cw, ch = 540, 510
    cx = 60
    cy = (HEIGHT - ch) // 2

    # Drop shadow
    shadow_card = pygame.Rect(cx + 6, cy + 6, cw, ch)
    pygame.draw.rect(screen, (5, 8, 18), shadow_card, border_radius=20)

    # Card body
    card = pygame.Surface((cw, ch), pygame.SRCALPHA)
    pygame.draw.rect(card, (15, 23, 42, 250), (0, 0, cw, ch), border_radius=20)
    pygame.draw.rect(card, (255, 255, 255, 30), (0, 0, cw, ch), width=1, border_radius=20)
    pygame.draw.rect(card, C_EMERALD, (32, 0, 90, 3), border_radius=2)
    pygame.draw.rect(card, C_CYAN, (126, 0, 50, 3), border_radius=2)
    screen.blit(card, (cx, cy))

    # Departure Status pill inside card
    status_rect = pygame.Rect(cx + 32, cy + 24, 280, 26)
    s_surf = pygame.Surface((status_rect.width, status_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s_surf, (16, 185, 129, 35), (0, 0, status_rect.width, status_rect.height), border_radius=13)
    pygame.draw.rect(s_surf, (16, 185, 129, 70), (0, 0, status_rect.width, status_rect.height), width=1, border_radius=13)
    screen.blit(s_surf, status_rect.topleft)
    pygame.draw.circle(screen, C_EMERALD, (status_rect.x + 14, status_rect.centery), 4)
    t_stat = font_tiny.render("FINAL BOARDING CALL • 60 SECONDS", True, C_EMERALD)
    screen.blit(t_stat, (status_rect.x + 24, status_rect.centery - t_stat.get_height() // 2))

    # Main Hero Title
    t_title = font_hero.render("LAYOVER RUN", True, C_WHITE)
    screen.blit(t_title, (cx + 32, cy + 58))

    # Subtitle
    t_sub = font_body.render("Sprint through Concourse B and catch your flight before gate closes!", True, C_MUTED)
    screen.blit(t_sub, (cx + 32, cy + 104))

    # Personal best banner
    pb_rect = pygame.Rect(cx + 32, cy + 134, cw - 64, 36)
    draw_glass_pill(screen, pb_rect, bg_alpha=200, border_alpha=30, radius=10)
    t_pb_lbl = font_tiny.render("PERSONAL BEST RECORD", True, C_MUTED)
    t_pb_val = font_mid.render(f"{high_score:,} PTS", True, C_AMBER)
    screen.blit(t_pb_lbl, (pb_rect.x + 16, pb_rect.centery - t_pb_lbl.get_height() // 2))
    screen.blit(t_pb_val, (pb_rect.right - 16 - t_pb_val.get_width(), pb_rect.centery - t_pb_val.get_height() // 2))

    # Menu Buttons
    btn_defs = [
        {"icon": "▶", "label": "START SPRINT", "sub": "Board flight immediately • [ENTER] / [SPACE]", "accent": C_EMERALD},
        {"icon": "ℹ", "label": "HOW TO PLAY", "sub": "Controls, obstacles & concourse boosts • [H]", "accent": C_CYAN},
        {"icon": "✕", "label": "EXIT GAME", "sub": "Quit to desktop • [ESC]", "accent": C_ROSE},
    ]

    btn_rects = []
    btn_w = cw - 64
    btn_h = 66
    btn_y0 = cy + 184
    gap = 14

    for i, b in enumerate(btn_defs):
        b_rect = pygame.Rect(cx + 32, btn_y0 + i * (btn_h + gap), btn_w, btn_h)
        btn_rects.append(b_rect)

        is_hovered = b_rect.collidepoint(mouse_pos)
        is_active = (selected_idx == i) or is_hovered

        b_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bg_col = (255, 255, 255, 26) if is_active else (255, 255, 255, 10)
        pygame.draw.rect(b_surf, bg_col, (0, 0, btn_w, btn_h), border_radius=14)

        border_alpha = int(140 + 60 * math.sin(now * 0.008)) if is_active else 25
        pygame.draw.rect(b_surf, (255, 255, 255, border_alpha if not is_active else 40), (0, 0, btn_w, btn_h), width=1, border_radius=14)
        screen.blit(b_surf, b_rect.topleft)

        if is_active:
            pygame.draw.rect(screen, b["accent"], b_rect, width=2, border_radius=14)
            pygame.draw.rect(screen, b["accent"], (b_rect.x + 8, b_rect.y + 12, 4, btn_h - 24), border_radius=2)

        title_col = C_WHITE if is_active else (235, 240, 250)
        t_lbl = font_large.render(f"{b['icon']}  {b['label']}", True, title_col)
        screen.blit(t_lbl, (b_rect.x + 24, b_rect.y + 12))

        sub_col = b["accent"] if is_active else C_MUTED
        t_sub_btn = font_tiny.render(b["sub"], True, sub_col)
        screen.blit(t_sub_btn, (b_rect.x + 24, b_rect.y + 38))

    # Footer instructions
    fs_label = "F11  EXIT FULLSCREEN" if is_fullscreen else "F11  FULLSCREEN"
    t_ft = font_tiny.render(f"↑ / ↓  SELECT     •     ENTER / SPACE  CONFIRM     •     {fs_label}", True, C_MUTED)
    screen.blit(t_ft, (cx + (cw - t_ft.get_width()) // 2, cy + ch - 22))

    return btn_rects

def draw_how_to_play(now, menu_scroll, mouse_pos):
    draw_background(menu_scroll)

    tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    tint.fill((11, 17, 32, 185))
    screen.blit(tint, (0, 0))

    cw, ch = 780, 520
    cx = (WIDTH - cw) // 2
    cy = (HEIGHT - ch) // 2

    # Drop shadow
    shadow_card = pygame.Rect(cx + 6, cy + 6, cw, ch)
    pygame.draw.rect(screen, (5, 8, 18), shadow_card, border_radius=20)

    card = pygame.Surface((cw, ch), pygame.SRCALPHA)
    pygame.draw.rect(card, (15, 23, 42, 252), (0, 0, cw, ch), border_radius=20)
    pygame.draw.rect(card, (255, 255, 255, 35), (0, 0, cw, ch), width=1, border_radius=20)
    pygame.draw.rect(card, C_CYAN, (cw // 2 - 50, 0, 100, 3), border_radius=2)
    screen.blit(card, (cx, cy))

    # Header
    t_head = font_title.render("AIRPORT PASSENGER BRIEFING", True, C_WHITE)
    screen.blit(t_head, (cx + (cw - t_head.get_width()) // 2, cy + 18))
    t_subhead = font_body.render("Layover Run Survival Guide • Terminal Concourse B", True, C_MUTED)
    screen.blit(t_subhead, (cx + (cw - t_subhead.get_width()) // 2, cy + 48))

    # 3 Content Panels
    p_w = cw - 64
    p_x = cx + 32

    # Panel 1: Mission
    p1_rect = pygame.Rect(p_x, cy + 76, p_w, 82)
    draw_glass_pill(screen, p1_rect, bg_alpha=200, border_alpha=30, radius=12)
    pygame.draw.rect(screen, C_EMERALD, (p1_rect.x + 8, p1_rect.y + 12, 3, p1_rect.h - 24), border_radius=2)
    t_p1_title = font_mid.render("🎯 THE MISSION", True, C_EMERALD)
    screen.blit(t_p1_title, (p1_rect.x + 20, p1_rect.y + 10))
    t_p1_d1 = font_body.render("Your connecting flight departs from Gate B12 in exactly 60 seconds!", True, C_WHITE)
    t_p1_d2 = font_body.render("Sprint through the busy concourse, jump baggage carts, and slide under obstacles to board in time.", True, C_MUTED)
    screen.blit(t_p1_d1, (p1_rect.x + 20, p1_rect.y + 34))
    screen.blit(t_p1_d2, (p1_rect.x + 20, p1_rect.y + 54))

    # Panel 2: Controls
    p2_rect = pygame.Rect(p_x, cy + 168, p_w, 150)
    draw_glass_pill(screen, p2_rect, bg_alpha=200, border_alpha=30, radius=12)
    pygame.draw.rect(screen, C_CYAN, (p2_rect.x + 8, p2_rect.y + 12, 3, p2_rect.h - 24), border_radius=2)
    t_p2_title = font_mid.render("🎮 CONTROLS", True, C_CYAN)
    screen.blit(t_p2_title, (p2_rect.x + 20, p2_rect.y + 10))

    controls_data = [
        ("SPACE  /  UP ARROW", "JUMP over luggage and baggage carts"),
        ("S  /  DOWN ARROW", "SLIDE under high obstacles & barriers"),
        ("F11  /  ALT+ENTER", "Toggle FULLSCREEN / WINDOWED mode"),
        ("ESC", "Return to MENU / Pause"),
    ]
    for idx, (k_txt, k_desc) in enumerate(controls_data):
        row_y = p2_rect.y + 36 + idx * 26
        k_w = 175
        kp_rect = pygame.Rect(p2_rect.x + 20, row_y - 2, k_w, 22)
        draw_glass_pill(screen, kp_rect, bg_alpha=220, border_alpha=35, radius=6)
        t_k = font_tiny.render(k_txt, True, C_WHITE)
        screen.blit(t_k, (kp_rect.centerx - t_k.get_width() // 2, kp_rect.centery - t_k.get_height() // 2))

        t_desc = font_body.render(k_desc, True, C_MUTED)
        screen.blit(t_desc, (p2_rect.x + 210, row_y + 1))

    # Panel 3: Boosts
    p3_rect = pygame.Rect(p_x, cy + 328, p_w, 95)
    draw_glass_pill(screen, p3_rect, bg_alpha=200, border_alpha=30, radius=12)
    pygame.draw.rect(screen, C_AMBER, (p3_rect.x + 8, p3_rect.y + 12, 3, p3_rect.h - 24), border_radius=2)
    t_p3_title = font_mid.render("⚡ TERMINAL POWER-UPS", True, C_AMBER)
    screen.blit(t_p3_title, (p3_rect.x + 20, p3_rect.y + 10))

    t_b1 = font_body.render("☕ Coffee Cup: Instant caffeine speed boost and +25 bonus points.", True, C_WHITE)
    t_b2 = font_body.render("⏩ Moving Walkway: Propels your avatar forward at top velocity to beat the clock.", True, C_WHITE)
    screen.blit(t_b1, (p3_rect.x + 20, p3_rect.y + 36))
    screen.blit(t_b2, (p3_rect.x + 20, p3_rect.y + 60))

    # Back Button
    back_btn_w = 260
    back_btn_h = 42
    back_rect = pygame.Rect(cx + (cw - back_btn_w) // 2, cy + ch - 54, back_btn_w, back_btn_h)

    is_hovered = back_rect.collidepoint(mouse_pos)
    back_surf = pygame.Surface((back_btn_w, back_btn_h), pygame.SRCALPHA)
    pygame.draw.rect(back_surf, (255, 255, 255, 28 if is_hovered else 16), (0, 0, back_btn_w, back_btn_h), border_radius=18)
    screen.blit(back_surf, back_rect.topleft)

    border_color = C_CYAN if is_hovered else (255, 255, 255, 45)
    pygame.draw.rect(screen, border_color, back_rect, width=2 if is_hovered else 1, border_radius=18)

    t_back = font_mid.render("←  BACK TO MENU", True, C_WHITE)
    screen.blit(t_back, (back_rect.centerx - t_back.get_width() // 2, back_rect.centery - t_back.get_height() // 2))

    return back_rect

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
    game["start_time"] = pygame.time.get_ticks()

def main():
    global game, is_fullscreen, screen

    high_score = load_high_score()
    state = "MENU"  # "MENU", "PLAYING", "HOW_TO_PLAY"
    menu_scroll = 0.0
    menu_anim_timer = 0.0
    selected_menu_idx = 0
    is_new_record = False

    menu_btn_rects = []
    howto_back_rect = None
    end_retry_rect = None
    end_menu_rect = None

    running = True

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        now = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        # Update menu scroll & anim when not actively in a run
        if state in ("MENU", "HOW_TO_PLAY"):
            menu_scroll += 45.0 * dt
            menu_anim_timer += 9.0 * dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                is_alt_enter = (event.key == pygame.K_RETURN and bool(event.mod & pygame.KMOD_ALT))
                if event.key == pygame.K_F11 or is_alt_enter:
                    toggle_fullscreen()
                    continue

                if state == "MENU":
                    if event.key in (pygame.K_UP, pygame.K_w):
                        selected_menu_idx = (selected_menu_idx - 1) % 3
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected_menu_idx = (selected_menu_idx + 1) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if selected_menu_idx == 0:
                            start_game()
                            is_new_record = False
                            state = "PLAYING"
                        elif selected_menu_idx == 1:
                            state = "HOW_TO_PLAY"
                        elif selected_menu_idx == 2:
                            running = False
                    elif event.key == pygame.K_h:
                        state = "HOW_TO_PLAY"
                    elif event.key == pygame.K_ESCAPE:
                        running = False

                elif state == "HOW_TO_PLAY":
                    if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_BACKSPACE):
                        state = "MENU"

                elif state == "PLAYING":
                    if game["game_over"] or game["won"]:
                        if event.key == pygame.K_r:
                            start_game()
                            is_new_record = False
                        elif event.key in (pygame.K_m, pygame.K_ESCAPE):
                            state = "MENU"
                    else:
                        if event.key == pygame.K_ESCAPE:
                            state = "MENU"
                        elif event.key in (pygame.K_SPACE, pygame.K_UP):
                            if not game["jumping"]:
                                game["velocity_y"] = -650
                                game["jumping"] = True
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            game["sliding_until"] = now + 550

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "MENU":
                    for i, b_rect in enumerate(menu_btn_rects):
                        if b_rect.collidepoint(event.pos):
                            if i == 0:
                                start_game()
                                is_new_record = False
                                state = "PLAYING"
                            elif i == 1:
                                state = "HOW_TO_PLAY"
                            elif i == 2:
                                running = False

                elif state == "HOW_TO_PLAY":
                    if howto_back_rect and howto_back_rect.collidepoint(event.pos):
                        state = "MENU"

                elif state == "PLAYING" and (game["game_over"] or game["won"]):
                    if end_retry_rect and end_retry_rect.collidepoint(event.pos):
                        start_game()
                        is_new_record = False
                    elif end_menu_rect and end_menu_rect.collidepoint(event.pos):
                        state = "MENU"

        # State updates and rendering
        if state == "MENU":
            for i, b_rect in enumerate(menu_btn_rects):
                if b_rect.collidepoint(mouse_pos):
                    selected_menu_idx = i
            menu_btn_rects = draw_start_menu(now, menu_scroll, menu_anim_timer, selected_menu_idx, high_score, mouse_pos)

        elif state == "HOW_TO_PLAY":
            howto_back_rect = draw_how_to_play(now, menu_scroll, mouse_pos)

        elif state == "PLAYING":
            elapsed = (now - game["start_time"]) / 1000
            remaining = max(0, 60 - elapsed)

            # Calculate player position
            sliding = now < game["sliding_until"]

            if not game["game_over"] and not game["won"]:
                game["bg_scroll"] += game["speed"] * dt

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

                if (game["game_over"] or game["won"]) and game["score"] > high_score:
                    high_score = game["score"]
                    save_high_score(high_score)
                    is_new_record = True

            # Render gameplay
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
                end_retry_rect, end_menu_rect = draw_end_modal(
                    game["won"], game["score"], game.get("top_speed", game["speed"]),
                    now, is_new_record, mouse_pos
                )

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
