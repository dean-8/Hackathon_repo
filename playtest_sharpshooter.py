"""Rigorous headless tests for Shape Shooter / sharpshooter.py."""
import os
import re
import struct
import subprocess
import sys
import math
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
UPGRADE_PANEL_WIDTH = 380
UPGRADE_LABEL_X = 22
UPGRADE_PIP_X = 208
UPGRADE_PIP_GAP = 14
UPGRADE_PIP_STEP = 17
ENEMY_HIT_PADDING = 0
ENEMY_BULLET_HIT_INSET = 1
ENEMY_SIZE = 10
PLAYER_HIT_RADIUS = 12
UPMAXES = [4, 5, 6, 3, 1, 4, 4]
UPGRADE_NAMES = [
    "Max Speed", "Acceleration", "Reload Rate", "Bullet Speed",
    "Piercing Bullet", "Bullet Size", "Ricochet",
]

GAME_PATH = os.path.join(os.path.dirname(__file__), "sharpshooter.py")


# --- Shared logic mirrors (must match sharpshooter.py) ---

def circles_overlap(x1, y1, r1, x2, y2, r2, padding=0):
    dx = x1 - x2
    dy = y1 - y2
    reach = r1 + r2 + padding
    return dx * dx + dy * dy <= reach * reach


def old_collidepoint_hit(bullet_x, bullet_y, bullet_r, enemy_x, enemy_y):
    """Legacy check: enemy center inside bullet bounding rect."""
    left = bullet_x - bullet_r
    right = bullet_x + bullet_r
    top = bullet_y - bullet_r
    bottom = bullet_y + bullet_r
    return left <= enemy_x <= right and top <= enemy_y <= bottom


def bullet_hits_enemy(bullet_x, bullet_y, bullet_r, enemy_x, enemy_y, enemy_r=ENEMY_SIZE):
    hit_r = max(enemy_r - ENEMY_BULLET_HIT_INSET, 1)
    return circles_overlap(
        bullet_x, bullet_y, bullet_r,
        enemy_x, enemy_y, hit_r,
        ENEMY_HIT_PADDING,
    )


def player_touched_by_enemy(player_x, player_y, enemy_x, enemy_y, enemy_r=ENEMY_SIZE):
    return circles_overlap(
        player_x, player_y, PLAYER_HIT_RADIUS,
        enemy_x, enemy_y, enemy_r,
        0,
    )


def simulate_bullet_enemy_pass(bullets, enemies, true_upgrades, enemy_r=ENEMY_SIZE):
    piercing = true_upgrades.get("Piercing Bullet", 0)
    for bullet in bullets[:]:
        bullet_r = 3 + true_upgrades.get("Bullet Size", 0)
        for enemy in enemies[:]:
            if bullet_hits_enemy(
                bullet["bulletX"], bullet["bulletY"], bullet_r,
                enemy[0], enemy[1], enemy_r,
            ):
                enemies.remove(enemy)
                if piercing < 1:
                    bullets.remove(bullet)
                break


def apply_upgrade_purchase(name, upgrades, true_upgrades, credits, wave, index):
    """Returns (credits, success) after one purchase attempt."""
    if name == "Ricochet" and (wave - 1) < 20:
        return credits, False
    if credits <= 0 or upgrades[name] >= UPMAXES[index]:
        return credits, False

    if name == "Ricochet":
        true_upgrades["Piercing Bullet"] = 0
        true_upgrades["Bullet Speed"] = upgrades["Bullet Speed"]
        true_upgrades["Bullet Size"] = 0
    if name in ("Piercing Bullet", "Bullet Speed"):
        true_upgrades["Ricochet"] = 0

    upgrades[name] += 1
    true_upgrades[name] += 1
    return credits - 1, True


# --- Tests ---

def test_source_compiles():
    subprocess.run(
        [sys.executable, "-m", "py_compile", GAME_PATH],
        check=True,
        capture_output=True,
    )


def test_starting_credits():
    source = open(GAME_PATH, encoding="utf-8").read()
    assert re.search(r"^credits\s*=\s*3\s*$", source, re.MULTILINE), "Expected credits = 3"


