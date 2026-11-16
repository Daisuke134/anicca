#!/usr/bin/env python3
"""Deterministically author LivingHome using Rive's public v7 binary format.

Only baseline vector/animation/state-machine properties are used (no fonts,
images, network assets, or editor required). See Rive/NOTES.md for provenance.
"""
import math
from pathlib import Path
import struct

ASSET = Path(__file__).resolve().parents[2] / "aniccaios/Views/Feed/Rive/living_home.riv"


def uint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def string(value):
    encoded = value.encode("utf-8")
    return uint(len(encoded)) + encoded


def number(value):
    return struct.pack("<f", value)


def color(value):
    return struct.pack("<I", value)


def generate():
    # Fingerprint, major/minor, file ID (unassigned), empty extension ToC.
    data = bytearray(b"RIVE" + bytes([7, 0, 0, 0]))
    next_component = 0

    def obj(kind, *properties):
        data.extend(uint(kind))
        for key, value in properties:
            data.extend(uint(key) + value)
        data.extend(b"\x00")

    def component(kind, name, parent=0, properties=()):
        nonlocal next_component
        index = next_component
        next_component += 1
        obj(kind, (4, string(name)), (5, uint(parent)), *properties)
        return index

    def glow(name, x, y, radius, rgb, opacity=1, ring=False):
        shape = component(3, name, properties=[
            (13, number(x)), (14, number(y)), (18, number(opacity))])
        component(4, name + "Ellipse", shape, [
            (20, number(radius * 2)), (21, number(radius * 2))])
        fill = component(20, name + "Fill", shape)
        gradient = component(17, name + "Gradient", fill, [(34, number(radius))])
        stops = [(0, 0), (0.62, 0), (0.78, 180), (1, 0)] if ring else [(0, 190), (0.45, 90), (1, 0)]
        for position, alpha in stops:
            component(19, "", gradient, [(38, color((alpha << 24) | rgb)), (39, number(position))])
        return shape

    obj(23)  # Backboard owns the artboard import context, but no component ID.
    component(1, "LivingHome", properties=[(7, number(390)), (8, number(844))])
    sage = glow("Sage", 70, 240, 240, 0xADD6BC)
    gold = glow("Gold", 320, 580, 260, 0xF2D7A0)
    mist = glow("Mist", 300, 110, 180, 0xD8E5E9)
    ripple = glow("Ripple", 195, 422, 210, 0xFFF1CF, opacity=0, ring=True)

    def animation(name, frames, loop):
        obj(31, (55, string(name)), (56, uint(60)), (57, uint(frames)), (59, uint(loop)))

    def track(target, property_key, keys):
        obj(25, (51, uint(target)))
        obj(26, (53, uint(property_key)))
        for frame, value in keys:
            # Interpolation 1 = linear; sampled cosine yields soft breathing.
            obj(30, (67, uint(frame)), (68, uint(1)), (70, number(value)))

    animation("Ambient", 720, 1)  # 12 seconds, endlessly looping.
    for target, x, y, direction in [(sage, 70, 240, 1), (gold, 320, 580, -1), (mist, 300, 110, -1)]:
        keys = [(frame, (1 - math.cos(2 * math.pi * frame / 720)) / 2) for frame in range(0, 721, 30)]
        track(target, 13, [(f, x + direction * 48 * t) for f, t in keys])
        track(target, 14, [(f, y - direction * 36 * t) for f, t in keys])
        for scale in (16, 17):
            track(target, scale, [(f, 1 + 0.12 * t) for f, t in keys])

    animation("Rest", 60, 1)
    track(ripple, 18, [(0, 0), (60, 0)])
    animation("WordChange", 36, 0)  # 0.6-second one-shot, independently retriggerable.
    track(ripple, 18, [(0, 0), (6, 0.95), (18, 0.65), (36, 0)])
    for scale in (16, 17):
        track(ripple, scale, [(0, 0.35), (12, 0.7), (36, 1.65)])

    obj(53, (55, string("Living")))
    obj(58, (138, string("WordChanged")))  # input 0, trigger

    def transition(destination, trigger=False, exit_ms=None):
        properties = [(151, uint(destination))]
        if exit_ms is not None:
            properties.extend([(152, uint(4)), (160, uint(exit_ms))])
        obj(65, *properties)
        if trigger:
            obj(68, (155, uint(0)))

    # State indices are per layer: Entry=0, Any=1, Exit=2, animations=3+.
    obj(57, (138, string("Ambient")))
    obj(63)
    transition(3)
    obj(62)
    obj(64)
    obj(61, (149, uint(0)))

    # Keeping the ripple on its own layer prevents resetting the ambient drift.
    obj(57, (138, string("Word transition")))
    obj(63)
    transition(3)
    obj(62)
    obj(64)
    obj(61, (149, uint(1)))  # Rest
    transition(4, trigger=True)
    obj(61, (149, uint(2)))  # WordChange
    transition(5, trigger=True)
    transition(3, exit_ms=600)
    # Two states share the same timeline: Rive ignores transitions to the
    # current state, so alternate instances to restart on every rapid trigger.
    obj(61, (149, uint(2)))  # WordChange, second instance
    transition(4, trigger=True)
    transition(3, exit_ms=600)
    return bytes(data)


if __name__ == "__main__":
    ASSET.write_bytes(generate())
    print(f"{ASSET}: {ASSET.stat().st_size} bytes")
