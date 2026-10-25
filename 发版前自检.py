#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""发版前自检 —— 别让我以为自己发出去了。

跑法：python 发版前自检.py
全过才去打 tag、推上去。任何一条红，就停。

它检查四件（都是我真栽过的）：
1. 测试全绿（204 项；挂了就是上次那种「演示那步找不到文件」）
2. 手册没超 500 字（超了说明我在写法典）
3. 版本号写清楚（notebook.py 里的 VERSION，跟要打的 tag 对得上）
4. 该推的东西里没有本地垃圾（_tmp/、_blind.txt、*.pyc、回执.md 这些）

第 4 条是给那两个教训留的座位：`_blind.txt` 推上去过一次，`_tmp/` 推上去过一次。
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JUNK_PATTERNS = ("_tmp/", "_blind", "__pycache__", ".pyc", "回执.md", "_probe", ".tmp.")
JUNK_OK = {"回执与旁批.md"}  # 不进仓库的那份在别的目录，这里防的是误放


def run(cmd):
    return subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, encoding="utf-8")


def check_tests():
    r = run([sys.executable, "test_notebook.py"])
    ok = r.returncode == 0 and "全部通过" in (r.stdout or "")
    tail = "" if ok else (r.stdout or r.stderr or "").strip().splitlines()[-3:]
    return ok, "测试全绿" if ok else f"测试挂了：{tail}"


def check_manual():
    p = os.path.join(HERE, "设计手册.md")
    if not os.path.exists(p):
        return False, "找不到 设计手册.md"
    n = len(open(p, encoding="utf-8").read())
    return n <= 500, f"设计手册 {n} 字符" + ("（≤500 ✓）" if n <= 500 else "（超过 500，删条款，别加条款）")


def check_version():
    p = os.path.join(HERE, "notebook.py")
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', open(p, encoding="utf-8").read(), re.M)
    if not m:
        return False, "notebook.py 里没有 VERSION"
    return True, f"VERSION = {m.group(1)}（打 tag 就用这个数）"


def check_junk():
    r = run(["git", "ls-files"])
    if r.returncode != 0:
        return False, "git ls-files 跑不了"
    bad = [f for f in (r.stdout or "").splitlines() if any(k in f for k in JUNK_PATTERNS)]
    return not bad, "要推的文件里没有本地垃圾" if not bad else f"这些不该推：{bad[:5]}"


def main():
    print("发版前自检\n")
    rows = [
        ("测试", check_tests()),
        ("手册", check_manual()),
        ("版本号", check_version()),
        ("文件干净", check_junk()),
    ]
    bad = 0
    for name, (ok, msg) in rows:
        print(f"  {'✓' if ok else '✗'} {name}：{msg}")
        if not ok:
            bad += 1
    print()
    if bad:
        print(f"没过（{bad} 条红）。别打 tag，别推。")
        return 1
    print("全过。可以换文件、打 tag、推上去了 —— 推完记得看 CI 那一条是不是绿的。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
