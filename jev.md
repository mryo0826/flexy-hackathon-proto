# Jev（TypeSafe）を REST で呼ぶ — 手元の手引き

> **このファイルの役割:** プロトタイプから Jev を呼ぶ為の、最小限の手引き。**出どころは公式の文書の `.md` 版**（[`api.md`](https://docs.typesafe.ai/api.md)・[`models.md`](https://docs.typesafe.ai/models.md)・[`primitives.md`](https://docs.typesafe.ai/primitives.md)。2026-10-17 に取得）。**細かい所で迷ったら、公式の文書を読み直す**（記憶で書き足さない）。
> **デモなので、SDK は使わず curl で REST を呼ぶ**（2026-10-17 のリムルの判断）。

## 1. 呼び方 `[Fact]`

```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

- **API キーは環境変数 `TYPESAFE_API_KEY` にある**（`notes.md` の 10:50 の確かめ）。ファイルに書かない。
- **本文は UTF-8 の JSON で、BOM を付けない**（付けると `400`）。
- **モデルは `"jev-latest"`**（2026-10-17 時点の実体は `jev-1.13.0`）。

## 2. 本文の形 `[Fact]`

```json
{
  "state": "判断の材料。文字列でも、オブジェクトでも良い",
  "model": "jev-latest",
  "questions": {
    "<自分で付ける名前>": { "type": "noul" | "choice" | "score", "instructions": "問い", "criteria": ... }
  }
}
```

- **`questions` は名前を付けた問いの集まり。答えは同じ名前で返る。** 名前はモデルには送られない。
- **1回の呼び出しに問いを複数入れられる**（まとめた方が速い——公式の Cookbook では13問を1回にまとめて平均 0.27 秒）。
- **`instructions` から `state` の中の項目を指す時は、バッククォートで囲む**（例: `` "`company` は残業が多めか" ``）。

### 問いの3つの型

| 型 | 何を返すか | `criteria` |
|---|---|---|
| `noul` | はい の確率（0〜1） | 省略可。`{"true": "はいの意味", "false": "いいえの意味"}` |
| `choice` | 選んだ1つと、全ての選択肢の確率 | `{"選択肢": "説明"}`（最大255個） |
| `score` | 段階の確率で重み付けした値（段階の間の値もありうる） | `["段階0の説明", "段階1の説明", ...]`（2〜10段階） |

## 3. 例（架空の企業）

`req.json`（UTF-8・BOM なしで保存する）:

```json
{
  "state": {
    "company": "架空の株式会社サンプル。従業員80名の SaaS 企業。フルリモート可。月の平均残業は25時間。1on1 は隔週。"
  },
  "model": "jev-latest",
  "questions": {
    "overtime_heavy": {
      "type": "noul",
      "instructions": "`company` は残業が多めか",
      "criteria": { "true": "月30時間を超える残業が普通にある", "false": "残業は少ない" }
    },
    "culture": {
      "type": "choice",
      "instructions": "`company` の職場の雰囲気に一番近いのはどれか",
      "criteria": { "casual": "くだけた雰囲気", "formal": "かしこまった雰囲気", "flat": "上下の少ない雰囲気" }
    },
    "growth": {
      "type": "score",
      "instructions": "`company` の成長の機会はどの位あるか",
      "criteria": ["少ない", "普通", "多い"]
    }
  }
}
```

PowerShell から呼ぶ（**`curl` ではなく `curl.exe` と書く**。PowerShell の `curl` は別の物の別名になっている事がある）:

```powershell
curl.exe -s https://api.typesafe.ai/v1/systemone `
  -H "Authorization: Bearer $env:TYPESAFE_API_KEY" `
  -H "Content-Type: application/json" `
  --data-binary "@req.json"
```

- ⚠️ **JSON をコマンドの引数に直接書かず、ファイルで渡す**（PowerShell の引用符の規則で JSON が崩れやすい為）。

## 4. 答えの形 `[Fact]`

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "overtime_heavy": { "type": "noul", "noul": 0.12 },
    "culture": { "type": "choice", "choice": "flat", "probabilities": { "casual": 0.2, "formal": 0.05, "flat": 0.75 }, "confidence": 0.6 },
    "growth": { "type": "score", "score": 1.4, "legend": { "0": "少ない", "1": "普通", "2": "多い" }, "probabilities": { "0": 0.05, "1": 0.5, "2": 0.45 }, "confidence": 0.5 }
  },
  "usage": { "input_tokens": 300, "output_tokens": 30 }
}
```

- ⚠️ **上の数値は形を示す為の作り物。** 実際の値は呼んで確かめる。
- **`confidence` は `choice` と `score` に付く**（0〜1）。

## 5. エラー `[Fact]`

| 状態 | 意味 |
|---|---|
| `400` | 本文が決まりに反する（UTF-8 でない・BOM・入れ子が深すぎる等） |
| `401` | API キーが無いか、違う |
| `422` | 本文の検証に通らない（必須の項目が無い・問いの形が違う）。本文に、どの項目かが書かれる |
| `429`・`529` | 呼び過ぎ・混雑。少し待って、間隔を伸ばしながらやり直す |

## 6. 実現性（審査の20点）で話せる数字

| 項目 | 値 | 出どころ |
|---|---|---|
| 料金 | 入力 100万 tokens あたり $0.042 | `models.md` `[Fact]` |
| 上限 | 1回の呼び出しで 64k tokens・1問あたり 32k tokens | `models.md` `[Fact]` |
| 応答の時間 | 東京から 130〜300ms | リムルの実測（2026-10） `[Fact]` |
