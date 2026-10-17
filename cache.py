"""Jev と Gemini の応答のキャッシュ（デモで動かない時の保険。notes.md の n1）。

鍵は問いの中身のハッシュ。同じ入力・同じ選択なら同じ鍵になるので、
キャッシュだけで1日分を辿り直せる。

SIM_MODE（環境変数）:
- auto（既定）: API を呼ぶ。失敗したらキャッシュで答える。
- cache: API を呼ばず、キャッシュだけで答える（ネットが無い時）。
保存は API が答えた時だけで、既にある鍵は上書きしない（ゲート g2 に当たる上書きを起こさない）。
"""

import hashlib
import json
import os
from pathlib import Path

DIR = Path(__file__).parent / "cache"

# 直近の応答の出どころ（"live" / "cache"）。デモは1人で使うので、1つで足りる
last = {"source": "live"}


def mode():
    return os.environ.get("SIM_MODE", "auto")


def _path(kind, payload):
    key = hashlib.sha256(json.dumps([kind, payload], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return DIR / f"{kind}-{key[:16]}.json"


def _read(path):
    if not path.exists():
        raise RuntimeError(f"キャッシュに無い（{path.name}）。SIM_MODE={mode()}")
    last["source"] = "cache"
    return json.loads(path.read_text(encoding="utf-8"))


def call(kind, payload, fn):
    """payload を鍵にして fn() の結果を返す。"""
    path = _path(kind, payload)
    if mode() == "cache":
        return _read(path)
    try:
        value = fn()
    except Exception:
        if path.exists():
            return _read(path)
        raise
    last["source"] = "live"
    if not path.exists():
        DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
    return value
