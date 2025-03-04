import pygame
import cv2
import numpy as np
from random import randint, uniform
import mediapipe as mp
import math
import time
import os

# -------------------------
# Initialization
# -------------------------
cam = cv2.VideoCapture(0)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=4,  # Up to 4 hands can be detected.
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

pygame.init()
pygame.mixer.init()  # Initialize sound mixer

clock = pygame.time.Clock()

myfont = pygame.font.SysFont("monospace", 24)
title_font = pygame.font.SysFont("monospace", 48, bold=True)
intro_font = pygame.font.SysFont("monospace", 28)
mode_font = pygame.font.SysFont("monospace", 36, bold=True)

win_width, win_height = 1280, 720
win = pygame.display.set_mode((win_width, win_height), pygame.FULLSCREEN)

# Helper function to load images.
def load_image(path, size):
    try:
        return pygame.transform.scale(pygame.image.load(path), size)
    except Exception as e:
        print(f"Error loading image {path}: {e}")
        return pygame.Surface(size)  # Return a blank surface if error occurs

# Load images.
bg = load_image('images/bg.jpg', (win_width, win_height))
watermelon = [load_image(f'images/watermelon{i}.png', (80, 80)) for i in range(1, 4)]
berry = [load_image(f'images/berry{i}.png', (80, 80)) for i in range(1, 4)]
orange = [load_image(f'images/orange{i}.png', (80, 80)) for i in range(1, 4)]
bomb = load_image('images/bomb.png', (80, 80))

blade_path = 'images/star1.png'
star = load_image(blade_path, (40, 40)) if os.path.exists(blade_path) else pygame.Surface((40, 40)).fill((255, 0, 0))

# Helper function to load sounds.
def load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception as e:
        print(f"Error loading sound {path}: {e}")
        return None

slash_sound = load_sound('sounds/slash.wav')
bomb_sound = load_sound('sounds/bomb.wav')
game_start_sound = load_sound('sounds/game_start.wav')
game_end_sound = load_sound('sounds/game_end.wav')

explosion_img = load_image('images/explosion.png', (80, 80))

# -------------------------
# Mode Selection Assets & Positions
# -------------------------
# Arrange the three modes horizontally and place "Quit Game" right below Dual Mode.
# Each icon is 80x80.
# Increase the horizontal gap further (e.g., 120 pixels) to avoid overlapping text labels for "Dual Mode" and "Multi-Player Mode".
icon_width, icon_height = 80, 80
horizontal_gap = 120  # Increased gap to ensure the mode text labels don't overlap

group_width = 3 * icon_width + 2 * horizontal_gap
start_x = (win_width - group_width) // 2
base_y = win_height // 2 - icon_height // 2

# Horizontal mode positions.
classic_fruit_pos = (start_x, base_y)                        # Classic Mode on the left.
dual_fruit_pos = (start_x + icon_width + horizontal_gap, base_y)  # Dual Mode in the center.
multi_fruit_pos = (start_x + 2 * (icon_width + horizontal_gap), base_y)  # Multi-Player Mode on the right.

# "Quit Game" positioned just below Dual Mode.
quit_game_pos = (dual_fruit_pos[0], base_y + icon_height + 20)

# Load images for mode selection.
classic_fruit = load_image('images/berry1.png', (icon_width, icon_height))
duel_fruit = load_image('images/orange1.png', (icon_width, icon_height))
multi_fruit = load_image('images/watermelon1.png', (icon_width, icon_height))
quit_game_image = load_image('images/bomb.png', (icon_width, icon_height))

