#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本子 v0.2 —— 自动化测试

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
if not os.path.exists(NOTEBOOK):
    NOTEBOOK = os.path.join(HERE, "notebook_v02.py")

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
    check("进隐藏房 pieces 仍 0（不自动抄）", len(g.pieces) == 0)
    check("进隐藏房纸仍在桌上", hidden[0] in g.hidden)
    ok, out = quiet(g.copy)
    check("抄写成功", ok is True)
    check("抄后 pieces=1", len(g.pieces) == 1)
    check("抄后 hidden 移除", hidden[0] not in g.hidden)
    check("原话落成了本子的一页", any(p["piece"] and p["text"] in nb.PIECES for p in g.pages))
    check("抄写写了 copy 日志", any(e[0] == "copy" for e in g.log), str(g.log[-1:]))

    g = nb.Notebook(seed=2)
    round_before = g.round
    ok, out = quiet(g.copy)
    check("没有纸时抄：返回 False", ok is False)
    check("没有纸时抄：不花醒来", g.round == round_before)
    check("没有纸时抄：有提示", "没有纸可抄" in out)

    g = nb.Notebook(seed=2)
    room = next(iter(g.hidden))
    walk(g, path_to((0, 0), room))
    # 找一间不是纸房的邻屋，离开再回来
    for d in "nsew":
        dx, dy = nb.ARROWS[d]
        nxt = (g.pos[0] + dx, g.pos[1] + dy)
        if nxt in nb.ROOMS and nxt not in g.hidden:
            walk(g, [d])
            break
    check("不抄离开：纸还在", room in g.hidden)
    walk(g, path_to(g.pos, room))
    check("重进纸房：还能看见", room in g.hidden)
    ok, _ = quiet(g.copy)
    check("重进纸房：能抄", ok is True)
    walk(g, path_to(g.pos, room))
    check("抄过再回：不再有纸", room not in g.hidden)

    # 防御分支：本子三页全是原话时，抄写失败且不花醒来、不丢纸
    g = nb.Notebook(seed=4)
    g.pages = [{"text": p, "ink": 0, "real": True, "piece": True} for p in nb.PIECES]
    g.pieces = list(nb.PIECES)
    g.pos = (1, 1)
    g.hidden = {(1, 1): "第四张？"}
    round_before = g.round
    ok, out = quiet(g.copy)
    check("满本抄写：返回 False", ok is False)
    check("满本抄写：不花醒来", g.round == round_before)
    check("满本抄写：纸没丢", (1, 1) in g.hidden)
    check("满本抄写：pieces 没变", len(g.pieces) == 3)

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
    check("验不存在的页：不留痕", not any(e[0] == "check" for e in g.log))

    g = nb.Notebook(seed=12)
    ok60, _ = quiet(g.write, "字" * 60)
    ok61, out61 = quiet(g.write, "字" * 61)
    check("60 字可以写", ok60 is True)
    check("61 字被拒绝并提示", ok61 is False and "太长了" in out61)

    # v0.3：后门要三张原话，还要你亲手验过一页
    g = nb.Notebook(seed=13)
    g.pieces = ["a", "b", "c"]
    ok, out = quiet(g.check_end)
    check("3 原话在门厅但没验过：不赢", g.over is None)
    check("3 原话没验过：门提示第二道锁", "验过一页" in out)
    quiet(g.check_end)
    check("提示只出一次", g.hinted is True)

    g = nb.Notebook(seed=13)
    g.pieces = ["a", "b", "c"]
    quiet(g.verify, 1)                   # 验的是开场页，也算验过
    g.check_end()
    check("验过一页（哪怕验的是开场页）：赢", g.over == "win")

    g = nb.Notebook(seed=13)
    g.pieces = ["a", "b", "c"]
    quiet(g.verify, 1)
    g.pos = (1, 1)
    g.check_end()
    check("验过了但不在门厅：不赢", g.over is None)

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
    check("醒来耗尽判负", g.over == "lose" and g.round == nb.WAKES + 1, str(g.round))


def test_e2e():
    group("端到端（真实 stdin）")

    # 按 seed 3 的真实布局算一条最短路线；每进一间纸房先 `抄`
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
    cmds, pos, copied = [], (0, 0), set()
    for d in seq:
        cmds.append(d)
        dx, dy = nb.ARROWS[d]
        pos = (pos[0] + dx, pos[1] + dy)
        if pos in rooms and pos not in copied:
            cmds.append("抄")
            copied.add(pos)
            if len(copied) == 1:                # v0.3：抄完第一张顺手验它（后门要验过一页）
                cmds.append("验 2")
    r = run(["--plain", "--seed", "3"], "\n".join(cmds) + "\n")
    out = r.stdout
    check("胜局：退出码 0", r.returncode == 0)
    check("胜局：后门开了", "后门开了" in out)
    check("胜局：已抄原话 3/3", "已抄原话 3/3" in out)
    check("胜局：验过一页（原话）", "原话不用编号" in out)
    check("胜局：撕掉 0 页", "你验出来 0 页" in out)
    check("--plain 没有颜色转义", "\x1b[" not in out)

    r = run(["--plain", "--seed", "3"], "n\ns\n" * 7)
    check("败局：醒来耗尽", r.returncode == 0 and f"第 {nb.WAKES} 次醒来用完了" in r.stdout)

    r = run(["--plain", "--seed", "2"], "s\n看\n写 " + "字" * 61 + "\n验 9\n乱打\n退\n")
    out = r.stdout
    check("无效指令：不花醒来", f"第 1/{nb.WAKES} 次醒来" in out and f"第 2/{nb.WAKES} 次醒来" not in out)
    check("无效指令：各有提示", all(k in out for k in ("那边没有门", "太长了", "没有这一页", "不认识")))
    check("帮助里提到抄", "抄" in out and "不认识" in out)
    check("退：打印结算", "这一局：原话" in out)

    r = run(["--plain", "--seed", "13"], "验 1\n看\n退\n")
    out = r.stdout
    check("B1 端到端：不撕开场页", "不是你写的" not in out)
    check("B1 端到端：本子没被清空", "（空的。你一页都没给自己留。）" not in out)


