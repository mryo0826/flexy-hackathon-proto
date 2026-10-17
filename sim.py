"""入社前シミュレーターの中身。Jev で判定し、Gemini で入社1日目の場面を書く。

流れ（notes.md の 11:22）: 会社の判定 → 朝・午後・夕方の3場面。各場面の終わりに3択を出し、
選んだ行動を Jev が判定して、Gemini が次の場面を書く。最後に締めくくり。
"""

import json

import cache
import gemini_client
import jev_client


def _jev(state, questions):
    return cache.call("jev", {"state": state, "questions": questions}, lambda: jev_client.ask(state, questions))


def _gemini(prompt, schema):
    return cache.call(
        "gemini", {"prompt": prompt, "schema": schema, "model": gemini_client.MODEL},
        lambda: gemini_client.generate_json(prompt, schema),
    )

LEVELS5 = ["とても低い", "低い", "普通", "高い", "とても高い"]

# 会社の判定の問い。state は {"company": 企業の説明, "seeker": 求職者の希望}
QUESTIONS = {
    "overtime_heavy": {
        "type": "noul",
        "instructions": "`company` は残業が多めか",
        "criteria": {"true": "月30時間を超える残業が普通にある", "false": "残業は少ない"},
    },
    "culture": {
        "type": "choice",
        "instructions": "`company` の職場の雰囲気に一番近いのはどれか",
        "criteria": {
            "casual": "くだけた雰囲気",
            "formal": "かしこまった雰囲気",
            "flat": "上下の少ない雰囲気",
            "speed": "速さと成果を強く求める雰囲気",
        },
    },
    "growth": {
        "type": "score",
        "instructions": "`company` で新しく入った人が成長できる機会はどの位あるか",
        "criteria": LEVELS5,
    },
    "workstyle_fit": {
        "type": "score",
        "instructions": "`seeker` の働き方の希望と、`company` の実際の働き方はどの位合っているか",
        "criteria": ["全く合わない", "あまり合わない", "どちらとも言えない", "かなり合う", "とても合う"],
    },
    "early_leave_risk": {
        "type": "score",
        "instructions": "`seeker` が `company` に入社したら、6ヶ月以内に辞めたくなる可能性はどの位か",
        "criteria": LEVELS5,
    },
}

CULTURE_LABEL = {k: v for k, v in QUESTIONS["culture"]["criteria"].items()}

# 選んだ行動の判定の問い。state は {"company", "seeker", "scene", "action"}
ACTION_QUESTIONS = {
    "company_fit": {
        "type": "score",
        "instructions": "`scene` の場面で `action` を選ぶ事は、`company` が新しく入った人に期待する振る舞いにどの位合っているか",
        "criteria": LEVELS5,
    },
    "self_fit": {
        "type": "score",
        "instructions": "`action` を選ぶ事で、`seeker` は自分の希望をどの位守れているか",
        "criteria": LEVELS5,
    },
}

SLOTS = [
    {"name": "朝", "range": "9:00〜12:00"},
    {"name": "午後", "range": "13:00〜17:00"},
    {"name": "夕方", "range": "17:30 以降"},
]


def judge(company, seeker):
    """Jev の答え（answers）をそのまま返す。"""
    return _jev({"company": company, "seeker": seeker}, QUESTIONS)


def _score_pct(answer, n_levels):
    return round(answer["score"] / (n_levels - 1) * 100)


def judgments_view(answers):
    """画面に出す形に揃える。pct は 0〜100、bad は「気を付けたい」向きか。"""

    def score_pct(name):
        return _score_pct(answers[name], len(QUESTIONS[name]["criteria"]))

    def score_label(name):
        crit = QUESTIONS[name]["criteria"]
        return crit[min(round(answers[name]["score"]), len(crit) - 1)]

    overtime = round(answers["overtime_heavy"]["noul"] * 100)
    culture = answers["culture"]
    return [
        {"label": "残業が多めの見込み", "value": f"{overtime}%", "pct": overtime, "bad": overtime >= 50},
        {
            "label": "職場の雰囲気",
            "value": CULTURE_LABEL[culture["choice"]],
            "pct": round(culture["probabilities"][culture["choice"]] * 100),
            "bad": False,
        },
        {"label": "成長の機会", "value": score_label("growth"), "pct": score_pct("growth"), "bad": score_pct("growth") < 40},
        {
            "label": "あなたの希望との合い方",
            "value": score_label("workstyle_fit"),
            "pct": score_pct("workstyle_fit"),
            "bad": score_pct("workstyle_fit") < 50,
        },
        {
            "label": "6ヶ月以内に辞めたくなる可能性",
            "value": score_label("early_leave_risk"),
            "pct": score_pct("early_leave_risk"),
            "bad": score_pct("early_leave_risk") >= 50,
        },
    ]


def judge_action(company, seeker, scene, action):
    """選んだ行動を判定し、{"company_fit": 0〜100, "self_fit": 0〜100} を返す。"""
    answers = _jev(
        {"company": company, "seeker": seeker, "scene": scene["text"] + "\n" + scene["question"], "action": action},
        ACTION_QUESTIONS,
    )
    return {name: _score_pct(answers[name], len(LEVELS5)) for name in ACTION_QUESTIONS}


SCENE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "time": {"type": "STRING"},
        "title": {"type": "STRING"},
        "text": {"type": "STRING"},
        "question": {"type": "STRING"},
        "options": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["time", "title", "text", "question", "options"],
}

ENDING_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "text": {"type": "STRING"},
        "six_months": {"type": "STRING"},
        "summary": {"type": "STRING"},
    },
    "required": ["text", "six_months", "summary"],
}