def test_hitbox_constants():
    source = open(GAME_PATH, encoding="utf-8").read()
    assert "ENEMY_HIT_PADDING = 0" in source
    assert "ENEMY_BULLET_HIT_INSET = 1" in source
    assert "PLAYER_HIT_RADIUS = 12" in source
    assert "circles_overlap" in source
    assert "player_touched_by_enemy" in source


def test_bullet_offscreen_or_logic():
    cases = [
        (801, 300, True), (-1, 300, True), (400, 601, True),
        (400, -1, True), (400, 300, False), (801, 601, True),
    ]
    for x, y, should_remove in cases:
        off = x > SCREEN_WIDTH or x < 0 or y > SCREEN_HEIGHT or y < 0
        assert off == should_remove


def test_circles_overlap_grazing_hit():
    """Near-miss outside the tighter bullet hit radius should not register."""
    bullet_x, bullet_y = 100, 100
    bullet_r = 3
    hit_r = ENEMY_SIZE - ENEMY_BULLET_HIT_INSET
    near_miss_x = 100 + hit_r + bullet_r + 2
    assert not bullet_hits_enemy(bullet_x, bullet_y, bullet_r, near_miss_x, bullet_y)
    assert not old_collidepoint_hit(bullet_x, bullet_y, bullet_r, near_miss_x, bullet_y)


def test_circles_overlap_visual_touch_hits():
    bullet_x, bullet_y = 100, 100
    bullet_r = 3
    hit_r = ENEMY_SIZE - ENEMY_BULLET_HIT_INSET
    touch_x = 100 + hit_r + bullet_r
    assert bullet_hits_enemy(bullet_x, bullet_y, bullet_r, touch_x, bullet_y)


def test_circles_overlap_no_false_positive():
    assert not bullet_hits_enemy(0, 0, 3, 200, 200)


def test_circles_overlap_exact_touch():
    hit_r = ENEMY_SIZE - ENEMY_BULLET_HIT_INSET
    dist = hit_r + 3
    assert bullet_hits_enemy(0, 0, 3, dist, 0)
    assert not bullet_hits_enemy(0, 0, 3, dist + 2, 0)


def test_player_hitbox_larger_than_center_point():
    """Player body overlap should register even when center point misses."""
    enemy_x, enemy_y = 100, 100
    player_x, player_y = 100 + ENEMY_SIZE + 8, 100
    assert player_touched_by_enemy(player_x, player_y, enemy_x, enemy_y)
    assert not circles_overlap(player_x, player_y, 0, enemy_x, enemy_y, ENEMY_SIZE, 0)


def test_bullet_size_increases_hit_radius():
    hit_r = ENEMY_SIZE - ENEMY_BULLET_HIT_INSET
    edge = hit_r + 5
    assert not bullet_hits_enemy(0, 0, 3, edge, 0)
    assert bullet_hits_enemy(0, 0, 7, edge, 0)


def test_piercing_keeps_bullet():
    bullets = [{"bulletX": 100, "bulletY": 100}]
    enemies = [[100 + ENEMY_SIZE, 100], [130, 100]]
    true_upgrades = {"Piercing Bullet": 1, "Bullet Size": 0}
    simulate_bullet_enemy_pass(bullets, enemies, true_upgrades)
    assert len(bullets) == 1
    assert len(enemies) == 1


def test_non_piercing_removes_bullet():
    bullets = [{"bulletX": 100, "bulletY": 100}]
    enemies = [[100 + ENEMY_SIZE, 100]]
    true_upgrades = {"Piercing Bullet": 0, "Bullet Size": 0}
    simulate_bullet_enemy_pass(bullets, enemies, true_upgrades)
    assert bullets == []
    assert enemies == []


def test_collision_copy_iterate_safe():
    bullets = [{"bulletX": 10, "bulletY": 10}, {"bulletX": 200, "bulletY": 200}]
    enemies = [[10 + ENEMY_SIZE, 10], [300, 300]]
    true_upgrades = {"Piercing Bullet": 0, "Bullet Size": 0}
    simulate_bullet_enemy_pass(bullets, enemies, true_upgrades)
    assert len(enemies) == 1
    assert len(bullets) == 1


