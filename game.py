
import pygame
import random
import sys
import os

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


clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 26)
big_font = pygame.font.SysFont("arial", 48, bold=True)

# Colors
WHITE = (245, 245, 245)
BLACK = (25, 30, 40)
BLUE = (60, 150, 230)
RED = (220, 65, 65)
GREEN = (60, 190, 120)
GRAY = (150, 160, 170)
YELLOW = (255, 200, 65)

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

    # Departure board
    pygame.draw.rect(
        screen, BLACK, (735, 25, 240, 65),
        border_radius=6
    )
    draw_text("GATE B12", 755, 32, GREEN)
    draw_text("BOARDING", 755, 60, WHITE)

def add_obstacle():
    kind = random.choice(["cart", "luggage", "queue"])

    if kind == "cart":
        rect = pygame.Rect(WIDTH, GROUND - 58, 75, 58)
        color = RED
    elif kind == "luggage":
        rect = pygame.Rect(WIDTH, GROUND - 45, 43, 45)
        color = (145, 90, 50)
    else:
        rect = pygame.Rect(WIDTH, GROUND - 90, 28, 90)
        color = (230, 150, 45)

    game["obstacles"].append({
        "rect": rect,
        "color": color,
        "kind": kind,
        "x": float(WIDTH),
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
            hitbox = obstacle["rect"].inflate(-8, -5)

            if player_rect.colliderect(hitbox):
                game["game_over"] = True

        game["score"] += int(10 * dt)
        if remaining <= 0:
            game["won"] = True

    # Render
    draw_background(game["bg_scroll"])

    for obstacle in game["obstacles"]:
        r = obstacle["rect"]
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
        elif obstacle["kind"] == "luggage":
            pygame.draw.rect(
                screen, BLACK,
                (r.x + 14, r.y - 7, 15, 7), 2
            )

    for boost in game["boosts"]:
        bx, by = int(boost["x"]), int(boost["y"])
        if boost["kind"] == "coffee":
            pygame.draw.circle(screen, YELLOW, (bx + 15, by + 15), 17)
            draw_text("C", bx + 7, by + 1, BLACK)
        else:
            pygame.draw.rect(
                screen, GREEN, (bx, by, 30, 30),
                border_radius=6
            )
            draw_text(">", bx + 5, by, WHITE)

    sliding = now < game["sliding_until"]
    ph = 42 if sliding else 70
    py = game["player_y"] + (28 if sliding else 0)
    player_rect = pygame.Rect(PLAYER_X, int(py), PLAYER_W, ph)
    frame_idx = int(game["anim_timer"]) % len(avatar_run_frames)
    draw_player(player_rect, sliding, frame_idx)

    # Stats HUD card
    hud_surf = pygame.Surface((180, 105), pygame.SRCALPHA)
    pygame.draw.rect(hud_surf, (25, 30, 40, 200), (0, 0, 180, 105), border_radius=8)
    pygame.draw.rect(hud_surf, (255, 255, 255, 40), (0, 0, 180, 105), width=1, border_radius=8)
    screen.blit(hud_surf, (20, 20))

    draw_text(f"Score: {game['score']}", 32, 26, WHITE)
    draw_text(f"Time: {int(remaining):02d}s", 32, 56, YELLOW)
    draw_text(f"Speed: {int(game['speed'])}", 32, 86, GREEN)

    if game["game_over"] or game["won"]:
        pygame.draw.rect(
            screen, WHITE, (220, 200, 560, 180),
            border_radius=15
        )

        title = "FLIGHT CAUGHT!" if game["won"] else "MISSED YOUR FLIGHT!"
        draw_text(title, 265, 225, GREEN if game["won"] else RED, big_font)
        draw_text(
            f"Final score: {game['score']}", 390, 290
        )
        draw_text("Press R to restart", 390, 330)

    pygame.display.flip()

pygame.quit()
sys.exit()
