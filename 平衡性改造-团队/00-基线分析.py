# -*- coding: utf-8 -*-
"""基线分析：九宫格布局、最短收纸路线、预算余量。

只读原版 notebook.py，不改动游戏。输出用于 v0.2 平衡设计。
"""
import importlib.util
import itertools
import os
import sys
from collections import deque, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("nb", os.path.join(GAME, "notebook.py"))
nb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nb)

START = (0, 0)


def shortest_path(start, goal):
    q = deque([(start, [])])
    seen = {start}
    while q:
        cur, steps = q.popleft()
        if cur == goal:
            return steps
        for d in "nsew":
            dx, dy = nb.ARROWS[d]
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt in nb.ROOMS and nxt not in seen:
                seen.add(nxt)
                q.append((nxt, steps + [d]))
    raise ValueError((start, goal))


def tour(rooms):
    best = None
    for perm in itertools.permutations(rooms):
        cur, seq = START, []
        for r in perm:
            p = shortest_path(cur, r)
            seq += p
            cur = r
        seq += shortest_path(cur, START)
        if best is None or len(seq) < len(best):
            best = seq
    return best


spots = [r for r in nb.ROOMS if r != START]
lengths = Counter()
examples = {}
for combo in itertools.combinations(spots, 3):
    seq = tour(combo)
    n = len(seq)
    lengths[n] += 1
    examples.setdefault(n, (combo, "".join(seq)))

print("九间屋子，门厅出发，收齐三张纸再回门厅：最短步数分布")
for n in sorted(lengths):
    combo, seq = examples[n]
    print(f"  {n} 步 × {lengths[n]:2d} 种布局   例：{combo}  路线 {seq}")

print("\n固定预算下能否『刚好抄完』（步数 + 3 次抄写）")
for wakes in (10, 11, 12, 13, 14):
    ok = sum(c for n, c in lengths.items() if n + 3 <= wakes)
    need_extra = {n: wakes - (n + 3) for n in sorted(lengths)}
    print(f"  WAKES={wakes:2d}: {ok}/{sum(lengths.values())} 布局可通关；"
          f"余量 {need_extra}")

print("\n原版十步扫荡 + 3 次抄写 = 13 次醒来")
print("  固定 14 次时仍有余量；固定 12 次时差 1；固定 11 次时差 2")

print("\n各布局最优路线长度（用于动态预算 = 最短步数 + 3 + 余量）")
for combo in itertools.combinations(spots, 3):
    n = len(tour(combo))
    if n >= 7:
        print(f"  {combo} -> {n} 步")