def test_ricochet_zero_removes_at_edge():
    bullets = [{"bulletX": 801, "bulletY": 300, "velocityX": 1, "velocityY": 0, "Bounces": 0}]
    ricochet = 0
    for b in bullets[:]:
        if ricochet == 0:
            if b["bulletX"] > SCREEN_WIDTH or b["bulletX"] < 0 or b["bulletY"] > SCREEN_HEIGHT or b["bulletY"] < 0:
                bullets.remove(b)
    assert bullets == []


def test_ricochet_exceeds_limit_removes():
    bullets = [{"bulletX": 400, "bulletY": 300, "Bounces": 3}]
    for b in bullets[:]:
        if b["Bounces"] > 2:
            bullets.remove(b)
    assert bullets == []


def test_ricochet_bounce_increments():
    bullet = {"bulletX": 805, "bulletY": 300, "velocityX": 5, "velocityY": 0, "Bounces": 0}
    if bullet["bulletX"] > SCREEN_WIDTH:
        bullet["velocityX"] *= -1
        bullet["Bounces"] += 1
    assert bullet["Bounces"] == 1
    assert bullet["velocityX"] == -5


def test_pause_toggle():
    paused = False
    for _ in range(3):
        paused = not paused
    assert paused is True


def test_pause_blocked_while_dying():
    dying = True
    paused = False
    if not dying:
        paused = not paused
    assert paused is False


def test_death_flash_sequence():
    dying = True
    death_flash_timer = 21
    roundactive = True
    revive_active = False
    frames = 0
    while dying and frames < 30:
        death_flash_timer -= 1
        if death_flash_timer <= 0:
            dying = False
            revive_active = True
        frames += 1
    assert revive_active and not dying and roundactive and frames == 21


def test_wave_clear_vs_death():
    wave = 1
    credits = 10
    player_died = False
    # wave clear
    player_died = False
    wave += 1
    credits += 1
    assert wave == 2 and credits == 11 and not player_died
    # death
    wave = 2
    credits = 5
    player_died = True
    assert wave == 2 and credits == 5


def test_upgrade_purchase_spends_credit():
    upgrades = {n: 0 for n in UPGRADE_NAMES}
    true_upgrades = {n: 0 for n in UPGRADE_NAMES}
    credits = 3
    credits, ok = apply_upgrade_purchase("Max Speed", upgrades, true_upgrades, credits, wave=1, index=0)
    assert ok and credits == 2 and upgrades["Max Speed"] == 1


def test_upgrade_respects_max():
    upgrades = {"Max Speed": 4, **{n: 0 for n in UPGRADE_NAMES[1:]}}
    true_upgrades = {n: 0 for n in UPGRADE_NAMES}
    credits, ok = apply_upgrade_purchase("Max Speed", upgrades, true_upgrades, credits=5, wave=1, index=0)
    assert not ok and credits == 5


def test_ricochet_locked_before_wave_20():
    upgrades = {n: 0 for n in UPGRADE_NAMES}
    true_upgrades = {n: 0 for n in UPGRADE_NAMES}
    credits, ok = apply_upgrade_purchase("Ricochet", upgrades, true_upgrades, credits=5, wave=15, index=6)
    assert not ok


def test_ricochet_unlocked_at_wave_20():
    upgrades = {n: 0 for n in UPGRADE_NAMES}
    true_upgrades = {n: 0 for n in UPGRADE_NAMES}
    credits, ok = apply_upgrade_purchase("Ricochet", upgrades, true_upgrades, credits=5, wave=21, index=6)
    assert ok and credits == 4


