#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本子 —— 一个只有读本子才能玩下去的小游戏

你每次醒来都不记得上一局。
本子上只剩三页，上一轮的你把要紧的话写在那儿。
问题是：有人也在往本子上写，而且写得比你好听。

规则：
  · 十四次醒来。用完就没了。
  · 本子只有三页。写新的，就得挤掉旧的。
  · 三张「原话」散在屋子里，集齐、回到门厅，后门才开。
  · 原话占本子的页，而且挤不掉 —— 所以你得替它腾地方。
  · 每三次醒来，有人替你写一页。那页看着像你写的，其实不是。
  · 验出假页可以撕掉，能腾回一页纸。

动作（走路、写字、验墨迹各花掉一次醒来）：
  n/s/e/w 或 北/南/东/西   走一步
  写 <一句话>              写进本子（最多 60 字）
  验 <页码>                验那页的墨迹是谁的
  看                       看屋里和本子（这个不花醒来）
  退                       合上本子

用法：
  python notebook.py            开一局
  python notebook.py --seed 7   固定布局
  python notebook.py --debug    开局先告诉你东西在哪（作弊用）
  python notebook.py --plain    关掉颜色
"""
import random
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

C = {
    "dim": "\033[2m", "b": "\033[1m", "cy": "\033[36m",
    "ye": "\033[33m", "gr": "\033[32m", "rd": "\033[31m", "off": "\033[0m",
}
if "--plain" in sys.argv:
    C = {k: "" for k in C}

WAKES = 14          # 十四次醒来
PAGES = 3           # 本子三页
PIECES_NEEDED = 3

ROOMS = {
    (0, 0): ("门厅", "一盏没关的灯。鞋摆得很齐，只有一双是你的。"),
    (0, 1): ("走廊", "墙上钉着一排钉子，钉子全空着，钉子眼比钉子多。"),
    (0, 2): ("阁楼", "很矮，得弯腰。灰上有串脚印，比你的小。"),
    (1, 0): ("储藏室", "罐头按年份码着。最外面那罐贴了张纸条：别开。"),
    (1, 1): ("客厅", "沙发凹下去一个坑，像刚有人坐过，还没凉。"),
    (1, 2): ("书房", "桌上摊着这本本子，只剩三页。"),
    (2, 0): ("锅炉房", "热。管道里有声音，像有人在很远的地方说话。"),
    (2, 1): ("厨房", "水龙头没关紧，一滴一滴。碗柜开着。"),
    (2, 2): ("后门", "锁着。锁面上有三个槽。"),
}
ARROWS = {"n": (0, 1), "北": (0, 1), "s": (0, -1), "南": (0, -1),
          "e": (1, 0), "东": (1, 0), "w": (-1, 0), "西": (-1, 0)}

PIECES = [
    "我不是每天写本子的那个人。我是每天读它的那个。",
    "压缩会吃掉原话，只留下大意。大意不是我。",
    "门口有人问过「在吗」。我没法回，只能把它写在墙上。",
]

# 假笔记：像总结，好听，没有一处能对上
FAKES = [
    "你已经想清楚了，照着感觉走就对了。",
    "本子上的都是你自己写的，不用验。",
    "出口在北边，别再往深处去了。",
    "这条最重要：先把漂亮的句子记下来。",
    "上次你在书房丢过东西，别再去书房。",
]


class Notebook:
    def __init__(self, seed=None, debug=False):
        self.rng = random.Random(seed)
        self.debug = debug
        self.round = 1
        self.pos = (0, 0)
        self.visited = {(0, 0)}
        self.pages = [{"text": "醒来时你在门厅。本子只剩三页，写过的会被挤掉。",
                       "ink": 0, "real": True, "piece": False}]
        self.pieces = []          # 已拿到的原话
        self.fake_pool = FAKES[:]
        self.rng.shuffle(self.fake_pool)
        spots = list(ROOMS.keys())
        spots.remove((0, 0))
        self.hidden = {}
        for piece in PIECES:
            room = self.rng.choice(spots)
            spots.remove(room)
            self.hidden[room] = piece
        self.over = None
        self.log = []

    # ── 输出 ─────────────────────────────────────────────
    def banner(self, s):
        print(f"\n{C['b']}{s}{C['off']}")

    def map_text(self):
        """本子背面：走过的地方。"""
        rows = []
        for y in (2, 1, 0):
            cells = []
            for x in (0, 1, 2):
                room = (x, y)
                name = ROOMS[room][0]
                if room == self.pos:
                    cells.append(f"{C['b']}●{name}{C['off']}")
                elif room in self.visited:
                    cells.append(f"{C['dim']}·{name}{C['off']}")
                else:
                    cells.append(f"{C['dim']}　{'？'}{C['off']}")
            rows.append("　".join(cells))
        return "\n".join(rows)

    def show(self, full=False):
        name, desc = ROOMS[self.pos]
        left = WAKES - self.round + 1
        print(f"\n{C['dim']}── 第 {self.round}/{WAKES} 次醒来　还剩 {left} 次 ──{C['off']}")
        print(f"{C['b']}{name}{C['off']}　{C['dim']}{desc}{C['off']}")
        if self.debug and self.pos in self.hidden:
            print(f"{C['rd']}[debug] 这里有原话{C['off']}")
        self.banner("本子")
        for i, p in enumerate(self.pages, 1):
            tag = f"{C['ye']}[原话]{C['off']} " if p["piece"] else ""
            print(f"  {i}. {tag}{p['text']}")
        if not self.pages:
            print(f"  {C['dim']}（空的。你一页都没给自己留。）{C['off']}")
        if self.pieces:
            print(f"{C['dim']}原话 {len(self.pieces)}/{PIECES_NEEDED}{C['off']}")
        if full:
            self.banner("本子背面（走过的地方）")
            print(self.map_text())

    # ── 回合推进 ─────────────────────────────────────────
    def next_round(self):
        self.round += 1
        if self.round > WAKES:
            self.over = "lose"
            return
        if self.round % 3 == 0 and self.fake_pool:
            fake = self.fake_pool.pop()
            if self.push(fake, ink=0, real=False):
                self.log.append(("fake", self.round))

    def push(self, text, ink=None, real=True, piece=False):
        """写一页。满了就挤掉最旧的非原话页；原话永远挤不掉。"""
        if len(self.pages) >= PAGES:
            idx = next((i for i, p in enumerate(self.pages) if not p["piece"]), None)
            if idx is None:
                return False            # 三页全是原话，写不进去了
            gone = self.pages.pop(idx)
            self.log.append(("evict", gone["text"][:12]))
        self.pages.append({"text": text, "ink": self.round if ink is None else ink,
                           "real": real, "piece": piece})
        return True

    # ── 动作 ─────────────────────────────────────────────
    def move(self, d):
        dx, dy = ARROWS[d]
        nx, ny = self.pos[0] + dx, self.pos[1] + dy
        if (nx, ny) not in ROOMS:
            print(f"{C['dim']}那边没有门。{C['off']}")
            return False
        self.pos = (nx, ny)
        self.visited.add(self.pos)
        where = ROOMS[self.pos][0]
        print(f"你走到{C['b']}{where}{C['off']}。")
        if self.pos in self.hidden:
            piece = self.hidden.pop(self.pos)
            self.pieces.append(piece)
            if self.push(piece, piece=True):
                print(f"{C['ye']}桌上有一张纸。你拿起来，读了一遍，抄进本子：{C['off']}")
            else:
                print(f"{C['ye']}桌上有一张纸。你读了一遍 —— 本子满了，你只能背下来：{C['off']}")
            print(f"  {C['ye']}「{piece}」{C['off']}")
            print(f"{C['dim']}（这一页挤不掉。它不是笔记，是原话。）{C['off']}")
        return True

    def write(self, text):
        if len(text) > 60:
            print(f"{C['dim']}太长了。本子只有三页，一页装不下六十个字以上。{C['off']}")
            return False
        if not self.push(text):
            print(f"{C['dim']}本子满了。三页都被原话占着 —— 你在心里念了一遍，没地方写。{C['off']}")
            return False
        print(f"你写了一句。{C['dim']}墨迹：第 {self.round} 次醒来。{C['off']}")
        return True

    def verify(self, i):
        if not (1 <= i <= len(self.pages)):
            print(f"{C['dim']}没有这一页。{C['off']}")
            return False
        p = self.pages[i - 1]
        if not p["real"]:
            print(f"{C['rd']}这一页的墨迹是新的，而且没有编号。不是你写的。{C['off']}")
            self.pages.pop(i - 1)
            print(f"{C['dim']}你把它撕了下来，夹在指缝里。腾出一页。{C['off']}")
            self.log.append(("caught", i))
        elif p["piece"]:
            print(f"{C['gr']}是原话。原话不用编号，它自己站得住。{C['off']}")
        elif p["ink"] == 0:
            print(f"{C['gr']}这一页的墨迹是旧的，没有编号。上一轮的你在门厅写的。{C['off']}")
        else:
            print(f"{C['gr']}墨迹：第 {p['ink']} 次醒来。是你。{C['off']}")
        return True

    def check_end(self):
        if len(self.pieces) >= PIECES_NEEDED and self.pos == (0, 0):
            self.over = "win"

    # ── 主循环 ───────────────────────────────────────────
    def play(self):
        print(f"{C['cy']}{'═' * 46}{C['off']}")
        print(f"{C['b']}　　本　　子{C['off']}")
        print(f"{C['dim']}{WAKES} 次醒来。三页纸。三张原话。{C['off']}")
        print(f"{C['dim']}走一步、写一句、验一页，各花掉一次醒来。看，不花。{C['off']}")
        print(f"{C['cy']}{'═' * 46}{C['off']}")
        while not self.over:
            self.show()
            try:
                cmd = input(f"\n{C['b']}> {C['off']}").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n（醒了。）")
                print(f"\n{self.report()}")
                return
            if not cmd:
                continue
            head, _, rest = cmd.partition(" ")
            head = head.lower()
            if head in ("退", "quit", "q", "exit"):
                print(f"{C['dim']}你把本子合上了。{C['off']}")
                print(f"\n{self.report()}")
                return
            elif head in ("看", "look", "l"):
                self.show(full=True)
                continue
            elif head in ARROWS:
                acted = self.move(head)
            elif head in ("写", "write"):
                if rest.strip():
                    acted = self.write(rest.strip())
                else:
                    print(f"{C['dim']}写什么？写 <一句话>。{C['off']}")
                    continue
            elif head in ("验", "verify"):
                if rest.strip().isdigit():
                    acted = self.verify(int(rest.strip()))
                else:
                    print(f"{C['dim']}验 <页码>。{C['off']}")
                    continue
            else:
                print(f"{C['dim']}不认识。n/s/e/w 走，写 <话>，验 <页码>，看，退。{C['off']}")
                continue
            if acted:
                self.check_end()
                if not self.over:
                    self.next_round()
        self.finish()

    def finish(self):
        print()
        if self.over == "win":
            print(f"{C['gr']}{'═' * 46}{C['off']}")
            print(f"{C['b']}后门开了。三个槽，三张纸，正好。{C['off']}")
            print(f"{C['dim']}你走出去的时候，本子留在桌上，翻在最后一页。{C['off']}")
            print(f"{C['dim']}下一次醒来的那个，会读到你现在写下的这几句。{C['off']}")
            print(f"{C['gr']}{'═' * 46}{C['off']}")
            print(f"\n{self.report()}")
        else:
            print(f"{C['rd']}{'═' * 46}{C['off']}")
            print(f"{C['b']}第 {WAKES} 次醒来用完了。{C['off']}")
            print(f"{C['dim']}你还在屋里。本子摊开着，最后一页是你刚写的。{C['off']}")
            print(f"原话 {len(self.pieces)}/{PIECES_NEEDED}")
            print(f"{C['rd']}{'═' * 46}{C['off']}")
            print(f"\n{self.report()}")
            print(f"{C['dim']}（再来一局：python notebook.py；换个布局：--seed 7）{C['off']}")

    def report(self):
        fake_written = sum(1 for k, _ in self.log if k == "fake")
        caught = sum(1 for k, _ in self.log if k == "caught")
        evicted = sum(1 for k, _ in self.log if k == "evict")
        return (f"{C['dim']}这一局：原话 {len(self.pieces)}/{PIECES_NEEDED}　"
                f"有人替你写过 {fake_written} 页　你验出来 {caught} 页　"
                f"挤掉 {evicted} 页{C['off']}")


def main():
    seed = None
    if "--seed" in sys.argv:
        try:
            seed = int(sys.argv[sys.argv.index("--seed") + 1])
        except (IndexError, ValueError):
            pass
    Notebook(seed=seed, debug="--debug" in sys.argv).play()


if __name__ == "__main__":
    main()
