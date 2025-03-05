import pyxel
import pygame
import math
import random

# ================================
# Intégration du contrôleur via pygame
# ================================

pygame.init()
pygame.joystick.init()

# Initialisation du premier joystick (si connecté)
if pygame.joystick.get_count() > 0:
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print("Joystick connecté:", joystick.get_name())
    print("Nombre de boutons:", joystick.get_numbuttons())
else:
    joystick = None

# --- Mapping des boutons ---
# Modifiez ces constantes si vos indices diffèrent.
BUTTON_A = 0    # Bouton A pour passer
BUTTON_B = 1    # Bouton B pour tirer
BUTTON_LB = 4   # Bouton LB pour changer de joueur

# Dictionnaires pour stocker l'état actuel et précédent du contrôleur pour l'équipe A.
CONTROLLER_STATE = {}
PREV_CONTROLLER_STATE = {}

def update_controller():
    """
    Met à jour l'état des touches virtuelles à partir du joystick pygame.
    Mapping :
      - Stick gauche horizontal : KEY_Q (gauche) et KEY_D (droite)
      - Stick gauche vertical   : KEY_Z (haut) et KEY_S (bas)
      - Bouton A (index BUTTON_A)        : KEY_A pour passer
      - Bouton B (index BUTTON_B)        : KEY_E pour tirer
      - Bouton LB (index BUTTON_LB)      : KEY_R pour changer de joueur
    """
    if not joystick:
        return

    pygame.event.pump()  # Actualise les événements de pygame

    deadzone = 0.2  # Seuil pour ignorer les petites variations

    # Mise à jour des axes
    axis_x = joystick.get_axis(0)
    axis_y = joystick.get_axis(1)
    CONTROLLER_STATE[pyxel.KEY_Q] = (axis_x < -deadzone)
    CONTROLLER_STATE[pyxel.KEY_D] = (axis_x > deadzone)
    CONTROLLER_STATE[pyxel.KEY_Z] = (axis_y < -deadzone)
    CONTROLLER_STATE[pyxel.KEY_S] = (axis_y > deadzone)

    # Mise à jour des boutons
    CONTROLLER_STATE[pyxel.KEY_A] = (joystick.get_button(BUTTON_A) > 0)
    CONTROLLER_STATE[pyxel.KEY_E] = (joystick.get_button(BUTTON_B) > 0)
    CONTROLLER_STATE[pyxel.KEY_R] = (joystick.get_button(BUTTON_LB) > 0)

def update_prev_controller_state():
    """Sauvegarde l'état précédent pour la détection d'un front montant (btnp)."""
    for key in [pyxel.KEY_Z, pyxel.KEY_S, pyxel.KEY_Q, pyxel.KEY_D,
                pyxel.KEY_A, pyxel.KEY_E, pyxel.KEY_R]:
        PREV_CONTROLLER_STATE[key] = CONTROLLER_STATE.get(key, False)

# --- Patch des fonctions d'entrée de Pyxel ---
_original_pyxel_btn = pyxel.btn
_original_pyxel_btnp = pyxel.btnp

def patched_btn(key):
    """Retourne True si la touche est activée par le clavier ou par le contrôleur."""
    return _original_pyxel_btn(key) or CONTROLLER_STATE.get(key, False)

def patched_btnp(key, hold=0, period=1):
    """
    Retourne True si la touche vient d'être pressée (front montant)
    soit via le clavier, soit par le contrôleur.
    """
    current = CONTROLLER_STATE.get(key, False)
    prev = PREV_CONTROLLER_STATE.get(key, False)
    return _original_pyxel_btnp(key, hold, period) or (current and not prev)

pyxel.btn = patched_btn
pyxel.btnp = patched_btnp

# Pour mettre à jour l'état précédent à chaque frame, on patche pyxel.run
_original_pyxel_run = pyxel.run
def patched_run(update, draw):
    def patched_update():
        update_controller()
        update_prev_controller_state()
        update()
    _original_pyxel_run(patched_update, draw)
pyxel.run = patched_run

# ================================
# Code du jeu (inchangé)
# ================================

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192

BALL_SPEED = 3.0       
PLAYER_SPEED = 2.0     
FRICTION = 0.98        

BALL_RADIUS = 3
PLAYER_RADIUS = 4

