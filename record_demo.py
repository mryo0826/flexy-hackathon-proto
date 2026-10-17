"""デモの会社（app.COMPANIES・全て架空）の1日分を、全ての分かれ道で辿り、cache/ に保存する。

uv run python record_demo.py [--sweep]
保存は cache.py の決まりどおり（既にある鍵は上書きしない）。--sweep で、辿らなかった物を cache-backup-HHMM/ に移す。1社につき3択×3回で、場面13・締めくくり27。
"""

import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ["SIM_MODE"] = "fill"  # 既にある物を辿り、無い所だけ API を呼ぶ（cache.py）

import app  # noqa: E402
import cache  # noqa: E402
import sim  # noqa: E402

S = app.SAMPLE_SEEKER


def walk(company, answers, history):
    """history の続きを全て辿り、辿った締めくくりの数を返す。"""
    if len(history) == len(sim.SLOTS):
        sim.ending(company, S, answers, history)
        return 1
    scene = sim.next_scene(company, S, answers, history)

    def branch(action):
        fit = sim.judge_action(company, S, scene, action)
        return walk(company, answers, history + [{"scene": scene, "action": action, "fit": fit}])

    with ThreadPoolExecutor(max_workers=3) as ex:
        return sum(ex.map(branch, scene["options"]))


def sweep(backup):
    """辿らなかったキャッシュを backup に移す（写してから消す。ゲート g2）。"""
    stale = [p for p in cache.DIR.glob("*.json") if p.name not in cache.used]
    if stale:
        backup.mkdir(exist_ok=True)
        for p in stale:
            shutil.copy2(p, backup / p.name)
            p.unlink()
    return len(stale)


if __name__ == "__main__":
    sim.gemini_client.warm_up()
    for c in app.COMPANIES:
        answers = sim.judge(c["text"], S)
        print(c["name"], "締めくくり", walk(c["text"], answers, []), "通りを辿った")
    if "--sweep" in sys.argv:
        backup = Path(__file__).parent / f"cache-backup-{time.strftime('%H%M')}"
        print("辿らなかった", sweep(backup), "個を", backup.name, "に移した")