# -------------------------
# Class Definitions
# -------------------------
class Img:
    def __init__(self, x, y, pic, u=12, g=0.4, is_bomb=False):
        self.x = x
        self.y = y
        self.pic = pic
        self.u = u                # initial upward velocity
        self.vx = uniform(-2, 2)  # horizontal velocity
        self.g = g                # gravitational constant
        self.is_bomb = is_bomb
        self.explosion_start_time = None

    def show(self, win, angle):
        rotated_pic = pygame.transform.rotate(self.pic, angle)
        win.blit(rotated_pic, (self.x, self.y))

    def update(self):
        self.x += self.vx
        self.y -= self.u
        self.u -= self.g
        if selected_mode != "duel":
            if self.x < 0:
                self.x = 0
                self.vx = -self.vx
            elif self.x + self.pic.get_width() > win_width:
                self.x = win_width - self.pic.get_width()
                self.vx = -self.vx

    def show_explosion(self, win):
        if self.explosion_start_time is None:
            self.explosion_start_time = time.time()
        win.blit(explosion_img, (self.x, self.y))

    def explosion_finished(self):
        return self.explosion_start_time is not None and (time.time() - self.explosion_start_time) > 2

# -------------------------
# Global Variables
# -------------------------
hand_positions = []           
prev_hand_positions = []      
run = True
angle = 0

score_p1, lives_p1 = 0, 5
score_p2, lives_p2 = 0, 5

score_mp, lives_mp = 0, 5
score_classic, lives_classic = 0, 5

game_started, game_over, game_end_sound_played = False, False, False
mode_selected = False
selected_mode = None

timer_start = 0
game_time = 90

