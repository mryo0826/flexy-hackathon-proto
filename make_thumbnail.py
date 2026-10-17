"""サムネ画像を作る: thumbnail-base.jpg（Gemini で作った絵）の左の淡い面に、コピーを重ねる。

uv run --with pillow python make_thumbnail.py
出力は thumbnail.png（1920×1080）。文字は thumbnail.md の1節のとおり。
"""

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
INK = (59, 74, 107)  # サイトの --ink（#3B4A6B）
BOLD = r"C:\Windows\Fonts\YuGothB.ttc"
REGULAR = r"C:\Windows\Fonts\YuGothM.ttc"
PANEL = 0.35  # 絵の左の淡い面の幅（全体に対する割合）

base = Image.open("thumbnail-base.jpg").convert("RGB")
scale = max(W / base.width, H / base.height)
base = base.resize((round(base.width * scale), round(base.height * scale)), Image.LANCZOS)
left = (base.width - W) // 2
img = base.crop((left, 0, left + W, H))  # 縦が足りる様に拡げ、横の余りを左右で均等に切る

draw = ImageDraw.Draw(img)
x = 64
blocks = [  # (文字, フォント, 大きさ, 次の行までの間)
    ("入社前シミュレーター", BOLD, 34, 72),
    ("応募する前に、", BOLD, 80, 108),
    ("入社1日目を。", BOLD, 80, 140),
    ("AI が、その会社での", REGULAR, 38, 58),
    ("あなたの1日を", REGULAR, 38, 58),
    ("シミュレーションします", REGULAR, 38, 0),
]
total = sum(b[3] for b in blocks) + blocks[-1][2]
y = (H - total) // 2
for text, font, size, gap in blocks:
    f = ImageFont.truetype(font, size)
    assert draw.textlength(text, font=f) <= W * PANEL - x - 24, f"淡い面からはみ出す: {text}"
    draw.text((x, y), text, font=f, fill=INK)
    y += gap

img.save("thumbnail.png")
print("thumbnail.png", img.size)
