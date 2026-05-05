import pygame
import random
import math
import sys
from dataclasses import dataclass, field
from typing import List, Tuple

# ── Configurações ────────────────────────────────────────────────────────────

CELL = 24
COLS, ROWS = 28, 22
HEADER_H = 60
WIDTH  = COLS * CELL
HEIGHT = ROWS * CELL + HEADER_H

# Paleta — tema neon escuro
BG_DARK     = (15, 18, 28)
BG_GRID     = (22, 26, 40)
BG_GRID_ALT = (26, 30, 46)
HEADER_BG   = (20, 24, 36)
PANEL_BG    = (28, 32, 48)

SNAKE_HEAD  = (140, 230, 120)
SNAKE_BODY  = (90, 200, 140)
SNAKE_TAIL  = (60, 160, 110)
SNAKE_GLOW  = (160, 255, 150)

FOOD_COLOR  = (255, 90, 110)
FOOD_GLOW   = (255, 140, 160)

WALL_COLOR  = (90, 100, 140)
WALL_HIGH   = (130, 145, 190)

TEXT        = (235, 240, 250)
TEXT_DIM    = (140, 150, 175)
ACCENT      = (120, 200, 255)
GOLD        = (255, 200, 80)


# ── Fases ────────────────────────────────────────────────────────────────────

@dataclass
class Phase:
    number: int
    name: str
    target: int          # frutas para passar de fase
    speed: float         # movimentos por segundo
    walls: List[Tuple[int, int]] = field(default_factory=list)
    accent: Tuple[int, int, int] = ACCENT


def build_phases() -> List[Phase]:
    phases = []

    # Fase 1 — campo livre
    phases.append(Phase(1, "Iniciante", target=5, speed=8.0,
                        walls=[], accent=(120, 220, 255)))

    # Fase 2 — bordas viram parede (já é padrão), acelera
    phases.append(Phase(2, "Aprendiz", target=8, speed=10.0,
                        walls=[], accent=(140, 200, 255)))

    # Fase 3 — quatro pilares
    walls3 = []
    for cx, cy in [(7, 6), (COLS - 8, 6), (7, ROWS - 7), (COLS - 8, ROWS - 7)]:
        for dx in range(3):
            for dy in range(3):
                walls3.append((cx + dx, cy + dy))
    phases.append(Phase(3, "Veterano", target=10, speed=11.5,
                        walls=walls3, accent=(255, 200, 120)))

    # Fase 4 — cruz central
    walls4 = []
    midx, midy = COLS // 2, ROWS // 2
    for d in range(-5, 6):
        walls4.append((midx + d, midy))
        walls4.append((midx, midy + d))
    phases.append(Phase(4, "Especialista", target=12, speed=13.0,
                        walls=walls4, accent=(255, 150, 200)))

    # Fase 5 — labirinto
    walls5 = []
    for x in range(4, COLS - 4, 6):
        for y in range(4, ROWS - 4):
            if y % 8 != 0:
                walls5.append((x, y))
    phases.append(Phase(5, "Mestre", target=15, speed=15.0,
                        walls=walls5, accent=(200, 130, 255)))

    return phases


# ── Partículas ───────────────────────────────────────────────────────────────

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, color):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(60, 220)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = self.max_life = random.uniform(0.4, 0.8)
        self.color = color
        self.size = random.uniform(2, 5)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        alpha = max(0, self.life / self.max_life)
        r = max(1, int(self.size * alpha))
        c = (*self.color, int(255 * alpha))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, c, (r, r), r)
        surf.blit(s, (self.x - r, self.y - r))


# ── Jogo ─────────────────────────────────────────────────────────────────────

class Snake:
    def __init__(self):
        self.reset()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.body = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.next_dir = (1, 0)
        self.grow_pending = 0

    def turn(self, d):
        if (d[0] == -self.direction[0] and d[1] == -self.direction[1]):
            return
        self.next_dir = d

    def step(self):
        self.direction = self.next_dir
        hx, hy = self.body[0]
        new = (hx + self.direction[0], hy + self.direction[1])
        self.body.insert(0, new)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()
        return new

    def grow(self, n=1):
        self.grow_pending += n

    def hits_self(self):
        return self.body[0] in self.body[1:]


