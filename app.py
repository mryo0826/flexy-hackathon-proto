"""入社前シミュレーター。uv run python app.py で http://127.0.0.1:5000 に立つ。

ページ: GET /（トップ）→ GET /start（会社を選ぶ）→ POST /play（Jev で会社を判定し、体験のページ）。
体験のページの中は #stage だけを入れ替える: POST /scene（Gemini で場面と3択）
→ POST /choose（Jev で選んだ行動を判定）→ POST /scene …… 3場面の後は /scene が振り返りを返す。
状態（入力・判定・ここまでの履歴）は、画面の hidden の欄で持ち回る。
"""

import json
import time

from flask import Flask, render_template, request

import cache
import sim

app = Flask(__name__)


def _took(t0):
    """画面に出す応答の時間。キャッシュから答えた時は「キャッシュ」。"""
    if cache.last["source"] == "cache":
        return "キャッシュ"
    return f"{round((time.perf_counter() - t0) * 1000)}ms"

# デモの会社（全て架空）。同じ求職者で、会社毎に1日目が変わる事を見せる（notes.md の n3）
COMPANIES = [
    {
        "name": "ミナトリンク",
        "hint": "残業が多く、速さを求める",
        "text": (
            "株式会社ミナトリンク（架空）。従業員120名の物流 SaaS 企業。出社は週4日。"
            "月の平均残業は35時間で、繁忙期は50時間を超える。新人研修は2日間で、後は OJT。"
            "評価は年1回で、成果の数字を重く見る。Slack の返信の速さが重んじられる。"
        ),
    },
    {
        "name": "ソラノハ",
        "hint": "早く帰れるが、学ぶ機会が乏しい",
        "text": (
            "株式会社ソラノハ（架空）。従業員40名の教育アプリ企業。フルリモートで、"
            "コアタイム11〜15時のフレックス。月の平均残業は5時間程度。"
            "10年前に作った仕組みを使い続けていて、新しい技術の導入には慎重。"
            "研修やメンターの制度は無く、社内の勉強会もほぼ無い。評価は年功寄り。"
        ),
    },
    {
        "name": "ハヤテラボ",
        "hint": "学べるが、成果の評価が厳しい",
        "text": (
            "株式会社ハヤテラボ（架空）。従業員300名の AI スタートアップ。出社は週2日。"
            "月の平均残業は20時間で、リリース前は増える。最新の技術を積極的に採り入れ、"
            "毎週の社内勉強会と書籍購入の補助がある。四半期毎の目標で評価し、"
            "成果が出ないと配置換えもある。子育て中の社員向けの時短勤務制度がある。"
        ),
    },
]
SAMPLE_COMPANY = COMPANIES[0]["text"]
SAMPLE_SEEKER = (
    "30歳・Web エンジニア歴5年。子どもが生まれたばかりで、18時には仕事を終えたい。"
    "リモート中心の働き方を希望。新しい技術を学べる環境を重視する。"
)


def _state():
    f = request.form
    return {
        "company": f["company"],
        "seeker": f["seeker"],
        "answers": json.loads(f["answers"]) if "answers" in f else None,
        "history": json.loads(f["history"]) if "history" in f else [],
    }


def _carry(state):
    """hidden の欄に載せる値。"""
    return {
        "company": state["company"],
        "seeker": state["seeker"],
        "answers_json": sim.dumps(state["answers"]),
        "history_json": sim.dumps(state["history"]),
    }


@app.context_processor
def _mode():
    return {"mode": cache.mode()}


@app.get("/")
def landing():
    return render_template("landing.html")


@app.get("/slides")
def slides():
    """発表のスライド（→ / Space / クリックで次、← で前）。"""
    return render_template("slides.html")


@app.get("/start")
def start():
    """?c=2 で3社目（ハヤテラボ）を選んだ状態で開く（デモ用）。"""
    i = request.args.get("c", default=0, type=int)
    i = i if 0 <= i < len(COMPANIES) else 0
    return render_template(
        "start.html", companies=COMPANIES, selected=i, company=COMPANIES[i]["text"], seeker=SAMPLE_SEEKER
    )


@app.post("/play")
def play():
    """会社を判定し、体験のページを返す。この後は #stage の中だけを入れ替える。"""
    st = _state()
    t0 = time.perf_counter()
    try:
        st["answers"] = sim.judge(st["company"], st["seeker"])
    except Exception as e:  # デモ中は画面にエラーを出して続ける
        return render_template("play.html", stage="error.html", where="Jev", message=str(e))
    ms = _took(t0)
    return render_template(
        "play.html", stage="judge.html", judgments=sim.judgments_view(st["answers"]), ms=ms, **_carry(st)
    )


@app.post("/scene")
def scene():
    st = _state()
    done = len(st["history"]) >= len(sim.SLOTS)
    t0 = time.perf_counter()
    try:
        if done:
            result = sim.ending(st["company"], st["seeker"], st["answers"], st["history"])
        else:
            result = sim.next_scene(st["company"], st["seeker"], st["answers"], st["history"])
    except Exception as e:
        return render_template("error.html", where="Gemini", message=str(e))
    ms = _took(t0)
    if done:
        fits = [h["fit"] for h in st["history"]]
        avg = {k: round(sum(f[k] for f in fits) / len(fits)) for k in ("company_fit", "self_fit")}
        return render_template(
            "ending.html", end=result, avg=avg, history=st["history"], route=sim.route(st["history"]), ms=ms
        )
    return render_template(
        "scene.html", scene=result, scene_json=sim.dumps(result), step=len(st["history"]) + 1, ms=ms, **_carry(st)
    )


@app.post("/choose")
def choose():
    st = _state()
    current = json.loads(request.form["scene"])
    action = request.form["action"]
    t0 = time.perf_counter()
    try:
        fit = sim.judge_action(st["company"], st["seeker"], current, action)
    except Exception as e:
        return render_template("error.html", where="Jev", message=str(e))
    ms = _took(t0)
    st["history"].append({"scene": current, "action": action, "fit": fit})
    return render_template(
        "choose.html", scene=current, action=action, fit=fit, ms=ms, step=len(st["history"]),
        last=len(st["history"]) >= len(sim.SLOTS), **_carry(st),
    )


if __name__ == "__main__":
    if cache.mode() != "cache":
        try:
            sim.gemini_client.warm_up()  # 最初の場面が gcloud を待たないように
        except Exception as e:  # 落ちても、場面を作る時に取り直す
            print(f"warm_up に失敗: {e}")
    app.run(debug=True)
