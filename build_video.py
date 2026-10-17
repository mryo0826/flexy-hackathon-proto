"""発表の動画（デモ以外）を作る: 読み上げ（Google の音声合成）＋ スライドの画像 → ffmpeg。

uv run python build_video.py
- 読み上げ文: narration/<スライドの番号>.txt（1〜3 が前半、5〜7 が後半。4 はデモで、リムルが自分でする）
- スライドの画像: http://127.0.0.1:5000/slides#n を Edge のヘッドレスで 1920×1080 で撮る（サーバーを立てておく）
- 出力: video/intro.mp4（スライド1〜3）・video/closing.mp4（スライド5〜7）
認証は gcloud のユーザー認証のトークン（gemini_client と同じ）。notes.md の tts1。
"""

import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import gemini_client

ROOT = Path(__file__).parent
OUT = ROOT / "video"
VOICES = ["ja-JP-Chirp3-HD-Aoede", "ja-JP-Neural2-B"]  # 女声。前が使えなければ後
PARTS = {"intro": [1, 2, 3], "closing": [5, 6, 7]}
PAD = 0.8  # 各スライドの声の後の間（秒）
EDGE = next(
    p for p in (
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ) if Path(p).exists()
)


def tts(text, path):
    for voice in VOICES:
        body = {
            "input": {"text": text},
            "voice": {"languageCode": "ja-JP", "name": voice},
            "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 24000},
        }
        req = urllib.request.Request(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {gemini_client._token()}",
                "x-goog-user-project": gemini_client._project(),
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                path.write_bytes(base64.b64decode(json.load(r)["audioContent"]))
            return voice
        except urllib.error.HTTPError as e:
            print(f"{voice} は使えなかった: {e.code} {e.read().decode('utf-8', 'replace')[:200]}")
    raise RuntimeError("どの声も使えなかった")


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def shot_url(url, path):
    path.unlink(missing_ok=True)
    subprocess.run(
        [EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1920,1080",
         f"--screenshot={path}", url],
        capture_output=True, check=False,
    )
    if not path.exists():
        raise RuntimeError(f"{url} を撮れなかった（サーバーは立っているか）")


def shot(n, path):
    shot_url(f"http://127.0.0.1:5000/slides#{n}", path)


def clip(png, mp3, seconds, path):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-i", str(mp3),
         "-af", f"apad=pad_dur={PAD}", "-t", f"{seconds:.2f}",
         "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(path)],
        check=True,
    )


def concat(paths, out):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.name}'\n" for p in paths), encoding="utf-8")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)],
        check=True,
    )
    lst.unlink()


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for part, slides in PARTS.items():
        clips, total = [], 0.0
        for n in slides:
            mp3, png, mp4 = OUT / f"{n}.mp3", OUT / f"{n}.png", OUT / f"{n}.mp4"
            voice = tts((ROOT / "narration" / f"{n}.txt").read_text(encoding="utf-8").strip(), mp3)
            png.unlink(missing_ok=True)
            shot(n, png)
            seconds = duration(mp3) + PAD
            clip(png, mp3, seconds, mp4)
            clips.append(mp4)
            total += seconds
            print(f"スライド{n}: {seconds:.1f} 秒（{voice}）")
        concat(clips, OUT / f"{part}.mp4")
        print(f"{part}.mp4: {total:.1f} 秒")
