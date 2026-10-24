# -*- coding: utf-8 -*-
"""信息量实验：开局知道 0 / 1 / 3 张原话的位置时，盲玩最优胜率。

用于回答「固定 12 次醒来是否只剩运气」：如果知道 0 张时上界只有 62.5%，
而知道 1 张能到 90%+，说明「给一条线索」是比加预算更省的补救。
"""
import functools
from itertools import combinations

ROOMS = [(x, y) for y in range(3) for x in range(3)]
START = (0, 0)
IDX = {r: i for i, r in enumerate(ROOMS)}
ARROWS = {"n": (0, 1), "s": (0, -1), "e": (1, 0), "w": (-1, 0)}


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors(p):
    out = []
    for dx, dy in ARROWS.values():
        q = (p[0] + dx, p[1] + dy)
        if q in ROOMS:
            out.append(q)
    return out


EMPTY0 = 1 << IDX[START]


def popcount(x):
    return bin(x).count("1")


@functools.lru_cache(maxsize=None)
def V(pos, empty_mask, known_mask, k, b):
    """known_mask: 已知有纸但还没抄的屋子；k: 已抄张数；b: 剩余醒来。"""
    if k == 3:
        return 1.0 if b >= dist(pos, START) else 0.0
    if b <= 0:
        return 0.0
    unknown_total = 3 - k - popcount(known_mask)
    unvisited = [r for r in ROOMS
                 if not (empty_mask >> IDX[r]) & 1 and not (known_mask >> IDX[r]) & 1]
    n_unknown_rooms = len([r for r in unvisited if not (known_mask >> IDX[r]) & 1])
    best = 0.0
    for q in neighbors(pos):
        i = IDX[q]
        if (empty_mask >> i) & 1:
            best = max(best, V(q, empty_mask, known_mask, k, b - 1))
        elif (known_mask >> i) & 1:
            if b >= 2:
                best = max(best, V(q, empty_mask | (1 << i), known_mask & ~(1 << i),
                                   k + 1, b - 2))
        else:
            p = unknown_total / n_unknown_rooms if n_unknown_rooms else 0.0
            v_piece = V(q, empty_mask | (1 << i), known_mask, k + 1, b - 2) if b >= 2 else 0.0
            v_empty = V(q, empty_mask | (1 << i), known_mask, k, b - 1)
            best = max(best, p * v_piece + (1 - p) * v_empty)
    return best


def rate(known_rooms, b):
    known_mask = 0
    for r in known_rooms:
        known_mask |= 1 << IDX[r]
    return V(START, EMPTY0, known_mask, 0, b)


if __name__ == "__main__":
    spots = [r for r in ROOMS if r != START]
    print("开局知道 0 张：")
    for b in (10, 11, 12, 13):
        print(f"  WAKES={b:2d}: {V(START, EMPTY0, 0, 0, b):.1%}")
    print("\n开局知道 1 张（8 种位置平均 / 最差）：")
    for b in (10, 11, 12, 13):
        vals = [rate([r], b) for r in spots]
        print(f"  WAKES={b:2d}: 平均 {sum(vals)/len(vals):.1%}  最差 {min(vals):.1%}  "
              f"最好 {max(vals):.1%}")
    print("\n开局知道 2 张（28 种位置组合平均 / 最差）：")
    for b in (10, 11, 12, 13):
        vals = [rate(list(pair), b) for pair in combinations(spots, 2)]
        print(f"  WAKES={b:2d}: 平均 {sum(vals)/len(vals):.1%}  最差 {min(vals):.1%}  "
              f"最好 {max(vals):.1%}")
    print("\n开局知道全部 3 张（56 种布局，平均胜率 / 最差布局余量）：")
    layouts = list(combinations(spots, 3))
    for b in (11, 12, 13):
        vals = [rate(list(L), b) for L in layouts]
        win = sum(1 for v in vals if v > 0) / len(vals)
        print(f"  WAKES={b:2d}: 胜率 {win:.1%}  （知道位置后是确定性路线题，"
              f"成本 4/6/8+3 = 7/9/11）")