TEAM_A_COLOR = 8      
TEAM_B_COLOR = 12      
FIELD_COLOR = 11
BACKGROUND_COLOR = 3   
GOAL_COLOR = 7  

FIELD_MARGIN = 5

GOAL_WIDTH = 12
GOAL_HEIGHT = 40

# Les touches de l'équipe A (contrôlées par la manette et/ou le clavier)
TEAM_A_KEYS = {
    'up': pyxel.KEY_Z,
    'down': pyxel.KEY_S,
    'left': pyxel.KEY_Q,
    'right': pyxel.KEY_D,
    'pass': pyxel.KEY_A,    # Bouton A pour passer
    'shoot': pyxel.KEY_E,   # Bouton B pour tirer
    'select': pyxel.KEY_R   # Bouton LB pour changer de joueur
}

# L'équipe B joue au clavier
TEAM_B_KEYS = {
    'up': pyxel.KEY_UP,
    'down': pyxel.KEY_DOWN,
    'left': pyxel.KEY_LEFT,
    'right': pyxel.KEY_RIGHT,
    'pass': pyxel.KEY_K,
    'shoot': pyxel.KEY_L,
    'select': pyxel.KEY_O
}

class Ball:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.vx = 0
        self.vy = 0
        self.radius = BALL_RADIUS
        self.in_pass = False
        self.pass_receiver = None
        self.cooldown = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= FRICTION
        self.vy *= FRICTION
        if self.cooldown > 0:
            self.cooldown -= 1
        if abs(self.vx) < 0.1 and abs(self.vy) < 0.1:
            self.vx = 0
            self.vy = 0
            self.in_pass = False
            self.pass_receiver = None
        goal_top = (SCREEN_HEIGHT - GOAL_HEIGHT) // 2
        goal_bottom = goal_top + GOAL_HEIGHT
        if self.x - self.radius < 0:
            if goal_top <= self.y <= goal_bottom:
                Game.instance.score['B'] += 1
                Game.instance.reset_positions()
                return
            else:
                self.vx = abs(self.vx) * 0.7
                self.x = self.radius
        if self.x + self.radius > SCREEN_WIDTH:
            if goal_top <= self.y <= goal_bottom:
                Game.instance.score['A'] += 1
                Game.instance.reset_positions()
                return
            else:
                self.vx = -abs(self.vx) * 0.7
                self.x = SCREEN_WIDTH - self.radius
        if self.y - self.radius < FIELD_MARGIN:
            self.vy = abs(self.vy) * 0.7
            self.y = self.radius + FIELD_MARGIN
        if self.y + self.radius > SCREEN_HEIGHT - FIELD_MARGIN:
            self.vy = -abs(self.vy) * 0.7
            self.y = SCREEN_HEIGHT - self.radius - FIELD_MARGIN

    def draw(self):
        pyxel.circ(self.x, self.y, self.radius, pyxel.COLOR_WHITE)

