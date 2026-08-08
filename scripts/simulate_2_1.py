#!/usr/bin/env python3
"""Reference simulation of the 2.1 CamillaDSP signal chain."""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path


class Biquad:
    def __init__(
        self, b0: float, b1: float, b2: float, a0: float, a1: float, a2: float
    ) -> None:
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0
        self.w1 = 0.0
        self.w2 = 0.0

    def process(self, x: float) -> float:
        w = x - self.a1 * self.w1 - self.a2 * self.w2
        y = self.b0 * w + self.b1 * self.w1 + self.b2 * self.w2
        self.w2 = self.w1
        self.w1 = w
        return y


def butterworth(kind: str, freq: float, fs: float) -> Biquad:
    q = 1.0 / math.sqrt(2.0)
    w0 = 2.0 * math.pi * freq / fs
    cos_w = math.cos(w0)
    sin_w = math.sin(w0)
    alpha = sin_w / (2.0 * q)
    a0 = 1.0 + alpha
    a1 = -2.0 * cos_w
    a2 = 1.0 - alpha
    if kind == "highpass":
        b0 = (1.0 + cos_w) / 2.0
        b1 = -(1.0 + cos_w)
        b2 = (1.0 + cos_w) / 2.0
    elif kind == "lowpass":
        b0 = (1.0 - cos_w) / 2.0
        b1 = 1.0 - cos_w
        b2 = (1.0 - cos_w) / 2.0
    else:
        raise ValueError(f"Unknown filter kind: {kind}")
    return Biquad(b0, b1, b2, a0, a1, a2)


def _process_sequence(samples: list[float], filters: list[Biquad]) -> list[float]:
    out = samples
    for filt in filters:
        out = [filt.process(x) for x in out]
    return out


def soft_clip(x: float, limit_db: float = -0.5) -> float:
    limit = 10.0 ** (limit_db / 20.0)
    if abs(x) <= limit:
        return x
    headroom = 1.0 - limit
    if x > limit:
        return limit + headroom * math.tanh((x - limit) / headroom)
    return -limit - headroom * math.tanh((-x - limit) / headroom)


def rms(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(v * v for v in values) / len(values))


class Simulated2_1:
    def __init__(
        self,
        samplerate: int = 48000,
        crossover_hz: float = 100.0,
        clip_db: float = -0.5,
    ) -> None:
        self.hp_left = [
            butterworth("highpass", crossover_hz, samplerate),
            butterworth("highpass", crossover_hz, samplerate),
        ]
        self.hp_right = [
            butterworth("highpass", crossover_hz, samplerate),
            butterworth("highpass", crossover_hz, samplerate),
        ]
        self.lp_sub = [
            butterworth("lowpass", crossover_hz, samplerate),
            butterworth("lowpass", crossover_hz, samplerate),
        ]
        self.clip_db = clip_db

    def process_frame(self, left: float, right: float) -> tuple[float, float, float]:
        sat_l = _process_sequence([left], self.hp_left)[0]
        sat_r = _process_sequence([right], self.hp_right)[0]
        sub = _process_sequence([left + right], self.lp_sub)[0]
        return (
            soft_clip(sat_l, self.clip_db),
            soft_clip(sat_r, self.clip_db),
            soft_clip(sub, self.clip_db),
        )


def process_file(
    input_wav: str | Path,
    output_wav: str | Path,
    samplerate: int = 48000,
    crossover_hz: float = 100.0,
) -> None:
    dsp = Simulated2_1(samplerate=samplerate, crossover_hz=crossover_hz)
    with wave.open(str(input_wav), "rb") as src:
        if src.getnchannels() != 2:
            raise ValueError("Input WAV must be stereo")
        frame_rate = src.getframerate()
        out_path = Path(output_wav)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as dst:
            dst.setnchannels(3)
            dst.setsampwidth(2)
            dst.setframerate(frame_rate)
            frames = bytearray()
            for _ in range(src.getnframes()):
                raw = src.readframes(1)
                l, r = struct.unpack("<hh", raw)
                l_out, r_out, sub = dsp.process_frame(l / 32768.0, r / 32768.0)
                frames += struct.pack(
                    "<hhh",
                    max(-32768, min(32767, int(round(l_out * 32767)))),
                    max(-32768, min(32767, int(round(r_out * 32767)))),
                    max(-32768, min(32767, int(round(sub * 32767)))),
                )
            dst.writeframes(bytes(frames))


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate 2.1 bass management")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--crossover", type=float, default=100.0)
    parser.add_argument("--samplerate", type=int, default=48000)
    args = parser.parse_args()
    process_file(
        args.input,
        args.output,
        samplerate=args.samplerate,
        crossover_hz=args.crossover,
    )


if __name__ == "__main__":
    main()
