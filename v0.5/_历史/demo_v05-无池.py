#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本子 v0.5「折叠与门缝」——两局演示（非交互）。

第一局：seed 3，最短收纸路线，赢，往门缝里留一句。
第二局：seed 1，共用同一道门缝，--echo always；第 8 次醒来折起一页，
        展开它（花第 9 次醒来），再验第 3 页，验到第一局留在门缝里的回声。

两局回执分开写，门缝是同一个文件。退出码 0 表示演示全部成立。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.join(HERE, "notebook_v05.py")
TMP = os.path.join(HERE, "_tmp", "demo_v05")
R1 = os.path.join(TMP, "回执-第一局.md")
R2 = os.path.join(TMP, "回执-第二局.md")
DOOR = os.path.join(TMP, "门缝", "留话.txt")
LEAVE = "下一局的人，别急着写。"


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


def main():
    for d in (TMP, os.path.dirname(DOOR)):
        os.makedirs(d, exist_ok=True)
    for p in (R1, R2, DOOR):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass

    # 第一局：seed 3，最短收纸路线；折叠在途中发生，路线仍赢。
    first = "\n".join([
        "n", "抄", "验 2", "n", "抄", "s", "e", "e", "s", "抄", "w", "w",
        LEAVE,
    ]) + "\n"
    g1 = run(["--plain", "--seed", "3", "--receipt", R1, "--door", DOOR,
              "--name", "甲"], first)
    print("=== 第一局（seed 3）===")
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
    if not os.path.exists(DOOR) or LEAVE not in open(DOOR, encoding="utf-8").read():
        print("第一局的留话没进门缝")
        return 1

    # 第二局：共用门缝；第 9 次醒来展开折痕，再验第 3 页（回声页）。
    second = "\n".join([
        "n", "s", "n", "s", "n", "s", "n",
        "展开 1",
        "验 3",
        # 不写「退」：退出分支只报数、不落回执；让醒来自然用完，finish() 才会留话+写回执。
        "n", "s", "n", "s",
    ]) + "\n"
    g2 = run(["--plain", "--seed", "1", "--receipt", R2, "--door", DOOR,
              "--echo", "always", "--name", "乙"], second)
    print("\n=== 第二局（seed 1，共享门缝）===")
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
    if not os.path.exists(R1):
        print("第一局回执被覆盖")
        return 1
    print("\n两局完成：第一局赢并留话；第二局第 9 次醒来展开后验到回声。")
    print("回执分开：%s / %s" % (os.path.basename(R1), os.path.basename(R2)))
    print("门缝共用：门缝/留话.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
