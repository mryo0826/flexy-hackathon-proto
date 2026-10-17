"""デモの初期値（架空の企業と求職者）の1日分を、全ての分かれ道で辿り、cache/ に保存する。

uv run python record_demo.py
保存は cache.py の決まりどおり（既にある鍵は上書きしない）。3択×3回で、場面13・締めくくり27。
"""

from concurrent.futures import ThreadPoolExecutor

import app
import sim

C, S = app.SAMPLE_COMPANY, app.SAMPLE_SEEKER


def walk(answers, history):
    """history の続きを全て辿り、辿った締めくくりの数を返す。"""
    if len(history) == len(sim.SLOTS):
        sim.ending(C, S, answers, history)
        return 1
    scene = sim.next_scene(C, S, answers, history)

    def branch(action):
        fit = sim.judge_action(C, S, scene, action)
        return walk(answers, history + [{"scene": scene, "action": action, "fit": fit}])

    with ThreadPoolExecutor(max_workers=3) as ex:
        return sum(ex.map(branch, scene["options"]))


if __name__ == "__main__":
    sim.gemini_client.warm_up()
    answers = sim.judge(C, S)
    print("締めくくり", walk(answers, []), "通りを辿った")
