import pyxel
import random
import math

# =============================================================================
# CONSTANTES ET CONFIGURATION
# =============================================================================
SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192

# Vitesse et physique
BALL_SPEED = 3.0       # Vitesse de base de la balle
PLAYER_SPEED = 2.0     # Vitesse de déplacement des joueurs
FRICTION = 0.98        # Coefficient de friction appliqué à la balle

# Rayons pour les collisions
BALL_RADIUS = 4
PLAYER_RADIUS = 5

# Couleurs (indices de 0 à 15 dans Pyxel)
TEAM_A_COLOR = 8       # Rouge pour l'équipe A
TEAM_B_COLOR = 12      # Bleu pour l'équipe B
FIELD_COLOR = 11       # Vert (couleur du terrain)
BACKGROUND_COLOR = 3   # Fond du terrain (couleur sombre)
GOAL_COLOR = 7         # Blanc (pour l'affichage des buts)

# Marges du terrain
FIELD_MARGIN = 5

# Dimensions des buts (pour un affichage plus visible)
GOAL_WIDTH = 12
GOAL_HEIGHT = 40

# Touches de contrôle pour chaque équipe
TEAM_A_KEYS = {
    'up': pyxel.KEY_W,
    'down': pyxel.KEY_S,
    'left': pyxel.KEY_A,
    'right': pyxel.KEY_D,
    'pass': pyxel.KEY_Q,
    'shoot': pyxel.KEY_E,
    'select': pyxel.KEY_R  # Permet de changer le joueur contrôlé
}

TEAM_B_KEYS = {
    'up': pyxel.KEY_UP,
    'down': pyxel.KEY_DOWN,
    'left': pyxel.KEY_LEFT,
    'right': pyxel.KEY_RIGHT,
    'pass': pyxel.KEY_K,
    'shoot': pyxel.KEY_L,
    'select': pyxel.KEY_O  # Permet de changer le joueur contrôlé
}

# =============================================================================
# CLASSE BALL
# =============================================================================
class Ball:
    def __init__(self):
        self.reset()

    def reset(self):
        """Réinitialise la balle au centre du terrain avec une vélocité nulle."""
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.vx = 0
        self.vy = 0
        self.radius = BALL_RADIUS

    def update(self):
        """Met à jour la position de la balle en tenant compte de sa vélocité et de la friction."""
        self.x += self.vx
        self.y += self.vy

        # Application de la friction pour ralentir la balle
        self.vx *= FRICTION
        self.vy *= FRICTION

        # Gestion des rebonds sur les bords du terrain (hors zone de but)
        if self.x - self.radius < FIELD_MARGIN or self.x + self.radius > SCREEN_WIDTH - FIELD_MARGIN:
            self.vx *= -0.7
            self.x = max(self.radius + FIELD_MARGIN, min(self.x, SCREEN_WIDTH - self.radius - FIELD_MARGIN))
        if self.y - self.radius < FIELD_MARGIN or self.y + self.radius > SCREEN_HEIGHT - FIELD_MARGIN:
            self.vy *= -0.7
            self.y = max(self.radius + FIELD_MARGIN, min(self.y, SCREEN_HEIGHT - self.radius - FIELD_MARGIN))

    def draw(self):
        """Dessine la balle."""
        pyxel.circ(self.x, self.y, self.radius, pyxel.COLOR_WHITE)