go_again_fruit = orange[0]
go_again_pos = [win_width // 2 - 120, win_height // 2 + 60]
quit_game_fruit = berry[0]
quit_game_over_pos = [win_width // 2 + 40, win_height // 2 + 60]

a_dual, a_multi, a_classic = [], [], []
sliced_fruits = []
slashes, explosions = [], []

spawn_timer_dual = 0
spawn_timer_multi = 0
spawn_timer_classic = 0

# -------------------------
# Utility Functions
# -------------------------
def reset_game():
    global a_dual, a_multi, a_classic, sliced_fruits
    global score_p1, score_p2, lives_p1, lives_p2
    global score_mp, lives_mp, score_classic, lives_classic
    global game_started, game_over, game_end_sound_played, timer_start
    a_dual, a_multi, a_classic, sliced_fruits = [], [], [], []
    if selected_mode == "duel":
        score_p1, score_p2, lives_p1, lives_p2 = 0, 0, 5, 5
    elif selected_mode == "multi-player":
        score_mp, lives_mp = 0, 5
    elif selected_mode == "classic":
        score_classic, lives_classic = 0, 5
    game_started, game_over, game_end_sound_played = True, False, False
    timer_start = time.time()

def is_slashing(prev_pos, curr_pos):
    dx = curr_pos[0] - prev_pos[0]
    dy = curr_pos[1] - prev_pos[1]
    return (dx * dx + dy * dy) > (40 * 40)

def create_slashing_effect(x, y):
    slashes.append([(x, y), (x + 20, y + 20), 5])

def spawn_sliced_fruits(fruit_obj):
    if fruit_obj.pic == watermelon[0]:
        left_img = Img(fruit_obj.x - 10, fruit_obj.y, watermelon[1], u=fruit_obj.u, g=fruit_obj.g)
        right_img = Img(fruit_obj.x + 10, fruit_obj.y, watermelon[2], u=fruit_obj.u, g=fruit_obj.g)
    elif fruit_obj.pic == berry[0]:
        left_img = Img(fruit_obj.x - 10, fruit_obj.y, berry[1], u=fruit_obj.u, g=fruit_obj.g)
        right_img = Img(fruit_obj.x + 10, fruit_obj.y, berry[2], u=fruit_obj.u, g=fruit_obj.g)
    elif fruit_obj.pic == orange[0]:
        left_img = Img(fruit_obj.x - 10, fruit_obj.y, orange[1], u=fruit_obj.u, g=fruit_obj.g)
        right_img = Img(fruit_obj.x + 10, fruit_obj.y, orange[2], u=fruit_obj.u, g=fruit_obj.g)
    else:
        return
    sliced_fruits.append((left_img, time.time()))
    sliced_fruits.append((right_img, time.time()))

def check_mode_selection(hand_positions):
    global selected_mode, mode_selected
    for hx, hy in hand_positions:
        # Check Classic Mode option.
        if pygame.Rect(classic_fruit_pos, (icon_width, icon_height)).collidepoint(hx, hy):
            selected_mode = "classic"
            mode_selected = True
        # Check Dual Mode option.
        elif pygame.Rect(dual_fruit_pos, (icon_width, icon_height)).collidepoint(hx, hy):
            selected_mode = "duel"
            mode_selected = True
        # Check Multi-Player Mode option.
        elif pygame.Rect(multi_fruit_pos, (icon_width, icon_height)).collidepoint(hx, hy):
            selected_mode = "multi-player"
            mode_selected = True
        # Check Quit Game option.
        elif pygame.Rect(quit_game_pos, (icon_width, icon_height)).collidepoint(hx, hy):
            pygame.quit()
            os._exit(0)

# -------------------------
# Main Loop
# -------------------------
while run:
    ret, frame = cam.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    prev_hand_positions = hand_positions.copy()
    hand_positions.clear()

    if results.multi_hand_landmarks:
        # In classic mode, track only the first hand.
        if selected_mode == "classic":
            hand_landmarks_list = [results.multi_hand_landmarks[0]]
        else:
            hand_landmarks_list = results.multi_hand_landmarks
        for hand_landmarks in hand_landmarks_list:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            h, w, _ = frame.shape
            fx, fy = int(index_tip.x * win_width), int(index_tip.y * win_height)
            hand_positions.append((fx, fy))
            win.blit(star, (fx - star.get_width() // 2, fy - star.get_height() // 2))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.rot90(frame)
    frame = np.flipud(frame)
    frame = pygame.surfarray.make_surface(frame)
    frame = pygame.transform.scale(frame, (win_width, win_height))
    win.blit(frame, (0, 0))

    if not mode_selected:
        # Draw title and introduction text.
        title_text = title_font.render("AR FRUITNINJA", True, (0, 0, 0))
        intro_text1 = intro_font.render("Welcome to AR Fruit Ninja!", True, (255, 255, 255))
        intro_text2 = intro_font.render("Use your hand to slice fruits in mid-air while avoiding bombs.", True, (255, 255, 255))
        intro_text3 = intro_font.render("Slice a fruit to select a mode!", True, (255, 255, 255))
        
        win.blit(title_text, (win_width // 2 - title_text.get_width() // 2, win_height // 2 - 300))
        win.blit(intro_text1, (win_width // 2 - intro_text1.get_width() // 2, win_height // 2 - 250))
        win.blit(intro_text2, (win_width // 2 - intro_text2.get_width() // 2, win_height // 2 - 210))
        win.blit(intro_text3, (win_width // 2 - intro_text3.get_width() // 2, win_height // 2 - 170))
        
        # Define an extra vertical gap between each icon and its label text.
        label_gap = 10
        
        # Classic Mode.
        win.blit(classic_fruit, classic_fruit_pos)
        classic_label = myfont.render("Classic Mode", True, (255, 255, 255))
        win.blit(classic_label, (classic_fruit_pos[0] + (icon_width - classic_label.get_width()) // 2,
                                 classic_fruit_pos[1] + icon_height + label_gap))
        
        # Dual Mode.
        win.blit(duel_fruit, dual_fruit_pos)
        duel_label = myfont.render("Dual Mode", True, (255, 255, 255))
        win.blit(duel_label, (dual_fruit_pos[0] + (icon_width - duel_label.get_width()) // 2,
                              dual_fruit_pos[1] + icon_height + label_gap))
        
        # Multi-Player Mode.
        win.blit(multi_fruit, multi_fruit_pos)
        multi_label = myfont.render("Multi-Player Mode", True, (255, 255, 255))
        win.blit(multi_label, (multi_fruit_pos[0] + (icon_width - multi_label.get_width()) // 2,
                               multi_fruit_pos[1] + icon_height + label_gap))
        
        # Quit Game placed right below Dual Mode.
        win.blit(quit_game_image, quit_game_pos)
        quit_label = myfont.render("Quit Game", True, (255, 255, 255))
        win.blit(quit_label, (quit_game_pos[0] + (icon_width - quit_label.get_width()) // 2,
                              quit_game_pos[1] + icon_height + label_gap))
        
        check_mode_selection(hand_positions)
        
    elif game_over:
        if not game_end_sound_played:
            if game_end_sound:
                game_end_sound.play()
            game_end_sound_played = True
        game_over_text = myfont.render("Game Over!", True, (255, 0, 0))
        win.blit(game_over_text, (win_width // 2 - 50, win_height // 2 - 100))
        
        if selected_mode == "duel":
            winner_text = myfont.render("Player 1 Wins!" if score_p1 > score_p2 
                                         else "Player 2 Wins!" if score_p2 > score_p1 
                                         else "It's a Tie!", True, (255, 255, 255))
            win.blit(winner_text, (win_width // 2 - winner_text.get_width() // 2, win_height // 2 - 70))
            final_score_text = myfont.render(f"P1: {score_p1}  P2: {score_p2}", True, (255, 255, 255))
        elif selected_mode == "multi-player":
            final_score_text = myfont.render("Score: " + str(score_mp), True, (255, 255, 255))
        else:
            final_score_text = myfont.render("Score: " + str(score_classic), True, (255, 255, 255))
        win.blit(final_score_text, (win_width // 2 - final_score_text.get_width() // 2, win_height // 2 - 40))
        
        win.blit(go_again_fruit, go_again_pos)
        go_again_text = myfont.render("Go Again?", True, (255, 255, 255))
        win.blit(go_again_text, (go_again_pos[0] - 20, go_again_pos[1] + 60))
        
        win.blit(quit_game_fruit, quit_game_over_pos)
        quit_game_text = myfont.render("Quit Game", True, (255, 255, 255))
        win.blit(quit_game_text, (quit_game_over_pos[0] - 20, quit_game_over_pos[1] + 60))
        
        if any(pygame.Rect(go_again_pos, (icon_width, icon_height)).collidepoint(hx, hy) for hx, hy in hand_positions):
            mode_selected = False
            reset_game()
        if any(pygame.Rect(quit_game_over_pos, (icon_width, icon_height)).collidepoint(hx, hy) for hx, hy in hand_positions):
            run = False
    else:
        if selected_mode == "duel":
            pygame.draw.line(win, (255, 255, 255), (win_width // 2, 0), (win_width // 2, win_height), 4)
            if not game_started:
                reset_game()
                timer_start = time.time()
                game_started = True
                if game_start_sound:
                    game_start_sound.play()
            elapsed = int(time.time() - timer_start)
            remaining = game_time - elapsed
            timer_text = myfont.render(f"Time: {remaining}s", True, (255, 255, 255))
            win.blit(timer_text, (win_width // 2 - timer_text.get_width() // 2, 10))
            if remaining <= 0:
                game_over = True

            score_text_p1 = myfont.render(f"P1 Score: {score_p1}", True, (255, 255, 255))
            lives_text_p1 = myfont.render(f"P1 Lives: {lives_p1}", True, (255, 0, 0))
            win.blit(score_text_p1, (20, 10))
            win.blit(lives_text_p1, (20, 40))

            score_text_p2 = myfont.render(f"P2 Score: {score_p2}", True, (255, 255, 255))
            lives_text_p2 = myfont.render(f"P2 Lives: {lives_p2}", True, (255, 0, 0))
            win.blit(score_text_p2, (win_width - score_text_p2.get_width() - 20, 10))
            win.blit(lives_text_p2, (win_width - lives_text_p2.get_width() - 20, 40))

            spawn_timer_dual += 1
            if spawn_timer_dual > 60:
                spawn_timer_dual = 0
                num = randint(1, 3)
                is_bomb = (randint(0, 3) == 0)
                if not is_bomb:
                    fruit = [watermelon[0], berry[0], orange[0]][randint(0, 2)]
                else:
                    fruit = bomb
                for _ in range(num):
                    pos_p1 = randint(50, win_width // 2 - 80)
                    pos_p2 = randint(win_width // 2 + 50, win_width - 80)
                    a_dual.append((Img(pos_p1, win_height, fruit, u=randint(15, 25), is_bomb=is_bomb), "P1"))
                    a_dual.append((Img(pos_p2, win_height, fruit, u=randint(15, 25), is_bomb=is_bomb), "P2"))

            remove_list = []
            for fruit_obj, player in a_dual:
                fruit_obj.update()
                width = fruit_obj.pic.get_width()
                if player == "P1":
                    if fruit_obj.x < 50:
                        fruit_obj.vx = abs(fruit_obj.vx)
                    if fruit_obj.x + width > win_width // 2 - 10:
                        fruit_obj.vx = -abs(fruit_obj.vx)
                else:
                    if fruit_obj.x < win_width // 2 + 10:
                        fruit_obj.vx = abs(fruit_obj.vx)
                    if fruit_obj.x + width > win_width - 50:
                        fruit_obj.vx = -abs(fruit_obj.vx)
                fruit_obj.show(win, angle)
                fruit_rect = pygame.Rect(fruit_obj.x, fruit_obj.y, width, fruit_obj.pic.get_height())
                for prev_pos, curr_pos in zip(prev_hand_positions, hand_positions):
                    if is_slashing(prev_pos, curr_pos) and fruit_rect.colliderect(pygame.Rect(curr_pos[0], curr_pos[1], 40, 40)):
                        if slash_sound:
                            slash_sound.play()
                        create_slashing_effect(curr_pos[0], curr_pos[1])
                        if fruit_obj.is_bomb:
                            if bomb_sound:
                                bomb_sound.play()
                            explosions.append(fruit_obj)
                            if player == "P1":
                                lives_p1 -= 1
                            else:
                                lives_p2 -= 1
                            if lives_p1 <= 0 or lives_p2 <= 0:
                                game_over = True
                                a_dual.clear()
                                break
                            remove_list.append((fruit_obj, player))
                        else:
                            if player == "P1":
                                score_p1 += 1
                            else:
                                score_p2 += 1
                            spawn_sliced_fruits(fruit_obj)
                            remove_list.append((fruit_obj, player))
                if fruit_obj.y >= win_height:
                    if not fruit_obj.is_bomb:
                        if player == "P1":
                            lives_p1 -= 1
                        else:
                            lives_p2 -= 1
                        if lives_p1 <= 0 or lives_p2 <= 0:
                            game_over = True
                            a_dual.clear()
                            break
                    remove_list.append((fruit_obj, player))
            for item in remove_list:
                if item in a_dual:
                    a_dual.remove(item)

        elif selected_mode == "multi-player":
            score_text_mp = myfont.render(f"Score: {score_mp}", True, (255, 255, 255))
            lives_text_mp = myfont.render(f"Lives: {lives_mp}", True, (255, 0, 0))
            win.blit(score_text_mp, (20, 10))
            win.blit(lives_text_mp, (20, 40))
            if not game_started:
                reset_game()
                if game_start_sound:
                    game_start_sound.play()
                game_started = True
            spawn_timer_multi += 1
            if spawn_timer_multi > 30:
                spawn_timer_multi = 0
                num = randint(2, 4)
                for _ in range(num):
                    pos = randint(50, win_width - 80)
                    is_bomb = (randint(0, 3) == 0)
                    if is_bomb:
                        a_multi.append(Img(pos, win_height, bomb, u=randint(15, 25), is_bomb=True))
                    else:
                        fruit = [watermelon[0], berry[0], orange[0]][randint(0, 2)]
                        a_multi.append(Img(pos, win_height, fruit, u=randint(15, 25)))
            remove_list = []
            for fruit_obj in a_multi:
                fruit_obj.update()
                fruit_obj.show(win, angle)
                fruit_rect = pygame.Rect(fruit_obj.x, fruit_obj.y, fruit_obj.pic.get_width(), fruit_obj.pic.get_height())
                for prev_pos, curr_pos in zip(prev_hand_positions, hand_positions):
                    if is_slashing(prev_pos, curr_pos) and fruit_rect.colliderect(pygame.Rect(curr_pos[0], curr_pos[1], 40, 40)):
                        if slash_sound:
                            slash_sound.play()
                        create_slashing_effect(curr_pos[0], curr_pos[1])
                        if fruit_obj.is_bomb:
                            if bomb_sound:
                                bomb_sound.play()
                            explosions.append(fruit_obj)
                            lives_mp -= 1
                            if lives_mp <= 0:
                                game_over = True
                                a_multi.clear()
                                break
                            remove_list.append(fruit_obj)
                        else:
                            score_mp += 1
                            spawn_sliced_fruits(fruit_obj)
                            remove_list.append(fruit_obj)
                if fruit_obj.y >= win_height:
                    if not fruit_obj.is_bomb:
                        lives_mp -= 1
                        if lives_mp <= 0:
                            game_over = True
                            a_multi.clear()
                            break
                    remove_list.append(fruit_obj)
            for item in remove_list:
                if item in a_multi:
                    a_multi.remove(item)

        elif selected_mode == "classic":
            score_text_classic = myfont.render(f"Score: {score_classic}", True, (255, 255, 255))
            lives_text_classic = myfont.render(f"Lives: {lives_classic}", True, (255, 0, 0))
            win.blit(score_text_classic, (20, 10))
            win.blit(lives_text_classic, (20, 40))
            if not game_started:
                reset_game()
                if game_start_sound:
                    game_start_sound.play()
                game_started = True
            spawn_timer_classic += 1
            if spawn_timer_classic > 60:
                spawn_timer_classic = 0
                num = randint(1, 2)
                for _ in range(num):
                    pos = randint(50, win_width - 80)
                    is_bomb = (randint(0, 3) == 0)
                    if is_bomb:
                        a_classic.append(Img(pos, win_height, bomb, u=randint(15, 25), is_bomb=True))
                    else:
                        fruit = [watermelon[0], berry[0], orange[0]][randint(0, 2)]
                        a_classic.append(Img(pos, win_height, fruit, u=randint(15, 25)))
            remove_list = []
            for fruit_obj in a_classic:
                fruit_obj.update()
                fruit_obj.show(win, angle)
                fruit_rect = pygame.Rect(fruit_obj.x, fruit_obj.y, fruit_obj.pic.get_width(), fruit_obj.pic.get_height())
                for prev_pos, curr_pos in zip(prev_hand_positions, hand_positions):
                    if is_slashing(prev_pos, curr_pos) and fruit_rect.colliderect(pygame.Rect(curr_pos[0], curr_pos[1], 40, 40)):
                        if slash_sound:
                            slash_sound.play()
                        create_slashing_effect(curr_pos[0], curr_pos[1])
                        if fruit_obj.is_bomb:
                            if bomb_sound:
                                bomb_sound.play()
                            explosions.append(fruit_obj)
                            lives_classic -= 1
                            if lives_classic <= 0:
                                game_over = True
                                a_classic.clear()
                                break
                            remove_list.append(fruit_obj)
                        else:
                            score_classic += 1
                            spawn_sliced_fruits(fruit_obj)
                            remove_list.append(fruit_obj)
                if fruit_obj.y >= win_height:
                    if not fruit_obj.is_bomb:
                        lives_classic -= 1
                        if lives_classic <= 0:
                            game_over = True
                            a_classic.clear()
                            break
                    remove_list.append(fruit_obj)
            for item in remove_list:
                if item in a_classic:
                    a_classic.remove(item)

        # Display sliced fruits.
        for sliced_obj, spawn_time in sliced_fruits:
            if time.time() - spawn_time > 2:
                continue
            sliced_obj.update()
            sliced_obj.show(win, angle)
        sliced_fruits = [(obj, t) for (obj, t) in sliced_fruits if time.time() - t <= 2]

        # Display explosions.
        for explosion in explosions:
            explosion.show_explosion(win)
        explosions = [e for e in explosions if not e.explosion_finished()]

        # Display slashing effects.
        for s in slashes:
            pygame.draw.line(win, (255, 0, 0), s[0], s[1], s[2])
        slashes.clear()

    angle = (angle + 1) % 360
    pygame.display.update()
    clock.tick(30)

cam.release()
pygame.quit()
