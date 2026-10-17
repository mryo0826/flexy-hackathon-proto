# STATE — 入社前シミュレーター（FLEXY AI ハッカソン Vol.1・2026-10-17）

> **このファイルの役割:** 今の状態・動かし方・ファイルの地図・残っている事を1か所にまとめる。**新しいセッション（別の環境で `git clone` した時も）は、`CLAUDE.md` の次にこれを読む。** 判断の経緯は `notes.md`（時刻順の記録）、発表の手順は `pitch.md`。
> 最終更新: 2026-10-17 16:05（AI・Claude Opus 5.5）。

## 1. 何か

応募する前に、架空の会社での「入社1日目」を体験する Web アプリ。会社の判定 → 朝・午後・夕方の3つの分かれ道で行動を選ぶ → 選ぶ度に「会社の期待との合い方」「自分の希望の守り方」を 0〜100 で測る → 選び方で結末（相性）が変わる。

- 判断は **Jev**（TypeSafe）、文章は **Gemini 2.5 Flash**（Vertex AI）。Claude は使っていない（API キーが無い。`notes.md` の 10:50）。
- 会社は全て架空（ミナトリンク・ソラノハ・ハヤテラボ）。求職者は1人（18時に帰りたい Web エンジニア）。

## 2. 今の状態（16:05）

| 物 | 状態 |
|---|---|
| アプリ | 動く。デモは**キャッシュモード**でする（`notes.md` の 15:13） |
| サムネ | `thumbnail.png`（1920×1080）。ゲート `g4` 承認済み。**提出済み**（16:05・リムル） |
| スライド | アプリの `/slides`（7枚） |
| 発表の動画 | `video/intro.mp4`（1分10秒）・`video/closing.mp4`（1分22秒）。デモはリムルが自分でする |
| デモの録画（保険） | `video/demo.mp4`（1分53秒・ハヤテラボの両立の道）。本選の追加用に `video/minato.mp4`（1分43秒・ミナトリンクの一番良い道） |
| 台本 | `pitch.md`（当日の時刻表とデモの手順） |
| git | `main` を private の `mryo0826/flexy-hackathon-proto` に push している（最初は 15:46・`ea0411e`、最新の push は `git log origin/main -1` で見る） |

## 3. 残っている事

- [x] サムネの提出（16:05 済み）
- [ ] ゲート `g3`: 本番の手順（`intro.mp4` → デモ → `closing.mp4`）で1回通し、6分以内か測る
- [ ] `video/` の3本と `thumbnail.png` を、USB メモリかスマホにも写す（今日マシンが3回落ちた）

## 4. 動かし方

### 要る物（Windows で確かめた）

| 物 | 用途 |
|---|---|
| `uv`・Python 3.13 | アプリ（依存は Flask だけ。`uv sync`） |
| 環境変数 `TYPESAFE_API_KEY` | Jev。ファイルに書かない |
| `gcloud`（ログイン済み・プロジェクト設定済み） | Gemini と音声合成のトークン（`gcloud auth print-access-token`）。ADC は使わない。プロジェクトで Vertex AI（`aiplatform.googleapis.com`）と音声合成（`texttospeech.googleapis.com`）の API が有効な事 |
| Chromium 系のブラウザ（Edge か Chrome） | スライドと画面を撮る（ヘッドレス）。環境変数 `BROWSER` があればそれ、無ければ Edge → Chrome の順に探す（Windows・Mac・Linux の場所）。既定を Edge にしたのは Windows 11 に必ず入っている為で、Chrome と比べて選んだ訳ではない（Chrome でも撮れる事を確かめた） |
| ffmpeg | 動画を作る |
| Pillow（その場限り） | サムネを作る時だけ `uv run --with pillow` |

### コマンド（PowerShell）

