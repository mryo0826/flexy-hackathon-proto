"""Jev（TypeSafe）を REST で呼ぶ。呼び方は jev.md のとおり。"""

import json
import os
import urllib.error
import urllib.request

URL = "https://api.typesafe.ai/v1/systemone"


def ask(state, questions, model="jev-latest", timeout=15):
    """問いの集まりを1回で投げ、名前毎の答え（answers）を返す。"""
    body = json.dumps(
        {"state": state, "model": model, "questions": questions},
        ensure_ascii=False,
    ).encode("utf-8")  # BOM なしの UTF-8
    req = urllib.request.Request(
        URL,
        data=body,
        headers={
            "Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.load(res)["answers"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Jev {e.code}: {e.read().decode('utf-8', 'replace')}") from e
