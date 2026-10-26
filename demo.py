#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本子 v0.5（原话池 + 跨机器门缝）——两局演示（非交互）。

第一局：seed 3，最短收纸路线，赢，往 inbox 里留一句。
第二局：seed 1，共用同一个 inbox，--echo always；第 8 次醒来折起一页，
        展开它（花第 9 次醒来），再验第 3 页，验到第一局留在 inbox 里的回声。
第二局回执会写 `原话池：原话池-v1` 和三张原话 id；演示用定稿池。

两局回执分开写；门缝是一人一份文件，第一局的文件不被第二局覆盖。
退出码 0 表示演示全部成立。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.join(HERE, "notebook.py")
TMP = os.path.join(HERE, "_tmp", "demo")
R1 = os.path.join(TMP, "回执-第一局.md")
R2 = os.path.join(TMP, "回执-第二局.md")
INBOX = os.path.join(TMP, "门缝", "inbox")
LEAVE = "下一局的人，别急着写。"
LEAVE2 = "我收到了，你也别急。"


def run(args, stdin_text):
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, NOTEBOOK] + args,
        input=stdin_text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=env,
    )


def inbox_files():
    try:
        return sorted(n for n in os.listdir(INBOX) if n.endswith(".md"))
    except FileNotFoundError:
        return []


def main():
    for d in (TMP, INBOX):
        os.makedirs(d, exist_ok=True)
    for p in (R1, R2):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
    for n in inbox_files():
        os.remove(os.path.join(INBOX, n))

    # 第一局：seed 3，最短收纸路线；折叠在途中发生，路线仍赢。
    first = "\n".join([
        "n", "抄", "验 2", "n", "抄", "s", "e", "e", "s", "抄", "w", "w",
        LEAVE,
    ]) + "\n"
    g1 = run(["--plain", "--seed", "3", "--receipt", R1, "--inbox", INBOX,
              "--name", "甲"], first)
    print("=== 第一局（seed 3，inbox）===")
    print("\n".join(g1.stdout.splitlines()[-10:]))
    if g1.returncode != 0:
        print("第一局退出码 %s\n%s" % (g1.returncode, g1.stderr[-400:]))
        return 1
    if "原话 3/3" not in g1.stdout:
        print("第一局没有收齐三张原话")
        return 1
    if not os.path.exists(R1):
        print("第一局回执没写出来")
        return 1
    r1_text = open(R1, encoding="utf-8").read()
    if "- 原话池：原话池-v1" not in r1_text:
        print("第一局回执没有标原话池版本")
        return 1
    if "- 原话 id：" not in r1_text:
        print("第一局回执没有记原话 id")
        return 1
    files1 = inbox_files()
    if len(files1) != 1:
        print("第一局没有在 inbox 里留下恰好一份文件：%s" % files1)
        return 1
    first_path = os.path.join(INBOX, files1[0])
    if LEAVE not in open(first_path, encoding="utf-8").read():
        print("第一局的留话没进 inbox")
        return 1
    if "门缝是明文" not in g1.stdout:
        print("第一局没有明说门缝是明文")
        return 1

    # 第二局：共用 inbox；第 9 次醒来展开折痕，再验第 3 页（回声页）。
    second = "\n".join([
        "n", "s", "n", "s", "n", "s", "n",
        "展开 1",
        "验 3",
        # 不写「退」：退出分支只报数、不落回执；让醒来自然用完，finish() 才会留话+写回执。
        "n", "s", "n", "s",
        LEAVE2,
    ]) + "\n"
    g2 = run(["--plain", "--seed", "1", "--receipt", R2, "--inbox", INBOX,
              "--echo", "always", "--name", "乙"], second)
    print("\n=== 第二局（seed 1，共享 inbox）===")
    print("\n".join(g2.stdout.splitlines()[-12:]))
    if g2.returncode != 0:
        print("第二局退出码 %s\n%s" % (g2.returncode, g2.stderr[-400:]))
        return 1
    if "有人留在门缝里的那句" not in g2.stdout:
        print("第二局没有验到门缝回声")
        return 1
    if "把折痕抹开" not in g2.stdout:
        print("第二局没有演示展开")
        return 1
    if not os.path.exists(R2):
        print("第二局回执没写出来")
        return 1
    if not os.path.exists(first_path):
        print("第一局的门缝文件被覆盖/删掉了")
        return 1
    if LEAVE not in open(first_path, encoding="utf-8").read():
        print("第一局的门缝文件被改写了")
        return 1
    files2 = inbox_files()
    if len(files2) != 2:
        print("第二局后 inbox 不是一人一份：%s" % files2)
        return 1
    print("\n两局完成：第一局赢并留话；第二局第 9 次醒来展开后验到回声。")
    print("回执分开：%s / %s" % (os.path.basename(R1), os.path.basename(R2)))
    print("门缝一人一份：%s" % " / ".join(files2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
