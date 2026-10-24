# -*- coding: utf-8 -*-
"""最终验收：不跑游戏 UI，只按 v0.2 规则复算 56 布局与 300 种子的胜负。

用法（在 本子游戏 目录）：
    python "平衡性改造-团队\07-最终验收.py"
    python "平衡性改造-团队\07-最终验收.py" "平衡性改造-团队\notebook_v02.py"
"""
import importlib.util
import itertools
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NB_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "notebook.py")
NB_PATH = os.path.abspath(NB_PATH)
spec = importlib.util.spec_from_file_location("nb_final", NB_PATH)
nb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nb)

START = (0, 0)
SWEEP = "nneeswseww"
# 8 步哈密顿路径，终点客厅 (1,1)：e e n n w w s e
HAM = "eennwwse"
BUDGET = nb.WAKES


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def until_third(hidden, route):
    """沿固定顺序走，抄每张纸，拿到第三张就回门厅；返回 (cost, third_step)。"""
    pos, got, cost = START, set(), 0
    for i, ch in enumerate(route, 1):
        dx, dy = nb.ARROWS[ch]
        pos = (pos[0] + dx, pos[1] + dy)
        cost += 1
        if pos in hidden and pos not in got:
            got.add(pos)
            cost += 1
            if len(got) == 3:
                cost += dist(pos, START)
                return cost, i
    return 10 ** 9, None


def full_sweep(hidden):
    """走完十步并抄每张纸，再回门厅；成本固定 10+3。"""
    pos, cost = START, 0
    for ch in SWEEP:
        dx, dy = nb.ARROWS[ch]
        pos = (pos[0] + dx, pos[1] + dy)
        cost += 1
    return cost + 3


def optimal(hidden):
    rooms = list(hidden)
    best = None
    for order in itertools.permutations(rooms):
        cur, cost = START, 0
        for r in order:
            cost += dist(cur, r)
            cur = r
        cost += dist(cur, START) + 3
        best = cost if best is None else min(best, cost)
    return best


spots = [r for r in nb.ROOMS if r != START]
layouts = list(itertools.combinations(spots, 3))
sweep56 = sum(until_third({r: "x" for r in L}, SWEEP)[0] <= BUDGET for L in layouts)
full56 = sum(full_sweep({r: "x" for r in L}) <= BUDGET for L in layouts)
ham56 = sum(until_third({r: "x" for r in L}, HAM)[0] <= BUDGET for L in layouts)
opt56 = sum(optimal({r: "x" for r in L}) <= BUDGET for L in layouts)

print(f"模块：{NB_PATH}")
print(f"WAKES = {BUDGET}")
print(f"56 布局：全程扫荡+抄 {full56}/56；扫到第三张即回 {sweep56}/56；8 步哈密顿 {ham56}/56；全知 {opt56}/56")

wins_sweep = wins_full = wins_ham = wins_opt = 0
loss_steps = {}
opt_costs = {}
for seed in range(300):
    g = nb.Notebook(seed=seed)
    hidden = dict(g.hidden)
    c1, third = until_third(hidden, SWEEP)
    if c1 <= BUDGET:
        wins_sweep += 1
    else:
        loss_steps[third] = loss_steps.get(third, 0) + 1
    wins_full += full_sweep(hidden) <= BUDGET
    wins_ham += until_third(hidden, HAM)[0] <= BUDGET
    c = optimal(hidden)
    wins_opt += c <= BUDGET
    opt_costs[c] = opt_costs.get(c, 0) + 1

print(f"300 种子：全程扫荡+抄 {wins_full}/300；扫到第三张即回 {wins_sweep}/300；8 步哈密顿 {wins_ham}/300；全知 {wins_opt}/300")
print(f"扫到第三张即回的输局（第三张步数 -> 局数）：{dict(sorted(loss_steps.items()))}")
print(f"全知最优成本分布：{dict(sorted(opt_costs.items()))}")

ok = (
    full56 == 0 and wins_full == 0
    and sweep56 == 35 and wins_sweep == 180
    and ham56 == 35 and 165 <= wins_ham <= 210
    and opt56 == 56 and wins_opt == 300
)
print("验收：", "通过" if ok else "不通过")
raise SystemExit(0 if ok else 1)
