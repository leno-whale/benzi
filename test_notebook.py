#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本子 —— 自动化测试

    python test_notebook.py

安静跑完：只报每组通过数，失败项逐条列出。全过退出 0，否则退出 1。
"""
import contextlib
import importlib.util
import io
import itertools
import os
import subprocess
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.join(HERE, "notebook.py")

_spec = importlib.util.spec_from_file_location("nb", NOTEBOOK)
nb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nb)

GROUPS = []      # [标题, 总数, 通过数]
FAILS = []


def group(title):
    GROUPS.append([title, 0, 0])


def check(name, cond, detail=""):
    g = GROUPS[-1]
    g[1] += 1
    if cond:
        g[2] += 1
    else:
        FAILS.append(name)
        print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ""))


def quiet(fn, *args, **kwargs):
    """调用并吞掉游戏输出，返回 (返回值, 输出文本)。"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    return result, buf.getvalue()


def run(args, stdin):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, NOTEBOOK, *args],
        input=stdin, capture_output=True, text=True, encoding="utf-8", env=env,
    )


def path_to(start, goal):
    """从 start 走到 goal 的最短方向序列。"""
    q = deque([(start, [])])
    seen = {start}
    while q:
        (x, y), steps = q.popleft()
        if (x, y) == goal:
            return steps
        for d in "nsew":
            dx, dy = nb.ARROWS[d]
            nxt = (x + dx, y + dy)
            if nxt in nb.ROOMS and nxt not in seen:
                seen.add(nxt)
                q.append((nxt, steps + [d]))
    return []


def walk(g, steps):
    """按 play() 的规则逐步走：成功才结算、才推进醒来次数。"""
    for d in steps:
        acted, _ = quiet(g.move, d)
        if acted:
            g.check_end()
            if not g.over:
                g.next_round()


def test_api():
    group("API 规则")

    g = nb.Notebook(seed=1)
    hidden = list(g.hidden.keys())
    check("开局本子只有 1 页", len(g.pages) == 1)
    check("开局站在门厅", g.pos == (0, 0))
    check("开局是第 1 次醒来", g.round == 1)
    check("三张原话各有其屋", len(hidden) == 3 and len(set(g.hidden.values())) == 3)
    check("门厅里不藏原话", (0, 0) not in hidden)

    acted, out = quiet(g.move, "s")
    check("撞墙返回 False", acted is False)
    check("撞墙不移动", g.pos == (0, 0))
    check("撞墙有提示", "那边没有门" in out)

    g = nb.Notebook(seed=1)
    walk(g, path_to((0, 0), hidden[0]))
    check("进隐藏房拿到原话", len(g.pieces) >= 1)
    check("原话落成了本子的一页", any(p["piece"] and p["text"] in nb.PIECES for p in g.pages))

    g = nb.Notebook(seed=2)
    for t in ("甲甲", "乙乙", "丙丙"):
        quiet(g.write, t)
    oldest = g.pages[0]["text"]
    quiet(g.write, "丁丁")
    check("写满后挤掉最老一页", oldest not in [p["text"] for p in g.pages])
    check("本子始终只有 3 页", len(g.pages) == 3)

    g = nb.Notebook(seed=3)
    quiet(g.push, "原话A", piece=True)
    quiet(g.push, "笔记乙")
    quiet(g.push, "笔记丙")
    quiet(g.write, "笔记丁")
    check("原话不会被挤掉", any(p["text"] == "原话A" for p in g.pages))

    g = nb.Notebook(seed=4)
    for t in ("p1", "p2", "p3"):
        quiet(g.push, t, piece=True)
    ok, out = quiet(g.write, "再写一句")
    check("三页全是原话时写不进去", ok is False and "本子满了" in out)

    g = nb.Notebook(seed=5)
    for _ in range(12):
        g.next_round()
    fakes = [e[1] for e in g.log if e[0] == "fake"]
    check("伪页在第 3/6/9/12 次醒来出现", fakes == [3, 6, 9, 12], str(fakes))

    g = nb.Notebook(seed=6)
    g.next_round()                       # 走到第 2 次醒来
    check("第 1、2 次醒来没有伪页", g.round == 2 and not [e for e in g.log if e[0] == "fake"])

    g = nb.Notebook(seed=7)
    g.next_round()
    g.next_round()                       # 走到第 3 次醒来，伪页出现
    fake_idx = next(i for i, p in enumerate(g.pages) if not p["real"])
    ok, out = quiet(g.verify, fake_idx + 1)
    check("验伪页：撕掉", ok and len(g.pages) == 1)
    check("验伪页：说明不是你写的", "不是你写的" in out)

    g = nb.Notebook(seed=8)
    quiet(g.write, "我的笔记")
    ok, out = quiet(g.verify, 2)
    check("验真笔记：保留", ok and len(g.pages) == 2)
    check("验真笔记：认出是自己", "是你" in out)

    g = nb.Notebook(seed=9)
    quiet(g.push, "原话X", piece=True)
    ok, out = quiet(g.verify, 2)
    check("验原话：保留并认出", ok and len(g.pages) == 2 and "原话不用编号" in out)

    g = nb.Notebook(seed=10)
    ok, out = quiet(g.verify, 1)
    check("B1 回归：开局验第 1 页不撕", ok and len(g.pages) == 1)
    check("B1 回归：不再误判为伪造", "不是你写的" not in out)
    check("B1 回归：说明是上一轮的自己", "旧的" in out)

    g = nb.Notebook(seed=11)
    ok, out = quiet(g.verify, 9)
    check("验不存在的页：失败并提示", ok is False and "没有这一页" in out)

    g = nb.Notebook(seed=12)
    ok60, _ = quiet(g.write, "字" * 60)
    ok61, out61 = quiet(g.write, "字" * 61)
    check("60 字可以写", ok60 is True)
    check("61 字被拒绝并提示", ok61 is False and "太长了" in out61)

    g = nb.Notebook(seed=13)
    g.pieces = ["a", "b", "c"]
    g.check_end()
    check("3 原话在门厅：赢", g.over == "win")

    g = nb.Notebook(seed=13)
    g.pieces = ["a", "b", "c"]
    g.pos = (1, 1)
    g.check_end()
    check("3 原话但不在门厅：没赢", g.over is None)

    g = nb.Notebook(seed=13)
    g.pieces = ["a", "b"]
    g.check_end()
    check("2 原话在门厅：没赢", g.over is None)

    g = nb.Notebook(seed=13)
    for _ in range(nb.WAKES):
        g.next_round()
    check("第 15 次醒来：耗尽判负", g.over == "lose")