def _route_cost(hidden, route, copy=True, stop_at_three=False, verify=True):
    """按固定顺序走；copy 时进纸房抄 1 次；verify 时第一次抄完顺手验一页（后门要）。"""
    pos, got, cost, done = (0, 0), set(), 0, False
    for ch in route:
        dx, dy = nb.ARROWS[ch]
        pos = (pos[0] + dx, pos[1] + dy)
        cost += 1
        if pos in hidden and pos not in got:
            got.add(pos)
            if copy:
                cost += 1
                if verify and not done:
                    cost += 1
                    done = True
                if stop_at_three and len(got) == 3:
                    cost += abs(pos[0]) + abs(pos[1])
                    return cost
    return cost


def _optimal_cost(hidden):
    best = None
    for order in itertools.permutations(hidden):
        cur, cost = (0, 0), 0
        for r in order:
            cost += abs(cur[0] - r[0]) + abs(cur[1] - r[1])
            cur = r
        cost += abs(cur[0]) + abs(cur[1]) + 4      # 3 次抄 + 1 次验
        best = cost if best is None else min(best, cost)
    return best


def test_balance():
    group("平衡性（56 布局 + 300 种子）")

    sweep = "nneeswseww"
    ham = "eennwwse"             # 8 步哈密顿，终点客厅 (1,1)
    spots = [r for r in nb.ROOMS if r != (0, 0)]
    layouts = list(itertools.combinations(spots, 3))

    full56 = sum(_route_cost({r: "x" for r in L}, sweep) <= nb.WAKES for L in layouts)
    stop56 = sum(_route_cost({r: "x" for r in L}, sweep, stop_at_three=True) <= nb.WAKES for L in layouts)
    ham56 = sum(_route_cost({r: "x" for r in L}, ham, stop_at_three=True) <= nb.WAKES for L in layouts)
    opt56 = sum(_optimal_cost({r: "x" for r in L}) <= nb.WAKES for L in layouts)

    check("56 布局：走完全程+抄 0 胜", full56 == 0, str(full56))
    check("56 布局：扫到第三张即回 35 胜", stop56 == 35, str(stop56))
    check("56 布局：8 步哈密顿 35 胜", ham56 == 35, str(ham56))
    check("56 布局：全知 56 胜", opt56 == 56, str(opt56))

    wins_full = wins_stop = wins_ham = wins_opt = 0
    bad_pages = 0
    loss_steps = {}
    opt_costs = {}
    for seed in range(300):
        hidden = dict(nb.Notebook(seed=seed).hidden)
        wins_full += _route_cost(hidden, sweep) <= nb.WAKES
        c = _route_cost(hidden, sweep, stop_at_three=True)
        if c <= nb.WAKES:
            wins_stop += 1
        else:
            # 复算第三张在第几步：用同一路线重放
            pos, got = (0, 0), set()
            for i, ch in enumerate(sweep, 1):
                dx, dy = nb.ARROWS[ch]
                pos = (pos[0] + dx, pos[1] + dy)
                if pos in hidden and pos not in got:
                    got.add(pos)
                    if len(got) == 3:
                        loss_steps[i] = loss_steps.get(i, 0) + 1
                        break
        wins_ham += _route_cost(hidden, ham, stop_at_three=True) <= nb.WAKES
        oc = _optimal_cost(hidden)
        wins_opt += oc <= nb.WAKES
        opt_costs[oc] = opt_costs.get(oc, 0) + 1
        bad_pages += len(nb.Notebook(seed=seed).pages) > nb.PAGES

    check("300 种子：走完全程+抄 0 胜", wins_full == 0, str(wins_full))
    check("300 种子：扫到第三张即回 180 胜", wins_stop == 180, str(wins_stop))
    check("300 种子：8 步哈密顿 55%–70%", 165 <= wins_ham <= 210, str(wins_ham))
    check("300 种子：全知 300 胜", wins_opt == 300, str(wins_opt))
    check("输局第三张都在第 8 步", loss_steps == {8: 120}, str(loss_steps))
    check("全知成本分布 8/10/12", opt_costs == {8: 4, 10: 108, 12: 188}, str(opt_costs))
    check("页数从不超 3", bad_pages == 0)

    # 实跑一局「走完全程 + 抄」：第 13 次成本前就耗尽，且本子不超页
    g = nb.Notebook(seed=0)
    for d in sweep:
        if g.over:
            break
        ok, _ = quiet(g.move, d)
        if ok:
            quiet(g.check_end)
            if not g.over:
                g.next_round()
        if g.pos in g.hidden and not g.over:
            ok, _ = quiet(g.copy)
            if ok:
                quiet(g.check_end)
                if not g.over:
                    g.next_round()
    check("实跑全程扫荡+抄：判负", g.over == "lose", str(g.over))
    check("实跑全程扫荡+抄：预算耗尽", g.round == nb.WAKES + 1, str(g.round))
    check("实跑全程扫荡+抄：页数≤3", len(g.pages) <= nb.PAGES)


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
    test_balance()
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
