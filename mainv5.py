import pyxel
import random
import math


SCREEN_WIDTH = 256
SCREEN_HEIGHT = 192

BALL_SPEED = 3.0       
PLAYER_SPEED = 2.0     
FRICTION = 0.98        

BALL_RADIUS = 3
PLAYER_RADIUS = 4


TEAM_A_COLOR = 8      
TEAM_B_COLOR = 12      
FIELD_COLOR = 11 #Vert
BACKGROUND_COLOR = 3   
GOAL_COLOR = 7   #Blanc 

# Marges du terrain
FIELD_MARGIN = 5

# Dimensions des buts 
GOAL_WIDTH = 12
GOAL_HEIGHT = 40

# Touches de contrôle 
TEAM_A_KEYS = {
    'up': pyxel.KEY_Z,
    'down': pyxel.KEY_S,
    'left': pyxel.KEY_Q,
    'right': pyxel.KEY_D,
    'pass': pyxel.KEY_A,
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


class Ball:
    def __init__(self):
        self.reset()

    def reset(self):
        """
        Réinitialise la balle au centre du terrain avec une vélocité nulle.
        La balle n'est pas en passe et n'a pas de destinataire.
        """
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.vx = 0
        self.vy = 0
        self.radius = BALL_RADIUS
        self.in_pass = False       # Indique que la balle est actuellement en passe
        self.pass_receiver = None  # Le joueur destiné à recevoir la passe

    def update(self):
    # Mise à jour de la position selon la vitesse
        self.x += self.vx
        self.y += self.vy

    # Application de la friction 
        self.vx *= FRICTION
        self.vy *= FRICTION

    # arret balle
        if abs(self.vx) < 0.1 and abs(self.vy) < 0.1:
            self.vx = 0
            self.vy = 0
            self.in_pass = False
            self.pass_receiver = None

    # Définir la zone verticale des buts
        goal_top = (SCREEN_HEIGHT - GOAL_HEIGHT) // 2
        goal_bottom = goal_top + GOAL_HEIGHT

    
        if self.x - self.radius < 0:
        # Si la balle se trouve dans la zone verticale du but
            if goal_top <= self.y <= goal_bottom:
            # But pour l'équipe B
                Game.instance.score['B'] += 1
                Game.instance.reset_positions()
                return  # Arrête la mise à jour pour éviter un rebond supplémentaire
            else:
            # Sinon, rebondir sur le mur gauche : la vitesse devient positive
                self.vx = abs(self.vx) * 0.7
            # Repositionnement pour éviter de rester collée au bord
                self.x = self.radius

   
        if self.x + self.radius > SCREEN_WIDTH:
            if goal_top <= self.y <= goal_bottom:
            # But pour l'équipe A
                Game.instance.score['A'] += 1
                Game.instance.reset_positions()
                return
            else:
            # Rebond sur le mur droit : la vitesse devient négative
                self.vx = -abs(self.vx) * 0.7
                self.x = SCREEN_WIDTH - self.radius

    
        if self.y - self.radius < FIELD_MARGIN:
            self.vy = abs(self.vy) * 0.7
            self.y = self.radius + FIELD_MARGIN
        if self.y + self.radius > SCREEN_HEIGHT - FIELD_MARGIN:
            self.vy = -abs(self.vy) * 0.7
            self.y = SCREEN_HEIGHT - self.radius - FIELD_MARGIN

    def draw(self):
        """Dessine la balle."""
        pyxel.circ(self.x, self.y, self.radius, pyxel.COLOR_WHITE)


class Player:
    def __init__(self, x, y, team, keys=None, is_keeper=False, controlled=False):
        self.x = x
        self.y = y
        self.team = team                  # 'A' ou 'B'
        self.keys = keys                  # Mapping clavier None pour l'IA
        self.is_keeper = is_keeper        # Gardien si True, sinon joueur de champ
        self.controlled = controlled      # True si contrôlé par l'humain
        self.radius = PLAYER_RADIUS
        self.has_ball = False
        self.facing = (0, 0)              # Dernière direction de déplacement (pour la passe)
        # Position par défaut (en défense)
        self.default_x = x
        self.default_y = y

    def update(self, ball, teammates, opponents):
        """
        Met à jour le joueur :
         - Vérifie la collision avec la balle.
         - Gère l'input du joueur contrôlé ou le comportement de l'IA.
         - Contrainte de rester dans le terrain.
        """
        self.check_ball_collision(ball)

        if self.controlled and self.keys is not None:
            self.handle_input(ball)
        else:
            self.ai_behavior(ball, teammates, opponents)

        # Limiter les déplacements dans les limites du terrain
        self.x = max(FIELD_MARGIN + self.radius, min(self.x, SCREEN_WIDTH - FIELD_MARGIN - self.radius))
        self.y = max(FIELD_MARGIN + self.radius, min(self.y, SCREEN_HEIGHT - FIELD_MARGIN - self.radius))

    def check_ball_collision(self, ball):
        """
        Vérifie si le joueur est en collision avec la balle.
        Si la balle est en passe, seuls le destinataire ou un adversaire interceptant
        capturent la balle. Sinon, la balle est récupérée.
        """
        distance = math.hypot(self.x - ball.x, self.y - ball.y)
        if distance < self.radius + ball.radius:
            if ball.in_pass and ball.pass_receiver is not None:
                # Si la balle est en passe, on autorise la capture uniquement
                # par le joueur destiné ou un adversaire (pour une interception)
                if ball.pass_receiver == self:
                    self.has_ball = True
                    ball.in_pass = False
                    ball.pass_receiver = None
                    ball.vx = 0
                    ball.vy = 0
                elif self.team != ball.pass_receiver.team:
                    # Interception par un joueur adverse
                    self.has_ball = True
                    ball.in_pass = False
                    ball.pass_receiver = None
                    ball.vx = 0
                    ball.vy = 0
                else:
                    self.has_ball = False
            else:
                # Si la balle n'est pas en passe, capture normale
                self.has_ball = True
                ball.vx = 0
                ball.vy = 0
        else:
            self.has_ball = False

    def handle_input(self, ball):
        """
        Gère le déplacement du joueur contrôlé et déclenche les actions de passe ou de tir.
        """
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

        # Conserver la dernière direction pour la passe
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
        """
        Effectue une passe :
         - Recherche le coéquipier le plus proche.
         - Calcule la vélocité de la balle dans sa direction.
         - Active l'état "in_pass" et définit le destinataire de la passe.
         - Transfère le contrôle au receveur.
        """
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
            # Définir le destinataire de la passe et activer l'état "in_pass"
            ball.in_pass = True
            ball.pass_receiver = best_mate

            # Transfert de contrôle : le receveur devient le joueur contrôlé
            team = Game.instance.teams[self.team]
            for p in team.players:
                p.controlled = False
                p.keys = None
            best_mate.controlled = True
            best_mate.keys = team.keys

    def shoot_ball(self, ball):
        """
        Effectue un tir en calculant la direction vers le but adverse.
        """
        if self.team == 'A':
            goal_x = SCREEN_WIDTH - FIELD_MARGIN - GOAL_WIDTH // 2
        else:
            goal_x = FIELD_MARGIN + GOAL_WIDTH // 2
        goal_y = SCREEN_HEIGHT // 2  # Milieu du but
        dx = goal_x - self.x
        dy = goal_y - self.y
        d = math.hypot(dx, dy)
        if d != 0:
            ball.vx = (dx / d) * BALL_SPEED * 1.5
            ball.vy = (dy / d) * BALL_SPEED * 1.5
            ball.in_pass = True
            ball.pass_receiver = None  # Aucun destinataire défini pour un tir

    def ai_behavior(self, ball, teammates, opponents):
        """
        Comportement de base de l'IA :
         - En attaque (si l'équipe possède la balle) : se diriger vers le but adverse.
         - En défense : revenir à sa position initiale.
         - Le gardien se positionne toujours devant son but.
        """
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
        """
        Dessine le joueur avec sa couleur d'équipe.
        Si le joueur est contrôlé, un contour jaune l'identifie.
        """
        color = TEAM_A_COLOR if self.team == 'A' else TEAM_B_COLOR
        pyxel.circ(self.x, self.y, self.radius, color)
        if self.controlled:
            pyxel.circb(self.x, self.y, self.radius + 2, pyxel.COLOR_YELLOW)
        if self.has_ball:
            pyxel.circ(self.x, self.y, self.radius - 2, pyxel.COLOR_WHITE)


class Team:
    def __init__(self, team, keys):
        self.team = team                # 'A' ou 'B'
        self.keys = keys                # Mapping clavier pour l'équipe
        self.players = []               # Liste des joueurs
        self.selected_index = 0         # Indice du joueur actuellement contrôlé

    def add_player(self, player):
        """Ajoute un joueur à l'équipe."""
        self.players.append(player)

    def cycle_player(self):
        """
        Change le joueur contrôlé en parcourant la liste.
        Utile pour le changement manuel de joueur.
        """
        self.selected_index = (self.selected_index + 1) % len(self.players)
        for i, player in enumerate(self.players):
            player.controlled = (i == self.selected_index)
            player.keys = self.keys if player.controlled else None

    def update_selection(self):
        """
        Détecte l'appui sur la touche de sélection pour changer le joueur contrôlé.
        """
        if pyxel.btnp(self.keys['select']):
            self.cycle_player()

    def draw_players(self):
        """Dessine l'ensemble des joueurs de l'équipe."""
        for player in self.players:
            player.draw()


class Game:
    # Référence statique à l'instance du jeu pour y accéder depuis d'autres classes
    instance = None

    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Pyxel Football")
        Game.instance = self
        self.ball = Ball()

        # Initialisation des équipes
        self.teams = {}
        self.teams['A'] = Team('A', TEAM_A_KEYS)
        self.teams['B'] = Team('B', TEAM_B_KEYS)

        # Création de l'équipe A : 4 joueurs de champ + 1 gardien
        self.teams['A'].add_player(Player(30, 50, 'A', TEAM_A_KEYS, controlled=True))
        self.teams['A'].add_player(Player(50, 70, 'A'))
        self.teams['A'].add_player(Player(30, 100, 'A'))
        self.teams['A'].add_player(Player(50, 130, 'A'))
       

        # Création de l'équipe B : 4 joueurs de champ + 1 gardien
        self.teams['B'].add_player(Player(220, 50, 'B', TEAM_B_KEYS, controlled=True))
        self.teams['B'].add_player(Player(200, 70, 'B'))
        self.teams['B'].add_player(Player(220, 100, 'B'))
        self.teams['B'].add_player(Player(200, 130, 'B'))
       

        # Score initial
        self.score = {'A': 0, 'B': 0}

        # Démarrage de la boucle principale
        pyxel.run(self.update, self.draw)

    def team_has_possession(self, team):
        """
        Retourne True si un joueur de l'équipe possède la balle.
        Permet de déterminer la tactique (attaque/défense).
        """
        for player in self.teams[team].players:
            if player.has_ball:
                return True
        return False

    def update(self):
        """Met à jour la logique globale du jeu (sélection, déplacements, balle, buts)."""
        self.teams['A'].update_selection()
        self.teams['B'].update_selection()

        for team in self.teams.values():
            for player in team.players:
                teammates = team.players
                opponents = self.teams['B'].players if team.team == 'A' else self.teams['A'].players
                player.update(self.ball, teammates, opponents)

        self.ball.update()

        # Vérification des buts (la balle qui sort sur les côtés)
        if self.ball.x - self.ball.radius < 0:
            self.score['B'] += 1
            self.reset_positions()
        elif self.ball.x + self.ball.radius > SCREEN_WIDTH:
            self.score['A'] += 1
            self.reset_positions()

    def reset_positions(self):
        """
        Réinitialise la balle et replace chaque joueur à sa position par défaut
        après qu'un but ait été marqué.
        """
        self.ball.reset()
        for team in self.teams.values():
            for player in team.players:
                player.x = player.default_x
                player.y = player.default_y

    def draw_field(self):
        """Dessine le terrain, les bordures et les buts."""
        pyxel.cls(BACKGROUND_COLOR)
        pyxel.rect(FIELD_MARGIN, FIELD_MARGIN, SCREEN_WIDTH - 2 * FIELD_MARGIN, SCREEN_HEIGHT - 2 * FIELD_MARGIN, FIELD_COLOR)
        pyxel.rectb(FIELD_MARGIN, FIELD_MARGIN, SCREEN_WIDTH - 2 * FIELD_MARGIN, SCREEN_HEIGHT - 2 * FIELD_MARGIN, pyxel.COLOR_WHITE)

        goal_top = (SCREEN_HEIGHT - GOAL_HEIGHT) // 2
        # But de l'équipe A (gauche)
        pyxel.rect(0, goal_top, GOAL_WIDTH, GOAL_HEIGHT, GOAL_COLOR)
        pyxel.rectb(0, goal_top, GOAL_WIDTH, GOAL_HEIGHT, pyxel.COLOR_BLACK)
        # But de l'équipe B (droite)
        pyxel.rect(SCREEN_WIDTH - GOAL_WIDTH, goal_top, GOAL_WIDTH, GOAL_HEIGHT, GOAL_COLOR)
        pyxel.rectb(SCREEN_WIDTH - GOAL_WIDTH, goal_top, GOAL_WIDTH, GOAL_HEIGHT, pyxel.COLOR_BLACK)

        pyxel.line(SCREEN_WIDTH // 2, FIELD_MARGIN, SCREEN_WIDTH // 2, SCREEN_HEIGHT - FIELD_MARGIN, pyxel.COLOR_WHITE)

    def draw(self):
        """Dessine le terrain, la balle, les joueurs et le score."""
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