class Player:
    def __init__(self, x, y, team, keys=None, is_keeper=False, controlled=False):
        self.x = x
        self.y = y
        self.team = team              # 'A' ou 'B'
        self.keys = keys              # Mapping clavier ou None pour l'IA
        self.is_keeper = is_keeper    # Gardien si True, sinon joueur de champ
        self.controlled = controlled  # Contrôlé par l'humain si True
        self.radius = PLAYER_RADIUS
        self.has_ball = False
        self.facing = (0, 0)
        self.default_x = x
        self.default_y = y

    def update(self, ball, teammates, opponents):
        self.check_ball_collision(ball)
        if self.controlled and self.keys is not None:
            self.handle_input(ball)
        else:
            self.ai_behavior(ball, teammates, opponents)
        self.x = max(FIELD_MARGIN + self.radius, min(self.x, SCREEN_WIDTH - FIELD_MARGIN - self.radius))
        self.y = max(FIELD_MARGIN + self.radius, min(self.y, SCREEN_HEIGHT - FIELD_MARGIN - self.radius))
        if self.has_ball:
            ball.x = self.x
            ball.y = self.y
            ball.vx = 0
            ball.vy = 0

    def check_ball_collision(self, ball):
        if ball.cooldown > 0 and ball.pass_receiver != self:
            self.has_ball = False
            return
        distance = math.hypot(self.x - ball.x, self.y - ball.y)
        if distance < self.radius + ball.radius:
            if ball.in_pass and ball.pass_receiver is not None:
                if ball.pass_receiver == self:
                    self.has_ball = True
                    ball.in_pass = False
                    ball.pass_receiver = None
                    ball.vx = 0
                    ball.vy = 0
                elif self.team != ball.pass_receiver.team:
                    self.has_ball = True
                    ball.in_pass = False
                    ball.pass_receiver = None
                    ball.vx = 0
                    ball.vy = 0
                else:
                    self.has_ball = False
            else:
                self.has_ball = True
                ball.vx = 0
                ball.vy = 0
        else:
            self.has_ball = False

    def handle_input(self, ball):
        dx = 0
        dy = 0
        if pyxel.btn(self.keys['left']):
            dx -= PLAYER_SPEED
        if pyxel.btn(self.keys['right']):
            dx += PLAYER_SPEED
        if pyxel.btn(self.keys['up']):
            dy -= PLAYER_SPEED
        if pyxel.btn(self.keys['down']):
            dy += PLAYER_SPEED
        if dx != 0 or dy != 0:
            self.facing = (dx, dy)
        self.x += dx
        self.y += dy
        if self.has_ball:
            if pyxel.btnp(self.keys['pass']):
                self.pass_ball(ball)
            elif pyxel.btnp(self.keys['shoot']):
                self.shoot_ball(ball)

    def pass_ball(self, ball):
        best_mate = None
        best_dist = float('inf')
        for mate in Game.instance.teams[self.team].players:
            if mate is not self:
                d = math.hypot(mate.x - self.x, mate.y - self.y)
                if d < best_dist:
                    best_dist = d
                    best_mate = mate
        if best_mate is not None:
            dx = best_mate.x - self.x
            dy = best_mate.y - self.y
            d = math.hypot(dx, dy)
            if d != 0:
                ball.vx = (dx / d) * BALL_SPEED * 1.2
                ball.vy = (dy / d) * BALL_SPEED * 1.2
            ball.in_pass = True
            ball.pass_receiver = best_mate
            ball.cooldown = 10
            team = Game.instance.teams[self.team]
            for p in team.players:
                p.controlled = False
                p.keys = None
            best_mate.controlled = True
            best_mate.keys = team.keys
            self.has_ball = False

    def shoot_ball(self, ball):
        if self.team == 'A':
            goal_x = SCREEN_WIDTH - FIELD_MARGIN - GOAL_WIDTH // 2
        else:
            goal_x = FIELD_MARGIN + GOAL_WIDTH // 2
        goal_y = SCREEN_HEIGHT // 2
        dx = goal_x - self.x
        dy = goal_y - self.y
        d = math.hypot(dx, dy)
        if d != 0:
            ball.vx = (dx / d) * BALL_SPEED * 1.5
            ball.vy = (dy / d) * BALL_SPEED * 1.5
            ball.in_pass = True
            ball.pass_receiver = None
            ball.cooldown = 10
            self.has_ball = False

    def ai_behavior(self, ball, teammates, opponents):
        if Game.instance.team_has_possession(self.team):
            if self.team == 'A':
                target_x = SCREEN_WIDTH - FIELD_MARGIN - GOAL_WIDTH - 10
            else:
                target_x = FIELD_MARGIN + GOAL_WIDTH + 10
            target_y = self.y
        else:
            target_x = self.default_x
            target_y = self.default_y
        if self.is_keeper:
            if self.team == 'A':
                target_x = FIELD_MARGIN + self.radius + 2
                target_y = SCREEN_HEIGHT // 2
            else:
                target_x = SCREEN_WIDTH - FIELD_MARGIN - self.radius - 2
                target_y = SCREEN_HEIGHT // 2
        angle = math.atan2(target_y - self.y, target_x - self.x)
        self.x += math.cos(angle) * PLAYER_SPEED * 0.6
        self.y += math.sin(angle) * PLAYER_SPEED * 0.6

    def draw(self):
        color = TEAM_A_COLOR if self.team == 'A' else TEAM_B_COLOR
        pyxel.circ(self.x, self.y, self.radius, color)
        if self.controlled:
            pyxel.circb(self.x, self.y, self.radius + 2, pyxel.COLOR_YELLOW)
        if self.has_ball:
            pyxel.circ(self.x, self.y, self.radius - 2, pyxel.COLOR_WHITE)

