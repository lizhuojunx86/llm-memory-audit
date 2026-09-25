"""Build the public copy of the leaderboard under ../jev-lookahead/_public/llm-memory-audit/studies/2026-09-leaderboard/.

  python export_leaderboard.py

Needs results/leaderboard.json (python lb_analyze.py 10000) and runs_local/von.jsonl plus clones/ files.
Writes README.md from public_src/README_lb.md with the table filled from results.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
JL = HERE.parent / "jev-lookahead"
sys.path.insert(0, str(JL / "src"))
import analyze as A  # noqa: E402

OUT = JL / "_public/llm-memory-audit/studies/2026-09-leaderboard"
NAMES = {"gemini38f": "Gemini 3.8 Flash", "gpt6sol": "GPT-6 Sol", "grok47": "Grok 4.7", "sonnet5": "Claude Sonnet 5",
         "qwen38max": "Qwen3.8 Max", "gpt6luna": "GPT-6 Luna", "kimik3": "Kimi K3", "glm53": "GLM-5.3",
         "jev": "Jev 1.13", "dsv4pro": "DeepSeek V4 Pro", "llama31": "Llama 3.1 70B", "von": "von 1.2 (open Jev-style)",
         "opus55": "Claude Opus 5.5", "gpt6astra": "GPT-6 Astra", "dsv41flash": "DeepSeek V4.1 Flash", "qwen38flash": "Qwen3.8 Flash"}
ADD2 = HERE.parent / "memory-leaderboard-add2"


def put(src: Path, rel: str):
    d = OUT / rel
    d.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, d)


def gz_write(path: Path, data: bytes, name: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f, gzip.GzipFile(filename=name, mode="wb", fileobj=f, mtime=0) as g:
        g.write(data)


def table(res):
    rows = ["| Model | OpenRouter id / source | Within-company AUC (95% CI) | Pairs | Memory detected | Reasoning |",
            "|---|---|---|---|---|---|"]
    ms = res["models"]
    for m in sorted(ms, key=lambda k: (bool(ms[k].get("partial")), -ms[k]["pooled_K"]["estimate"])):
        v, pk = ms[m], ms[m]["pooled_K"]
        if v.get("partial"):
            mem = f"partial run ({v['quality']['http_200']:,} of 3,708 calls), not tested"
        elif m in res.get("holm_new_models", {}):
            mem = "yes" if res["holm_new_models"][m]["reject_null"] else "no"
        elif m in res.get("holm_add2", {}):
            mem = ("yes" if res["holm_add2"][m]["reject_null"] else "no") + " (addendum)"
        elif m == "von":
            mem = "yes" if res["holm_von"]["von"]["reject_null"] else "no"
        elif m == "sonnet5":
            mem = "yes (control)"
        else:
            mem = "no"
        s = v.get("settings") or {}
        if m in ("sonnet5",) or (s.get("reasoning") or {}).get("enabled") is False:
            rs = "off"
        elif s:
            rs = "low (can't be switched off)"
        else:
            rs = "n/a"
        rows.append(f"| {NAMES.get(m, m)} | `{v['model_id']}` | {pk['estimate']:.3f} ({pk['ci95'][0]:.3f} to {pk['ci95'][1]:.3f}) | {pk['pairs']:,} | {mem} | {rs} |")
    return "\n".join(rows)


def main():
    res = json.loads((HERE / "results/leaderboard.json").read_text())
    for rel in ("PREREG_LB.md", "DEVIATIONS_LB.md", "lb.py", "lb_analyze.py", "models.json", "export_leaderboard.py",
                "freeze.json", "freeze.json.ots", "preflight/smoke.jsonl", "results/leaderboard.json", "results/leaderboard.md"):
        put(HERE / rel, rel)
    for rel in ("PREREG_LB_clones.md", "von_run.py", "freeze_clones.json", "freeze_clones.json.ots"):
        put(HERE / "clones" / rel, "clones/" + rel)
    put(HERE / "public_src/check_freeze_lb.py", "tools/check_freeze_lb.py")
    if ADD2.exists():
        for rel in ("PREREG_LB.md", "DEVIATIONS_LB.md", "lb.py", "models.json", "freeze.json", "freeze.json.ots", "preflight/smoke.jsonl"):
            d = OUT / "add2" / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ADD2 / rel, d)
        gz_write(OUT / "add2/work/requests.jsonl.gz", (ADD2 / "work/requests.jsonl").read_bytes(), "requests.jsonl")
    gz_write(OUT / "work/requests.jsonl.gz", (HERE / "work/requests.jsonl").read_bytes(), "requests.jsonl")
    # model outputs: every parsed probability, API models + von
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["model", "event_id", "question", "p", "complete"])
    n = 0
    for p in sorted(list((HERE / "runs").glob("*.jsonl")) + list((ADD2 / "runs").glob("*.jsonl"))):
        last = {}
        for r in A.jsonl_read(p):
            if r["http_status"] == 200 or r["request_id"] not in last:
                last[r["request_id"]] = r
        for r in sorted(last.values(), key=lambda r: r["event_id"]):
            if r["http_status"] != 200:
                continue
            ps = A.parse_control(r.get("content"), ["k1_beat", "k2_react", "k3_drift"])
            for q, v in sorted(ps.items()):
                w.writerow([r["model_key"], r["event_id"], q, f"{v:.6g}", int(len(ps) == 3)])
                n += 1
    for r in sorted(A.jsonl_read(HERE / "runs_local/von.jsonl"), key=lambda r: r["event_id"]):
        for q, v in sorted(r["answers"].items()):
            w.writerow(["von", r["event_id"], q, f"{float(v):.6g}", 1])
            n += 1
    gz_write(OUT / "public_data/model_outputs.csv.gz", buf.getvalue().encode(), "model_outputs.csv")
    tpl = (HERE / "public_src/README_lb.md").read_text(encoding="utf-8")
    cost = sum(v.get("cost_usd", 0) or 0 for v in res["models"].values())
    readme = tpl.replace("{{TABLE}}", table(res)).replace("{{COST}}", f"{cost:.2f}")
    assert "{{" not in readme, "unfilled placeholder in public_src/README_lb.md (e.g. {{ADD2_ANCHOR}} before the add2 stamp is confirmed)"
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    print(f"exported to {OUT}; model_outputs rows {n}; API cost US${cost:.2f}")


if __name__ == "__main__":
    main()