COMMON = """あなたは「入社前シミュレーター」です。求職者が応募する前に、その企業で働く入社1日目を体験させます。

# 企業（架空）
{company}

# 求職者の希望
{seeker}

# AI による会社の判定（Jev）
{judgments}

# ここまでの1日目
{history}

# 必ず守る事
- 今日は入社1日目。「昨日入社した」等、1日目と食い違う事を書かない。
- 人の名前や「〇〇さん」の様な伏せ字を使わず、「先輩」「リーダー」「メンター」等と呼ぶ。
- 企業の説明と食い違う事を書かない（例: 残業が少ない会社なのに、残業が増えると予測しない）。
"""

SCENE_PROMPT = COMMON + """
# 書く事
入社1日目の「{slot_name}」（{slot_range}）の場面を1つ書く。
- 求職者を「あなた」と呼ぶ二人称。text は3〜4文で、具体的な出来事と、あなたが感じる事を書く。
- ここまでの選択の結果を、この場面に自然に引き継ぐ（例: 前の場面で断った事が、周りの反応に表れる）。
- 場面の終わりは、会社の期待と、あなたの希望がぶつかる小さな分かれ道にする。question でその分かれ道を1文で問う。
- options は3つ。「会社の期待に寄った行動」「自分の希望を守る行動」「相談・交渉・段取りの工夫で、会社の期待と自分の希望の両方を叶えようとする行動」を1つずつ、どれが正解か分からない書き方で、順番を混ぜて出す。各1文。
- 企業の説明に無い大きな事実（具体的な人名・実在の企業名・数字）を作らない。
"""

ENDING_PROMPT = COMMON + """
# この1日の結末（選択の判定から決まった）
{route_title}。{route_note}
{route_guide}

# 書く事
入社1日目の締めくくりを、上の結末に沿って書く。
- 結末の見出しや、「エンディング」「ルート」の様な言葉は本文に書かない。
- text: 1日目を終えて帰る道のあなたを、ここまでの選択を踏まえて2〜3文で書く（二人称）。
- six_months: 入社6ヶ月後のあなたを、上の結末と、ここまでの選択の傾向を踏まえて2文で予測する。
- summary: この企業とあなたの相性を、応募前に確かめるべき事と合わせて2文でまとめる。
  求職者はまだ応募する前なので、「〜を確かめましょう」と書き、「〜すべきでした」と過去形にしない。
"""

# 結末の3つの道。選んだ行動の2本の棒の平均のうち、低い方で決める（notes.md の gr1）
# title と note は画面にも出すので、転職サイトの言い方にする（「グッドエンディング」等の比喩は使わない）
ROUTES = {
    "good": {
        "title": "相性が良さそうです",
        "note": "会社の期待と、あなたの希望を両立できる働き方が見つかりました",
        "guide": "あなたの選択は、会社の期待と自分の希望の両方を叶えた。text と six_months は前向きに書き、"
        "「この会社でも、こう動けば続けられる」という希望の持てる予測にする。ただし企業の説明と食い違う甘い事は書かない。"
        "summary には、上手くいく為の動き方を1つ入れる。",
    },
    "mixed": {
        "title": "工夫すれば続けられそうです",
        "note": "やっていける手応えはありますが、どこかで無理が出そうです",
        "guide": "あなたの選択は、会社の期待か自分の希望のどちらかに少し無理をした。text と six_months は、"
        "やっていける手応えと、続けると出てくる無理の両方を書く。",
    },
    "bad": {
        "title": "入社前に、もう一度確かめましょう",
        "note": "会社の期待か、あなたの希望のどちらかを大きく削る働き方になりそうです",
        "guide": "あなたの選択は、会社の期待か自分の希望のどちらかを大きく削った。text と six_months は、"
        "このまま続けた時のつらさを正直に書き、入る前に考え直す材料にする。",
    },
}


def route(history):
    """選んだ行動の判定から、結末の道（good / mixed / bad）を決める。"""
    low = min(
        sum(h["fit"][k] for h in history) / len(history) for k in ("company_fit", "self_fit")
    )
    key = "good" if low >= 55 else "mixed" if low >= 35 else "bad"
    return {"key": key, **ROUTES[key]}


def _history_text(history):
    if not history:
        return "（まだ始まっていない）"
    lines = []
    for h in history:
        s = h["scene"]
        lines.append(
            f"- {s['time']} {s['title']}: {s['text']} 分かれ道「{s['question']}」で、あなたは「{h['action']}」を選んだ"
            f"（会社の期待との合い方 {h['fit']['company_fit']}/100・自分の希望の守り方 {h['fit']['self_fit']}/100）"
        )
    return "\n".join(lines)


def _common_args(company, seeker, answers, history):
    return {
        "company": company,
        "seeker": seeker,
        "judgments": "\n".join(f"- {j['label']}: {j['value']}" for j in judgments_view(answers)),
        "history": _history_text(history),
    }


def next_scene(company, seeker, answers, history):
    slot = SLOTS[len(history)]
    prompt = SCENE_PROMPT.format(
        slot_name=slot["name"], slot_range=slot["range"], **_common_args(company, seeker, answers, history)
    )
    scene = _gemini(prompt, SCENE_SCHEMA)
    scene["options"] = scene["options"][:3]
    return scene


def ending(company, seeker, answers, history):
    r = route(history)
    prompt = ENDING_PROMPT.format(
        route_title=r["title"], route_note=r["note"], route_guide=r["guide"],
        **_common_args(company, seeker, answers, history),
    )
    return _gemini(prompt, ENDING_SCHEMA)


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False)
