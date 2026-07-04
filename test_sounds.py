"""Verify procedural game sounds load and play headless."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import math
import struct
import pygame

pygame.init()
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


def make_death_sound():
    sample_rate = 44100
    duration_ms = 450
    n_samples = int(sample_rate * duration_ms / 1000)
    frames = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        progress = i / n_samples
        freq = 220 - 120 * progress
        envelope = max(0, 1 - progress ** 0.7)
        sample = int(32767 * 0.35 * envelope * math.sin(2 * math.pi * freq * t))
        sample = max(-32767, min(32767, sample))
        frames += struct.pack("<hh", sample, sample)
    return pygame.mixer.Sound(buffer=bytes(frames))


def make_wave_sound():
    sample_rate = 44100
    frames = bytearray()
    for freq, duration_ms in [(523, 90), (659, 90), (784, 140)]:
        n_samples = int(sample_rate * duration_ms / 1000)
        for i in range(n_samples):
            t = i / sample_rate
            envelope = max(0, 1 - (i / n_samples) ** 0.4)
            sample = int(32767 * 0.22 * envelope * math.sin(2 * math.pi * freq * t))
            sample = max(-32767, min(32767, sample))
            frames += struct.pack("<hh", sample, sample)
    return pygame.mixer.Sound(buffer=bytes(frames))


sounds = {
    "shoot": make_beep(920, 55, 0.18, 0.8),
    "hit": make_beep(420, 90, 0.22, 0.6),
    "death": make_death_sound(),
    "wave": make_wave_sound(),
}

for name, sound in sounds.items():
    assert sound.get_length() > 0, name
    sound.play()
    print(f"PASS: {name} ({sound.get_length():.2f}s)")

pygame.time.wait(100)
pygame.mixer.quit()
pygame.quit()
print("All game sounds OK")
