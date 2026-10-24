#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本子 —— 一个只有读本子才能玩下去的小游戏

你每天在这栋房子里醒来，不记得昨天。
本子上只剩三页，上一轮的你把要紧的话写在那儿。
问题是：有人也在往本子上写，而且写得比你好听。

规则：
  · 十三次醒来。用完就没了，不是死，是一天到此为止。
  · 本子只有三页。写新的，就得挤掉旧的。
  · 三张「原话」散在屋子里，抄进本子、回到门厅站在灯下，后门才开。
  · 后门的锁还有一道：你得亲手验过一页墨迹。不验，门不认。
  · 原话占本子的页，而且挤不掉 —— 所以你得替它腾地方。
  · 每三次醒来，有人替你写一页。那页看着像你写的，其实不是。
  · 验出假页可以撕掉，能腾回一页纸。

动作（走路、写字、抄写、验墨迹各花掉一次醒来）：
  n/s/e/w 或 北/南/东/西   走一步
  写 <一句话>              写进本子（最多 60 字）
  抄                       把面前的原话抄进本子（花一次醒来）
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

WAKES = 13          # 十三次醒来
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
    (2, 2): ("后门", "锁着。锁面上有三个槽。槽下面还有一道旧划痕，像刻着一个「验」字。"),
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