# =============================================================================
# CLASSE PLAYER
# =============================================================================
class Player:
    def __init__(self, x, y, team, keys=None, is_keeper=False, controlled=False):
        self.x = x
        self.y = y
        self.team = team                  # 'A' ou 'B'
        self.keys = keys                  # Mapping clavier (None pour l'IA)
        self.is_keeper = is_keeper        # Gardien si True, joueur de champ sinon
        self.controlled = controlled      # True si le joueur est contrôlé par l'humain
        self.radius = PLAYER_RADIUS
        self.has_ball = False
        self.facing = (0, 0)              # Dernière direction de déplacement (utile pour la passe)
        # Position par défaut pour le retour en défense
        self.default_x = x
        self.default_y = y

    def update(self, ball, teammates, opponents):
        """Met à jour le joueur : collision avec la balle, déplacement (input ou IA) et contrainte de terrain."""
        self.check_ball_collision(ball)

        # Si contrôlé par l'humain, traiter les commandes clavier
        if self.controlled and self.keys is not None:
            self.handle_input(ball)
        else:
            self.ai_behavior(ball, teammates, opponents)

        # Empêcher le joueur de sortir du terrain
        self.x = max(FIELD_MARGIN + self.radius, min(self.x, SCREEN_WIDTH - FIELD_MARGIN - self.radius))
        self.y = max(FIELD_MARGIN + self.radius, min(self.y, SCREEN_HEIGHT - FIELD_MARGIN - self.radius))

    def check_ball_collision(self, ball):
        """Vérifie si le joueur entre en collision avec la balle et lui confère la possession."""
        distance = math.hypot(self.x - ball.x, self.y - ball.y)
        if distance < self.radius + ball.radius:
            self.has_ball = True
            # La balle suit le joueur qui la contrôle
            ball.x = self.x
            ball.y = self.y
        else:
            self.has_ball = False

    def handle_input(self, ball):
        """Gère le déplacement et les actions du joueur contrôlé."""
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

        # Conserver la dernière direction utilisée (pour la passe si aucune touche n'est pressée)
        if dx != 0 or dy != 0:
            self.facing = (dx, dy)
        self.x += dx
        self.y += dy

        # Actions si le joueur possède la balle
        if self.has_ball:
            if pyxel.btnp(self.keys['pass']):
                self.pass_ball(ball)
            elif pyxel.btnp(self.keys['shoot']):
                self.shoot_ball(ball)

    def pass_ball(self, ball):
        """
        Effectue une passe :
         - Recherche le coéquipier le plus proche.
         - Affecte une vélocité à la balle dans sa direction.
         - Transfère le contrôle au receveur.
        """
        best_mate = None
        best_dist = float('inf')
        # Accès à l'instance du jeu via Game.instance
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
            # Transfert de contrôle : le receveur devient le joueur contrôlé
            team = Game.instance.teams[self.team]
            for p in team.players:
                p.controlled = False
                p.keys = None
            best_mate.controlled = True
            best_mate.keys = team.keys

    def shoot_ball(self, ball):
        """
        Effectue un tir :
         - Calcule la direction vers le but adverse.
         - Affecte une vélocité à la balle dans cette direction.
        """
        if self.team == 'A':
            goal_x = SCREEN_WIDTH - FIELD_MARGIN - GOAL_WIDTH // 2
        else:
            goal_x = FIELD_MARGIN + GOAL_WIDTH // 2
        goal_y = SCREEN_HEIGHT // 2  # Cibler le milieu du but
        dx = goal_x - self.x
        dy = goal_y - self.y
        d = math.hypot(dx, dy)
        if d != 0:
            ball.vx = (dx / d) * BALL_SPEED * 1.5
            ball.vy = (dy / d) * BALL_SPEED * 1.5

    def ai_behavior(self, ball, teammates, opponents):
        """
        Comportement de base de l'IA :
         - En attaque (si l'équipe possède la balle) : se diriger vers le but adverse.
         - En défense (si l'équipe adverse possède la balle) : revenir à sa position par défaut.
         - Le gardien se positionne toujours devant son but.
        """
        # Utilisation de la méthode de Game pour déterminer la possession
        if Game.instance.team_has_possession(self.team):
            # En attaque : se diriger vers le but adverse
            if self.team == 'A':
                target_x = SCREEN_WIDTH - FIELD_MARGIN - GOAL_WIDTH - 10
            else:
                target_x = FIELD_MARGIN + GOAL_WIDTH + 10
            target_y = self.y  # Garder une cohérence verticale
        else:
            # En défense : revenir à sa position initiale
            target_x = self.default_x
            target_y = self.default_y

        # Pour le gardien, toujours se positionner devant le but
        if self.is_keeper:
            if self.team == 'A':
                target_x = FIELD_MARGIN + self.radius + 2
                target_y = SCREEN_HEIGHT // 2
            else:
                target_x = SCREEN_WIDTH - FIELD_MARGIN - self.radius - 2
                target_y = SCREEN_HEIGHT // 2

        # Déplacement progressif vers la cible
        angle = math.atan2(target_y - self.y, target_x - self.x)
        self.x += math.cos(angle) * PLAYER_SPEED * 0.6
        self.y += math.sin(angle) * PLAYER_SPEED * 0.6

    def draw(self):
        """Dessine le joueur et, s'il est contrôlé, un contour pour l'identifier."""
        color = TEAM_A_COLOR if self.team == 'A' else TEAM_B_COLOR
        pyxel.circ(self.x, self.y, self.radius, color)
        # Surligner le joueur contrôlé par un cercle jaune
        if self.controlled:
            pyxel.circb(self.x, self.y, self.radius + 2, pyxel.COLOR_YELLOW)
        # Indiquer la possession de la balle
        if self.has_ball:
            pyxel.circ(self.x, self.y, self.radius - 2, pyxel.COLOR_WHITE)