def test_e2e():
    group("端到端（真实 stdin）")

    # 按 seed 3 的真实布局算一条最短路线：不写字、不验页，直接通关
    g = nb.Notebook(seed=3)
    rooms = list(g.hidden.keys())

    def route_len(perm):
        cur, seq = (0, 0), []
        for r in perm:
            p = path_to(cur, r)
            seq += p
            cur = r
        back = path_to(cur, (0, 0))
        return len(seq) + len(back), seq + back

    seq = min((route_len(p) for p in itertools.permutations(rooms)), key=lambda t: t[0])[1]
    r = run(["--plain", "--seed", "3"], "\n".join(seq) + "\n")
    out = r.stdout
    check("胜局：退出码 0", r.returncode == 0)
    check("胜局：后门开了", "后门开了" in out)
    check("胜局：原话 3/3", "原话 3/3" in out)
    check("胜局：全程没验过页", "你验出来 0 页" in out)
    check("--plain 没有颜色转义", "\x1b[" not in out)

    r = run(["--plain", "--seed", "3"], "n\ns\n" * 7)
    check("败局：醒来耗尽", r.returncode == 0 and "第 14 次醒来用完了" in r.stdout)

    r = run(["--plain", "--seed", "2"], "s\n看\n写 " + "字" * 61 + "\n验 9\n乱打\n退\n")
    out = r.stdout
    check("无效指令：不花醒来", "第 1/14 次醒来" in out and "第 2/14 次醒来" not in out)
    check("无效指令：各有提示", all(k in out for k in ("那边没有门", "太长了", "没有这一页", "不认识")))
    check("退：打印结算", "这一局：原话" in out)

    r = run(["--plain", "--seed", "13"], "验 1\n看\n退\n")
    out = r.stdout
    check("B1 端到端：不撕开场页", "不是你写的" not in out)
    check("B1 端到端：本子没被清空", "（空的。你一页都没给自己留。）" not in out)


def test_sweep():
    group("300 种子扫荡")

    sweep = "nneeswseww"          # 走遍 9 间、回门厅，共 10 步
    wins, dropped, size_bad = 0, 0, 0
    bad = []
    for seed in range(300):
        g = nb.Notebook(seed=seed)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            for d in sweep:
                if not g.move(d):
                    break
                g.check_end()
                if not g.over:
                    g.next_round()
        if g.over == "win":
            wins += 1
        else:
            bad.append(seed)
        if len(g.pieces) != nb.PIECES_NEEDED:
            dropped += 1
        if len(g.pages) > nb.PAGES:
            size_bad += 1
    check("10 步全屋扫荡：300 局全胜", wins == 300, f"没赢的种子 {bad[:5]}")
    check("扫荡：原话一张不落", dropped == 0)
    check("扫荡：本子从不超页", size_bad == 0)


