"""Gemini（Vertex AI）を REST で呼ぶ。

認証は gcloud のユーザー認証のトークン（ADC は使わない。notes.md の 10:55）。
プロジェクトも gcloud の設定から読む（ファイルに書かない）。
"""

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request

MODEL = "gemini-2.5-flash"
_TOKEN_TTL = 45 * 60  # トークンは約60分で切れるので、早めに取り直す

_cache = {"token": None, "token_at": 0.0, "project": None}


def _gcloud(*args):
    exe = shutil.which("gcloud")  # Windows では gcloud.cmd
    if exe is None:
        raise RuntimeError("gcloud が見つからない")
    return subprocess.run(
        [exe, *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _token():
    if _cache["token"] is None or time.time() - _cache["token_at"] > _TOKEN_TTL:
        _cache["token"] = _gcloud("auth", "print-access-token")
        _cache["token_at"] = time.time()
    return _cache["token"]


def _project():
    if _cache["project"] is None:
        _cache["project"] = _gcloud("config", "get-value", "project")
    return _cache["project"]


def warm_up():
    """トークンとプロジェクトを先に取っておく（gcloud の呼び出しは数秒かかる）。"""
    _token()
    _project()


def generate_json(prompt, schema, timeout=60):
    """prompt を投げ、schema に沿った JSON を dict で返す。"""
    url = (
        f"https://aiplatform.googleapis.com/v1/projects/{_project()}"
        f"/locations/global/publishers/google/models/{MODEL}:generateContent"
    )
    body = json.dumps(
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema,
                "thinkingConfig": {"thinkingBudget": 0},  # デモの待ち時間を縮める
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            data = json.load(res)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini {e.code}: {e.read().decode('utf-8', 'replace')}") from e
    return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