| 何をする | コマンド |
|---|---|
| デモ用に立てる（API を呼ばない） | `$env:SIM_MODE='cache'; uv run python app.py` → http://127.0.0.1:5000 |
| ライブで立てる | `uv run python app.py`（`SIM_MODE` は既定の `auto`: API を呼び、落ちたらキャッシュ） |
| 3社×27通りのキャッシュを埋める | `uv run python record_demo.py`（中で `SIM_MODE=fill`）。`--sweep` で、辿らなかった物を `cache-backup-HHMM/` に写してから消す（ゲート `g2`） |
| 発表の動画を作り直す | サーバーを立てて `uv run python build_video.py`（読み上げ文は `narration/1〜3・5〜7.txt`） |
| デモの録画を作り直す | サーバーを立てて `$env:SIM_MODE='cache'; uv run python build_demo_video.py`（`narration/demo-01〜10.txt`） |
| サムネを作り直す | `uv run --with pillow python make_thumbnail.py` |

### URL

| URL | 中身 |
|---|---|
| `/` | トップ（サムネと同じ一枚絵） |
| `/start?c=0〜2` | 会社を選ぶ（`c=2` でハヤテラボを選んだ状態） |
| `/play`（POST） | 体験（判定 → 朝 → 午後 → 夕方 → 振り返り） |
| `/slides#n` | 発表のスライド（n 枚目から） |

## 5. 気を付ける事

- ⚠️ **`gemini-2.5-flash` は 2026-10-20 に退役する**（`notes.md` の 12:36）。その後はライブでは動かない。キャッシュモードは動く。差し替えは `gemini_client.py` の `MODEL`（差し替えるとキャッシュは取り直し）。
- ⚠️ **キャッシュの鍵は、問いの中身そのもの。** 指示の文（`sim.py`）・会社の説明（`app.py` の `COMPANIES`）・求職者の文を1字でも変えると、その先のキャッシュは使えなくなる。変えたら `record_demo.py` で埋め直す。表示だけの文言は、指示に入らない所（テンプレートや `ROUTES` の `title`・`note`）で変える。
- ⚠️ **数字（1人の体験 約0.45円・応答の秒数等）の正本は `notes.md` の 12:31・12:36。** 同じ数字が `pitch.md`・`templates/slides.html`・`narration/5.txt` にもある。変える時は4か所。
- サーバーを立てるコマンド等は、`pitch.md`（1節・3節）にもわざと重ねて書いてある（本番で手元に置く物なので、他を開かずに済む様に）。コマンドを変える時は `pitch.md` も直す。
- 動作を確かめたのは Windows 11 だけ。gcloud は `shutil.which` で探すので他の OS でも動く筈 `[Assumption]`。
- `cache/` は3社×27通りのちょうど240個（Gemini 120・Jev 120）。`cache-backup-*/` と `video/` の中間ファイルは追跡しない（`.gitignore`）。

## 6. ファイルの地図

| ファイル | 中身 |
|---|---|
| `CLAUDE.md` | 当日の規律・ゲート（`g1`〜`g6`）・審査の観点 |
| `STATE.md` | これ |
| `notes.md` | 判断と気づきの時刻順の記録（司令塔が作業日誌に写す） |
| `pitch.md` | 発表の時刻表・デモの手順・動かない時の保険 |
| `thumbnail.md` | サムネのコピーと画像の指示 |
| `jev.md`・`devin-use.md` | Jev の呼び方・Devin CLI の呼び方 |
| `devin-task-style.md`・`devin-task-pastel.md` | Devin に頼んだ文（記録） |
| `handoff-v4.md` | 事前の案（Namazu との壁打ち）の無改変の写し。参考に留める |
| `ハッカソン発表_AI声スライド動画作成ガイド.md` | 他の生成 AI と作った動画の手順。声は Fish Audio ではなく Google の音声合成にした（`notes.md` の 14:46） |
| `app.py`・`sim.py`・`cache.py`・`jev_client.py`・`gemini_client.py` | アプリ |
| `record_demo.py`・`build_video.py`・`build_demo_video.py`・`make_thumbnail.py` | キャッシュ・動画・サムネを作る |
| `templates/`・`static/` | 画面（`static/hero.jpg` はサムネの元の絵） |
| `narration/` | 動画の読み上げ文 |

## 7. 使っていない候補

- 課題のスライドに数字（早期離職の割合等）を足す時の出典の候補: https://career-research.mynavi.jp/column/20251010_102320/ （リムルが挙げた。未読・未使用）