def _pg(text, real=True, piece=False, ink=3):
    return {"text": text, "ink": ink, "real": real, "piece": piece}


def _blank(seed=1):
    g = nb.Notebook(seed=seed)
    g.pages, g.pieces, g.log = [], [], []
    return g


def test_endings():
    group("七个结局")

    def case_a():
        g = _blank()
        g.pages = [_pg(p, piece=True) for p in nb.PIECES]
        g.pieces = list(nb.PIECES)
        g.over = "win"
        g.log = [("write", 2), ("evict", "我写的那句", True, False), ("fake", 3)]
        g.own_evicted = ["我写的那句"]
        return g

    def case_b():
        g = _blank()
        g.pages = [_pg(p, piece=True) for p in nb.PIECES]
        g.pieces = list(nb.PIECES)
        g.over = "win"
        g.log = [("fake", 3)]
        return g

    def case_c():
        g = _blank()
        g.pages = [_pg("上一轮的句子"), _pg("你已经想清楚了，照着感觉走就对了。", real=False, ink=0),
                   _pg(nb.PIECES[0], piece=True)]
        g.pieces = [nb.PIECES[0]]
        g.pos = (1, 2)
        g.over = "lose"
        g.log = [("evict", "旧的", True, False), ("fake", 3)]
        return g

    def case_d():
        g = _blank()
        g.pages = [_pg("我写的"), _pg(nb.PIECES[0], piece=True)]
        g.pieces = [nb.PIECES[0]]
        g.pos = (2, 1)
        g.over = "lose"
        g.log = [("write", 2), ("fake", 3), ("caught", 2, "本子上的都是你自己写的，不用验。")]
        return g

    def case_e():
        g = _blank()
        g.pages = [_pg(p, piece=True) for p in nb.PIECES]
        g.pieces = list(nb.PIECES)
        g.pos = (1, 2)
        g.over = "lose"
        g.log = [("fake", 3), ("fake", 6), ("fake", 9), ("fake", 12)]
        return g

    def case_f():
        g = case_e()
        g.pos = (2, 2)
        g.log = g.log + [("full", 13, "我想留一句自己的话。")]
        return g

    def case_g():
        g = _blank()
        g.pages = [_pg("我写的"), _pg(nb.PIECES[0], piece=True)]
        g.pieces = [nb.PIECES[0]]
        g.pos = (1, 0)
        g.over = "lose"
        g.log = [("write", 2), ("fake", 3), ("evict", "出口在北边，别再往深处去了。", False, False)]
        return g

    want = {"A": case_a, "B": case_b, "C": case_c, "D": case_d,
            "E": case_e, "F": case_f, "G": case_g}
    for code, make in want.items():
        g = make()
        got = g.ending()
        check(f"结局 {code}（{nb.TITLES[code]}）判得对", got == code, f"实际 {got}")
        lines = g.ending_text(got)
        left = [ln for ln in lines if "{" in ln or "}" in ln]
        check(f"结局 {code} 占位符填干净", not left, str(left[:1]))
        check(f"结局 {code} 有文本", len(lines) >= 10 and any(lines))

    g = case_a()
    t = "\n".join(g.ending_text("A"))
    check("A 引用了自己写的原句", "我写的那句" in t)
    g = case_c()
    t = "\n".join(g.ending_text("C"))
    check("C 引用了那页假话", "照着感觉走" in t)
    check("C 页码写对", "第 2 页" in t)
    g = case_c()
    g.pages = [_pg(nb.PIECES[0], piece=True), _pg("假话", real=False, ink=0)]
    g.log = [("fake", 3)]
    t = "\n".join(g.ending_text("C"))
    check("C 没撕过纸时换成另一句", "一页也没撕过" in t)
    g = case_f()
    t = "\n".join(g.ending_text("F"))
    check("F 引用想写没写进去的那句", "我想留一句自己的话" in t)
    g = case_d()
    g.pages = []
    t = "\n".join(g.ending_text("D"))
    check("D 本子空着时兜得住", "一页都没给自己留" in t)
    g = case_g()
    t = "\n".join(g.ending_text("G"))
    check("G 引用被挤掉的假话", "出口在北边" in t)
    check("G 报出你的页数", "1 页是你的字" in t)


def main():
    print("本子 自动化测试\n")
    test_api()
    test_endings()
    test_e2e()
    test_sweep()
    print()
    for title, total, passed in GROUPS:
        print(f"  {title}：{passed}/{total}")
    if FAILS:
        print(f"\n失败 {len(FAILS)} 项：{'、'.join(FAILS)}")
        sys.exit(1)
    print("\n全部通过。")
    sys.exit(0)


if __name__ == "__main__":
    main()
