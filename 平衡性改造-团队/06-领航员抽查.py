# -*- coding: utf-8 -*-
"""领航员抽查：不依赖代码员的测试，直接验证 notebook_v02.py 的核心语义。"""
import contextlib
import importlib.util
import io
import itertools
import os
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "notebook_v02.py")
spec = importlib.util.spec_from_file_location("nbv2", P)
nb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nb)

FAILS = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"  ({detail})" if detail else ""))
    if not cond:
        FAILS.append(name)


def quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = fn(*args, **kwargs)
    return r, buf.getvalue()


def path_to(start, goal):
    q = deque([(start, [])])
    seen = {start}
    while q:
        p, steps = q.popleft()
        if p == goal:
            return steps
        for d in "nsew":
            dx, dy = nb.ARROWS[d]
            n = (p[0] + dx, p[1] + dy)
            if n in nb.ROOMS and n not in seen:
                seen.add(n)
                q.append((n, steps + [d]))
    return []


def act(g, fn, *args):
    if g.over:
        return False, ""
    r, out = quiet(fn, *args)
    if r:
        g.check_end()
        if not g.over:
            g.next_round()
    return r, out


def walk(g, steps):
    for d in steps:
        act(g, g.move, d)


def go(g, room):
    walk(g, path_to(g.pos, room))


check("WAKES == 12", nb.WAKES == 12, str(nb.WAKES))

# 1. 进纸房不自动抄；抄了才带走；抄过再抄失败且不花醒来
g = nb.Notebook(seed=1)
room = next(iter(g.hidden))
piece = g.hidden[room]
go(g, room)
check("进纸房 pieces 仍 0", len(g.pieces) == 0, str(g.pieces))
check("进纸房 hidden 仍在", room in g.hidden)
r, _ = act(g, g.copy)
check("copy 成功", r is True)
check("copy 后 pieces=1", len(g.pieces) == 1)
check("copy 后 hidden 移除", room not in g.hidden)
check("copy 后落成原话页", any(p["piece"] and p["text"] == piece for p in g.pages))
round_before = g.round
r, out = act(g, g.copy)
check("无纸 copy 返回 False", r is False)
check("无纸 copy 不花醒来", g.round == round_before, f"{round_before}->{g.round}")
check("无纸 copy 有提示", "没有纸可抄" in out)

# 2. 不抄离开、重进还能看见；抄过再回来不再显示
g = nb.Notebook(seed=2)
room = next(iter(g.hidden))
go(g, room)
# 找相邻房间离开再回来
for d in "nsew":
    dx, dy = nb.ARROWS[d]
    n = (g.pos[0] + dx, g.pos[1] + dy)
    if n in nb.ROOMS and n not in g.hidden:
        act(g, g.move, d)
        break
check("离开后 hidden 仍在", room in g.hidden)
go(g, room)
_, out = quiet(g.show)
check("重进能看见纸", "桌上有一张纸" in out)
r, _ = act(g, g.copy)
check("重进 copy 成功", r is True)
go(g, room)  # 已抄，原地；show 不再显示
_, out = quiet(g.show)
check("抄过再回来不显示纸", "桌上有一张纸" not in out)

# 3. 十步扫荡 + 抄 = 输
g = nb.Notebook(seed=3)
for ch in "nneeswseww":
    act(g, g.move, ch)
    if g.pos in g.hidden:
        act(g, g.copy)
check("扫荡+抄判负", g.over == "lose", str(g.over))
check("扫荡+抄预算耗尽", g.round > nb.WAKES, str(g.round))

# 4. 全知最优 seed 3 = 赢
g = nb.Notebook(seed=3)
rooms = list(g.hidden)
best = None
for perm in itertools.permutations(rooms):
    cur, cost = (0, 0), 0
    for r in perm:
        cost += abs(cur[0] - r[0]) + abs(cur[1] - r[1])
        cur = r
    cost += abs(cur[0]) + abs(cur[1])
    if best is None or cost < best[0]:
        best = (cost, perm)
for r in best[1]:
    go(g, r)
    if r in g.hidden:
        act(g, g.copy)
go(g, (0, 0))
check("seed 3 最优+抄赢", g.over == "win", str(g.over))
check("seed 3 三张抄齐", len(g.pieces) == 3, str(len(g.pieces)))

# 5. 抄写挤掉自己写的页，A 仍可判
g = nb.Notebook(seed=4)
act(g, g.write, "我自己的字")
room = next(iter(g.hidden))
go(g, room)
act(g, g.copy)
check("抄写不产生 write 日志之外的怪状态", len(g.pages) <= 3)
check("页数始终 <= 3", all(len(x.pages) <= 3 for x in [g]))

print()
if FAILS:
    print("FAIL:", FAILS)
    raise SystemExit(1)
print("全部通过")
