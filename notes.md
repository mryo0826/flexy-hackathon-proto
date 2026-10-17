# 当日の判断と気づき（FLEXY AI ハッカソン Vol.1・2026-10-17）

> **このファイルの役割:** このディレクトリで動くセッションが、当日の判断と気づきを書く所（`CLAUDE.md` の0節）。**後で司令塔のセッションが読んで、作業日誌に写す。** ⇒ **このファイルだけ読んでも分かるように書く**（「さっきの」「上の」で指さない）。
> ⚠️ **プロトタイプの判断だけを書く。** このディレクトリの中身は成果物として主催に帰属しうる（`CLAUDE.md` の8節）。

## 起動した直後の確かめ

| 確かめる事 | 結果 | 確度 |
|---|---|---|
| AIDD の Skill（`review-before-commit` 等）が `/context` の Skill の一覧に無いか（`rp3`） | **無い。** 10:47 の `/context` の Skill は21個で、全て Built-in（`dataviz`・`code-review` 等）か claude.ai sync（`docs`・`docx`・`pdf`・`pptx`・`xlsx`）。`review-before-*` は一覧に無い。⚠️ 同じ時刻の `/usage` の「Top skills」には `/review-before-commit` が出るが、これはこの機械の他のセッションも含めた過去24時間・7日間の集計で、このセッションで読み込まれた Skill の一覧ではない（`/skill-doctor` の「Skills loaded this session」にも無い） | `[Fact]`（`/context`・`/skill-doctor` の出力） |

## 判断の記録

| 時刻 | 決めた事 | 誰が決めたか（リムル／シエル／Devin） | 根拠・退けた案 |
|---|---|---|---|
| 10:50 | 方向性は `handoff-v4.md` の2節「入社前シミュレーター」で進める | リムル | キックオフで、テーマ以外の制約は特に出なかった（リムルの報告） |

## 気づき（レトロの材料）

| 時刻 | 起きた事 | 誰が気づいたか |
|---|---|---|
| 10:50 | `CLAUDE.md` の5節は「API キーは環境変数にある」と書くが、このプロセスの環境変数にあるのは `TYPESAFE_API_KEY`（Jev）だけで、`ANTHROPIC_API_KEY` は無い。リムルによれば、Claude は Claude Pro のサブスクの中で使っていて、API キーは持っていない。⇒ プロトタイプからその場で呼べる AI は Jev だけ。v4 の5節の構成（Haiku・Sonnet を API で呼ぶ）はそのままでは動かない | シエル（リムルが訂正） |
| 10:55 | リムルの提案で、GCP の Gemini を確かめた。gcloud 585.0.0 にプロジェクトが設定済みで、Vertex AI の API（`aiplatform.googleapis.com`）も有効。ADC（`gcloud auth application-default`）はトークンが取れない（exit 1）が、gcloud のユーザー認証（`gcloud auth print-access-token`）では取れる。そのトークンで、global の `gemini-2.5-flash` に REST で1問投げて、1.7秒で日本語の応答が返った `[Fact]` ⇒ 文章の生成は、その場で Gemini で出来る | シエル |