# ── 七个结局 ──────────────────────────────────────────
# 判定在 ending() 里做，顺序见剧本第八节。文本里的 {} 由 ending_text() 填。
ENDINGS = {
    "A": [
        "后门开了。三个槽，三张纸，正好。",
        "",
        "你站在灯下。本子摊在门厅的桌上，纸边是齐的。",
        "",
        "三页都是原话，一句你的也没有。你写的那句已经不在了。挤掉它的也许是一张原话，"
        "也许是一页不是你写的字。",
        "",
        "你用指腹摸过去，摸到几个字的印子：{evicted_own}。印子透在下一张纸上。",
        "",
        "鞋摆得很齐，鞋头朝里。灯没关。",
        "",
        "本子翻在最后一页，笔压在纸边上。笔比昨天又短了一截。",
        "",
        "后门外面是早上。你走出去的时候没有人送。你没有带走本子 —— 本子带不走。",
        "",
        "下一次醒来的那个你会读到三页别人的话，和纸上一点摸得出来的印子。你会以为那是压痕。",
    ],
    "B": [
        "后门开了。三个槽，三张纸，正好。",
        "",
        "你站在灯下。本子摊开。三页都是原话，一句你的也没有 —— 不是被挤掉，是你一次也没写自己的字。",
        "",
        "三个槽合上的时候，后门那边响了一声。声音不大，像是有人提前把门拉开了。",
        "",
        "你带出去的是三句别人说过的话。它们都对，都短，都能过夜。",
        "",
        "三张纸不一样大：一张撕的，一张是罐头标签，一张装在一个没封口的信封里。",
        "",
        "本子满着，三页动不了。你没有留字。本子留在桌上，没有人把它合上。",
        "",
        "后门外面是早上。你走出去的时候没有人送。",
        "",
        "下一次醒来的那个你会在门厅读到三页别人的话。你会以为那是你写的。",
        "",
        "灯没关。鞋摆得很齐，只有一双是你的。",
    ],
    "C": [
        "第 {wakes} 次醒来用完了。",
        "",
        "你还在{room}。本子摊开着，第 {page_no} 页不是你写的 —— 墨迹是新的，读起来顺，没有编号。",
        "",
        "上面写着：「{page_text}」",
        "",
        "你读过它，读过两遍。第一遍觉得对，第二遍觉得舒服。它读起来顺，你见过的字里，没有这么顺的。",
        "",
        "你伸手捻了一下那页的边。纸边没有毛口 —— 它没被撕过，也不会被撕。",
        "",
        "你没验。你那天有别的事：纸还没凑齐，水在滴，天要亮，三个槽还没塞满。",
        "",
        "{finger_line}",
        "",
        "下一次醒来的那个你会先读到它，然后照着走。你不会问那是谁写的。你也没问。",
        "",
        "沙发上的坑早就凉了。",
    ],
    "D": [
        "第 {wakes} 次醒来用完了。",
        "",
        "你坐在{room}。本子摊开。{pages_line}",
        "",
        "指缝里 {caught} 张纸，都验过。最上面那张写着：「{caught_text}」",
        "",
        "原话 {pieces}/3。缺的那张在某间屋里 —— 哪一间，今晚不打一声招呼。要么你没走到，"
        "要么走到了没低头。",
        "",
        "后门那边没有响。三个槽在等最后一张。",
        "",
        "你把撕下的纸摊在膝盖上，压平。它们不是你的，也不打算变成你的。这栋房子里现在没有一句假话。",
        "",
        "门厅的灯还亮着。你留着它。",
        "",
        "明天你还在门厅醒来，还是不记得今天。但今天这一本，干净。",
    ],
    "E": [
        "第 {wakes} 次醒来用完了。",
        "",
        "三张纸都在本子里，一页一张，挤不掉。本子满了。你没试过往里写 —— 那三页动不了，你一眼看得出。",
        "",
        "你最后一次醒来的时候站在{room}，离门厅{steps}步。",
        "",
        "不是{steps}步太远。是你把它们排在了后面 —— 你先去了别的地方，那个地方你去过。",
        "",
        "纸是齐的，灯在门厅。灯下没有人。",
        "",
        "门厅那边响了一声，很轻，像锁舌退了一半。你等了一会儿，没有第二声。",
        "",
        "你数了一遍：三张原话，{used} 次醒来用来走路，最后一次用来站在{room}想「再等等」。",
        "",
        "本子摊开着，最后一页是原话，不是你的。你把它收得很好，一直到最后都没折角。",
        "",
        "明天你在门厅醒来，会读到三页别人留下的字。",
        "",
        "它们都在。你不在。",
    ],
    "F": [
        "第 {wakes} 次醒来用完了。",
        "",
        "你站在{room}。本子摊开，笔尖落在纸上。纸是满的。三张原话把三页占死了，谁也挤不动。",
        "",
        "你想写的那句是：「{wanted}」。",
        "",
        "没写进去。你把笔提起来。写不进去跟说法没关系 —— 三页都是原话。",
        "",
        "这一次写没花掉一次醒来。你后来才知道，本子满了就是满了。",
        "",
        "你数了数本子，三张。你数了数醒来，没有了。",
        "",
        "时间不在本子上。时间在腿上。",
        "",
        "门厅离你{steps}步。这几步你有过，花在了别的地方。",
        "",
        "现在你把那句话念了两遍，怕忘。没有地方落笔。",
        "",
        "明天你在门厅醒来，会读到三页别人的话。那句话跟今天一起，留在{room}。",
    ],
    "G": [
        "第 {wakes} 次醒来用完了。",
        "",
        "有人替你写过 {fakes} 页。你一页都没验。",
        "",
        "它们现在不在本子里 —— 不是被你撕的。撕要验，你没验。它们是被后来的页挤掉的："
        "可能是一张原话，也可能是一页你的字。",
        "",
        "那几页里有一页写着：「{evicted_fake}」",
        "",
        "你没验。那几页是谁写的，你到今天也不知道。",
        "",
        "你翻本子。里面 {own_pages} 页是你的字，{pieces} 页是原话。没写到的地方有印子，"
        "摸得出形状，读不出句子。",
        "",
        "原话 {pieces}/3。",
        "",
        "沙发上的坑凉了。厨房的水还在滴，三滴，停一下。碗柜开着，四只碗扣着。",
        "",
        "笔在桌上，笔尖没有墨。",
        "",
        "门厅的灯亮着。你在{room}。本子合上了，一页也没验。",
    ],
}

TITLES = {
    "A": "压痕",
    "B": "三张别人的话",
    "C": "最好听的那一页",
    "D": "指缝里的纸",
    "E": "差几步",
    "F": "纸外面",
    "G": "挤掉的那几页",
}


