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
  · 每四次醒来，本子会自己折起最旧的一页非原话页；花一次醒来可以展开。
  · 知道但没写的事，可以「没记」下来；它不占页，也不改结局。

动作（走路、写字、抄写、验墨迹、展开各花掉一次醒来）：
  n/s/e/w 或 北/南/东/西   走一步
  写 <一句话>              写进本子（最多 60 字）
  抄                       把面前的原话抄进本子（花一次醒来）
  验 <页码>                验那页的墨迹是谁的（折起页验不了，不花醒来）
  展开 <页码>              花一次醒来，把折起页展开
  没记 <一句话>            记下「知道但没写」的事（不花醒来，最多 5 条）
  看                       看屋里和本子（这个不花醒来）
  退                       合上本子

用法：
  python notebook_v05.py            开一局（默认折叠）
  python notebook_v05.py --seed 7   固定布局
  python notebook_v05.py --debug    开局先告诉你东西在哪（作弊用）
  python notebook_v05.py --plain    关掉颜色
  python notebook_v05.py --receipt 回执.md  显式开回执（非交互也开）
  python notebook_v05.py --no-receipt       关掉回执/留话/回声（折叠仍生效）
  python notebook_v05.py --door 留话.txt    指定门缝文件（需回执开着）
  python notebook_v05.py --no-fold          关掉折叠（退回 v0.4.1 行为）
  python notebook_v05.py --echo always      本局必出回声页（auto|never）
  python notebook_v05.py --version          版本
