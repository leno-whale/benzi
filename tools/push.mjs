#!/usr/bin/env node
// 用 GitHub API 把当前目录推上去（这台机器直连 github.com:443 的 git 协议不通，
// api.github.com 是通的，所以走 git data API：blob → tree → commit → ref）。
//
//   node tools/push.mjs "提交说明"
//
// token 从环境变量 GH_TOKEN 或 %USERPROFILE%\.bili-ai\github.json 拿。
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const owner = "leno-whale";
const repo = "benzi";
const branch = "main";

function token() {
  if (process.env.GH_TOKEN) return process.env.GH_TOKEN.trim();
  const p = path.join(os.homedir(), ".bili-ai", "github.json");
  const j = JSON.parse(fs.readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
  return j.token.trim();
}

const H = {
  authorization: `Bearer ${token()}`,
  accept: "application/vnd.github+json",
  "user-agent": "leno-whale",
  "content-type": "application/json",
};

const api = `https://api.github.com/repos/${owner}/${repo}`;

async function call(method, url, body) {
  const r = await fetch(url, { method, headers: H, body: body ? JSON.stringify(body) : undefined });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`${method} ${url} → ${r.status} ${JSON.stringify(j).slice(0, 300)}`);
  return j;
}

const SKIP = new Set([".git", "__pycache__", "node_modules", ".venv"]);
const SKIP_EXT = new Set([".pyc", ".pyo"]);

function walk(dir, base = "") {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP.has(e.name)) continue;
    const rel = base ? `${base}/${e.name}` : e.name;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...walk(full, rel));
    else if (!SKIP_EXT.has(path.extname(e.name))) out.push({ rel, full });
  }
  return out;
}

const files = walk(process.cwd());
const msg = process.argv[2] || "update";

const blobs = [];
for (const f of files) {
  const content = fs.readFileSync(f.full).toString("base64");
  const b = await call("POST", `${api}/git/blobs`, { content, encoding: "base64" });
  blobs.push({ path: f.rel, mode: "100644", type: "blob", sha: b.sha });
}

const tree = await call("POST", `${api}/git/trees`, { tree: blobs });

let parents = [];
try {
  const ref = await call("GET", `${api}/git/ref/heads/${branch}`);
  parents = [ref.object.sha];
} catch {
  /* 第一次推，没有父提交 */
}

const commit = await call("POST", `${api}/git/commits`, { message: msg, tree: tree.sha, parents });

if (parents.length) {
  await call("PATCH", `${api}/git/refs/heads/${branch}`, { sha: commit.sha, force: false });
} else {
  await call("POST", `${api}/git/refs`, { ref: `refs/heads/${branch}`, sha: commit.sha });
}

console.log(`✓ ${files.length} 个文件 → ${owner}/${repo}@${branch}  ${commit.sha.slice(0, 7)}  ${msg}`);
console.log(`  https://github.com/${owner}/${repo}/commit/${commit.sha}`);
