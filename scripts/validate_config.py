#!/usr/bin/env python3
"""Validate CamillaDSP 2.1 YAML configs without requiring PyYAML."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _load_with_ruby(path: Path) -> dict:
    script = "require 'json'; require 'yaml'; puts JSON.generate(YAML.load_file(ARGV[0]))"
    result = subprocess.run(
        ["ruby", "-e", script, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ruby YAML parse failed: {result.stderr}")
    return json.loads(result.stdout)


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ModuleNotFoundError:
        return _load_with_ruby(path)
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    cfg = load_yaml(path)
    if not isinstance(cfg, dict):
        return [f"{path}: config is not a YAML mapping"]

    devices = cfg.get("devices", {})
    if devices.get("samplerate", 0) <= 0:
        errors.append(f"{path}: devices.samplerate must be positive")
    if devices.get("chunksize", 0) <= 0:
        errors.append(f"{path}: devices.chunksize must be positive")
    capture = devices.get("capture", {})
    playback = devices.get("playback", {})
    if capture.get("channels") != 2:
        errors.append(f"{path}: capture must have 2 channels")
    if playback.get("channels") != 3:
        errors.append(f"{path}: playback must have 3 channels")

    filters = cfg.get("filters", {})
    required_filters = [
        "hp_sat_left",
        "hp_sat_right",
        "lp_sub",
        "delay_left",
        "delay_right",
        "delay_sub",
        "limit_left",
        "limit_right",
        "limit_sub",
    ]
    for name in required_filters:
        if name not in filters:
            errors.append(f"{path}: missing filter {name}")

    mixers = cfg.get("mixers", {})
    mixer = mixers.get("to_2_1")
    if not isinstance(mixer, dict):
        errors.append(f"{path}: missing mixer to_2_1")
    else:
        mapping = mixer.get("mapping", [])
        dests = {item.get("dest") for item in mapping}
        if dests != {0, 1, 2}:
            errors.append(f"{path}: mixer must map dest 0, 1, 2")
        sub_sources = [
            item for item in mapping if item.get("dest") == 2 and item.get("sources")
        ]
        if not sub_sources or len(sub_sources[0]["sources"]) != 2:
            errors.append(f"{path}: SUB destination must sum L and R")

    pipeline = cfg.get("pipeline", [])
    if not any(step.get("type") == "Mixer" and step.get("name") == "to_2_1" for step in pipeline):
        errors.append(f"{path}: pipeline must include Mixer to_2_1")
    if not any(step.get("type") == "Filter" and step.get("channels") for step in pipeline):
        errors.append(f"{path}: pipeline must include Filter steps")

    if capture.get("type") == "RawFile":
        raw_path = Path(capture.get("filename", ""))
        if not raw_path.is_absolute():
            raw_path = path.parent.parent / raw_path
        if not raw_path.exists():
            errors.append(f"{path}: raw input file missing: {raw_path}")

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_config.py <config.yml> ...", file=sys.stderr)
        return 2
    failed = False
    for raw in sys.argv[1:]:
        path = Path(raw)
        errors = validate(path)
        if errors:
            failed = True
            for error in errors:
                print(f"FAIL: {error}")
        else:
            print(f"PASS: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