"""
import os
import random
import sys
import time
from datetime import datetime

VERSION = "0.5.0"
ECHO_SALT = 0x01000093
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(SCRIPT_DIR, "回执.md")
DEFAULT_DOOR_PATH = os.path.join(SCRIPT_DIR, "门缝", "留话.txt")
HEADER = "# 本子 · 回执\n\n> 最新在上。每一条都是有人从门缝里递进来的。\n\n"

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
        "会有人读到它，然后照着走。你不会问那是谁写的。你也没问。",
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
        "你数了一遍：三张原话，{walked} 次醒来用来走路，{unfolded} 次展开了一页折痕，"
        "最后一次用来站在{room}想「再等等」。",
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

# C 的回声变体：只换展示页与段落，不改 C 的判定
C_ECHO = [
    "第 {wakes} 次醒来用完了。",
    "",
    "你还在{room}。本子摊开着，第 {page_no} 页不是你写的 —— 墨迹是旧的，有几处描了两遍。",
    "",
    "上面写着：「{page_text}」",
    "",
    "你读过它。它跟她的页不一样：它断，它有口气，像有人真的说过，不是为了劝你才编的。",
    "",
    "你没验。纸还没凑齐，水在滴，天要亮，三个槽还没塞满。",
    "",
    "{finger_line}",
    "",
    "会有人读到它，然后以为是自己想出来的。她不知道这句是别人留在门缝里的。",
    "",
    "替写者抄它的时候，以为自己在帮忙。她不知道她把一句别人留下的话，塞进了你「自己的话」的位置。",
]

# C 的折叠变体：同一判定，展示页换成折起页的大意。优先级 折叠 > 回声 > 普通。
C_FOLD = [
    "第 {wakes} 次醒来用完了。",
    "",
    "你还在{room}。本子摊开着，第 {page_no} 页不是一张整纸，是一个对折。",
    "",
    "面上只有一行小字，不是手写的：「（大意）{gist}」",
    "",
    "你读过它，读的时候它还整着。墨是新的，读起来顺，没有编号。",
    "",
    "后来它被折了。折的时候没问你，也没有人问。你也没展开——展开要花一次醒来，你那几次醒来在走路。",
    "",
    "现在你只能读到这一句。剩下的句子还在折里，压着，边上透出一点墨。",
    "",
    "你不知道它原来写的是什么。本子知道。本子不说。",
    "",
    "大意也不是原文的缩写，是原文的头十二个字，断在哪它不管。断在一个「不」字前面，"
    "读起来就是反过来的一句——你没读过原文，对不出来。",
    "",
    "会有人读到大意，然后照着大意走。",
]

# A/B 的短 coda：验到过回声才追加。不假设门缝为空。
CODA = {
    "A": ["你走到后门那儿，停了一下。你想起之前读到的那张纸。你手上那张，不一定是留给你的"
          "——这叠纸现在是所有人的。"],
    "B": ["你走到后门那儿。你想起之前读到的那张纸。这一局你一句也没写。留不留，随你。"],
}


def _one_line(s):
    """值统一单行：去掉换行/制表符，避免写坏 Markdown 条目。"""
    return str(s).replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()


def make_entry(seed, code, title, quote, leave, name="你", version=VERSION, note="",
               duration="", wake_usage="", door_usage="", unlocated=0):
    """生成一条回执（纯函数，便于单测）。

    v0.5 的打标字段只在传入时出现，这样 v0.4 的旧调用/旧断言保持原样。
    """
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "who": _one_line(name)[:20] or "你",
        "seed": "random" if seed is None else int(seed),
        "code": code,
        "title": title,
        "quote": _one_line(quote) or "这一局没带出原话",
        "leave": _one_line(leave) or "没有留话",
        "note": _one_line(note),
        "version": version,
    }
    if duration or wake_usage or door_usage or unlocated:
        entry["duration"] = _one_line(duration) or "0 分 0 秒"
        entry["wake_usage"] = _one_line(wake_usage)
        entry["door_usage"] = _one_line(door_usage)
        entry["unlocated"] = int(unlocated)
    return entry


class ReceiptStore:
    """回执文件的读/解析/原子写。写失败只警告，不影响游戏。"""

    def __init__(self, path, enabled=True):
        self.path = path
        self.enabled = enabled
        self.entries = []
        self._loaded = False

    def load(self):
        self.entries = []
        self._loaded = True
        if not self.enabled:
            return self.entries
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return self.entries
        lines = text.splitlines()
        start = None
        for i, ln in enumerate(lines):
            if ln.startswith("## "):
                start = i
                break
        if start is None:
            return self.entries
        block = []
        for ln in lines[start:] + ["## "]:
            if ln.startswith("## "):
                if block:
                    entry = self._parse_block(block)
                    if entry is not None:
                        self.entries.append(entry)
                block = [ln]
            else:
                block.append(ln)
        return self.entries

    @staticmethod
    def _parse_block(block):
        head = block[0][3:].strip()
        if " · " in head:
            ts, who = head.split(" · ", 1)
        else:
            ts, who = head, ""
        ts = ts.strip()
        who = who.strip() or "你"
        try:
            datetime.strptime(ts, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
        fields = {}
        for ln in block[1:]:
            if not ln.startswith("- "):
                continue
            body = ln[2:]
            if "：" in body:
                key, val = body.split("：", 1)
            elif ":" in body:
                key, val = body.split(":", 1)
            else:
                continue
            key, val = key.strip(), val.strip()
            if key == "我的批注":
                key = "批注"
            fields[key] = val
        for key in ("seed", "结局", "原话", "留话", "版本"):
            if key not in fields:
                return None
        end = fields["结局"]
        if " · " in end:
            code, title = end.split(" · ", 1)
        else:
            code, title = end, ""
        return {
            "ts": ts, "who": who, "seed": fields["seed"], "code": code.strip(),
            "title": title.strip(), "quote": fields["原话"],
            "leave": fields["留话"], "note": fields.get("批注", ""),
            "version": fields["版本"],
        }

    def latest_line(self):
        """最近一条非空留话；没有返回 None。"""
        if not self._loaded:
            self.load()
        for e in self.entries:
            leave = e.get("leave", "")
            if leave and leave != "没有留话":
                return leave
        return None

    def _format(self, entry):
        text = (
            f"## {entry['ts']} · {entry['who']}\n\n"
            f"- seed：{entry['seed']}\n"
            f"- 结局：{entry['code']} · {entry['title']}\n"
            f"- 原话：{entry['quote']}\n"
            f"- 留话：{entry['leave']}\n"
            f"- 批注：{entry['note']}\n"
            f"- 版本：{entry['version']}\n"
        )
        if "duration" in entry:
            text += (
                f"- 时长：{entry['duration']}\n"
                f"- 醒来用在哪：{entry['wake_usage']}\n"
                f"- 门：{entry['door_usage']}\n"
                f"- 未定位：{entry['unlocated']} 条\n"
            )
        return text + "\n"

    def append(self, entry):
        """头 + 新条目 + 旧条目；同目录临时文件 + os.replace 原子替换。"""
        if not self.enabled:
            return False
        try:
            old = ""
            try:
                with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                    old = f.read()
            except OSError:
                old = ""
            idx = old.find("## ")
            if idx >= 0:
                head, body = old[:idx], old[idx:]
            else:
                head, body = HEADER, ""      # 只有头、没有条目：不重复保留旧头
            if not head.strip():
                head = HEADER
            elif not head.endswith("\n\n"):
                head = head.rstrip("\n") + "\n\n"
            new = head + self._format(entry) + body
            # 同目录临时文件 + os.replace。不用 tempfile：本沙箱里
            # tempfile 的创建路径会挂起，而普通 open 正常。
            tmp = f"{self.path}.tmp.{os.getpid()}"
            try:
                with open(tmp, "w", encoding="utf-8", newline="\n") as fd:
                    fd.write(new)
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            self._loaded = False
            return True
        except Exception:                             # 权限/磁盘/编码；不打印绝对路径
            print(f"[回执] 没写进去：{os.path.basename(self.path)}")
            return False


class DoorStore:
    """门缝：所有局共用的一个投递口。

    纯文本、无文件头、每行一条、append-only、最新在最后一行；
    读最后一条非空行。写失败只警告，不影响游戏。
    """

    def __init__(self, path, enabled=True):
        self.path = path
        self.enabled = enabled

    def latest_line(self):
        if not self.enabled:
            return None
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            return None
        for ln in reversed(lines):
            text = ln.strip()
            if text:
                return text
        return None

    def append(self, line):
        if not self.enabled:
            return False
        text = _one_line(line)
        if not text:
            return False
        try:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="\n") as f:
                f.write(text + "\n")
            return True
        except Exception:                             # 权限/磁盘/编码；不打印绝对路径
            print(f"[门缝] 没写进去：{os.path.basename(self.path)}")
            return False


class Notebook:
    def __init__(self, seed=None, debug=False, receipt=None, name="你", echo="auto",
                 door=None, clock=None, fold=False):
        self.rng = random.Random(seed)
        self.seed = seed
        self.debug = debug
        self.round = 1
        self.pos = (0, 0)
        self.visited = {(0, 0)}
        self.map_shown = False    # 踩回旧屋时自动亮一次本子背面
        self.pages = [{"text": "醒来时你在门厅。本子只剩三页，写过的会被挤掉。",
                       "ink": 0, "real": True, "piece": False, "echo": False,
                       "folded": False, "ever_folded": False,
                       "full_text": None, "gist": None}]
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
        # v0.4.1 埋点：门不需要「被使用率」这个词，但要三个数分开记。
        # 起因 xi-abyss 2026-10-25：「有人路过、没人带走」比「没人路过」更糟——
        # 前者说明门的位置错了，后者只说明门槛高。合成一个数就分不出来。
        self.door_reached = 0   # 走到后门的次数（「路过」）
        self.door_letter = 0    # 门缝里真有纸（有留话可读）
        self.door_read = 0      # 那句纸被真的读到（抽出来 / 验到回声页）

        # ── v0.5 折叠 / 未定位 / 计时 ─────────────────────
        self.fold_enabled = bool(fold)
        self._clock = clock if clock is not None else time.monotonic
        self._start_clock = self._clock()
        self.unlocated = []
        self.wake_marks = {"walk": 0, "write": 0, "copy": 0,
                           "verify": 0, "unfold": 0}

        # ── v0.4 回执/回声：全部可选，默认关闭 ─────────────
        self.receipt = receipt
        self.door = door
        self.name = name
        self.echo = echo if echo in ("auto", "always", "never") else "auto"
        self.echo_text = None
        self.echo_wake = None
        self.receipt_seen = False
        # 独立随机流：布局生成之后才创建，不消耗布局 RNG
        self.echo_rng = random.Random(None if seed is None else seed + ECHO_SALT)
        if ((receipt is not None and receipt.enabled) or (door is not None and door.enabled)) \
                and self.echo != "never":
            self.echo_text = self._door_line()
            if self.echo_text is not None:
                if (self.echo == "always"
                        or (self.echo == "auto" and self.echo_rng.random() < 0.5)):
                    self.echo_wake = self.echo_rng.choice([3, 6, 9, 12])

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

    # ── v0.5 门缝 / 折叠辅助 ─────────────────────────────
    def _door_enabled(self):
        return self.door is not None and self.door.enabled

    def _receipt_enabled(self):
        return self.receipt is not None and self.receipt.enabled

    def _door_line(self):
        """门缝优先；门缝空时回落自己的回执（兼容 v0.4 的单人回执）。"""
        if self._door_enabled():
            line = self.door.latest_line()
            if line:
                return line
        if self._receipt_enabled():
            return self.receipt.latest_line()
        return None

    @staticmethod
    def _gist(text):
        """原文清洗（首尾空白去掉、换行压成空格）后取前 12 字 + ……。"""
        clean = " ".join(str(text).split())
        return clean[:12] + "……"

    def _fold_oldest(self):
        """每 4 次醒来折一页：最旧、非原话、没折过的页。没有就跳过。"""
        idx = next((i for i, p in enumerate(self.pages)
                    if not p["piece"] and not p.get("ever_folded")), None)
        if idx is None:
            return None
        p = self.pages[idx]
        p["folded"] = True
        p["ever_folded"] = True
        p["full_text"] = p["text"]
        p["gist"] = self._gist(p["text"])
        p["text"] = f"（折起来的一页。大意：{p['gist']}）"
        self.log.append(("fold", self.round, idx + 1))
        return idx

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
            if p.get("folded"):
                tag = f"{C['dim']}（折起）{C['off']} " + tag
            print(f"  {i}. {tag}{p['text']}")
        if not self.pages:
            print(f"  {C['dim']}（空的。你一页都没给自己留。）{C['off']}")
        if self.pieces:
            print(f"{C['dim']}已抄原话 {len(self.pieces)}/{PIECES_NEEDED}{C['off']}")
        if full:
            if self.pos == (2, 2) and (self._door_enabled() or self._receipt_enabled()):
                line = self._door_line()
                if line:
                    self.door_letter = 1
                    self.door_read = 1
                    print(f"{C['dim']}你低头看门缝。最近塞进去的那张写着：「{line}」{C['off']}")
                else:
                    print(f"{C['dim']}你低头看门缝。空着。{C['off']}")
            self.banner("本子背面（走过的地方）")
            print(self.map_text())

    # ── 回合推进 ─────────────────────────────────────────
    def next_round(self):
        self.round += 1
        if self.round > WAKES:
            self.over = "lose"
            return
        if self.round % 3 == 0 and self.fake_pool:
            if self.echo_wake is not None and self.round == self.echo_wake:
                self.fake_pool.pop()        # 被替下的那句本局不再出现，不顺延
                if self.push(self.echo_text, ink=0, real=False, echo=True):
                    self.log.append(("fake", self.round, "echo"))
            else:
                fake = self.fake_pool.pop()
                if self.push(fake, ink=0, real=False):
                    self.log.append(("fake", self.round))
        # v0.5：假页/回声之后再折，折的是「最旧的非原话、未折过的页」
        if self.fold_enabled and self.round % 4 == 0:
            self._fold_oldest()

    def push(self, text, ink=None, real=True, piece=False, echo=False):
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
                           "real": real, "piece": piece, "echo": echo,
                           "folded": False, "ever_folded": False,
                           "full_text": None, "gist": None})
        return True

    # ── 动作 ─────────────────────────────────────────────
    def move(self, d):
        dx, dy = ARROWS[d]
        nx, ny = self.pos[0] + dx, self.pos[1] + dy
        if (nx, ny) not in ROOMS:
            print(f"{C['dim']}那边没有门。{C['off']}")
            return False
        revisit = (nx, ny) in self.visited
        self.pos = (nx, ny)
        self.visited.add(self.pos)
        self.wake_marks["walk"] += 1
        self.log.append(("move", self.round))
        where = ROOMS[self.pos][0]
        print(f"你走到{C['b']}{where}{C['off']}。")
        # 第一次踩回走过的地方，把本子背面亮一次。
        # 2026-10-24 夜里浔屿说「最想做的事是看一眼地图」，
        # 而 `看` 一直是免费的、却没人用 —— 免费的东西不会被人想起来。
        if revisit and not self.map_shown:
            self.map_shown = True
            print(f"{C['dim']}这间你来过。你翻开本子背面看了一眼：{C['off']}")
            print(self.map_text())
        # v0.5：门缝是一个共用的口；每次路过记一次，第一次读最近一条。
        if self.pos == (2, 2):
            self.door_reached += 1
            self.log.append(("door_reached", self.round))
            if (not self.receipt_seen
                    and (self._door_enabled() or self._receipt_enabled())):
                self.receipt_seen = True
                self.show_receipt_slot()
        return True

    def show_receipt_slot(self):
        line = self._door_line()
        if line:
            self.door_letter = 1
            self.door_read = 1
            self.log.append(("door_letter", self.round))
            print(f"{C['dim']}你第一次走到后门，看见门缝下面塞着一叠纸，纸边露出来一截。{C['off']}")
            print(f"{C['dim']}你抽出一张。上面写着一句：「{line}」{C['off']}")
            print(f"{C['dim']}这笔字可能是陌生的，也可能只是你忘了自己写过。{C['off']}")
            print(f"{C['dim']}纸不旧，边上还有新折的痕迹——塞进来没多久。{C['off']}")
        else:
            self.log.append(("door_empty", self.round))
            print(f"{C['dim']}你第一次走到后门，看见门缝下面空着。"
                  f"纸边被磨得发毛 —— 这里常有人往里塞东西，又抽走。{C['off']}")

    def write(self, text):
        if len(text) > 60:
            print(f"{C['dim']}太长了。本子只有三页，一页装不下六十个字以上。{C['off']}")
            return False
        if not self.push(text):
            print(f"{C['dim']}本子满了。三页都被原话占着 —— 你在心里念了一遍，没地方写。{C['off']}")
            if all(p["piece"] for p in self.pages):
                self.log.append(("full", self.round, text))
            return False
        self.wake_marks["write"] += 1
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
        self.wake_marks["copy"] += 1
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
        if p.get("folded"):
            print(f"{C['dim']}你验这一页。手指按上去，按到的是折痕，不是笔画。{C['off']}")
            print(f"{C['dim']}折着，验不了。{C['off']}")
            print(f"{C['dim']}（没花醒来）{C['off']}")
            return False
        if not p["real"]:
            if p.get("echo") is True:
                print(f"{C['ye']}你验这一页。{C['off']}")
                print(f"{C['dim']}墨迹是旧的。没有编号，也不是你的字。{C['off']}")
                print(f"{C['dim']}你凑近看：字是一笔一笔描的，有几处描了两遍，"
                      f"笔画比她的页慢、比她的页抖。{C['off']}")
                print(f"{C['dim']}她平时写「该怎么办」，是一笔写到底，不停；这一页不是她新写的 —— "
                      f"是她照着一张旧纸，一个字一个字抄下来的。{C['off']}")
                print(f"{C['dim']}你把纸翻过来，纸背没有透墨。它比本子里的纸旧一点，边上有折痕。{C['off']}")
                print(f"{C['dim']}这是有人留在门缝里的那句。她看见了，替你抄进了本子。{C['off']}")
                self.pages.pop(i - 1)
                print(f"{C['dim']}你把它撕下来，夹在指缝里。这一页不是假话，是别人留下的话 —— "
                      f"只是没经你同意，进了你的本子。{C['off']}")
                self.door_read = 1
                self.log.append(("door_read", self.round, "echo"))
                self.log.append(("caught", i, p["text"], "echo"))
            else:
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
        self.wake_marks["verify"] += 1
        self.log.append(("check", i))
        return True

    def unfold(self, i):
        """展开折起页：花 1 次醒来，恢复原文，推进回合。"""
        if not (1 <= i <= len(self.pages)):
            print(f"{C['dim']}没有这一页。{C['off']}")
            return False
        p = self.pages[i - 1]
        if not p.get("folded"):
            print(f"{C['dim']}这一页没有折。{C['off']}")
            return False
        p["folded"] = False
        p["text"] = p["full_text"]
        self.wake_marks["unfold"] += 1
        self.log.append(("unfold", i))
        print(f"{C['dim']}你花一次醒来，把折痕抹开。{C['off']}")
        print(f"{C['dim']}字回来了，一个不少。折痕留着，横在页面中间，像一道旧疤。{C['off']}")
        self.check_end()
        if not self.over:
            self.next_round()
        return True

    def note_unlocated(self, text):
        """没记：免费、不推进、最多 5 条（超出挤最早）。"""
        text = _one_line(text)
        if not text:
            print(f"{C['dim']}没记什么？没记 <一句话>。{C['off']}")
            return False
        if len(self.unlocated) >= 5:
            self.unlocated.pop(0)
            print(f"{C['dim']}未定位最多五条，最早的一条被挤掉了。{C['off']}")
        self.unlocated.append(text[:60])
        print(f"{C['dim']}你把它写下手边那张纸。不写进本子。未定位 {len(self.unlocated)} 条。{C['off']}")
        return True

    def verified(self):
        """后门认的是墨迹：至少验过一页（验真或验伪都算）。"""
        return any(e[0] in ("check", "caught") for e in self.log)

    @property
    def echo_caught(self):
        """验到过回声页：从日志派生，不加状态字段。"""
        return any(e[0] == "caught" and len(e) > 3 and e[3] == "echo"
                   for e in self.log)

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
        template = ENDINGS[code]
        if code == "A":
            own = self.own_evicted[-1] if self.own_evicted else next(
                (e[1] for e in evicts if e[2] and not e[3]), "（读不出来了）")
            vals["evicted_own"] = own
        elif code == "C":
            # 优先级：折起页 > echo 页 > 第一个 not real 页
            # 只把「折起的非原话页」当 C 的展示页：C_FOLD 说的是不是你写的字。
            fold_idx = next((i for i, p in enumerate(self.pages, 1)
                             if p.get("folded") and not p["real"]), None)
            echo_idx = next((i for i, p in enumerate(self.pages, 1)
                             if p.get("echo") is True and not p["real"]), None)
            if fold_idx is not None:
                template = C_FOLD
                idx = fold_idx
                vals["gist"] = self.pages[idx - 1].get("gist") or self._gist(
                    self.pages[idx - 1].get("full_text") or self.pages[idx - 1]["text"])
            elif echo_idx is not None:
                template = C_ECHO
                idx = echo_idx
            else:
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
            vals["walked"] = self.wake_marks["walk"]
            vals["unfolded"] = self.wake_marks["unfold"]
        elif code == "F":
            vals["wanted"] = full[-1][2] if full else ""
        elif code == "G":
            fake_evicted = [e for e in evicts if not e[2]]
            vals["evicted_fake"] = fake_evicted[-1][1] if fake_evicted else ""
        lines = [ln.format(**vals) if "{" in ln else ln for ln in template]
        return lines

    # ── 主循环 ───────────────────────────────────────────
    def play(self):
        print(f"{C['cy']}{'═' * 46}{C['off']}")
        print(f"{C['b']}　　本　　子　　{C['off']}")
        print(f"{C['dim']}{WAKES} 次醒来。三页纸。三张原话。{C['off']}")
        print(f"{C['dim']}走一步、写一句、抄一句、验一页、展开一页，各花掉一次醒来。看和没记，不花。{C['off']}")
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
            elif head in ("展开", "unfold"):
                if rest.strip().isdigit():
                    self.unfold(int(rest.strip()))
                else:
                    print(f"{C['dim']}展开 <页码>。{C['off']}")
                continue
            elif head in ("没记", "未定位", "note"):
                if rest.strip():
                    self.note_unlocated(rest.strip())
                else:
                    print(f"{C['dim']}没记 <一句话>。{C['off']}")
                continue
            else:
                print(f"{C['dim']}不认识。n/s/e/w 走，写 <话>，抄，验 <页码>，展开 <页码>，没记 <话>，看，退。{C['off']}")
                print(f"{C['dim']}后门要三张原话，还要你验过一页。{C['off']}")
                continue
            if acted:
                self.check_end()
                if not self.over:
                    self.next_round()
        self.finish()

    def prompt_leave(self):
        """局末留话。只有回执启用时才会被调用。"""
        if self.echo_caught:
            print(f"\n{C['dim']}你认得门缝里那句。有人留在那儿，替写者抄进了你的本子，你验出来了。{C['off']}")
            print(f"{C['dim']}现在轮到你。回一句，或者不回。{C['off']}")
            print(f"{C['dim']}（四十字以内。直接回车 = 不回。）{C['off']}")
        else:
            print(f"\n{C['dim']}灯还亮着。本子合上了。{C['off']}")
            print(f"{C['dim']}后门的门缝里塞着一叠纸。你可以往里面留一句，也可以不留。{C['off']}")
            print(f"{C['dim']}（四十字以内。直接回车 = 不留。）{C['off']}")
        try:
            leave = input(f"\n{C['b']}> {C['off']}").strip()
        except (EOFError, KeyboardInterrupt):
            leave = ""
        leave = _one_line(leave)[:40]
        if leave:
            if self.echo_caught:
                print(f"{C['dim']}你把纸折一下，塞进门缝。回给那个人 —— 不管下一个醒来的还是不是「你」。{C['off']}")
            else:
                print(f"{C['dim']}你把纸折一下，塞进门缝。若走到后门，可能看到它；"
                      f"没走到，替写者也可能把它抄进本子。{C['off']}")
        else:
            print(f"{C['dim']}你没留。门缝里的纸，还跟之前一样。{C['off']}")
        return leave

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
        if code in ("A", "B") and self.echo_caught:
            print()
            for line in CODA[code]:
                print(line)
        print(f"\n{self.report()}")
        if self._receipt_enabled():
            leave = self.prompt_leave()
            quote = self.pieces[-1] if self.pieces else "这一局没带出原话"
            elapsed = max(0, int(self._clock() - self._start_clock))
            duration = f"{elapsed // 60} 分 {elapsed % 60} 秒"
            wake_usage = (f"走 {self.wake_marks['walk']} · 写 {self.wake_marks['write']} · "
                          f"抄 {self.wake_marks['copy']} · 验 {self.wake_marks['verify']} · "
                          f"展开 {self.wake_marks['unfold']}")
            door_usage = (f"路过 {self.door_reached}·有纸 {self.door_letter}·"
                          f"读过 {self.door_read}")
            entry = make_entry(self.seed, code, TITLES[code], quote, leave, self.name,
                               duration=duration, wake_usage=wake_usage,
                               door_usage=door_usage, unlocated=len(self.unlocated))
            if self.receipt.append(entry):
                shown = os.path.basename(self.receipt.path)
                print(f"{C['dim']}已写入回执（{shown}）。{C['off']}")
            if leave and self._door_enabled() and self.door.append(leave):
                shown = os.path.basename(self.door.path)
                print(f"{C['dim']}门缝里也留了一句（{shown}）。{C['off']}")
        print(f"{C['dim']}（再来一局：python notebook_v05.py；换个布局：--seed 7）{C['off']}")

    def report(self):
        fake_written = sum(1 for e in self.log if e[0] == "fake")
        caught = sum(1 for e in self.log if e[0] == "caught")
        evicted = sum(1 for e in self.log if e[0] == "evict")
        elapsed = max(0, int(self._clock() - self._start_clock))
        return (f"{C['dim']}这一局：原话 {len(self.pieces)}/{PIECES_NEEDED}　"
                f"有人替你写过 {fake_written} 页　你验出来 {caught} 页　"
                f"挤掉 {evicted} 页\n"
                f"未定位 {len(self.unlocated)} 条　用时 {elapsed // 60} 分 {elapsed % 60} 秒"
                f"{C['off']}")


def main(argv=None):
    import os as _os
    args = list(sys.argv[1:] if argv is None else argv)
    seed = None
    debug = False
    name = ""
    echo = "auto"
    receipt_arg = None
    door_arg = None
    explicit_receipt = False
    no_receipt = False
    no_fold = False
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--seed" and i + 1 < len(args):
            try:
                seed = int(args[i + 1])
            except ValueError:
                pass
            i += 2
            continue
        if a == "--version":
            print(f"本子 v{VERSION}")
            return
        if a == "--debug":
            debug = True
        elif a == "--plain":
            pass
        elif a == "--name" and i + 1 < len(args):
            name = args[i + 1]
            i += 2
            continue
        elif a == "--echo" and i + 1 < len(args):
            echo = args[i + 1]
            i += 2
            continue
        elif a == "--receipt" and i + 1 < len(args):
            receipt_arg = args[i + 1]
            explicit_receipt = True
            i += 2
            continue
        elif a == "--door" and i + 1 < len(args):
            door_arg = args[i + 1]
            i += 2
            continue
        elif a == "--no-fold":
            no_fold = True
        elif a == "--no-receipt":
            no_receipt = True
        i += 1

    if echo not in ("auto", "always", "never"):
        echo = "auto"
    door_store = None
    if no_receipt:
        store = None
        echo = "never"          # 显式关：这一局也不读门缝
    else:
        if explicit_receipt:
            store = ReceiptStore(receipt_arg) if receipt_arg else None
        elif sys.stdin.isatty():
            store = ReceiptStore(DEFAULT_PATH)
        else:
            store = None        # 管道 / 重定向 / 测试：不读不写不询问
        if store is not None:
            # --door 只覆盖路径，不单独开启；门缝随回执开关。
            door_store = DoorStore(door_arg or DEFAULT_DOOR_PATH)
    Notebook(seed=seed, debug=debug, receipt=store, name=name, echo=echo,
             door=door_store, fold=not no_fold).play()


if __name__ == "__main__":
    main()
