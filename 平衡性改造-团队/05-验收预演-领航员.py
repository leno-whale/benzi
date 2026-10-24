# -*- coding: utf-8 -*-
"""验收预演：用真实 notebook.py 的开局布局，验证架构方案第 6 节的数字。

不修改游戏，只读 Notebook(seed).hidden。
"""
import importlib.util
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NB = os.path.join(HERE, "..", "notebook.py")
spec = importlib.util.spec_from_file_location("nb", NB)
nb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nb)

START = (0, 0)
BUDGET = 12  # 架构方案拟定的预算；notebook.py 里现在还是 14
SWEEP = "nneeswseww"
ARROWS = nb.ARROWS
ROOMS = nb.ROOMS


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def path_to(start, goal):
    from collections import deque
    q = deque([(start, [])])
    seen = {start}
    while q:
        p, steps = q.popleft()
        if p == goal:
            return steps
        for d in "nsew":
            dx, dy = ARROWS[d]
            nxt = (p[0] + dx, p[1] + dy)
            if nxt in ROOMS and nxt not in seen:
                seen.add(nxt)
                q.append((nxt, steps + [d]))
    return []


def sweep_win(hidden, copy=True):
    """沿十步扫荡路线；copy=True 时进纸房就抄。返回 (win, cost, third_step)。"""
    pos, pieces, cost, third = START, [], 0, None
    for i, ch in enumerate(SWEEP, 1):
        dx, dy = ARROWS[ch]
        pos = (pos[0] + dx, pos[1] + dy)
        cost += 1
        if pos in hidden and pos not in pieces:
            pieces.append(pos)
            if copy:
                cost += 1
            if len(pieces) == 3:
                third = i
                cost += dist(pos, START)
                return cost <= BUDGET, cost, third
    return False, cost, third


def optimal_win(hidden):
    rooms = list(hidden.keys())
    best = None
    for order in itertools.permutations(rooms):
        cur, cost = START, 0
        for r in order:
            cost += dist(cur, r)
            cur = r
        cost += dist(cur, START) + 3
        if best is None or cost < best:
            best = cost
    return best <= nb.WAKES, best


# 1) 56 布局枚举：扫荡的输赢分界
spots = [r for r in ROOMS if r != START]
layouts = list(itertools.combinations(spots, 3))
wins = 0
losing_thirds = {}
for L in layouts:
    hidden = {r: "x" for r in L}
    win, cost, third = sweep_win(hidden)
    wins += win
    if not win:
        losing_thirds[third] = losing_thirds.get(third, 0) + 1
print(f"56 布局：扫荡+抄 胜 {wins}/56 = {wins/56:.1%}")
print("输局中第三张所在步数分布：", losing_thirds)
# 第三张在路线第 8 步的屋子
pos = START
seq = []
for ch in SWEEP:
    dx, dy = ARROWS[ch]
    pos = (pos[0] + dx, pos[1] + dy)
    seq.append(pos)
print("路线：", list(enumerate(seq, 1)))
print("第 8 步 =", ROOMS[seq[7]][0], seq[7], " 第 9 步 =", ROOMS[seq[8]][0], seq[8])

# 2) 300 种子盲搜（固定扫荡路线）真实布局
wins = 0
loss_costs = []
for seed in range(300):
    g = nb.Notebook(seed=seed)
    hidden = dict(g.hidden)
    win, cost, third = sweep_win(hidden)
    wins += win
    if not win:
        loss_costs.append(cost)
print(f"300 种子（固定扫荡+抄）：胜 {wins}/300 = {wins/300:.1%}；输局成本 {sorted(set(loss_costs))}")

# 3) 300 种子最优：全胜
all_ok = True
slack = {}
for seed in range(300):
    g = nb.Notebook(seed=seed)
    ok, cost = optimal_win(g.hidden)
    all_ok &= ok
    slack[cost] = slack.get(cost, 0) + 1
print(f"300 种子最优：{all_ok}；成本分布 {dict(sorted(slack.items()))}；余量 = WAKES-cost")

