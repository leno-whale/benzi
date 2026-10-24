import importlib.util, itertools, subprocess, os, sys
P=os.path.join(os.path.dirname(os.path.abspath(__file__)), "notebook.py")
spec=importlib.util.spec_from_file_location("nb",P); nb=importlib.util.module_from_spec(spec); spec.loader.exec_module(nb)
def dist(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
seed=3
g=nb.Notebook(seed=seed)
rooms=list(g.hidden.keys())
best=None
for perm in itertools.permutations(rooms):
    cur=(0,0); tot=0
    for r in perm: tot+=dist(cur,r); cur=r
    tot+=dist(cur,(0,0))
    if best is None or tot<best[0]: best=(tot,perm)
order=best[1]
cmds=[]
cur=(0,0)
for r in order:
    while cur!=r:
        dx=r[0]-cur[0]; dy=r[1]-cur[1]
        if dx>0: cmds.append("e"); cur=(cur[0]+1,cur[1])
        elif dx<0: cmds.append("w"); cur=(cur[0]-1,cur[1])
        elif dy>0: cmds.append("n"); cur=(cur[0],cur[1]+1)
        else: cmds.append("s"); cur=(cur[0],cur[1]-1)
while cur!=(0,0):
    dx=-cur[0]; dy=-cur[1]
    if dx>0: cmds.append("e"); cur=(cur[0]+1,cur[1])
    elif dx<0: cmds.append("w"); cur=(cur[0]-1,cur[1])
    elif dy>0: cmds.append("n"); cur=(cur[0],cur[1]+1)
    else: cmds.append("s"); cur=(cur[0],cur[1]-1)
print("seed",seed,"路线", " ".join(cmds), "(共", len(cmds), "步, 预算", nb.WAKES, ")")
actions=[]
cur=(0,0); copied=set()
for d in cmds:
    actions.append(d)
    if d=="n": cur=(cur[0],cur[1]+1)
    elif d=="s": cur=(cur[0],cur[1]-1)
    elif d=="e": cur=(cur[0]+1,cur[1])
    else: cur=(cur[0]-1,cur[1])
    if cur in rooms and cur not in copied:
        actions.append("抄")
        copied.add(cur)
        if len(copied) == 1:                 # v0.3：后门要验过一页
            actions.append("验 2")
print("动作", " ".join(actions), "(共", len(actions), "次醒来)")
env=dict(os.environ); env["PYTHONUTF8"]="1"
out=subprocess.run([sys.executable,P,"--seed",str(seed)],input="\n".join(actions)+"\n",capture_output=True,text=True,encoding="utf-8",env=env).stdout
lines=out.splitlines()
print("\n".join(lines[-26:]))
