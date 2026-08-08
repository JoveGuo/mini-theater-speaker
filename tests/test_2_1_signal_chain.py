#!/usr/bin/env python3
"""Automated checks for the 2.1 signal chain without external dependencies."""

from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import generate_test_tones as gt
import simulate_2_1 as sim


def channel_rms(wav_path: Path, channel: int) -> float:
    with wave.open(str(wav_path), "rb") as wav:
        channels = wav.getnchannels()
        if channel >= channels:
            return 0.0
        values: list[float] = []
        for _ in range(wav.getnframes()):
            frame = wav.readframes(1)
            samples = struct.unpack(f"<{'h' * channels}", frame)
            values.append(samples[channel] / 32768.0)
    return sim.rms(values)


class Test21SignalChain(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        gt.generate(self.dir)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def process(self, name: str) -> Path:
        out = self.dir / f"out_{name}.wav"
        sim.process_file(self.dir / f"{name}.wav", out)
        return out

    def test_left_tone_routes_to_left_only(self) -> None:
        out = self.process("left_1k")
        self.assertGreater(channel_rms(out, 0), 0.05)
        self.assertLess(channel_rms(out, 1), 0.02)
        self.assertLess(channel_rms(out, 2), 0.02)

    def test_right_tone_routes_to_right_only(self) -> None:
        out = self.process("right_1k")
        self.assertGreater(channel_rms(out, 1), 0.05)
        self.assertLess(channel_rms(out, 0), 0.02)
        self.assertLess(channel_rms(out, 2), 0.02)

    def test_low_freq_tone_routes_to_sub(self) -> None:
        out = self.process("sub_50")
        self.assertGreater(channel_rms(out, 2), 0.05)
        self.assertLess(channel_rms(out, 0), 0.02)
        self.assertLess(channel_rms(out, 1), 0.02)

    def test_stereo_1k_stays_in_satellites(self) -> None:
        out = self.process("stereo_1k")
        self.assertGreater(channel_rms(out, 0), 0.05)
        self.assertGreater(channel_rms(out, 1), 0.05)
        self.assertLess(channel_rms(out, 2), 0.02)

    def test_all_configs_validate(self) -> None:
        configs = [
            ROOT / "configs" / "2.1.yml",
            ROOT / "configs" / "2.1.stdin.yml",
            ROOT / "configs" / "2.1.file.yml",
            ROOT / "configs" / "2.1.usb.yml",
        ]
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_config.py"), *map(str, configs)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