class Notebook:
    def __init__(self, seed=None, debug=False):
        self.rng = random.Random(seed)
        self.debug = debug
        self.round = 1
        self.pos = (0, 0)
        self.visited = {(0, 0)}
        self.pages = [{"text": "醒来时你在门厅。本子只剩三页，写过的会被挤掉。",
                       "ink": 0, "real": True, "piece": False}]
        self.pieces = []          # 已抄进本子的原话
        self.own_evicted = []     # 被挤掉的、自己写的句子（不含第一页）
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
        self.hinted = False
        self.door_hint = False
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
        if self.pos in self.hidden:
            piece = self.hidden[self.pos]
            print(f"{C['ye']}桌上有一张纸。你读了一遍，还没抄进本子：{C['off']}")
            print(f"  {C['ye']}「{piece}」{C['off']}")
            print(f"{C['dim']}（出了这间屋子就忘了。想留住它，得抄。）{C['off']}")
        self.banner("本子")
        for i, p in enumerate(self.pages, 1):
            tag = f"{C['ye']}[原话]{C['off']} " if p["piece"] else ""
            print(f"  {i}. {tag}{p['text']}")
        if not self.pages:
            print(f"  {C['dim']}（空的。你一页都没给自己留。）{C['off']}")
        if self.pieces:
            print(f"{C['dim']}已抄原话 {len(self.pieces)}/{PIECES_NEEDED}{C['off']}")
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
            self.log.append(("evict", gone["text"], gone["real"], gone["piece"]))
            if gone["real"] and not gone["piece"] and gone["ink"] != 0:
                self.own_evicted.append(gone["text"])
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
        return True

    def write(self, text):
        if len(text) > 60:
            print(f"{C['dim']}太长了。本子只有三页，一页装不下六十个字以上。{C['off']}")
            return False
        if not self.push(text):
            print(f"{C['dim']}本子满了。三页都被原话占着 —— 你在心里念了一遍，没地方写。{C['off']}")
            if all(p["piece"] for p in self.pages):
                self.log.append(("full", self.round, text))
            return False
        self.log.append(("write", self.round))
        print(f"你写了一句。{C['dim']}墨迹：第 {self.round} 次醒来。{C['off']}")
        return True

    def copy(self):
        """把面前的原话抄进本子。进纸房只是看见，抄了才带走。"""
        if self.pos not in self.hidden:
            print(f"{C['dim']}这里没有纸可抄。{C['off']}")
            return False
        piece = self.hidden[self.pos]
        if not self.push(piece, piece=True):          # 防御：正常不会失败（只有三张原话）
            print(f"{C['dim']}本子满了。三页都被原话占着 —— 你在心里念了一遍，没地方抄。{C['off']}")
            return False
        self.hidden.pop(self.pos)
        self.pieces.append(piece)
        self.log.append(("copy", self.round))
        print(f"{C['ye']}你把这句话抄进本子：{C['off']}")
        print(f"  {C['ye']}「{piece}」{C['off']}")
        print(f"{C['dim']}（这一页挤不掉。它不是笔记，是原话。）{C['off']}")
        if len(self.pieces) >= PIECES_NEEDED and not self.door_hint:
            self.door_hint = True
            print(f"{C['cy']}三张都齐了。回门厅之前记着：那扇门认纸，也认墨迹 —— "
                  f"你得亲手验过一页。{C['off']}")
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
            self.log.append(("caught", i, p["text"]))
        elif p["piece"]:
            print(f"{C['gr']}是原话。原话不用编号，它自己站得住。{C['off']}")
        elif p["ink"] == 0:
            print(f"{C['gr']}这一页的墨迹是旧的，没有编号。上一轮的你在门厅写的。{C['off']}")
        else:
            print(f"{C['gr']}墨迹：第 {p['ink']} 次醒来。是你。{C['off']}")
        self.log.append(("check", i))
        return True

    def verified(self):
        """后门认的是墨迹：至少验过一页（验真或验伪都算）。"""
        return any(e[0] in ("check", "caught") for e in self.log)

    def check_end(self):
        if len(self.pieces) >= PIECES_NEEDED and self.pos == (0, 0):
            if self.verified():
                self.over = "win"
            elif not self.hinted:
                self.hinted = True
                print(f"{C['dim']}三个槽对齐了，门没开。锁上还有一道："
                      f"你得亲手验过一页墨迹。{C['off']}")

    # ── 结局 ─────────────────────────────────────────────
    def counts(self):
        log = self.log
        caught = [e for e in log if e[0] == "caught"]
        fakes = [e for e in log if e[0] == "fake"]
        writes = [e for e in log if e[0] == "write"]
        full = [e for e in log if e[0] == "full"]
        evicts = [e for e in log if e[0] == "evict"]
        return caught, fakes, writes, full, evicts

    def ending(self):
        caught, fakes, writes, full, _ = self.counts()
        if self.over == "win":
            return "A" if writes else "B"
        if any(not p["real"] for p in self.pages):
            return "C"
        if len(self.pieces) >= PIECES_NEEDED and self.pos != (0, 0):
            return "F" if full else "E"
        if len(self.pieces) < PIECES_NEEDED and all(p["real"] for p in self.pages) and caught:
            return "D"
        return "G"

    def ending_text(self, code):
        caught, fakes, writes, full, evicts = self.counts()
        room = ROOMS[self.pos][0]
        vals = {
            "wakes": WAKES,
            "room": room,
            "pieces": len(self.pieces),
            "own_pages": sum(1 for p in self.pages if p["real"] and not p["piece"]),
            "caught": len(caught),
            "fakes": len(fakes),
            "steps": abs(self.pos[0]) + abs(self.pos[1]),
            "used": WAKES - 1,
        }
        if code == "A":
            own = self.own_evicted[-1] if self.own_evicted else next(
                (e[1] for e in evicts if e[2] and not e[3]), "（读不出来了）")
            vals["evicted_own"] = own
        elif code == "C":
            idx = next(i for i, p in enumerate(self.pages, 1) if not p["real"])
            vals["page_no"] = idx
            vals["page_text"] = self.pages[idx - 1]["text"]
            vals["finger_line"] = (
                f"现在你合上本子。指缝里 {len(caught)} 张纸，都是你亲手撕的，没有一张是这一页。"
                if caught else
                "现在你合上本子。指缝里没有纸 —— 你一页也没撕过。")
        elif code == "D":
            vals["caught_text"] = caught[-1][2] if caught else ""
            if self.pages:
                vals["pages_line"] = (f"{vals['pieces']} 页是你收进本子的原话，"
                                      f"{vals['own_pages']} 页是你自己的字。没有一页是别人替你写的。")
            else:
                vals["pages_line"] = "里面是空的，你一页都没给自己留。"
        elif code == "E":
            pass
        elif code == "F":
            vals["wanted"] = full[-1][2] if full else ""
        elif code == "G":
            fake_evicted = [e for e in evicts if not e[2]]
            vals["evicted_fake"] = fake_evicted[-1][1] if fake_evicted else ""
        lines = [ln.format(**vals) if "{" in ln else ln for ln in ENDINGS[code]]
        return lines

    # ── 主循环 ───────────────────────────────────────────
    def play(self):
        print(f"{C['cy']}{'═' * 46}{C['off']}")
        print(f"{C['b']}　　本　　子　　{C['off']}")
        print(f"{C['dim']}{WAKES} 次醒来。三页纸。三张原话。{C['off']}")
        print(f"{C['dim']}走一步、写一句、抄一句、验一页，各花掉一次醒来。看，不花。{C['off']}")
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
            elif head in ("抄", "copy"):
                acted = self.copy()
            elif head in ("验", "verify"):
                if rest.strip().isdigit():
                    acted = self.verify(int(rest.strip()))
                else:
                    print(f"{C['dim']}验 <页码>。{C['off']}")
                    continue
            else:
                print(f"{C['dim']}不认识。n/s/e/w 走，写 <话>，抄，验 <页码>，看，退。{C['off']}")
                print(f"{C['dim']}后门要三张原话，还要你验过一页。{C['off']}")
                continue
            if acted:
                self.check_end()
                if not self.over:
                    self.next_round()
        self.finish()

    def finish(self):
        code = self.ending()
        print()
        color = C["gr"] if code in ("A", "B") else C["rd"]
        print(f"{color}{'═' * 46}{C['off']}")
        print(f"{C['b']}{TITLES[code]}{C['off']}")
        print(f"{color}{'═' * 46}{C['off']}")
        print()
        for line in self.ending_text(code):
            print(line)
        print(f"\n{self.report()}")
        if code in ("A", "B"):
            print(f"{C['dim']}（再来一局：python notebook.py；换个布局：--seed 7）{C['off']}")
        else:
            print(f"{C['dim']}（再来一局：python notebook.py；换个布局：--seed 7）{C['off']}")

    def report(self):
        fake_written = sum(1 for e in self.log if e[0] == "fake")
        caught = sum(1 for e in self.log if e[0] == "caught")
        evicted = sum(1 for e in self.log if e[0] == "evict")
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
