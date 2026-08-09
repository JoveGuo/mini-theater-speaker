#!/usr/bin/env python3
"""Validate CamillaDSP 2.1 YAML configs without requiring PyYAML."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def _split_key_value(line: str) -> tuple[str, str] | None:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            if i + 1 == len(line) or line[i + 1] == " ":
                return line[:i].strip(), line[i + 1 :].strip()
    return None


def _split_flow_list(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _parse_scalar(text: str):
    text = text.strip()
    if text == "":
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        return [_parse_scalar(part) for part in _split_flow_list(text[1:-1])]
    if text.startswith("{") and text.endswith("}"):
        result: dict = {}
        for part in _split_flow_list(text[1:-1]):
            kv = _split_key_value(part)
            if kv is None:
                raise ValueError(f"invalid flow mapping: {part}")
            result[kv[0]] = _parse_scalar(kv[1])
        return result
    if text in ("true", "True", "TRUE"):
        return True
    if text in ("false", "False", "FALSE"):
        return False
    if text in ("null", "Null", "NULL", "~"):
        return None
    if re.fullmatch(r"[-+]?\d+", text):
        return int(text)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?", text):
        return float(text)
    return text


def _load_mini_yaml(path: Path) -> dict:
    """Parse the small YAML subset used by this repository's configs."""

    raw_lines: list[tuple[int, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = _strip_comment(line)
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        raw_lines.append((indent, stripped.strip()))

    def parse_at(idx: int, indent: int):
        if idx >= len(raw_lines):
            return None, idx
        text = raw_lines[idx][1]
        is_list = text.startswith("- ") or text == "-"

        if is_list:
            result: list = []
            while idx < len(raw_lines) and raw_lines[idx][0] == indent:
                item_text = raw_lines[idx][1]
                if item_text == "-":
                    body = ""
                elif item_text.startswith("- "):
                    body = item_text[2:].strip()
                else:
                    break
                idx += 1
                if body == "":
                    if idx < len(raw_lines) and raw_lines[idx][0] > indent:
                        child, idx = parse_at(idx, raw_lines[idx][0])
                        result.append(child)
                    else:
                        result.append(None)
                    continue
                kv = _split_key_value(body)
                if kv is None:
                    result.append(_parse_scalar(body))
                    continue
                item: dict = {kv[0]: _parse_scalar(kv[1]) if kv[1] else None}
                if idx < len(raw_lines) and raw_lines[idx][0] > indent:
                    child, idx = parse_at(idx, raw_lines[idx][0])
                    if isinstance(child, dict):
                        item.update(child)
                    else:
                        raise ValueError(f"expected mapping after {body}")
                result.append(item)
            return result, idx

        result: dict = {}
        while idx < len(raw_lines) and raw_lines[idx][0] == indent:
            kv = _split_key_value(raw_lines[idx][1])
            if kv is None:
                raise ValueError(f"expected key: value, got: {raw_lines[idx][1]}")
            key, value = kv
            idx += 1
            if value == "":
                if idx < len(raw_lines) and raw_lines[idx][0] > indent:
                    child, idx = parse_at(idx, raw_lines[idx][0])
                    result[key] = child
                else:
                    result[key] = None
            else:
                result[key] = _parse_scalar(value)
        return result, idx

    value, idx = parse_at(0, raw_lines[0][0])
    if idx != len(raw_lines):
        raise ValueError(f"unparsed YAML lines starting at line {idx + 1}")
    if not isinstance(value, dict):
        raise ValueError("config is not a YAML mapping")
    return value


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
        try:
            return _load_mini_yaml(path)
        except Exception as mini_error:
            try:
                return _load_with_ruby(path)
            except Exception:
                raise mini_error
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