class Game:
    STATE_PLAYING    = "playing"
    STATE_GAME_OVER  = "game_over"
    STATE_PHASE_DONE = "phase_done"
    STATE_WIN        = "win"
    STATE_PAUSED     = "paused"

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Snake — Aventura por Fases")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font_xl = pygame.font.SysFont("segoeui", 56, bold=True)
        self.font_lg = pygame.font.SysFont("segoeui", 32, bold=True)
        self.font_md = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_sm = pygame.font.SysFont("segoeui", 16)

        self.phases = build_phases()
        self.reset_full()

    # ── reset ────────────────────────────────────────────────────────────────

    def reset_full(self):
        self.phase_idx = 0
        self.score = 0
        self.total_eaten = 0
        self._enter_phase()

    def _enter_phase(self):
        self.snake = Snake()
        self.eaten_in_phase = 0
        self.particles: List[Particle] = []
        self.move_timer = 0.0
        self.state = self.STATE_PLAYING
        self.phase_anim = 1.0  # animação de entrada da fase
        self._spawn_food()

    def _next_phase(self):
        if self.phase_idx + 1 < len(self.phases):
            self.phase_idx += 1
            self._enter_phase()
        else:
            self.state = self.STATE_WIN

    @property
    def phase(self) -> Phase:
        return self.phases[self.phase_idx]

    # ── comida ───────────────────────────────────────────────────────────────

    def _spawn_food(self):
        occupied = set(self.snake.body) | set(self.phase.walls)
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in occupied]
        self.food = random.choice(free) if free else None

    # ── input ────────────────────────────────────────────────────────────────

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if event.type != pygame.KEYDOWN:
            return

        if self.state == self.STATE_PLAYING:
            if event.key in (pygame.K_UP, pygame.K_w):    self.snake.turn((0, -1))
            elif event.key in (pygame.K_DOWN, pygame.K_s):  self.snake.turn((0, 1))
            elif event.key in (pygame.K_LEFT, pygame.K_a):  self.snake.turn((-1, 0))
            elif event.key in (pygame.K_RIGHT, pygame.K_d): self.snake.turn((1, 0))
            elif event.key in (pygame.K_p, pygame.K_ESCAPE): self.state = self.STATE_PAUSED

        elif self.state == self.STATE_PAUSED:
            if event.key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
                self.state = self.STATE_PLAYING

        elif self.state == self.STATE_PHASE_DONE:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._next_phase()

        elif self.state in (self.STATE_GAME_OVER, self.STATE_WIN):
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.reset_full()

    # ── update ───────────────────────────────────────────────────────────────

    def update(self, dt):
        # decai animação de entrada da fase
        if self.phase_anim > 0:
            self.phase_anim = max(0, self.phase_anim - dt * 1.4)

        # partículas sempre animam
        self.particles = [p for p in self.particles if p.update(dt)]

        if self.state != self.STATE_PLAYING:
            return

        self.move_timer += dt
        step_t = 1.0 / self.phase.speed
        while self.move_timer >= step_t:
            self.move_timer -= step_t
            self._step()
            if self.state != self.STATE_PLAYING:
                self.move_timer = 0
                return

    def _step(self):
        head = self.snake.step()
        hx, hy = head

        # bater na borda
        if hx < 0 or hx >= COLS or hy < 0 or hy >= ROWS:
            return self._die()

        # bater em parede
        if (hx, hy) in self.phase.walls:
            return self._die()

        # bater em si mesma
        if self.snake.hits_self():
            return self._die()

        # comer
        if head == self.food:
            self.snake.grow(1)
            self.eaten_in_phase += 1
            self.total_eaten += 1
            self.score += 10 * self.phase.number
            self._burst(self.food, FOOD_COLOR)
            if self.eaten_in_phase >= self.phase.target:
                self.state = self.STATE_PHASE_DONE
                self.score += 100 * self.phase.number  # bônus
            else:
                self._spawn_food()

    def _die(self):
        head = self.snake.body[0]
        self._burst(head, SNAKE_HEAD, count=40)
        self.state = self.STATE_GAME_OVER

    def _burst(self, cell, color, count=22):
        cx = cell[0] * CELL + CELL / 2
        cy = cell[1] * CELL + CELL / 2 + HEADER_H
        for _ in range(count):
            self.particles.append(Particle(cx, cy, color))

    # ── desenho ──────────────────────────────────────────────────────────────

    def draw(self):
        self.screen.fill(BG_DARK)
        self._draw_header()
        self._draw_board()
        self._draw_walls()
        self._draw_food()
        self._draw_snake()
        for p in self.particles:
            p.draw(self.screen)
        self._draw_overlays()
        pygame.display.flip()

    def _draw_header(self):
        rect = pygame.Rect(0, 0, WIDTH, HEADER_H)
        pygame.draw.rect(self.screen, HEADER_BG, rect)
        pygame.draw.line(self.screen, self.phase.accent,
                         (0, HEADER_H - 2), (WIDTH, HEADER_H - 2), 2)

        # Fase
        phase_txt = self.font_md.render(
            f"Fase {self.phase.number} · {self.phase.name}", True, TEXT)
        self.screen.blit(phase_txt, (16, 10))

        # Progresso
        prog_w = 220
        prog_x = 16
        prog_y = 38
        pygame.draw.rect(self.screen, BG_GRID,
                         (prog_x, prog_y, prog_w, 10), border_radius=5)
        ratio = self.eaten_in_phase / self.phase.target
        fill_w = int(prog_w * min(1.0, ratio))
        if fill_w > 0:
            pygame.draw.rect(self.screen, self.phase.accent,
                             (prog_x, prog_y, fill_w, 10), border_radius=5)
        prog_txt = self.font_sm.render(
            f"{self.eaten_in_phase}/{self.phase.target}", True, TEXT_DIM)
        self.screen.blit(prog_txt, (prog_x + prog_w + 10, prog_y - 3))

        # Score
        score_txt = self.font_md.render(f"{self.score}", True, GOLD)
        score_lbl = self.font_sm.render("PONTOS", True, TEXT_DIM)
        sw = score_txt.get_width()
        self.screen.blit(score_lbl, (WIDTH - sw - 16, 10))
        self.screen.blit(score_txt, (WIDTH - sw - 16, 26))

    def _draw_board(self):
        for x in range(COLS):
            for y in range(ROWS):
                color = BG_GRID if (x + y) % 2 == 0 else BG_GRID_ALT
                pygame.draw.rect(
                    self.screen, color,
                    (x * CELL, y * CELL + HEADER_H, CELL, CELL))

    def _draw_walls(self):
        for (x, y) in self.phase.walls:
            r = pygame.Rect(x * CELL + 2, y * CELL + HEADER_H + 2,
                            CELL - 4, CELL - 4)
            pygame.draw.rect(self.screen, WALL_COLOR, r, border_radius=4)
            pygame.draw.rect(self.screen, WALL_HIGH, r, width=1, border_radius=4)

    def _draw_food(self):
        if not self.food:
            return
        x, y = self.food
        cx = x * CELL + CELL // 2
        cy = y * CELL + CELL // 2 + HEADER_H

        # pulso
        t = pygame.time.get_ticks() / 1000
        pulse = (math.sin(t * 4) + 1) / 2
        glow_r = int(CELL * 0.7 + pulse * 4)

        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for i in range(4, 0, -1):
            alpha = int(40 * (i / 4))
            pygame.draw.circle(glow, (*FOOD_GLOW, alpha),
                               (glow_r, glow_r), int(glow_r * i / 4))
        self.screen.blit(glow, (cx - glow_r, cy - glow_r))

        pygame.draw.circle(self.screen, FOOD_COLOR, (cx, cy), CELL // 2 - 3)
        pygame.draw.circle(self.screen, FOOD_GLOW,
                           (cx - 3, cy - 3), 3)

    def _draw_snake(self):
        n = len(self.snake.body)
        for i, (x, y) in enumerate(self.snake.body):
            r = pygame.Rect(x * CELL + 2, y * CELL + HEADER_H + 2,
                            CELL - 4, CELL - 4)
            if i == 0:
                # cabeça
                pygame.draw.rect(self.screen, SNAKE_HEAD, r, border_radius=8)
                self._draw_eyes(x, y)
            else:
                t = i / max(1, n - 1)
                color = (
                    int(SNAKE_BODY[0] * (1 - t) + SNAKE_TAIL[0] * t),
                    int(SNAKE_BODY[1] * (1 - t) + SNAKE_TAIL[1] * t),
                    int(SNAKE_BODY[2] * (1 - t) + SNAKE_TAIL[2] * t),
                )
                pygame.draw.rect(self.screen, color, r, border_radius=6)

    def _draw_eyes(self, x, y):
        dx, dy = self.snake.direction
        cx = x * CELL + CELL // 2
        cy = y * CELL + HEADER_H + CELL // 2
        # posição dos olhos relativa à direção
        offset = CELL // 4
        if dx == 1:    e1, e2 = (cx + 3, cy - offset), (cx + 3, cy + offset)
        elif dx == -1: e1, e2 = (cx - 3, cy - offset), (cx - 3, cy + offset)
        elif dy == 1:  e1, e2 = (cx - offset, cy + 3), (cx + offset, cy + 3)
        else:          e1, e2 = (cx - offset, cy - 3), (cx + offset, cy - 3)
        for (ex, ey) in (e1, e2):
            pygame.draw.circle(self.screen, (20, 20, 30), (ex, ey), 3)
            pygame.draw.circle(self.screen, TEXT, (ex - 1, ey - 1), 1)

    def _draw_overlays(self):
        # animação de entrada da fase
        if self.phase_anim > 0 and self.state == self.STATE_PLAYING:
            alpha = int(255 * self.phase_anim)
            txt = self.font_xl.render(f"Fase {self.phase.number}", True, self.phase.accent)
            sub = self.font_lg.render(self.phase.name, True, TEXT)
            txt.set_alpha(alpha); sub.set_alpha(alpha)
            self.screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 60))
            self.screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 10))

        if self.state == self.STATE_PAUSED:
            self._modal("PAUSADO", "Pressione P para continuar", ACCENT)
        elif self.state == self.STATE_GAME_OVER:
            self._modal("GAME OVER",
                        f"Pontuação: {self.score}   ·   ENTER para recomeçar",
                        FOOD_COLOR)
        elif self.state == self.STATE_PHASE_DONE:
            self._modal(f"Fase {self.phase.number} concluída!",
                        f"+{100 * self.phase.number} bônus   ·   ENTER para avançar",
                        GOLD)
        elif self.state == self.STATE_WIN:
            self._modal("VOCÊ É O MESTRE DA COBRA!",
                        f"Pontuação final: {self.score}   ·   ENTER para recomeçar",
                        GOLD)

    def _modal(self, title, subtitle, color):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 170))
        self.screen.blit(veil, (0, 0))

        panel_w, panel_h = 520, 200
        panel_x = WIDTH // 2 - panel_w // 2
        panel_y = HEIGHT // 2 - panel_h // 2
        pygame.draw.rect(self.screen, PANEL_BG,
                         (panel_x, panel_y, panel_w, panel_h),
                         border_radius=18)
        pygame.draw.rect(self.screen, color,
                         (panel_x, panel_y, panel_w, panel_h),
                         width=2, border_radius=18)

        t = self.font_lg.render(title, True, color)
        s = self.font_sm.render(subtitle, True, TEXT_DIM)
        self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, panel_y + 50))
        self.screen.blit(s, (WIDTH // 2 - s.get_width() // 2, panel_y + 120))

    # ── loop ─────────────────────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