# =============================================================================
# CLASSE TEAM
# =============================================================================
class Team:
    def __init__(self, team, keys):
        self.team = team                # 'A' ou 'B'
        self.keys = keys                # Mapping clavier pour l'équipe
        self.players = []               # Liste des joueurs de l'équipe
        self.selected_index = 0         # Indice du joueur actuellement contrôlé

    def add_player(self, player):
        """Ajoute un joueur à l'équipe."""
        self.players.append(player)

    def cycle_player(self):
        """Cycle le joueur contrôlé (permet de changer manuellement de joueur)."""
        self.selected_index = (self.selected_index + 1) % len(self.players)
        for i, player in enumerate(self.players):
            player.controlled = (i == self.selected_index)
            player.keys = self.keys if player.controlled else None

    def update_selection(self):
        """
        Vérifie si la touche de sélection est pressée
        et appelle cycle_player pour changer le joueur contrôlé.
        """
        if pyxel.btnp(self.keys['select']):
            self.cycle_player()

    def draw_players(self):
        """Dessine l'ensemble des joueurs de l'équipe."""
        for player in self.players:
            player.draw()

# =============================================================================
# CLASSE GAME
# =============================================================================
class Game:
    # Référence statique à l'instance du jeu pour y accéder depuis d'autres classes
    instance = None

    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Pyxel Football")
        # Stocker l'instance du jeu
        Game.instance = self
        self.ball = Ball()

        # Initialiser les équipes
        self.teams = {}
        self.teams['A'] = Team('A', TEAM_A_KEYS)
        self.teams['B'] = Team('B', TEAM_B_KEYS)

        # Création de l'équipe A : 4 joueurs de champ + 1 gardien
        # Le premier joueur de chaque équipe est contrôlé par défaut
        self.teams['A'].add_player(Player(30, 50, 'A', TEAM_A_KEYS, controlled=True))
        self.teams['A'].add_player(Player(50, 70, 'A'))
        self.teams['A'].add_player(Player(30, 100, 'A'))
        self.teams['A'].add_player(Player(50, 130, 'A'))
        self.teams['A'].add_player(Player(10, 90, 'A', is_keeper=True))

        # Création de l'équipe B : 4 joueurs de champ + 1 gardien
        self.teams['B'].add_player(Player(220, 50, 'B', TEAM_B_KEYS, controlled=True))
        self.teams['B'].add_player(Player(200, 70, 'B'))
        self.teams['B'].add_player(Player(220, 100, 'B'))
        self.teams['B'].add_player(Player(200, 130, 'B'))
        self.teams['B'].add_player(Player(240, 90, 'B', is_keeper=True))

        # Score initial
        self.score = {'A': 0, 'B': 0}

        # Lancer la boucle de jeu
        pyxel.run(self.update, self.draw)

    def team_has_possession(self, team):
        """
        Retourne True si un joueur de l'équipe possède la balle.
        Cette fonction permet de déterminer si l'équipe doit attaquer ou défendre.
        """
        for player in self.teams[team].players:
            if player.has_ball:
                return True
        return False

    def update(self):
        """Met à jour la logique du jeu : sélection, déplacements, balle et gestion des buts."""
        # Mettre à jour la sélection manuelle des joueurs pour chaque équipe
        self.teams['A'].update_selection()
        self.teams['B'].update_selection()

        # Mettre à jour chaque joueur (contrôlé ou IA)
        for team in self.teams.values():
            for player in team.players:
                # Séparer coéquipiers et adversaires pour l'IA
                teammates = team.players
                opponents = self.teams['B'].players if team.team == 'A' else self.teams['A'].players
                player.update(self.ball, teammates, opponents)

        # Mettre à jour la balle
        self.ball.update()

        # Vérifier si un but a été marqué (si la balle traverse les extrémités du terrain)
        if self.ball.x - self.ball.radius < 0:
            # But pour l'équipe B
            self.score['B'] += 1
            self.reset_positions()
        elif self.ball.x + self.ball.radius > SCREEN_WIDTH:
            # But pour l'équipe A
            self.score['A'] += 1
            self.reset_positions()

    def reset_positions(self):
        """
        Réinitialise la position de la balle et de tous les joueurs
        après qu'un but ait été marqué.
        """
        self.ball.reset()
        # Réinitialisation de la position de chaque joueur à sa position par défaut
        for team in self.teams.values():
            for player in team.players:
                player.x = player.default_x
                player.y = player.default_y

    def draw_field(self):
        """Dessine le terrain, les bordures et les buts."""
        # Fond du terrain
        pyxel.cls(BACKGROUND_COLOR)
        # Zone de jeu
        pyxel.rect(FIELD_MARGIN, FIELD_MARGIN, SCREEN_WIDTH - 2 * FIELD_MARGIN, SCREEN_HEIGHT - 2 * FIELD_MARGIN, FIELD_COLOR)
        # Bordure du terrain
        pyxel.rectb(FIELD_MARGIN, FIELD_MARGIN, SCREEN_WIDTH - 2 * FIELD_MARGIN, SCREEN_HEIGHT - 2 * FIELD_MARGIN, pyxel.COLOR_WHITE)

        # Dessin des buts (affichés de chaque côté du terrain)
        goal_top = (SCREEN_HEIGHT - GOAL_HEIGHT) // 2
        # But de l'équipe A (côté gauche)
        pyxel.rect(0, goal_top, GOAL_WIDTH, GOAL_HEIGHT, GOAL_COLOR)
        pyxel.rectb(0, goal_top, GOAL_WIDTH, GOAL_HEIGHT, pyxel.COLOR_BLACK)
        # But de l'équipe B (côté droit)
        pyxel.rect(SCREEN_WIDTH - GOAL_WIDTH, goal_top, GOAL_WIDTH, GOAL_HEIGHT, GOAL_COLOR)
        pyxel.rectb(SCREEN_WIDTH - GOAL_WIDTH, goal_top, GOAL_WIDTH, GOAL_HEIGHT, pyxel.COLOR_BLACK)

        # Ligne médiane
        pyxel.line(SCREEN_WIDTH // 2, FIELD_MARGIN, SCREEN_WIDTH // 2, SCREEN_HEIGHT - FIELD_MARGIN, pyxel.COLOR_WHITE)

    def draw(self):
        """Dessine le terrain, la balle, les joueurs et le score."""
        self.draw_field()
        # Dessiner la balle
        self.ball.draw()
        # Dessiner les joueurs pour chaque équipe
        self.teams['A'].draw_players()
        self.teams['B'].draw_players()

        # Afficher le score en haut de l'écran
        score_text = f"Team A: {self.score['A']}   Team B: {self.score['B']}"
        pyxel.text(SCREEN_WIDTH // 2 - 40, 10, score_text, pyxel.COLOR_YELLOW)

# =============================================================================
# POINT D'ENTRÉE DU PROGRAMME
# =============================================================================
def main():
    Game()

if __name__ == "__main__":
    main()
