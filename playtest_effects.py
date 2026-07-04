"""Simulate death flash timing and sound triggers without a display."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import math
import struct
import pygame


def make_beep(freq, duration_ms, volume=0.25, decay=0.5):
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    frames = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        envelope = max(0, 1 - (i / n_samples) ** decay)
        sample = int(32767 * volume * envelope * math.sin(2 * math.pi * freq * t))
        sample = max(-32767, min(32767, sample))
        frames += struct.pack('<hh', sample, sample)
    return pygame.mixer.Sound(buffer=bytes(frames))


def test_death_flash_sequence():
    dying = False
    death_flash_timer = 0
    roundactive = True
    player_died = False

    # simulate enemy hit
    dying = True
    death_flash_timer = 21

    frames = 0
    while dying and frames < 30:
        death_flash_timer -= 1
        if death_flash_timer <= 0:
            roundactive = False
            player_died = True
            dying = False
        frames += 1

    assert not roundactive
    assert player_died
    assert not dying
    assert 18 <= frames <= 22


def test_all_game_sounds_build():
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    sounds = {
        "shoot": make_beep(920, 55, 0.18, 0.8),
        "hit": make_beep(420, 90, 0.22, 0.6),
    }
    for name, snd in sounds.items():
        assert snd.get_length() > 0, name
    for name in sounds:
        sounds[name].play()
    pygame.time.wait(50)
    pygame.mixer.quit()


if __name__ == "__main__":
    test_death_flash_sequence()
    print("PASS: test_death_flash_sequence")
    test_all_game_sounds_build()
    print("PASS: test_all_game_sounds_build")
    print("Death flash + sound tests passed.")
