"""デモの録画（動かない時の保険）を作る: キャッシュモードの画面を順に撮り、デモの「話す事」を読ませて繋ぐ。

$env:SIM_MODE='cache'; uv run python build_demo_video.py
  → 予選: ハヤテラボで 朝 A → 午後 B → 夕方 B（両立の道 →「相性が良さそうです」）。
    読み上げ文 narration/demo-<番号>.txt、出力 video/demo.mp4
$env:SIM_MODE='cache'; uv run python build_demo_video.py --company 0 --path CCA --name minato --no-landing
  → 本選の追加: ミナトリンクの一番良い道（→「工夫すれば続けられそうです」止まり）。
    読み上げ文 narration/minato-<番号>.txt、出力 video/minato.mp4
体験のページは Flask のテスト用クライアントで作り、static は立てたサーバー（127.0.0.1:5000）から読ませて撮る。
"""

import argparse
import html
import os
import re

os.environ.setdefault("SIM_MODE", "cache")

import app  # noqa: E402
from build_video import OUT, ROOT, clip, concat, duration, shot_url, tts  # noqa: E402

SERVER = "http://127.0.0.1:5000"


def hidden(t, n):
    m = re.search(r'name="%s" value="([^"]*)"' % n, t)
    return html.unescape(m.group(1)) if m else None


def carry(t):
    return {k: hidden(t, k) for k in ("company", "seeker", "answers", "history")}


def stage_of(t):
    return re.search(r'<div id="stage">(.*)</div>\s*</main>', t, re.S).group(1)


def frames(company, path, name, landing):
    """(番号, 撮る URL) を順に返す。体験のページは HTML に書き出して file:// で撮る。"""
    c = app.app.test_client()
    co = app.COMPANIES[company]["text"]
    page = c.post("/play", data={"company": co, "seeker": app.SAMPLE_SEEKER}).get_data(as_text=True)

    def write(n, stage):
        p = re.sub(r'(<div id="stage">).*?(</div>\s*</main>)', lambda m: m.group(1) + stage + m.group(2), page, flags=re.S)
        p = p.replace('href="/static/', f'href="{SERVER}/static/').replace('src="/static/', f'src="{SERVER}/static/')
        f = OUT / f"{name}-{n:02}.html"
        f.write_text(p, encoding="utf-8")
        return f.resolve().as_uri()

    n = 1
    if landing:
        yield n, f"{SERVER}/"
        n += 1
    yield n, f"{SERVER}/start?c={company}"
    t = stage_of(page)
    yield n + 1, write(n + 1, t)
    n += 2
    for k in path:
        t = c.post("/scene", data=carry(t)).get_data(as_text=True)
        yield n, write(n, t)
        opts = [html.unescape(o) for o in re.findall(r'name="action" value="([^"]*)"', t)]
        d = carry(t)
        d["scene"], d["action"] = hidden(t, "scene"), opts[k]
        t = c.post("/choose", data=d).get_data(as_text=True)
        yield n + 1, write(n + 1, t)
        n += 2
    t = c.post("/scene", data=carry(t)).get_data(as_text=True)
    yield n, write(n, t)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--company", type=int, default=2, help="app.COMPANIES の番号（既定 2 = ハヤテラボ）")
    ap.add_argument("--path", default="ABB", help="朝・午後・夕方に選ぶ選択肢（既定 ABB）")
    ap.add_argument("--name", default="demo", help="読み上げ文 narration/<name>-NN.txt と出力 video/<name>.mp4 の名前")
    ap.add_argument("--no-landing", action="store_true", help="トップの画面を省き、会社を選ぶ画面から始める")
    a = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    clips, total = [], 0.0
    for n, url in frames(a.company, ["ABC".index(x) for x in a.path.upper()], a.name, not a.no_landing):
        stem = OUT / f"{a.name}-{n:02}"
        mp3, png, mp4 = stem.with_suffix(".mp3"), stem.with_suffix(".png"), stem.with_suffix(".mp4")
        tts((ROOT / "narration" / f"{a.name}-{n:02}.txt").read_text(encoding="utf-8").strip(), mp3)
        shot_url(url, png)
        seconds = duration(mp3) + 0.8
        clip(png, mp3, seconds, mp4)
        clips.append(mp4)
        total += seconds
        print(f"{a.name} {n}: {seconds:.1f} 秒")
    concat(clips, OUT / f"{a.name}.mp4")
    print(f"{a.name}.mp4: {total:.1f} 秒")
