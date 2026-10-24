# -*- coding: utf-8 -*-
"""领航员的盲玩最优策略上界：部分可观测下的动态规划。

玩家不知道三张原话在哪，只知道：
  - 已经进过、且没有纸的屋子（空屋）；
  - 已经抄到几张；
  - 剩下没进的屋子中，纸均匀分布。
每进一间没进过的屋，以 (剩余纸数)/(剩余未进屋子数) 的概率撞见纸；
撞见就抄（抄写花 1 次醒来）。抄满三张后走最短路回门厅。
求预算 b 下的最大胜率，作为「盲玩高手」的上界。
"""
import functools
from itertools import combinations

ROOMS = [(x, y) for y in range(3) for x in range(3)]
START = (0, 0)
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


EMPTY0 = 1 << ROOMS.index(START)  # 门厅已知无纸


@functools.lru_cache(maxsize=None)
def V(pos, empty_mask, k, b):
    """empty_mask: 已确认没有纸的屋子（含门厅）；k: 已抄张数；b: 剩余醒来。"""
    if k == 3:
        return 1.0 if b >= dist(pos, START) else 0.0
    if b <= 0:
        return 0.0
    unvisited = [r for r in ROOMS if not (empty_mask >> ROOMS.index(r)) & 1]
    # 如果所有屋子都进过且还没凑齐，不可能赢
    if not unvisited and k < 3:
        return 0.0
    best = 0.0
    for q in neighbors(pos):
        idx = ROOMS.index(q)
        known_empty = (empty_mask >> idx) & 1
        if known_empty:
            # 已知空屋：只花一步
            best = max(best, V(q, empty_mask, k, b - 1))
        else:
            # 未进过的屋：揭示
            n_unv = len(unvisited)
            n_piece = 3 - k
            p_piece = n_piece / n_unv if n_unv else 0.0
            # 有纸：移动 1 + 抄写 1，抄完这间变空屋
            v_piece = 0.0
            if b >= 2:
                v_piece = V(q, empty_mask | (1 << idx), k + 1, b - 2)
            # 没纸：移动 1，这间变空屋
            v_empty = V(q, empty_mask | (1 << idx), k, b - 1)
            best = max(best, p_piece * v_piece + (1 - p_piece) * v_empty)
    return best


def best_first_move(b):
    """返回第一步的最优动作及其胜率。"""
    best = (-1, None)
    for q in neighbors(START):
        idx = ROOMS.index(q)
        if (EMPTY0 >> idx) & 1:
            v = V(q, EMPTY0, 0, b - 1)
        else:
            n_piece = 3
            v_piece = V(q, EMPTY0 | (1 << idx), 1, b - 2) if b >= 2 else 0.0
            v_empty = V(q, EMPTY0 | (1 << idx), 0, b - 1)
            v = (n_piece / 8) * v_piece + (1 - n_piece / 8) * v_empty
        if v > best[0]:
            best = (v, q)
    return best


if __name__ == "__main__":
    print("盲玩最优策略（知道空屋与剩余纸数，不知道纸在哪）")
    for b in range(8, 16):
        print(f"  WAKES={b:2d}: 胜率上界 {V(START, EMPTY0, 0, b):.1%}  第一步 {best_first_move(b)}")
