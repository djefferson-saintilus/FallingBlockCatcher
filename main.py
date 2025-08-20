import pygame
import random
import sys
import math
import os

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Falling Blocks Catcher - Enhanced Edition")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
PINK = (255, 192, 203)

# Game variables
basket_width = 100
basket_height = 20
basket_x = WIDTH // 2 - basket_width // 2
basket_y = HEIGHT - 30
basket_speed = 8

block_size = 30
blocks = []
power_ups = []
block_speed = 3
block_spawn_rate = 30  # Lower is faster

score = 0
high_score = 0
health = 100
level = 1
level_thresholds = [0, 500, 1000, 2000, 5000]  # Score thresholds for levels
level_colors = [BLUE, GREEN, PURPLE, ORANGE, RED]
level_names = ["Beginner", "Intermediate", "Advanced", "Expert", "Master"]

# Power-up types and their durations (in frames)
POWERUP_TYPES = {
    "slow_motion": {"duration": 300, "color": CYAN, "name": "Slow Motion"},
    "double_points": {"duration": 450, "color": YELLOW, "name": "Double Points"},
    "magnet": {"duration": 600, "color": PINK, "name": "Magnet"},
    "shield": {"duration": 500, "color": PURPLE, "name": "Shield"}
}

active_power_ups = {key: 0 for key in POWERUP_TYPES.keys()}  # Track active power-ups

# Block types with their properties
BLOCK_TYPES = {
    "good": {"points": 10, "color": GREEN, "spawn_chance": 60},
    "bad": {"points": -10, "color": RED, "spawn_chance": 25},
    "special": {"points": 20, "color": YELLOW, "spawn_chance": 10, "heal": 5},
    "bonus": {"points": 50, "color": ORANGE, "spawn_chance": 4, "heal": 10},
    "bomb": {"points": -30, "color": BLACK, "spawn_chance": 1, "damage": 20}
}

game_over = False
game_paused = False
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 24)

# Create sound objects with buffer to fix playback issues
try:
    # Create silent sound objects using numpy arrays
    import numpy
    silent_array = numpy.zeros((2205, 2), dtype=numpy.int16)  # 0.05s of silence at 44100Hz stereo
    catch_sound = pygame.mixer.Sound(silent_array)
    damage_sound = pygame.mixer.Sound(silent_array)
    powerup_sound = pygame.mixer.Sound(silent_array)
    level_up_sound = pygame.mixer.Sound(silent_array)
    
    # Try to load actual sound files if they exist
    if os.path.exists("catch.wav"):
        catch_sound = pygame.mixer.Sound("catch.wav")
    if os.path.exists("damage.wav"):
        damage_sound = pygame.mixer.Sound("damage.wav")
    if os.path.exists("powerup.wav"):
        powerup_sound = pygame.mixer.Sound("powerup.wav")
    if os.path.exists("levelup.wav"):
        level_up_sound = pygame.mixer.Sound("levelup.wav")
    
    has_sound = True
except Exception as e:
    print(f"Sound initialization error: {e}")
    has_sound = False

# Particle system for visual effects
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(2, 6)
        self.speed_x = random.uniform(-3, 3)
        self.speed_y = random.uniform(-3, 3)
        self.life = random.randint(20, 40)
    
    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.life -= 1
        self.size = max(0, self.size - 0.1)
        return self.life <= 0
    
    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.size))

particles = []

def create_particles(x, y, color, count=10):
    for _ in range(count):
        particles.append(Particle(x, y, color))

def update_particles():
    global particles
    particles = [p for p in particles if not p.update()]

def draw_particles(surface):
    for p in particles:
        p.draw(surface)

# Draw a gradient background based on level
def draw_background():
    color = level_colors[level - 1]
    for y in range(HEIGHT):
        # Calculate gradient intensity
        intensity = 0.3 + 0.7 * (y / HEIGHT)
        r = min(255, int(color[0] * intensity))
        g = min(255, int(color[1] * intensity))
        b = min(255, int(color[2] * intensity))
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

# Draw the basket with visual effects
def draw_basket():
    color = BLUE
    if active_power_ups["shield"] > 0:
        # Pulsing effect for shield
        pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) * 50
        color = (min(255, BLUE[0] + pulse), min(255, BLUE[1] + pulse), BLUE[2])
        
        # Draw shield glow
        shield_radius = basket_width * 0.7
        shield_surface = pygame.Surface((shield_radius*2, shield_radius*2), pygame.SRCALPHA)
        pygame.draw.circle(shield_surface, (PURPLE[0], PURPLE[1], PURPLE[2], 100), 
                          (int(shield_radius), int(shield_radius)), int(shield_radius))
        screen.blit(shield_surface, (basket_x + basket_width/2 - shield_radius, 
                                    basket_y + basket_height/2 - shield_radius))
    
    pygame.draw.rect(screen, color, (basket_x, basket_y, basket_width, basket_height))
    
    # Draw basket details
    pygame.draw.rect(screen, BLACK, (basket_x, basket_y, basket_width, basket_height), 2)
    for i in range(1, 4):
        pygame.draw.line(screen, BLACK, 
                        (basket_x + i * basket_width/4, basket_y),
                        (basket_x + i * basket_width/4, basket_y + basket_height), 2)