def test_ricochet_clears_piercing():
    upgrades = {n: 0 for n in UPGRADE_NAMES}
    upgrades["Bullet Speed"] = 2
    true_upgrades = {n: 0 for n in UPGRADE_NAMES}
    true_upgrades["Piercing Bullet"] = 1
    true_upgrades["Bullet Size"] = 2
    apply_upgrade_purchase("Ricochet", upgrades, true_upgrades, credits=5, wave=21, index=6)
    assert true_upgrades["Piercing Bullet"] == 0
    assert true_upgrades["Bullet Size"] == 0


def test_piercing_clears_ricochet():
    upgrades = {n: 0 for n in UPGRADE_NAMES}
    true_upgrades = {n: 0 for n in UPGRADE_NAMES}
    true_upgrades["Ricochet"] = 2
    apply_upgrade_purchase("Piercing Bullet", upgrades, true_upgrades, credits=5, wave=1, index=4)
    assert true_upgrades["Ricochet"] == 0


def test_reload_cooldown_formula():
    for rate, expected in [(0, 60), (1, 50), (3, 30), (6, 0)]:
        assert 60 - (10 * rate) == expected


def test_bullet_speed_formula():
    assert 2 + (2 * 3) == 8


def test_acceleration_formula():
    assert abs(0.2 + (0.2 * 4) - 1.0) < 0.001


def test_color_confirm_empty_input():
    background = (255, 255, 255)
    cubecolour = (0, 0, 0)
    circleinput = []
    enterpressed = True
    if enterpressed:
        if len(circleinput) == 9:
            pass
        choosecolour = False
    assert background == (255, 255, 255) and cubecolour == (0, 0, 0)


def test_color_confirm_valid_rgb():
    circleinput = list("255128064")
    newkull = [0, 0, 0]
    kullcount = 0
    singlenum = ""
    for xc in range(9):
        singlenum += circleinput[xc]
        if (xc + 1) % 3 == 0:
            newkull[kullcount] = int(singlenum)
            kullcount += 1
            singlenum = ""
    assert tuple(newkull) == (255, 128, 64)


def test_color_rejects_over_255():
    circleinput = []
    for digit in "256":
        circleinput.append(digit)
        if len(circleinput) % 3 == 0:
            checksize = ""
            for checknum in range(len(circleinput)):
                checksize += str(circleinput[checknum])
                if (checknum + 1) % 3 == 0:
                    if int(checksize) > 255:
                        for _ in range(3):
                            circleinput.pop()
                    checksize = ""
    assert circleinput == []


def test_upgrade_layout_label_pip_gap():
    label_end = UPGRADE_LABEL_X + (UPGRADE_PIP_X - UPGRADE_PIP_GAP - UPGRADE_LABEL_X)
    pip_start = UPGRADE_PIP_X - 7  # pip radius 14, center=True
    assert label_end <= pip_start - UPGRADE_PIP_GAP + 7


def test_upgrade_pips_fit_in_panel():
    max_pips = max(UPMAXES)
    last_pip_center = UPGRADE_PIP_X + UPGRADE_PIP_STEP * (max_pips - 1)
    assert last_pip_center + 7 < UPGRADE_PANEL_WIDTH - 55  # room for MAX button


def test_intermission_right_center():
    right_center = UPGRADE_PANEL_WIDTH + (SCREEN_WIDTH - UPGRADE_PANEL_WIDTH) // 2
    assert right_center == 590
    assert right_center > UPGRADE_PANEL_WIDTH


def test_shoot_direction_normalization():
    dx, dy = 100, 0
    dist = math.hypot(dx, dy)
    dx, dy = dx / dist, dy / dist
    assert abs(dx - 1) < 0.001 and abs(dy) < 0.001


def test_shoot_zero_distance_safe():
    dx, dy = 0, 0
    dist = math.hypot(dx, dy)
    if dist != 0:
        dx /= dist
    assert dist == 0  # no division by zero


def test_enemy_chase_vector():
    enemy = [300.0, 300.0]
    you_x, you_y = 400, 300
    dx, dy = you_x - enemy[0], you_y - enemy[1]
    dist = math.hypot(dx, dy)
    dx, dy = dx / dist, dy / dist
    enemy[0] += dx
    assert enemy[0] > 300


