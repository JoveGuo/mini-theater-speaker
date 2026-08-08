#!/usr/bin/env python3
"""Generate 2.1 validation test tones without third-party dependencies."""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 48000
AMPLITUDE = 0.25


def _samples(freq: float, duration: float) -> list[float]:
    count = int(SAMPLE_RATE * duration)
    return [
        AMPLITUDE * math.sin(2.0 * math.pi * freq * i / SAMPLE_RATE)
        for i in range(count)
    ]


def _sweep(
    duration: float = 5.0,
    start: float = 20.0,
    stop: float = 20000.0,
    amplitude: float = 0.2,
) -> list[float]:
    count = int(SAMPLE_RATE * duration)
    phase = 0.0
    out: list[float] = []
    for i in range(count):
        t = i / SAMPLE_RATE
        freq = start * (stop / start) ** (t / duration)
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        out.append(amplitude * math.sin(phase))
    return out


def _silence(duration: float = 1.0) -> list[float]:
    return [0.0] * int(SAMPLE_RATE * duration)


def build_tones() -> dict[str, tuple[list[float], list[float]]]:
    sweep = _sweep()
    return {
        "left_1k": (_samples(1000, 2.0), _silence(2.0)),
        "right_1k": (_silence(2.0), _samples(1000, 2.0)),
        "stereo_1k": (_samples(1000, 2.0), _samples(1000, 2.0)),
        "sub_50": (_samples(50, 2.0), _samples(50, 2.0)),
        "sweep_20_20k": (sweep, sweep),
        "silence_1s": (_silence(1.0), _silence(1.0)),
    }


def _to_i16(value: float) -> int:
    return max(-32768, min(32767, int(round(value * 32767))))


def _to_i32(value: float) -> int:
    return max(-2147483648, min(2147483647, int(round(value * 2147483647))))


def write_wav(path: Path, left: list[float], right: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for l, r in zip(left, right):
            frames += struct.pack("<hh", _to_i16(l), _to_i16(r))
        wav.writeframes(bytes(frames))


def write_raw_s32(path: Path, left: list[float], right: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as raw:
        for l, r in zip(left, right):
            raw.write(struct.pack("<ii", _to_i32(l), _to_i32(r)))


def generate(output_dir: str | Path, raw_dir: str | Path | None = None) -> Path:
    tones = build_tones()
    out = Path(output_dir)
    for name, (left, right) in tones.items():
        write_wav(out / f"{name}.wav", left, right)
        if raw_dir is not None:
            write_raw_s32(Path(raw_dir) / f"{name}.raw", left, right)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate 2.1 validation tones")
    parser.add_argument("--output-dir", default="assets/test_tones")
    parser.add_argument("--raw-dir", default=None)
    parser.add_argument(
        "--with-raw", action="store_true", help="also write S32LE raw files"
    )
    args = parser.parse_args()
    raw_dir = args.raw_dir
    if raw_dir is None and args.with_raw:
        raw_dir = "build/test_tones/raw"
    out = generate(args.output_dir, raw_dir)
    print(f"Generated WAV tones in {out}")
    if raw_dir:
        print(f"Generated S32LE raw tones in {raw_dir}")


if __name__ == "__main__":
    main()
