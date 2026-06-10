"""Escena de combate: visual estilo Pokémon.

Pipeline por turno (state machine interno):
    waiting_input → resolving_turn → showing_events → check_faint → next_turn
                                                 ↘ select_replacement →
"""
from __future__ import annotations
import pygame

import config
from src.core import BattleState, Action
from src.core.pokemon import Pokemon, all_species
from src.agents import RandomAgent, HeuristicAgent, HumanAgent, MinimaxAgent  #AGREGADO (MinimaxAgent)
from src.ui import audio
from src.ui.assets_loader import (
    get_font, load_pokemon_sprites, load_pokemon_icon,
    load_random_battle_background,
)
from src.ui.widgets.sprite_animator import SpriteAnimator
from src.ui.widgets.hp_bar import HPBar
from src.ui.widgets.text_box import TextBox
from .base_scene import Scene
from .session import BattleSession
from .move_select_scene import TYPE_COLORS


# Posiciones de sprites (centro)
ENEMY_POS = (700, 200)
PLAYER_POS = (240, 410)

# Tamaño uniforme de los HUDs (jugador y rival)
HUD_W = 320
HUD_H = 76
HUD_TEAM_BAR_H = 32      # franja para los 4 íconos de equipo

# Posiciones de los HUDs
HUD_ENEMY_POS = (32, 32)
# El del jugador va más abajo: pegado a la caja inferior, así no queda
# un hueco enorme entre el HUD y los menús/textbox.
HUD_PLAYER_POS = (config.WINDOW_W - HUD_W - 32, 340)

# Caja inferior unificada: aquí van textbox / main_menu / move_menu / switch_menu
BOTTOM_RECT = pygame.Rect(20, config.WINDOW_H - 168, config.WINDOW_W - 40, 148)


def _build_team(names, movesets) -> list[Pokemon]:
    team = []
    for nm, ms in zip(names, movesets):
        sp = all_species()[nm]
        team.append(Pokemon.build(sp, ms))
    return team


def _agent_for(name: str):
    #AGREGADO Inicio
    if name == "Minimax":
        return MinimaxAgent.from_weights_file()   # carga data/level3_weights.json
    #AGREGADO Fin
    return RandomAgent() if name == "Random" else HeuristicAgent()


