# -*- coding: utf-8 -*-
"""领航员独立平衡模拟：盲搜策略在不同预算下的胜率。

只模拟移动/抄写/回门厅，不涉及假页与结局。
三种策略：
  sweep     固定十步扫荡路线，遇到原话就抄，抄满三张立刻回家（盲玩的最优稳妥解）
  nearest   每次去最近的未访问屋，抄满三张回家
  oracle    全知最优（知道三张位置，走最短收纸路线）
"""
import itertools

ROOMS = [(x, y) for y in range(3) for x in range(3)]
START = (0, 0)
ARROWS = {"n": (0, 1), "s": (0, -1), "e": (1, 0), "w": (-1, 0)}


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def step_toward(cur, goal):
    if cur == goal:
        return None, cur
    for d, (dx, dy) in ARROWS.items():
        nxt = (cur[0] + dx, cur[1] + dy)
        if nxt in ROOMS and dist(nxt, goal) < dist(cur, goal):
            return d, nxt
    raise ValueError((cur, goal))


def path_moves(a, b):
    moves = []
    cur = a
    while cur != b:
        d, cur = step_toward(cur, b)
        moves.append(d)
    return moves


SWEEP = "nneeswseww"
SWEEP_POS = [START]
for ch in SWEEP:
    dx, dy = ARROWS[ch]
    SWEEP_POS.append((SWEEP_POS[-1][0] + dx, SWEEP_POS[-1][1] + dy))


def sweep_run(pieces, budget):
    """沿固定十步路线走；每到一屋若未抄则抄；抄满三张立即回家。"""
    copied = set()
    cost = 0
    pos = START
    for i, ch in enumerate(SWEEP, 1):
        dx, dy = ARROWS[ch]
        pos = (pos[0] + dx, pos[1] + dy)
        cost += 1
        if pos in pieces and pos not in copied:
            copied.add(pos)
            cost += 1
        if len(copied) == 3:
            cost += dist(pos, START)
            return cost <= budget, cost, len(copied)
        if cost >= budget:
            return False, cost, len(copied)
    return False, cost, len(copied)


def nearest_run(pieces, budget):
    pos = START
    copied = set()
    visited = {START}
    cost = 0
    while cost < budget:
        if pos in pieces and pos not in copied:
            copied.add(pos)
            cost += 1
            continue
        if len(copied) == 3:
            cost += dist(pos, START)
            return cost <= budget, cost, len(copied)
        unvisited = [r for r in ROOMS if r not in visited]
        if not unvisited:
            cost += dist(pos, START)
            return False, cost, len(copied)
        goal = min(unvisited, key=lambda r: (dist(pos, r), r[1], r[0]))
        d, nxt = step_toward(pos, goal)
        if nxt == pos:
            visited.add(pos)
            continue
        pos = nxt
        visited.add(pos)
        cost += 1
    return False, cost, len(copied)


def oracle_route(pieces):
    """枚举访问三张原话的顺序，取最短（含回家的距离）。"""
    best = 10**9
    for order in itertools.permutations(pieces):
        cur, cost = START, 0
        for p in order:
            cost += dist(cur, p)
            cur = p
        cost += dist(cur, START) + 3
        best = min(best, cost)
    return best


def all_layouts():
    spots = [r for r in ROOMS if r != START]
    return list(itertools.combinations(spots, 3))


LAYOUTS = all_layouts()


def report(strategy, budget):
    wins = 0
    costs = []
    for pieces in LAYOUTS:
        win, cost, n = strategy(set(pieces), budget)
        if win:
            wins += 1
            costs.append(cost)
    total = len(LAYOUTS)
    avg = f"{sum(costs)/len(costs):.2f}" if costs else "-"
    print(f"{strategy.__name__:12s} WAKES={budget:2d}  胜率 {wins:2d}/{total} = {wins/total:5.1%}  "
          f"胜局平均成本 {avg}")


if __name__ == "__main__":
    print("56 种布局全枚举（每张原话抄写耗 1 次醒来）")
    for s in (sweep_run, nearest_run):
        for b in (11, 12, 13, 14):
            report(s, b)
        print()
    # 全知最优成本分布
    from collections import Counter
    c = Counter(oracle_route(p) for p in LAYOUTS)
    print("全知最优通关成本分布：", dict(sorted(c.items())))
