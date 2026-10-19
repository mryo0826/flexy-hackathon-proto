# Devin CLI を使う — 手元の手引き

> **このファイルの役割:** このディレクトリで、Claude Code（シエル）から Devin CLI にコーディングを頼む為の手引き（`CLAUDE.md` の0節の「コーディング」の役）。**出どころは、この機の `devin --help` と `devin auth status`（2026-10-17 に確かめた）。** 細かい所で迷ったら `devin --help` を読み直す（記憶で書き足さない）。
>
> **当日に分かった事（2026-10-19 に足した）:** Free のプランで `swe-1-6-slow` が使えた事と、`accept-edits` はシェルのコマンドを承認しない事は、`notes.md` の 11:40頃・12:31 の行にある。下の表と節は、当日の朝に書いた物のまま。

## 1. この機の Devin CLI `[Fact]`

| 項目 | 値 |
|---|---|
| 場所 | `%LOCALAPPDATA%\devin\cli\bin\devin.exe`（PATH にある） |
| 版 | `devin 3000.10.31` |
| ログイン | 済み（`devin auth status` で「Logged in」・Plan は Free） |
| Telemetry | disabled (zero-data-retention) |
| 権限モードの既定 | この機では環境変数 `DEVIN_PERMISSION_MODE=accept-edits` が入っている（`devin --help` の表示） |

- ⚠️ **Free のプランは、時間で戻る枠で量る。** 使い切ると待つ事になる `[Fact]`（リムルが見た表示）。

## 2. 非対話で1回頼む（Claude Code から呼ぶ形）

```powershell
devin -p --prompt-file .\devin-task.md --model swe-1-6-slow --permission-mode accept-edits --respect-workspace-trust false
```

| 指定 | 意味 `[Fact]`（`devin --help`） |
|---|---|
| `-p` / `--print` | 非対話で実行する（対話の画面を開かない） |
| `--prompt-file <FILE>` | 頼む中身をファイルで渡す。**日本語の長い頼み事は、引数に書かずにファイルで渡す**（PowerShell の引用符で崩れない為） |
| `--model swe-1-6-slow` | SWE-1.6 Slow（コーディング向け）。⚠️ **Free のプランで使えるかは、最初の1回で確かめる** `[To Be Verified]`（使えるモデルは `devin models list`） |
| `--permission-mode accept-edits` | 読み取りと、このディレクトリの中の編集を自動で承認する。他に `auto`（読み取りだけ・既定）・`smart`・`dangerous`（全て承認）。**`dangerous` は使わない** |
| `--respect-workspace-trust false` | 非対話では「このフォルダを信頼するか」の確認を出せず、信頼していないフォルダでは失敗する。それを外す |

- **続きを頼む時は `-c`（直前の会話を続ける）か `-r <SESSION_ID>`。** 会話を残すなら `--export <PATH>`。

## 3. 頼む中身（`devin-task.md`）に必ず入れる事

- **何を作るか**（ファイル名・関数・入力と出力）と、**終わりの条件**（例: `uv run python app.py` で起動して `GET /` が 200 を返す）。
- 🔴 **「`git commit` と `git push` はしない」**——commit はシエルが、このディレクトリの `CLAUDE.md` の6節のゲート（`g5`・`g6`）を通してから、リムルの承認で打つ。
- 🔴 **「API キーをファイルに書かない。環境変数（`TYPESAFE_API_KEY` 等）から読む」。**
- 🔴 **「このディレクトリの外のファイルを読み書きしない」**（`CLAUDE.md` の0節）。
- **Jev の呼び方は `jev.md` を読む様に書く**（Devin には `CLAUDE.md` が渡らないので、要る物はファイルの名前で指す） `[Judgment]`。

## 4. Devin が終わった後にシエルがする事

1. `git status` と `git diff` で、何が変わったかを見る（Devin の報告だけを信じない）。
2. 動かして確かめる。
3. 判断と気づき（Devin に頼んだ事・結果・直した事）を `notes.md` に書く。
4. commit するなら、ゲート `g5` を通して、リムルに `y` / `n` で承認を求める。
