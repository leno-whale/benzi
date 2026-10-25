#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本子 v0.4「回执」—— 非交互演示

    python demo_v04.py

一局：seed 3，最短路线收齐三张原话，赢，留一句话进回执。
二局：同一份回执，让回声页出现，再把它验出来。
临时回执放在本目录 `_tmp/demo/`（本沙箱里系统 tempfile 会挂起）。
"""
import contextlib
import importlib.util
import io
import itertools
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 团队目录里叫 notebook_v04.py，进根目录后叫 notebook.py —— 两个名字都认。
_CAND = [os.path.join(HERE, "notebook.py"), os.path.join(HERE, "notebook_v04.py")]
NB = next((p for p in _CAND if os.path.exists(p)), _CAND[0])
TMP = os.path.join(HERE, "_tmp", "demo")
RECEIPT = os.path.join(TMP, "回执.md")
LEAVE = "上一次我走到后门，门缝里什么也没有。这次留一句。"


def load_nb():
    spec = importlib.util.spec_from_file_location("nb", NB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(lines, *args):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, NB, "--plain", "--seed", "3", "--receipt", RECEIPT, *args],
        input="\n".join(lines) + "\n", capture_output=True, text=True,
        encoding="utf-8", env=env)


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def route_cmds(nb):
    g = nb.Notebook(seed=3)
    rooms = list(g.hidden)

    def one(perm):
        cur, seq = (0, 0), []
        for r in perm:
            while cur != r:
                dx, dy = r[0] - cur[0], r[1] - cur[1]
                if dx > 0:
                    seq.append("e"); cur = (cur[0] + 1, cur[1])
                elif dx < 0:
                    seq.append("w"); cur = (cur[0] - 1, cur[1])
                elif dy > 0:
                    seq.append("n"); cur = (cur[0], cur[1] + 1)
                else:
                    seq.append("s"); cur = (cur[0], cur[1] - 1)
        while cur != (0, 0):
            dx, dy = -cur[0], -cur[1]
            if dx > 0:
                seq.append("e"); cur = (cur[0] + 1, cur[1])
            elif dx < 0:
                seq.append("w"); cur = (cur[0] - 1, cur[1])
            elif dy > 0:
                seq.append("n"); cur = (cur[0], cur[1] + 1)
            else:
                seq.append("s"); cur = (cur[0], cur[1] - 1)
        return seq

    seq = min((one(p) for p in itertools.permutations(rooms)), key=len)
    actions, pos, copied = [], (0, 0), set()
    for d in seq:
        actions.append(d)
        dx, dy = nb.ARROWS[d]
        pos = (pos[0] + dx, pos[1] + dy)
        if pos in rooms and pos not in copied:
            actions.append("抄")
            copied.add(pos)
            if len(copied) == 1:
                actions.append("验 2")
    return actions


def main():
    if not os.path.exists(NB):
        print("找不到 notebook_v04.py")
        return 1
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    nb = load_nb()

    print("=== 第一局：收纸、赢、留话 ===")
    actions = route_cmds(nb)
    print("动作：", " ".join(actions), f"（{len(actions)} 次醒来）")
    r = run(actions + [LEAVE], "--name", "演示的人")
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        return 1
    tail = [ln for ln in r.stdout.splitlines() if ln.strip()][-8:]
    print("\n".join(tail))
    if "后门开了" not in r.stdout:
        print("!! 第一局没有赢")
        return 1
    if not os.path.exists(RECEIPT):
        print("!! 没有写回执")
        return 1

    print("\n=== 回执文件（前 12 行） ===")
    with open(RECEIPT, encoding="utf-8") as f:
        print("\n".join(f.read().splitlines()[:12]))

    print("\n=== 第二局：回声页出现、验出来 ===")
    st = nb.ReceiptStore(RECEIPT)
    g = nb.Notebook(seed=3, receipt=st, echo="always")
    wake = g.echo_wake
    echo_text = g.echo_text
    if wake is None:
        print("!! 第二局没有排到回声")
        return 1
    print(f"回声排在第 {wake} 次醒来；门缝里的留话：「{echo_text}」")
    with contextlib.redirect_stdout(io.StringIO()):
        for _ in range(wake - 1):
            g.next_round()
    idx = next(i for i, p in enumerate(g.pages, 1) if p.get("echo") is True)
    print(f"回声页出现在第 {idx} 页；走 {wake - 1} 次，然后「验 {idx}」")
    moves = ["n", "s"] * ((wake - 1 + 1) // 2)
    r2 = run(moves[:wake - 1] + [f"验 {idx}", "退"],
             "--echo", "always", "--name", "下一个人")
    if r2.returncode != 0:
        print(r2.stdout[-2000:])
        print(r2.stderr[-2000:])
        return 1
    tail2 = [ln for ln in r2.stdout.splitlines() if ln.strip()][-14:]
    print("\n".join(tail2))
    if "门缝" not in r2.stdout or echo_text not in r2.stdout:
        print("!! 第二局没有验到回声")
        return 1

    print("\n=== 演示通过 ===")
    print(f"回执：{RECEIPT}（跑完保留，可自己打开看）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