# Draw blocks with visual effects
def draw_block(x, y, block_type):
    props = BLOCK_TYPES[block_type]
    color = props["color"]
    
    # Special effects for certain blocks
    if block_type == "bonus":
        # Pulsing effect for bonus blocks
        pulse = (math.sin(pygame.time.get_ticks() * 0.02) + 1) * 40
        color = (min(255, color[0] + pulse), min(255, color[1] + pulse), color[2])
    elif block_type == "bomb":
        # Flickering effect for bomb blocks
        if random.random() > 0.7:
            color = RED
    
    pygame.draw.rect(screen, color, (x, y, block_size, block_size))
    pygame.draw.rect(screen, BLACK, (x, y, block_size, block_size), 2)
    
    # Add special markings based on block type
    if block_type == "good":
        pygame.draw.circle(screen, WHITE, (x + block_size//2, y + block_size//2), block_size//4)
    elif block_type == "bad":
        pygame.draw.line(screen, WHITE, (x + 5, y + 5), (x + block_size - 5, y + block_size - 5), 2)
        pygame.draw.line(screen, WHITE, (x + block_size - 5, y + 5), (x + 5, y + block_size - 5), 2)
    elif block_type == "special":
        pygame.draw.polygon(screen, WHITE, [(x + block_size//2, y + 5),
                                          (x + block_size - 5, y + block_size - 5),
                                          (x + 5, y + block_size - 5)])
    elif block_type == "bonus":
        pygame.draw.rect(screen, WHITE, (x + block_size//4, y + block_size//4, 
                                        block_size//2, block_size//2))
    elif block_type == "bomb":
        pygame.draw.circle(screen, RED, (x + block_size//2, y + block_size//2), block_size//3)

# Draw power-ups with visual effects
def draw_power_up(x, y, power_type):
    props = POWERUP_TYPES[power_type]
    color = props["color"]
    
    # Pulsing effect for power-ups
    pulse = (math.sin(pygame.time.get_ticks() * 0.03) + 1) * 30
    color = (min(255, color[0] + pulse), min(255, color[1] + pulse), min(255, color[2] + pulse))
    
    pygame.draw.rect(screen, color, (x, y, block_size, block_size))
    pygame.draw.rect(screen, BLACK, (x, y, block_size, block_size), 2)
    
    # Add special markings based on power-up type
    if power_type == "slow_motion":
        pygame.draw.circle(screen, WHITE, (x + block_size//2, y + block_size//2), block_size//3, 2)
        pygame.draw.line(screen, WHITE, (x + block_size//2, y + block_size//3),
                        (x + block_size//2, y + 2*block_size//3), 2)
    elif power_type == "double_points":
        pygame.draw.line(screen, WHITE, (x + block_size//3, y + block_size//3),
                        (x + 2*block_size//3, y + 2*block_size//3), 2)
        pygame.draw.line(screen, WHITE, (x + 2*block_size//3, y + block_size//3),
                        (x + block_size//3, y + 2*block_size//3), 2)
    elif power_type == "magnet":
        pygame.draw.arc(screen, WHITE, (x + 5, y + 5, block_size - 10, block_size - 10), 
                        math.pi/4, 7*math.pi/4, 2)
    elif power_type == "shield":
        pygame.draw.circle(screen, WHITE, (x + block_size//2, y + block_size//2), block_size//3, 2)

# Draw the UI with visual improvements
def draw_ui():
    # Draw score with shadow effect
    score_text = font.render(f"Score: {score}", True, WHITE)
    pygame.draw.rect(screen, (0, 0, 0, 100), (10, 10, score_text.get_width() + 10, score_text.get_height() + 5))
    screen.blit(score_text, (15, 12))
    
    # Draw health bar
    health_width = 200
    health_height = 20
    pygame.draw.rect(screen, (50, 50, 50), (WIDTH - health_width - 10, 10, health_width, health_height))
    pygame.draw.rect(screen, GREEN, (WIDTH - health_width - 10, 10, health_width * (health/100), health_height))
    pygame.draw.rect(screen, WHITE, (WIDTH - health_width - 10, 10, health_width, health_height), 2)
    
    health_text = small_font.render(f"{health}%", True, WHITE)
    screen.blit(health_text, (WIDTH - health_width//2 - health_text.get_width()//2, 12))
    
    # Draw level indicator
    level_text = font.render(f"Level: {level} - {level_names[level-1]}", True, level_colors[level-1])
    screen.blit(level_text, (WIDTH//2 - level_text.get_width()//2, 10))
    
    # Draw active power-ups
    y_offset = 40
    for power_type, duration in active_power_ups.items():
        if duration > 0:
            props = POWERUP_TYPES[power_type]
            power_text = small_font.render(f"{props['name']}: {duration//60}s", True, props['color'])
            pygame.draw.rect(screen, (0, 0, 0, 100), (10, y_offset, power_text.get_width() + 10, power_text.get_height() + 5))
            screen.blit(power_text, (15, y_offset))
            y_offset += 25

# Spawn a new block based on probabilities
def spawn_block():
    total_chance = sum(BLOCK_TYPES[bt]["spawn_chance"] for bt in BLOCK_TYPES)
    rand = random.randint(1, total_chance)
    current = 0
    
    for block_type, props in BLOCK_TYPES.items():
        current += props["spawn_chance"]
        if rand <= current:
            return {
                "x": random.randint(0, WIDTH - block_size),
                "y": 0,
                "type": block_type,
                "speed": block_speed * (0.8 + 0.4 * random.random())  # Randomize speed slightly
            }
    
    return None

# Spawn a power-up with a low probability
def spawn_power_up():
    if random.random() < 0.01:  # 1% chance per frame to spawn a power-up
        power_type = random.choice(list(POWERUP_TYPES.keys()))
        return {
            "x": random.randint(0, WIDTH - block_size),
            "y": 0,
            "type": power_type,
            "speed": block_speed * 0.8  # Power-ups fall slightly slower
        }
    return None

# Apply a power-up effect
def apply_power_up(power_type):
    active_power_ups[power_type] = POWERUP_TYPES[power_type]["duration"]
    if has_sound:
        try:
            powerup_sound.play()
        except:
            pass

# Update active power-ups and their effects
def update_power_ups():
    global block_speed, score
    
    # Decrement all active power-ups
    for power_type in active_power_ups:
        if active_power_ups[power_type] > 0:
            active_power_ups[power_type] -= 1
    
    # Apply power-up effects
    if active_power_ups["slow_motion"] > 0:
        # Slow down all blocks
        for block in blocks:
            block["speed"] = block_speed * 0.5
    else:
        # Reset block speeds
        for block in blocks:
            block["speed"] = block_speed

# Check for level up
def check_level_up():
    global level, block_speed, block_spawn_rate
    
    for i, threshold in enumerate(level_thresholds):
        if score >= threshold and i + 1 > level:
            level = i + 1
            block_speed = 3 + level  # Increase speed with level
            block_spawn_rate = max(5, 30 - level * 3)  # Increase spawn rate with level
            
            # Create level up particles
            for _ in range(100):
                create_particles(WIDTH//2, HEIGHT//2, level_colors[level-1])
            
            if has_sound:
                try:
                    level_up_sound.play()
                except:
                    pass
            return True
    return False

# Draw the game over screen
def draw_game_over():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    
    game_over_text = font.render("GAME OVER", True, RED)
    final_score_text = font.render(f"Final Score: {score}", True, WHITE)
    high_score_text = font.render(f"High Score: {high_score}", True, YELLOW)
    level_text = font.render(f"Reached Level: {level} - {level_names[level-1]}", True, level_colors[level-1])
    restart_text = font.render("Press R to restart or Q to quit", True, WHITE)
    
    screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2 - 100))
    screen.blit(final_score_text, (WIDTH // 2 - final_score_text.get_width() // 2, HEIGHT // 2 - 50))
    screen.blit(high_score_text, (WIDTH // 2 - high_score_text.get_width() // 2, HEIGHT // 2))
    screen.blit(level_text, (WIDTH // 2 - level_text.get_width() // 2, HEIGHT // 2 + 50))
    screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 100))

# Draw the pause screen
def draw_pause_screen():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))
    
    pause_text = font.render("GAME PAUSED", True, YELLOW)
    continue_text = font.render("Press P to continue", True, WHITE)
    
    screen.blit(pause_text, (WIDTH // 2 - pause_text.get_width() // 2, HEIGHT // 2 - 50))
    screen.blit(continue_text, (WIDTH // 2 - continue_text.get_width() // 2, HEIGHT // 2 + 50))

# Main game loop
while not game_over:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game_over = True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                game_paused = not game_paused
            elif event.key == pygame.K_q and game_paused:
                game_over = True
    
    if game_paused:
        draw_pause_screen()
        pygame.display.flip()
        clock.tick(60)
        continue
    
    # Move basket with arrow keys
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and basket_x > 0:
        basket_x -= basket_speed
    if keys[pygame.K_RIGHT] and basket_x < WIDTH - basket_width:
        basket_x += basket_speed
    
    # Apply magnet effect if active
    if active_power_ups["magnet"] > 0:
        magnet_radius = 150
        for block in blocks:
            block_center_x = block["x"] + block_size/2
            block_center_y = block["y"] + block_size/2
            basket_center_x = basket_x + basket_width/2
            basket_center_y = basket_y + basket_height/2
            
            distance = math.sqrt((block_center_x - basket_center_x)**2 + 
                                (block_center_y - basket_center_y)**2)
            
            if distance < magnet_radius:
                # Move block toward basket
                angle = math.atan2(basket_center_y - block_center_y, 
                                  basket_center_x - block_center_x)
                block["x"] += math.cos(angle) * 5
                block["y"] += math.sin(angle) * 5
    
    # Spawn new blocks
    if random.randint(1, block_spawn_rate) == 1:
        new_block = spawn_block()
        if new_block:
            blocks.append(new_block)
    
    # Spawn power-ups
    new_power_up = spawn_power_up()
    if new_power_up:
        power_ups.append(new_power_up)
    
    # Move blocks and check for collisions
    for block in blocks[:]:
        block["y"] += block["speed"]
        
        # Check if block is caught by basket
        if (basket_y < block["y"] + block_size and
            basket_y + basket_height > block["y"] and
            basket_x < block["x"] + block_size and
            basket_x + basket_width > block["x"]):
            
            block_type = block["type"]
            props = BLOCK_TYPES[block_type]
            
            # Apply shield protection
            if active_power_ups["shield"] > 0 and props["points"] < 0:
                # Block is harmful but shield is active
                score += 5  # Small bonus for deflecting
                create_particles(block["x"] + block_size/2, block["y"] + block_size/2, PURPLE, 20)
            else:
                # Normal block handling
                points = props["points"]
                if active_power_ups["double_points"] > 0 and points > 0:
                    points *= 2
                
                score += points
                
                # FIXED: Health reduction for bad blocks
                if block_type == "bad" or block_type == "bomb":
                    if "damage" in props:
                        health -= props["damage"]
                    else:
                        health -= 10  # Default damage for bad blocks
                
                if "heal" in props:
                    health = min(100, health + props["heal"])
                
                # Create particles based on block type
                create_particles(block["x"] + block_size/2, block["y"] + block_size/2, props["color"], 15)
                
                # Play sound
                if has_sound:
                    try:
                        if points > 0:
                            catch_sound.play()
                        else:
                            damage_sound.play()
                    except:
                        pass
            
            blocks.remove(block)
        
        # Remove blocks that fall off the screen
        elif block["y"] > HEIGHT:
            blocks.remove(block)
    
    # Move power-ups and check for collisions
    for power_up in power_ups[:]:
        power_up["y"] += power_up["speed"]
        
        # Check if power-up is caught by basket
        if (basket_y < power_up["y"] + block_size and
            basket_y + basket_height > power_up["y"] and
            basket_x < power_up["x"] + block_size and
            basket_x + basket_width > power_up["x"]):
            
            apply_power_up(power_up["type"])
            create_particles(power_up["x"] + block_size/2, power_up["y"] + block_size/2, 
                            POWERUP_TYPES[power_up["type"]]["color"], 20)
            power_ups.remove(power_up)
        
        # Remove power-ups that fall off the screen
        elif power_up["y"] > HEIGHT:
            power_ups.remove(power_up)
    
    # Update power-ups
    update_power_ups()
    
    # Check for level up
    check_level_up()
    
    # Update particles
    update_particles()
    
    # Check for game over
    if health <= 0:
        game_over = True
        high_score = max(high_score, score)
    
    # Draw everything
    draw_background()
    
    # Draw particles
    draw_particles(screen)
    
    # Draw blocks
    for block in blocks:
        draw_block(block["x"], block["y"], block["type"])
    
    # Draw power-ups
    for power_up in power_ups:
        draw_power_up(power_up["x"], power_up["y"], power_up["type"])
    
    # Draw basket
    draw_basket()
    
    # Draw UI
    draw_ui()
    
    pygame.display.flip()
    clock.tick(60)

# Game over screen
while game_over:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                # Restart game by resetting variables
                blocks = []
                power_ups = []
                score = 0
                health = 100
                level = 1
                block_speed = 3
                block_spawn_rate = 30
                active_power_ups = {key: 0 for key in POWERUP_TYPES.keys()}
                particles = []
                game_over = False
            elif event.key == pygame.K_q:
                pygame.quit()
                sys.exit()
    
    draw_game_over()
    pygame.display.flip()
    clock.tick(60)

# Continue the game loop if restarted
if not game_over:
    # Reset the main game loop (this would need to be restructured for a proper game loop)
    pass

pygame.quit()
sys.exit()