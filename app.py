"""入社前シミュレーター。uv run python app.py で http://127.0.0.1:5000 に立つ。

流れ: POST /judge（Jev で会社を判定）→ POST /scene（Gemini で場面と3択）
→ POST /choose（Jev で選んだ行動を判定）→ POST /scene …… 3場面の後は /scene が締めくくりを返す。
状態（入力・判定・ここまでの履歴）は、画面の hidden の欄で持ち回る。
"""

import json
import time

from flask import Flask, render_template, request

import sim

app = Flask(__name__)

# デモの初期値（架空の企業と求職者）
SAMPLE_COMPANY = (
    "株式会社ミナトリンク（架空）。従業員120名の物流 SaaS 企業。出社は週4日。"
    "月の平均残業は35時間で、繁忙期は50時間を超える。新人研修は2日間で、後は OJT。"
    "評価は年1回で、成果の数字を重く見る。Slack の返信の速さが重んじられる。"
)
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


@app.get("/")
def index():
    return render_template("index.html", company=SAMPLE_COMPANY, seeker=SAMPLE_SEEKER)


@app.post("/judge")
def judge():
    st = _state()
    t0 = time.perf_counter()
    try:
        st["answers"] = sim.judge(st["company"], st["seeker"])
    except Exception as e:  # デモ中は画面にエラーを出して続ける
        return render_template("error.html", where="Jev", message=str(e))
    ms = round((time.perf_counter() - t0) * 1000)
    return render_template("judge.html", judgments=sim.judgments_view(st["answers"]), ms=ms, **_carry(st))


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
    ms = round((time.perf_counter() - t0) * 1000)
    if done:
        fits = [h["fit"] for h in st["history"]]
        avg = {k: round(sum(f[k] for f in fits) / len(fits)) for k in ("company_fit", "self_fit")}
        return render_template("ending.html", end=result, avg=avg, ms=ms)
    return render_template(
        "scene.html", scene=result, scene_json=sim.dumps(result), step=len(st["history"]) + 1,
        total=len(sim.SLOTS), ms=ms, **_carry(st),
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
    ms = round((time.perf_counter() - t0) * 1000)
    st["history"].append({"scene": current, "action": action, "fit": fit})
    return render_template(
        "choose.html", action=action, fit=fit, ms=ms, last=len(st["history"]) >= len(sim.SLOTS), **_carry(st)
    )


if __name__ == "__main__":
    sim.gemini_client.warm_up()  # 最初の場面が gcloud を待たないように
    app.run(debug=True)