class Team:
    def __init__(self, team, keys):
        self.team = team
        self.keys = keys
        self.players = []
        self.selected_index = 0

    def add_player(self, player):
        self.players.append(player)

    def cycle_player(self):
        self.selected_index = (self.selected_index + 1) % len(self.players)
        for i, player in enumerate(self.players):
            player.controlled = (i == self.selected_index)
            player.keys = self.keys if player.controlled else None

    def update_selection(self):
        if pyxel.btnp(self.keys['select']):
            self.cycle_player()

    def draw_players(self):
        for player in self.players:
            player.draw()

class Game:
    instance = None
    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Pyxel Football")
        Game.instance = self
        self.ball = Ball()
        self.teams = {}
        self.teams['A'] = Team('A', TEAM_A_KEYS)
        self.teams['B'] = Team('B', TEAM_B_KEYS)
        # Équipe A : contrôlée par la manette et/ou le clavier
        self.teams['A'].add_player(Player(30, 50, 'A', TEAM_A_KEYS, controlled=True))
        self.teams['A'].add_player(Player(50, 70, 'A'))
        self.teams['A'].add_player(Player(30, 100, 'A'))
        self.teams['A'].add_player(Player(50, 130, 'A'))
        # Équipe B : joue au clavier
        self.teams['B'].add_player(Player(220, 50, 'B', TEAM_B_KEYS, controlled=True))
        self.teams['B'].add_player(Player(200, 70, 'B'))
        self.teams['B'].add_player(Player(220, 100, 'B'))
        self.teams['B'].add_player(Player(200, 130, 'B'))
        self.score = {'A': 0, 'B': 0}
        pyxel.run(self.update, self.draw)

    def team_has_possession(self, team):
        for player in self.teams[team].players:
            if player.has_ball:
                return True
        return False

    def update(self):
        self.teams['A'].update_selection()
        self.teams['B'].update_selection()
        for team in self.teams.values():
            for player in team.players:
                teammates = team.players
                opponents = self.teams['B'].players if team.team == 'A' else self.teams['A'].players
                player.update(self.ball, teammates, opponents)
        self.ball.update()
        if self.ball.x - self.ball.radius < 0:
            self.score['B'] += 1
            self.reset_positions()
        elif self.ball.x + self.ball.radius > SCREEN_WIDTH:
            self.score['A'] += 1
            self.reset_positions()

    def reset_positions(self):
        self.ball.reset()
        for team in self.teams.values():
            for player in team.players:
                player.x = player.default_x
                player.y = player.default_y

    def draw_field(self):
        pyxel.cls(BACKGROUND_COLOR)
        pyxel.rect(FIELD_MARGIN, FIELD_MARGIN, SCREEN_WIDTH - 2 * FIELD_MARGIN, SCREEN_HEIGHT - 2 * FIELD_MARGIN, FIELD_COLOR)
        pyxel.rectb(FIELD_MARGIN, FIELD_MARGIN, SCREEN_WIDTH - 2 * FIELD_MARGIN, SCREEN_HEIGHT - 2 * FIELD_MARGIN, pyxel.COLOR_WHITE)
        goal_top = (SCREEN_HEIGHT - GOAL_HEIGHT) // 2
        pyxel.rect(0, goal_top, GOAL_WIDTH, GOAL_HEIGHT, GOAL_COLOR)
        pyxel.rectb(0, goal_top, GOAL_WIDTH, GOAL_HEIGHT, pyxel.COLOR_BLACK)
        pyxel.rect(SCREEN_WIDTH - GOAL_WIDTH, goal_top, GOAL_WIDTH, GOAL_HEIGHT, GOAL_COLOR)
        pyxel.rectb(SCREEN_WIDTH - GOAL_WIDTH, goal_top, GOAL_WIDTH, GOAL_HEIGHT, pyxel.COLOR_BLACK)
        pyxel.line(SCREEN_WIDTH // 2, FIELD_MARGIN, SCREEN_WIDTH // 2, SCREEN_HEIGHT - FIELD_MARGIN, pyxel.COLOR_WHITE)

    def draw(self):
        self.draw_field()
        self.ball.draw()
        self.teams['A'].draw_players()
        self.teams['B'].draw_players()
        score_text = f"Team A: {self.score['A']}   Team B: {self.score['B']}"
        pyxel.text(SCREEN_WIDTH // 2 - 40, 10, score_text, pyxel.COLOR_YELLOW)

def main():
    Game()

if __name__ == "__main__":
    main()