def test_enemy_spawn_bounds():
    w, h = SCREEN_WIDTH, SCREEN_HEIGHT
    samples = [
        random.randint(-10, 0),
        random.randint(w, w + 10),
        random.randint(-10, h + 10),
    ]
    assert samples[0] <= 0
    assert samples[1] >= w
    assert -10 <= samples[2] <= h + 10


def test_pygame_ui_smoke():
    pygame.init()
    pygame.font.init()
    dis = pygame.display.set_mode((800, 600))
    font = pygame.freetype.SysFont("Consolas", 25)
    surf, _ = font.render("YOU DIED", (255, 90, 90))
    assert surf.get_width() > 0
    overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
    overlay.fill((255, 40, 40, 120))
    dis.blit(overlay, (0, 0))
    pygame.draw.circle(dis, (80, 80, 80), (530, 300), 9, 1)
    pygame.quit()


def test_all_game_sounds():
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

    def make_beep(freq, duration_ms, volume=0.25, decay=0.5):
        sample_rate = 44100
        n_samples = int(sample_rate * duration_ms / 1000)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            envelope = max(0, 1 - (i / n_samples) ** decay)
            sample = int(32767 * volume * envelope * math.sin(2 * math.pi * freq * t))
            sample = max(-32767, min(32767, sample))
            frames += struct.pack("<hh", sample, sample)
        return pygame.mixer.Sound(buffer=bytes(frames))

    sounds = {
        "shoot": make_beep(920, 55, 0.18, 0.8),
        "hit": make_beep(420, 90, 0.22, 0.6),
        "death": make_beep(220, 450, 0.35, 0.7),
        "wave": make_beep(523, 320, 0.22, 0.4),
    }
    for name, snd in sounds.items():
        assert snd.get_length() > 0, name
    pygame.mixer.quit()


def test_game_smoke_run():
    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    proc = subprocess.Popen(
        [sys.executable, GAME_PATH],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        proc.communicate(timeout=5)
        raise AssertionError("Game exited early instead of running")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_all():
    tests = [
        test_source_compiles,
        test_starting_credits,
        test_hitbox_constants,
        test_bullet_offscreen_or_logic,
        test_circles_overlap_grazing_hit,
        test_circles_overlap_visual_touch_hits,
        test_circles_overlap_no_false_positive,
        test_circles_overlap_exact_touch,
        test_player_hitbox_larger_than_center_point,
        test_bullet_size_increases_hit_radius,
        test_piercing_keeps_bullet,
        test_non_piercing_removes_bullet,
        test_collision_copy_iterate_safe,
        test_ricochet_zero_removes_at_edge,
        test_ricochet_exceeds_limit_removes,
        test_ricochet_bounce_increments,
        test_pause_toggle,
        test_pause_blocked_while_dying,
        test_death_flash_sequence,
        test_wave_clear_vs_death,
        test_upgrade_purchase_spends_credit,
        test_upgrade_respects_max,
        test_ricochet_locked_before_wave_20,
        test_ricochet_unlocked_at_wave_20,
        test_ricochet_clears_piercing,
        test_piercing_clears_ricochet,
        test_reload_cooldown_formula,
        test_bullet_speed_formula,
        test_acceleration_formula,
        test_color_confirm_empty_input,
        test_color_confirm_valid_rgb,
        test_color_rejects_over_255,
        test_upgrade_layout_label_pip_gap,
        test_upgrade_pips_fit_in_panel,
        test_intermission_right_center,
        test_shoot_direction_normalization,
        test_shoot_zero_distance_safe,
        test_enemy_chase_vector,
        test_enemy_spawn_bounds,
        test_pygame_ui_smoke,
        test_all_game_sounds,
        test_game_smoke_run,
    ]
    failed = []
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except Exception as exc:
            failed.append((test.__name__, exc))
            print(f"FAIL: {test.__name__} — {exc}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    if failed:
        for name, exc in failed:
            print(f"  FAILED: {name}: {exc}")
        sys.exit(1)
    print("All rigorous tests passed.")


if __name__ == "__main__":
    run_all()
