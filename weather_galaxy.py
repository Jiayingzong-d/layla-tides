#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hong Kong daily weather (Aug 2024) as an interactive particle system.
- Pure black background
- X: Date axis (Aug 1 → Aug 31) with ticks
- Y: Temperature axis (higher temp → higher position) with ticks and grid
- Particle color = temperature gradient (blue → yellow → orange-red), with optional light weather tint
- Collapsible stats panel via mouse click (button or header)
- Particles orbit around their day anchor; hover shows details and repels neighbors

Data source: HKO via data_fetch.py (with its own fallback).
"""

import math
import random
from datetime import datetime
import pygame

from data_fetch import fetch_hk_data, WeatherDay


# ----------------------------- Window & Colors -----------------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 1400, 900
WHITE = (255, 255, 255)
BRIGHT_YELLOW = (255, 255, 100)
LIGHT_GRAY = (200, 200, 220)
BLUE = (74, 158, 255)
BLACK = (0, 0, 0)

# Axis margins
AXIS_MARGIN_L = 80
AXIS_MARGIN_R = 80
AXIS_MARGIN_T = 130
AXIS_MARGIN_B = 100

# --------------------- Color mode & temperature normalization --------------
# "temp" = pure temperature gradient; "temp_tinted" = +20% light weather tint
COLOR_MODE = "temp"   # change to "temp_tinted" if you want a little weather flavor

# will be set from real data in main()
TEMP_MIN, TEMP_MAX = 28.0, 34.0

def lerp(a, b, t): 
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))

def temp_gradient_color(temp):
    """3-stop gradient: blue -> yellow -> orange-red based on normalized temperature."""
    span = max(1e-6, (TEMP_MAX - TEMP_MIN))
    nt = max(0.0, min(1.0, (temp - TEMP_MIN) / span))
    c_cool  = ( 60, 130, 255)   # blue
    c_warm  = (255, 230, 120)   # yellow
    c_hot   = (255, 110,  60)   # orange-red
    if nt <= 0.5:
        return lerp_color(c_cool, c_warm, nt / 0.5)
    else:
        return lerp_color(c_warm, c_hot, (nt - 0.5) / 0.5)


# ---------------------------- Particle Object -----------------------------
class WeatherParticle:
    def __init__(self, wd: WeatherDay):
        self.weather_day = wd
        self.x = 0.0
        self.y = 0.0

        # Anchor set by layout
        self.anchor_x = SCREEN_WIDTH // 2
        self.anchor_y = SCREEN_HEIGHT // 2

        # Visual
        self.base_size = self._calc_size(wd.temperature)
        self.size = self.base_size

        # Local orbit around anchor
        self.local_angle = random.uniform(0, math.tau)
        self.local_speed = random.uniform(0.01, 0.03)
        self.local_radius = random.uniform(10, 22)

        # Organic motion & pulsing
        self.pulse_phase = random.uniform(0, math.tau)
        self.pulse_speed = random.uniform(0.02, 0.05)
        self.float_phase = random.uniform(0, math.tau)
        self.float_amp = random.uniform(2, 8)
        self.radial_phase = random.uniform(0, math.tau)
        self.radial_speed = random.uniform(0.01, 0.03)
        self.radial_amp = random.uniform(5, 15)
        self.org_angle = random.uniform(0, math.tau)
        self.org_speed = random.uniform(0.005, 0.02)
        self.org_radius = random.uniform(3, 8)

        # Hover/glow
        self.hovered = False
        self.glow = 0.0
        self.glow_target = 0.0

    def _calc_size(self, t: float) -> float:
        normalized = (t - 28.0) / 5.0
        size_factor = max(0.3, min(1.5, normalized))
        return (8 + size_factor * 15) * random.uniform(0.85, 1.2)

    def _color(self):
        """Temperature gradient first; optional light weather tint; then glow."""
        t = self.weather_day.temperature
        base = temp_gradient_color(t)

        if COLOR_MODE != "temp":
            # add very light weather tint to keep identity without muddy colors
            wt = self.weather_day.weather_type
            palette_tint = {
                "sunny":  (255, 220,  80),
                "rainy":  (100, 160, 255),
                "cloudy": (190, 195, 210),
            }
            weather_tint = palette_tint.get(wt, (220, 220, 220))
            mix = 0.20  # 20% weather tint only
            base = (
                int(base[0] * (1 - mix) + weather_tint[0] * mix),
                int(base[1] * (1 - mix) + weather_tint[1] * mix),
                int(base[2] * (1 - mix) + weather_tint[2] * mix),
            )

        # glow enhancement on hover
        if self.glow > 0:
            enh = 1.0 + self.glow * 0.25
            base = (min(255, int(base[0] * enh)),
                    min(255, int(base[1] * enh)),
                    min(255, int(base[2] * enh)))
        return base

    def update(self, frame: int, mouse_pos, all_particles):
        mx, my = mouse_pos
        self.hovered = (self.x - mx) ** 2 + (self.y - my) ** 2 < 40 ** 2
        self.glow_target = 1.0 if self.hovered else 0.0
        self.glow += (self.glow_target - self.glow) * 0.15

        # Local circular orbit + light radial pulsing
        self.local_angle += self.local_speed
        radial_off = math.sin(frame * self.radial_speed + self.radial_phase) * (self.radial_amp * 0.25)
        r = self.local_radius + radial_off

        # Organic micro motion
        self.org_angle += self.org_speed
        ox = math.cos(self.org_angle) * self.org_radius * 0.3
        oy = math.sin(self.org_angle * 0.7) * self.org_radius * 0.2

        # Repulsion from hovered particle
        repx = repy = 0.0
        hovered = next((p for p in all_particles if p.hovered), None)
        if hovered and hovered is not self:
            dx = self.x - hovered.x
            dy = self.y - hovered.y
            dist = max(1.0, math.hypot(dx, dy))
            strength = max(0.0, (200.0 - dist) / 200.0) * 80.0
            repx = (dx / dist) * strength
            repy = (dy / dist) * strength

        # Final position = anchor + local orbit + organic float + repulsion
        base_x = self.anchor_x + math.cos(self.local_angle) * r
        base_y = self.anchor_y + math.sin(self.local_angle) * r
        self.x = base_x + ox + math.sin(frame * 0.01 + self.float_phase) * self.float_amp * 0.5 + repx
        self.y = base_y + oy + math.cos(frame * 0.008 + self.float_phase) * self.float_amp * 0.3 + repy

        # Size animation
        if self.hovered:
            self.size = self.base_size * (1.5 + math.sin(frame * 0.1) * 0.2)
        elif hovered and hovered is not self:
            self.size = self.base_size * 0.9
        else:
            self.size = self.base_size * (1.0 + math.sin(frame * self.pulse_speed + self.pulse_phase) * 0.1)

    def draw(self, surface):
        color = self._color()
        size = int(self.size)

        # Glow halo
        if self.glow > 0.1 or self.size > self.base_size * 1.1:
            layers = 5 if self.hovered else 4
            mult = 2.0 if self.hovered else 1.0
            for i in range(layers):
                gsize = int(self.size * (3.0 - i * 0.4) * mult)
                galpha = int(self.glow * 40 / (i + 1) * mult)
                if galpha > 0:
                    surf = pygame.Surface((gsize * 4, gsize * 4), pygame.SRCALPHA)
                    glow_color = tuple(c // 2 for c in color)
                    pygame.draw.circle(surf, (*glow_color, galpha), (gsize * 2, gsize * 2), gsize)
                    surface.blit(surf, (self.x - gsize * 2, self.y - gsize * 2))

        # Hover ring
        if self.hovered:
            rsize = int(size * 2.5)
            alpha = int(100 * math.sin(pygame.time.get_ticks() * 0.01))
            if alpha > 0:
                ring = pygame.Surface((rsize * 4, rsize * 4), pygame.SRCALPHA)
                pygame.draw.circle(ring, (*color, alpha), (rsize * 2, rsize * 2), rsize, 3)
                surface.blit(ring, (self.x - rsize * 2, self.y - rsize * 2))

        # Body
        outer = tuple(max(0, c - 40) for c in color)
        pygame.draw.circle(surface, outer, (int(self.x), int(self.y)), size + 1)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), size)

        # Highlights
        hi = max(2, int(size * 0.4))
        pos = (int(self.x - size * 0.3), int(self.y - size * 0.3))
        pygame.draw.circle(surface, (255, 255, 255, 180), pos, hi)
        core = max(1, int(size * 0.15))
        pygame.draw.circle(surface, (255, 255, 255),
                           (int(self.x - size * 0.1), int(self.y - size * 0.1)), core)


# --------------------------- Animated Background ---------------------------
class ArtisticBackground:
    def __init__(self):
        self.stars = []
        self.nebula = []
        self._init_stars()
        self._init_nebula()

    def _init_stars(self):
        for _ in range(150):
            self.stars.append({
                "x": random.randint(0, SCREEN_WIDTH), "y": random.randint(0, SCREEN_HEIGHT),
                "size": random.uniform(0.5, 1.5), "b": random.uniform(50, 120),
                "ph": random.uniform(0, math.tau), "spd": random.uniform(0.02, 0.05), "layer": 1
            })
        for _ in range(30):
            self.stars.append({
                "x": random.randint(0, SCREEN_WIDTH), "y": random.randint(0, SCREEN_HEIGHT),
                "size": random.uniform(2, 4), "b": random.uniform(150, 255),
                "ph": random.uniform(0, math.tau), "spd": random.uniform(0.03, 0.08), "layer": 2
            })

    def _init_nebula(self):
        # Lower alpha so background doesn't compete with data colors
        for _ in range(8):
            self.nebula.append({
                "x": random.randint(-100, SCREEN_WIDTH + 100),
                "y": random.randint(-100, SCREEN_HEIGHT + 100),
                "size": random.uniform(200, 400),
                "color": random.choice([(20, 30, 80, 18), (80, 20, 50, 14), (50, 80, 20, 12)]),
                "drift": random.uniform(0.1, 0.3),
                "ph": random.uniform(0, math.tau)
            })

    def update(self, frame: int):
        for s in self.stars:
            s["cb"] = max(0, min(255, s["b"] + math.sin(frame * s["spd"] + s["ph"]) * 30))
        for n in self.nebula:
            n["x"] += n["drift"]
            if n["x"] > SCREEN_WIDTH + 200:
                n["x"] = -200
            n["ca"] = max(10, n["color"][3] + math.sin(frame * 0.02 + n["ph"]) * 10)

    def draw(self, surface):
        surface.fill(BLACK)
        # Nebula
        for n in self.nebula:
            surf = pygame.Surface((int(n["size"] * 2), int(n["size"] * 2)), pygame.SRCALPHA)
            for rr in range(int(n["size"]), 0, -5):
                alpha = int(n["ca"] * (rr / n["size"]))
                if alpha > 0:
                    pygame.draw.circle(
                        surf, (n["color"][0], n["color"][1], n["color"][2], alpha),
                        (int(n["size"]), int(n["size"])), rr
                    )
            surface.blit(surf, (n["x"] - n["size"], n["y"] - n["size"]))
        # Stars
        for s in self.stars:
            b = int(s["cb"])
            col = (b, b, b)
            if s["layer"] == 1:
                pygame.draw.circle(surface, col, (int(s["x"]), int(s["y"])), int(s["size"]))
            else:
                size = int(s["size"])
                pygame.draw.circle(surface, col, (int(s["x"]), int(s["y"])), size)
                L = size * 3
                pygame.draw.line(surface, col, (s["x"] - L, s["y"]), (s["x"] + L, s["y"]), 1)
                pygame.draw.line(surface, col, (s["x"], s["y"] - L), (s["x"], s["y"] + L), 1)


# ------------------------------ Info Panel (Collapsible) ------------------------------
class InfoPanel:
    """
    Collapsible statistics panel.
    - Button at top-right toggles it (large hit box)
    - When open, clicking panel header (top 56 px) also toggles
    """
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        # Smaller title font as requested
        self.ft_title = pygame.font.Font(None, 20)
        self.ft_text = pygame.font.Font(None, 20)
        self.is_open = True

        # Big clickable button at top-right
        self.btn_w, self.btn_h = 120, 40
        self.btn_rect = pygame.Rect(SCREEN_WIDTH - self.btn_w - 20, 16, self.btn_w, self.btn_h)

        # Header clickable region inside the panel
        self.header_height = 56

    def toggle(self):
        self.is_open = not self.is_open

    def handle_click(self, pos):
        if self.btn_rect.collidepoint(pos):
            self.toggle()
            return True
        if self.is_open:
            header_rect = pygame.Rect(self.x, self.y, self.w, self.header_height)
            if header_rect.collidepoint(pos):
                self.toggle()
                return True
        return False

    def draw_button(self, surface):
        label = "Stats ▾" if self.is_open else "Stats ▸"
        pygame.draw.rect(surface, (55, 55, 80), self.btn_rect, border_radius=10)
        pygame.draw.rect(surface, (150, 170, 230), self.btn_rect, 2, border_radius=10)
        ft = pygame.font.Font(None, 24)
        t = ft.render(label, True, WHITE)
        surface.blit(t, (self.btn_rect.centerx - t.get_width() // 2,
                         self.btn_rect.centery - t.get_height() // 2))

    def draw_panel(self, surface, stats):
        panel = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 30, 50, 200), (0, 0, self.w, self.h), border_radius=15)
        pygame.draw.rect(panel, (100, 150, 255, 140), (0, 0, self.w, self.h), 2, border_radius=15)
        surface.blit(panel, (self.x, self.y))

        header_rect = pygame.Rect(self.x, self.y, self.w, self.header_height)
        pygame.draw.rect(surface, (30, 45, 75, 220), header_rect, border_radius=15)

        y = 20
        surface.blit(self.ft_title.render("Hong Kong August 2024 Weather Data", True, WHITE),
                     (self.x + 20, self.y + y))
        y += 40
        for text, col in [
            (f"Sunny: {stats['sunny']} days", BRIGHT_YELLOW),
            (f"Rainy: {stats['rainy']} days", BLUE),
            (f"Cloudy: {stats['cloudy']} days", LIGHT_GRAY),
        ]:
            surface.blit(self.ft_text.render(text, True, col), (self.x + 20, self.y + y))
            y += 28
        y += 8
        for line in [
            f"Average Temp: {stats['avg_temp']:.1f} °C",
            f"Max Temp: {stats['max_temp']:.1f} °C",
            f"Min Temp: {stats['min_temp']:.1f} °C",
        ]:
            surface.blit(self.ft_text.render(line, True, (200, 200, 255)),
                         (self.x + 20, self.y + y))
            y += 24

    def draw(self, surface, stats):
        self.draw_button(surface)
        if self.is_open:
            self.draw_panel(surface, stats)


# ------------------------------ Axes & Layout ------------------------------
def compute_temp_range(weather_data):
    """Compute nice min/max (rounded) for temperature axis."""
    temps = [wd.temperature for wd in weather_data] or [28.0]
    tmin = min(temps)
    tmax = max(temps)
    # Add a small margin and round to integers
    tmin = math.floor(tmin - 0.5)
    tmax = math.ceil(tmax + 0.5)
    if tmax <= tmin:
        tmax = tmin + 1
    return tmin, tmax

def temp_to_y(temp, tmin, tmax):
    """Map temperature to screen Y (higher temp → higher position)."""
    top = AXIS_MARGIN_T
    bottom = SCREEN_HEIGHT - AXIS_MARGIN_B
    ratio = (temp - tmin) / max(0.0001, (tmax - tmin))
    return bottom - ratio * (bottom - top)

def layout_by_date_axis_temp(particles, tmin, tmax):
    """X by date, Y by temperature mapping."""
    if not particles:
        return
    particles.sort(key=lambda p: p.weather_day.date)
    n = len(particles)
    x0 = AXIS_MARGIN_L
    x1 = SCREEN_WIDTH - AXIS_MARGIN_R
    step = (x1 - x0) / max(1, n - 1)
    for i, p in enumerate(particles):
        p.anchor_x = x0 + i * step
        base_y = temp_to_y(p.weather_day.temperature, tmin, tmax)
        p.anchor_y = base_y + random.uniform(-8, 8)

def draw_axes(screen, particles, tmin, tmax):
    axis_color = (190, 200, 220)
    grid_color = (110, 120, 140)

    # Axes positions
    x0, x1 = AXIS_MARGIN_L, SCREEN_WIDTH - AXIS_MARGIN_R
    yx = SCREEN_HEIGHT - AXIS_MARGIN_B   # X-axis Y
    y0, y1 = AXIS_MARGIN_T, SCREEN_HEIGHT - AXIS_MARGIN_B  # Y-axis span

    # Draw axes (thicker for visibility)
    pygame.draw.line(screen, axis_color, (x0, yx), (x1, yx), 3)  # X-axis
    pygame.draw.line(screen, axis_color, (x0, y0), (x0, y1), 3)  # Y-axis

    # X ticks by day
    if particles:
        n = len(particles)
        step = (x1 - x0) / max(1, n - 1)
        ft = pygame.font.Font(None, 22)
        for i, p in enumerate(particles):
            x = x0 + i * step
            pygame.draw.line(screen, axis_color, (x, yx - 7), (x, yx + 7), 2)
            if (i + 1) % 2 == 1:  # label every 2 days
                label = p.weather_day.date.strftime("%m/%d")
                txt = ft.render(label, True, axis_color)
                screen.blit(txt, (x - txt.get_width() // 2, yx + 12))

    # Y ticks by temperature (nice integer step)
    temp_range = tmax - tmin
    step_deg = 1 if temp_range <= 12 else 2
    ftb = pygame.font.Font(None, 22)
    y_ticks = []
    val = tmin
    while val <= tmax + 1e-6:
        y = int(temp_to_y(val, tmin, tmax))
        y_ticks.append((y, val))
        val += step_deg

    for y, v in y_ticks:
        pygame.draw.line(screen, grid_color, (x0, y), (x1, y), 1)
        txt = ftb.render(f"{int(v)}°C", True, axis_color)
        screen.blit(txt, (x0 - 12 - txt.get_width(), y - txt.get_height() // 2))


# -------------------------------- Main --------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Hong Kong August 2024 Weather")
    clock = pygame.time.Clock()

    # Fetch data (with fallback inside data_fetch.py)
    weather_data = fetch_hk_data(2024, 8)
    if not weather_data:
        # Final local fallback if nothing available
        sample = []
        types = ["sunny", "cloudy", "rainy"]
        for i in range(31):
            day = datetime(2024, 8, i + 1)
            temp = 30.0 + ((i % 5) - 2) * 0.7
            wtype = types[i % 3]
            sample.append(WeatherDay(day, temp, wtype))
        weather_data = sample

    # Temperature axis range
    tmin, tmax = compute_temp_range(weather_data)

    # Provide the same range to color normalization
    global TEMP_MIN, TEMP_MAX
    TEMP_MIN, TEMP_MAX = tmin, tmax

    # Particles + layout (X by date, Y by temperature)
    particles = [WeatherParticle(wd) for wd in weather_data]
    layout_by_date_axis_temp(particles, tmin, tmax)

    # Systems
    bg = ArtisticBackground()
    info = InfoPanel(SCREEN_WIDTH - 280, 50, 260, 250)
    subtitle_font = pygame.font.Font(None, 28)

    frame, running = 0, True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.MOUSEBUTTONDOWN:
                info.handle_click(e.pos)

        frame += 1
        mouse = pygame.mouse.get_pos()

        # Update
        bg.update(frame)
        for p in particles:
            p.update(frame, mouse, particles)

        # Draw
        bg.draw(screen)
        draw_axes(screen, particles, tmin, tmax)
        for p in particles:
            p.draw(screen)

        # Stats
        stats = {
            "sunny": sum(1 for p in particles if p.weather_day.weather_type == "sunny"),
            "rainy": sum(1 for p in particles if p.weather_day.weather_type == "rainy"),
            "cloudy": sum(1 for p in particles if p.weather_day.weather_type == "cloudy"),
        }
        n = len(particles)
        stats.update({
            "avg_temp": (sum(p.weather_day.temperature for p in particles) / n) if n else 0.0,
            "max_temp": max((p.weather_day.temperature for p in particles), default=0.0),
            "min_temp": min((p.weather_day.temperature for p in particles), default=0.0),
        })
        info.draw(screen, stats)

        # Minimal hint
        hint = subtitle_font.render("Click 'Stats' button or panel header to collapse/expand; hover particles for details.",
                                    True, (160, 170, 200))
        screen.blit(hint, (30, SCREEN_HEIGHT - 40))

        # Tooltip
        hovered = next((p for p in particles if p.hovered), None)
        if hovered:
            wd = hovered.weather_day
            labels = {"sunny": "Sunny", "rainy": "Rainy", "cloudy": "Cloudy"}
            lines = [
                f"Date: {wd.date.strftime('%B %d, %Y')}",
                f"Mean Temp: {wd.temperature:.1f} °C",
                f"Weather: {labels.get(wd.weather_type, wd.weather_type.title())}",
            ]
            w, h = 240, len(lines) * 24 + 18
            mx, my = mouse
            tx = min(mx + 20, SCREEN_WIDTH - w - 10)
            ty = max(my - h - 20, 10)
            tip = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(tip, (30, 40, 60, 220), (0, 0, w, h), border_radius=10)
            pygame.draw.rect(tip, (100, 150, 255), (0, 0, w, h), 2, border_radius=10)
            screen.blit(tip, (tx, ty))
            for i, line in enumerate(lines):
                t = subtitle_font.render(line, True, WHITE)
                screen.blit(t, (tx + 14, ty + 12 + i * 24))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()