class BattleScene(Scene):
    STATE_INPUT = "input"
    STATE_EVENT = "event"
    STATE_FORCE_SWITCH = "force_switch"
    STATE_DONE = "done"

    def __init__(self, session: BattleSession):
        self.session = session
        self.bg = load_random_battle_background((config.WINDOW_W, config.WINDOW_H))

        team_p = _build_team(session.player_team, session.player_movesets)
        team_o = _build_team(session.opp_team, session.opp_movesets)
        self.state = BattleState(team_p, team_o, names=("Tú", "Rival"))

        self.player_agent = HumanAgent()
        self.opp_agent = _agent_for(session.opp_agent)

        self._anim_cache: dict[str, dict] = {}

        # Widgets
        self.text_box = TextBox(BOTTOM_RECT, font_size=20)
        self.player_hp = HPBar(180, 9)
        self.enemy_hp = HPBar(180, 9)
        self.player_hp.set_target(self._hp_ratio(0))
        self.enemy_hp.set_target(self._hp_ratio(1))

        self.menu_mode = "main"   # "main" | "moves" | "switch"
        self.main_cursor = 0
        self.move_cursor = 0
        self.switch_cursor = 0

        self.phase = self.STATE_INPUT
        self.pending_events: list = []

        self._refresh_sprites()
        self._intro_t = 0
        self._intro_done = False

        audio.play_music("battle_wild")
        audio.play_cry(self.state.active_pokemon(1).species.sprite_base)
        self._set_main_text()

    # ─── Helpers de estado ────────────────────────────────────────────────────
    def _hp_ratio(self, side: int) -> float:
        p = self.state.active_pokemon(side)
        return p.hp / p.hp_max if p.hp_max else 0.0

    def _set_main_text(self) -> None:
        active = self.state.active_pokemon(0)
        self.text_box.set_text(f"¿Qué hará {active.name}?")
        self.text_box.skip()

    def _refresh_sprites(self) -> None:
        for side in (0, 1):
            self._ensure_sprites_loaded(self.state.active_pokemon(side))
        self._update_active_animators()

    def _ensure_sprites_loaded(self, pokemon) -> dict:
        if pokemon.name not in self._anim_cache:
            self._anim_cache[pokemon.name] = load_pokemon_sprites(pokemon.species)
        return self._anim_cache[pokemon.name]

    def _update_active_animators(self) -> None:
        p = self.state.active_pokemon(0)
        o = self.state.active_pokemon(1)
        d_p = self._ensure_sprites_loaded(p)
        d_o = self._ensure_sprites_loaded(o)
        self.player_anim = SpriteAnimator(
            d_p["back_frames"] or d_p["front_frames"],
            d_p["back_durations"] or d_p["front_durations"],
            scale=2.5)
        self.enemy_anim = SpriteAnimator(
            d_o["front_frames"] or d_o["back_frames"],
            d_o["front_durations"] or d_o["back_durations"],
            scale=2.0)
        self.player_anim.alpha = 0
        self.enemy_anim.alpha = 0
        self._intro_t = 0
        self._intro_done = False

    # ─── Cálculo de posiciones de menús ───────────────────────────────────────
    def _main_menu_rects(self) -> list[pygame.Rect]:
        # Menú compacto: dos botones apilados (uno sobre otro) a la derecha.
        w = 240
        h = 44
        x = BOTTOM_RECT.right - w - 18
        gap = 10
        total_h = h * 2 + gap
        y_top = BOTTOM_RECT.centery - total_h // 2
        return [pygame.Rect(x, y_top, w, h),
                pygame.Rect(x, y_top + h + gap, w, h)]

    def _main_menu_items(self) -> list[str]:
        return ["Lucha", "Pokémon"]

    def _move_cell_rect(self, i: int) -> pygame.Rect:
        # 2 columnas, 2 filas, ocupando todo BOTTOM_RECT
        col, row = i % 2, i // 2
        cw = (BOTTOM_RECT.w - 16) // 2
        ch = (BOTTOM_RECT.h - 16) // 2
        return pygame.Rect(BOTTOM_RECT.x + 8 + col * (cw + 4),
                           BOTTOM_RECT.y + 8 + row * (ch + 4),
                           cw - 4, ch)

    def _switch_cell_rect(self, i: int) -> pygame.Rect:
        col, row = i % 2, i // 2
        cw = (BOTTOM_RECT.w - 16) // 2
        ch = (BOTTOM_RECT.h - 16) // 2
        return pygame.Rect(BOTTOM_RECT.x + 8 + col * (cw + 4),
                           BOTTOM_RECT.y + 8 + row * (ch + 4),
                           cw - 4, ch)

    def _move_disabled(self, i: int) -> bool:
        active = self.state.active_pokemon(0)
        return i >= len(active.moves) or active.pp[i] <= 0

    def _switch_disabled(self, i: int, force: bool) -> bool:
        team = self.state.teams[0]
        if i >= len(team):
            return True
        p = team[i]
        if p.is_fainted:
            return True
        if i == self.state.active[0] and not force:
            return True
        return False

    # ─── Eventos ──────────────────────────────────────────────────────────────
    def handle_event(self, ev) -> None:
        if self.phase == self.STATE_DONE:
            if ev.type == pygame.KEYDOWN or ev.type == pygame.MOUSEBUTTONDOWN:
                from .menu_scene import MenuScene
                self.next = MenuScene(self.session)
                self.done = True
            return

        if self.phase == self.STATE_EVENT:
            if (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z)) \
               or ev.type == pygame.MOUSEBUTTONDOWN:
                if not self.text_box.is_done:
                    self.text_box.skip()
                else:
                    self._advance_event()
            return

        if self.phase == self.STATE_FORCE_SWITCH:
            self._handle_switch_event(ev, force=True)
            return

        if self.phase == self.STATE_INPUT:
            if self.menu_mode == "main":
                self._handle_main_event(ev)
            elif self.menu_mode == "moves":
                self._handle_moves_event(ev)
            elif self.menu_mode == "switch":
                self._handle_switch_event(ev, force=False)

    def _handle_main_event(self, ev) -> None:
        items = self._main_menu_items()
        n = len(items)
        if ev.type == pygame.KEYDOWN:
            # Botones apilados: UP/DOWN navega; LEFT/RIGHT también funciona.
            if ev.key in (pygame.K_DOWN, pygame.K_s, pygame.K_RIGHT, pygame.K_d):
                self.main_cursor = (self.main_cursor + 1) % n
            elif ev.key in (pygame.K_UP, pygame.K_w, pygame.K_LEFT, pygame.K_a):
                self.main_cursor = (self.main_cursor - 1) % n
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                self._main_select(self.main_cursor)
        elif ev.type == pygame.MOUSEMOTION:
            for i in range(n):
                if self._main_menu_rects()[i].collidepoint(ev.pos):
                    self.main_cursor = i
                    break
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i in range(n):
                if self._main_menu_rects()[i].collidepoint(ev.pos):
                    self._main_select(i)
                    return

    def _main_select(self, idx: int) -> None:
        audio.play_sfx("select")
        if idx == 0:
            self.move_cursor = 0
            self.menu_mode = "moves"
        elif idx == 1:
            self.switch_cursor = 0
            self.menu_mode = "switch"
            # Si todos los demás están caídos: aviso y vuelta
            team = self.state.teams[0]
            others_alive = any(
                (not p.is_fainted) and i != self.state.active[0]
                for i, p in enumerate(team))
            if not others_alive:
                self.menu_mode = "main"
                self.text_box.set_text("¡No quedan otros Pokémon!")

    def _handle_moves_event(self, ev) -> None:
        n = 4
        cols = 2
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.menu_mode = "main"
                return
            if ev.key in (pygame.K_RIGHT, pygame.K_d):  self.move_cursor = (self.move_cursor + 1) % n
            elif ev.key in (pygame.K_LEFT, pygame.K_a): self.move_cursor = (self.move_cursor - 1) % n
            elif ev.key in (pygame.K_DOWN, pygame.K_s): self.move_cursor = (self.move_cursor + cols) % n
            elif ev.key in (pygame.K_UP, pygame.K_w):   self.move_cursor = (self.move_cursor - cols) % n
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                self._move_select(self.move_cursor)
        elif ev.type == pygame.MOUSEMOTION:
            for i in range(n):
                if self._move_cell_rect(i).collidepoint(ev.pos):
                    self.move_cursor = i; break
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i in range(n):
                if self._move_cell_rect(i).collidepoint(ev.pos):
                    self._move_select(i); return

    def _move_select(self, idx: int) -> None:
        if self._move_disabled(idx):
            return
        audio.play_sfx("select")
        self.player_agent.set_pending(Action.attack(idx))
        self._begin_resolve()

    def _handle_switch_event(self, ev, force: bool) -> None:
        team = self.state.teams[0]
        n = max(len(team), 4)
        cols = 2
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE and not force:
                self.menu_mode = "main"
                return
            if ev.key in (pygame.K_RIGHT, pygame.K_d):  self.switch_cursor = (self.switch_cursor + 1) % n
            elif ev.key in (pygame.K_LEFT, pygame.K_a): self.switch_cursor = (self.switch_cursor - 1) % n
            elif ev.key in (pygame.K_DOWN, pygame.K_s): self.switch_cursor = (self.switch_cursor + cols) % n
            elif ev.key in (pygame.K_UP, pygame.K_w):   self.switch_cursor = (self.switch_cursor - cols) % n
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                self._switch_select(self.switch_cursor, force)
        elif ev.type == pygame.MOUSEMOTION:
            for i in range(n):
                if self._switch_cell_rect(i).collidepoint(ev.pos):
                    self.switch_cursor = i; break
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i in range(n):
                if self._switch_cell_rect(i).collidepoint(ev.pos):
                    self._switch_select(i, force); return

    def _switch_select(self, idx: int, force: bool) -> None:
        if self._switch_disabled(idx, force):
            return
        audio.play_sfx("select")
        if force:
            self._do_force_switch(idx)
        else:
            self.player_agent.set_pending(Action.switch(idx))
            self._begin_resolve()

    # ─── Lógica de turno ──────────────────────────────────────────────────────
    def _begin_resolve(self) -> None:
        opp_action = self.opp_agent.choose_action(self.state, side=1)
        player_action = self.player_agent.take_pending()
        events = self.state.step(player_action, opp_action)
        self.pending_events = events
        self.phase = self.STATE_EVENT
        self._show_next_event()

    def _show_next_event(self) -> None:
        if not self.pending_events:
            self._after_events()
            return
        ev = self.pending_events.pop(0)
        self.text_box.set_text(ev.text)
        if ev.kind == "damage":
            target_side = ev.data["side"]
            (self.player_hp if target_side == 0 else self.enemy_hp).set_target(
                ev.data["hp_now"] / max(1, ev.data["hp_max"]))
            (self.player_anim if target_side == 0 else self.enemy_anim).shake(10, 0.4)
            eff = 1.0
            for upcoming in self.pending_events:
                if upcoming.kind == "eff":
                    eff = upcoming.data.get("mult", 1.0); break
                if upcoming.kind in ("use_move", "switch_in", "switch_out"):
                    break
            audio.play_hit(eff)
        elif ev.kind == "switch_in":
            self._update_active_animators()
            side = ev.data["side"]
            new_p = self.state.active_pokemon(side)
            new_ratio = new_p.hp / max(1, new_p.hp_max)
            bar = self.player_hp if side == 0 else self.enemy_hp
            bar.shown_ratio = new_ratio
            bar.target_ratio = new_ratio
            audio.play_cry(new_p.species.sprite_base)
        elif ev.kind == "faint":
            (self.player_anim if ev.data["side"] == 0 else self.enemy_anim).alpha = 80
            audio.play_sfx("faint")

    def _advance_event(self) -> None:
        if not (self.player_hp.is_settled and self.enemy_hp.is_settled):
            return
        if self.pending_events:
            self._show_next_event()
        else:
            self._after_events()

    def _after_events(self) -> None:
        if self.state.is_over():
            self._end_battle(); return
        if self.state.pending_switch[0]:
            self.switch_cursor = 0
            self.text_box.set_text("¡Elige tu siguiente Pokémon!")
            self.phase = self.STATE_FORCE_SWITCH
            return
        if self.state.pending_switch[1]:
            choice = self.opp_agent.choose_forced_switch(self.state, 1)
            self.pending_events = self.state.force_switch(1, choice.switch_to)
            self.phase = self.STATE_EVENT
            self._show_next_event(); return
        self.phase = self.STATE_INPUT
        self.menu_mode = "main"
        self._set_main_text()

    def _do_force_switch(self, idx: int) -> None:
        evs = self.state.force_switch(0, idx)
        self.pending_events = evs
        self.phase = self.STATE_EVENT
        self._show_next_event()

    def _end_battle(self) -> None:
        winner = self.state.winner()
        self.text_box.set_text("¡Has ganado!" if winner == 0 else "Has perdido...")
        self.phase = self.STATE_DONE
        audio.stop_music()
        audio.play_music("victory" if winner == 0 else "defeat", loop=False)

    # ─── Tick ─────────────────────────────────────────────────────────────────
    def update(self, dt_ms: int) -> None:
        self.text_box.update(dt_ms)
        self.player_hp.update(dt_ms)
        self.enemy_hp.update(dt_ms)
        self.player_anim.update(dt_ms)
        self.enemy_anim.update(dt_ms)
        if not self._intro_done:
            self._intro_t += dt_ms
            f = min(1.0, self._intro_t / 500)
            self.player_anim.alpha = int(255 * f)
            self.enemy_anim.alpha = int(255 * f)
            if f >= 1.0:
                self._intro_done = True

    # ═══ DIBUJO ═══════════════════════════════════════════════════════════════
    def draw(self, surf) -> None:
        surf.blit(self.bg, (0, 0))
        # Sprites
        self.enemy_anim.draw(surf, ENEMY_POS)
        self.player_anim.draw(surf, PLAYER_POS)
        # HUDs uniformes
        self._draw_hud(surf, side=1, topleft=HUD_ENEMY_POS)
        self._draw_hud(surf, side=0, topleft=HUD_PLAYER_POS, show_hp_text=True)
        # Caja inferior
        if self.phase == self.STATE_INPUT and self.menu_mode == "main":
            self.text_box.draw(surf)
            self._draw_main_menu(surf)
        elif self.phase == self.STATE_INPUT and self.menu_mode == "moves":
            self._draw_move_menu(surf)
        elif self.phase == self.STATE_INPUT and self.menu_mode == "switch":
            self._draw_switch_menu(surf, force=False)
        elif self.phase == self.STATE_FORCE_SWITCH:
            self._draw_switch_menu(surf, force=True)
        else:
            self.text_box.draw(surf)
        # Pantalla final
        if self.phase == self.STATE_DONE:
            self._draw_end_overlay(surf)

    # ─── HUD uniforme ─────────────────────────────────────────────────────────
    def _draw_hud(self, surf, side: int, topleft: tuple[int, int],
                  show_hp_text: bool = False) -> None:
        team = self.state.teams[side]
        active_idx = self.state.active[side]
        p = team[active_idx]
        rect = pygame.Rect(topleft[0], topleft[1], HUD_W, HUD_H)
        # Fondo del HUD principal
        pygame.draw.rect(surf, (250, 248, 232), rect, border_radius=10)
        pygame.draw.rect(surf, (60, 50, 30), rect, width=3, border_radius=10)

        # Nombre arriba-izquierda
        name = get_font(16, bold=True).render(p.name, True, (40, 40, 60))
        surf.blit(name, (rect.x + 10, rect.y + 8))
        # Tags de tipo arriba-derecha. Anchos según longitud del nombre del tipo.
        x = rect.right - 8
        for t in reversed(p.types):
            color = TYPE_COLORS.get(t, (200, 200, 200))
            tw = max(58, len(t) * 8 + 10)  # se adapta a "Eléctrico", "Siniestro"
            tag = pygame.Rect(x - tw, rect.y + 8, tw - 4, 18)
            pygame.draw.rect(surf, color, tag, border_radius=9)
            pygame.draw.rect(surf, (40, 40, 40), tag, width=1, border_radius=9)
            tr = get_font(9).render(t, True, (255, 255, 255))
            surf.blit(tr, (tag.centerx - tr.get_width() // 2,
                           tag.centery - tr.get_height() // 2))
            x -= tw + 4
        # Etiqueta HP
        hp_lbl = get_font(10, bold=True).render("HP", True, (60, 60, 80))
        surf.blit(hp_lbl, (rect.x + 10, rect.y + 32))
        # Barra HP
        bar = self.player_hp if side == 0 else self.enemy_hp
        bar.draw(surf, (rect.x + 38, rect.y + 36))
        # Texto HP/HP_max (sólo del jugador)
        if show_hp_text:
            txt = get_font(11, bold=True).render(f"{p.hp}/{p.hp_max}", True, (40, 40, 60))
            surf.blit(txt, (rect.right - txt.get_width() - 10, rect.y + 50))

        # Iconos del equipo justo debajo del HUD, sin cinta de fondo.
        icon_size = 32
        n = len(team)
        spacing = 10
        total_w = n * icon_size + (n - 1) * spacing
        ix0 = rect.x + (rect.w - total_w) // 2  # centrados respecto al HUD
        iy = rect.bottom + 6
        for i, pk in enumerate(team):
            ix = ix0 + i * (icon_size + spacing)
            icon = load_pokemon_icon(pk.species, size=icon_size)
            if pk.is_fainted:
                # Silueta casi negra (multiplicar canal RGB por gris muy oscuro).
                tinted = icon.copy()
                tinted.fill((40, 40, 40, 255), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(tinted, (ix, iy))
            else:
                surf.blit(icon, (ix, iy))

    # ─── Menús ────────────────────────────────────────────────────────────────
    def _draw_main_menu(self, surf) -> None:
        items = self._main_menu_items()
        rects = self._main_menu_rects()
        for i, (label, r) in enumerate(zip(items, rects)):
            sel = (i == self.main_cursor)
            bg = (255, 220, 130) if sel else (250, 248, 232)
            pygame.draw.rect(surf, bg, r, border_radius=10)
            pygame.draw.rect(surf, (60, 50, 30), r, width=3, border_radius=10)
            color = (40, 40, 60)
            txt = get_font(15, bold=True).render(label, True, color)
            surf.blit(txt, (r.centerx - txt.get_width() // 2,
                            r.centery - txt.get_height() // 2))
            if sel:
                pygame.draw.polygon(surf, (220, 60, 40),
                    [(r.x + 6, r.centery), (r.x + 14, r.centery - 6), (r.x + 14, r.centery + 6)])

    def _draw_move_menu(self, surf) -> None:
        active = self.state.active_pokemon(0)
        for i in range(4):
            r = self._move_cell_rect(i)
            mv = active.moves[i] if i < len(active.moves) else None
            sel = (i == self.move_cursor)
            disabled = self._move_disabled(i)
            bg = (255, 220, 130) if sel else (250, 248, 232)
            if disabled:
                bg = (200, 200, 200)
            pygame.draw.rect(surf, bg, r, border_radius=10)
            pygame.draw.rect(surf, (60, 50, 30), r, width=3, border_radius=10)
            if mv is None:
                continue
            pad_x = 14
            row_y = r.y + 12
            # Tag tipo
            type_color = TYPE_COLORS.get(mv.type, (200, 200, 200))
            tag = pygame.Rect(r.x + pad_x, row_y, 78, 20)
            pygame.draw.rect(surf, type_color, tag, border_radius=10)
            pygame.draw.rect(surf, (40, 40, 60), tag, width=1, border_radius=10)
            tg = get_font(9).render(mv.type, True, (255, 255, 255))
            surf.blit(tg, (tag.centerx - tg.get_width() // 2,
                           tag.centery - tg.get_height() // 2))
            # Tag categoría — usamos abreviatura para no recortarse
            cat_tag = pygame.Rect(tag.right + 6, row_y, 44, 20)
            cat_col = (210, 80, 80) if mv.category == "physical" else (80, 130, 210)
            pygame.draw.rect(surf, cat_col, cat_tag, border_radius=10)
            pygame.draw.rect(surf, (40, 40, 60), cat_tag, width=1, border_radius=10)
            cat = "Fis" if mv.category == "physical" else "Esp"
            cr = get_font(10, bold=True).render(cat, True, (255, 255, 255))
            surf.blit(cr, (cat_tag.centerx - cr.get_width() // 2,
                           cat_tag.centery - cr.get_height() // 2))
            # PP a la derecha del cell, en la misma fila que los tags
            pp_text = f"PP {active.pp[i]}/{mv.pp}"
            pp_r = get_font(11, bold=True).render(pp_text, True, (60, 60, 80))
            surf.blit(pp_r, (r.right - pp_r.get_width() - 14, row_y + 3))
            # Nombre del mov, debajo de los tags
            nm = get_font(15, bold=True).render(mv.name, True, (40, 40, 60))
            surf.blit(nm, (r.x + pad_x, row_y + 26))
            # Power y Accuracy en la última fila
            stats = f"Pot {mv.power}    Prec {mv.accuracy}"
            ss = get_font(11).render(stats, True, (60, 60, 80))
            surf.blit(ss, (r.x + pad_x, r.bottom - ss.get_height() - 8))

    def _draw_switch_menu(self, surf, force: bool) -> None:
        team = self.state.teams[0]
        for i in range(4):
            r = self._switch_cell_rect(i)
            sel = (i == self.switch_cursor)
            disabled = self._switch_disabled(i, force) if i < len(team) else True
            bg = (255, 220, 130) if sel else (250, 248, 232)
            if disabled:
                bg = (200, 200, 200)
            pygame.draw.rect(surf, bg, r, border_radius=10)
            pygame.draw.rect(surf, (60, 50, 30), r, width=3, border_radius=10)
            if i >= len(team):
                continue
            p = team[i]
            # Icono pixel a la izquierda
            icon = load_pokemon_icon(p.species, size=r.h - 18)
            ix = r.x + 8
            iy = r.centery - icon.get_height() // 2
            if p.is_fainted:
                tinted = icon.copy()
                tinted.fill((40, 40, 40, 130), special_flags=pygame.BLEND_RGBA_MULT)
                surf.blit(tinted, (ix, iy))
            else:
                surf.blit(icon, (ix, iy))
            # Nombre
            text_x = ix + icon.get_width() + 12
            nm = get_font(14, bold=True).render(p.name, True, (40, 40, 60))
            surf.blit(nm, (text_x, r.y + 8))
            # Tag activo o caído
            label_tag = None
            if i == self.state.active[0]:
                label_tag = ("EN PISTA", (90, 130, 200))
            elif p.is_fainted:
                label_tag = ("DEBIL", (130, 130, 130))
            if label_tag:
                tx, tcol = label_tag
                tag = pygame.Rect(r.right - 88, r.y + 10, 76, 16)
                pygame.draw.rect(surf, tcol, tag, border_radius=8)
                tr = get_font(9).render(tx, True, (255, 255, 255))
                surf.blit(tr, (tag.centerx - tr.get_width() // 2,
                               tag.centery - tr.get_height() // 2))
            # HP texto + barra mini
            hp_t = get_font(11).render(f"HP {p.hp}/{p.hp_max}", True, (60, 60, 80))
            surf.blit(hp_t, (text_x, r.y + 32))
            track = pygame.Rect(text_x, r.y + 50, r.right - text_x - 12, 8)
            pygame.draw.rect(surf, (210, 200, 180), track, border_radius=4)
            ratio = p.hp / max(1, p.hp_max)
            fill = pygame.Rect(track.x, track.y, int(track.w * ratio), track.h)
            color = (96, 200, 96) if ratio > 0.5 else ((240, 200, 64) if ratio > 0.2 else (224, 64, 64))
            pygame.draw.rect(surf, color, fill, border_radius=4)
            pygame.draw.rect(surf, (60, 50, 30), track, width=1, border_radius=4)

    def _draw_end_overlay(self, surf) -> None:
        overlay = pygame.Surface((config.WINDOW_W, config.WINDOW_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 110))
        surf.blit(overlay, (0, 0))
        winner = self.state.winner()
        big = get_font(40, bold=True).render(
            "Victoria" if winner == 0 else "Derrota",
            True, (255, 245, 200))
        surf.blit(big, ((config.WINDOW_W - big.get_width()) // 2, 220))
        self.text_box.draw(surf)
        tip = get_font(11).render("Pulsa cualquier tecla para volver al menú",
                                  True, (240, 240, 240))
        surf.blit(tip, ((config.WINDOW_W - tip.get_width()) // 2, config.WINDOW_H - 40))
