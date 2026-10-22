"""Command line: verify submissions, referee a pull request, rebuild the record tables."""

import argparse
import os
import sys
from pathlib import Path

from .exact import fmt
from .problems import repo_root
from .records import compute, evaluate_file, same_orbit, write_outputs


def cmd_verify(args):
    from .problems import all_problems
    metas = all_problems()
    bad = 0
    for f in args.files:
        sub, res = evaluate_file(Path(f), metas)
        if res.valid:
            print(f"VALID    {f}: {res.score_text}")
            for d in res.details:
                print(f"         - {d}")
        else:
            bad += 1
            print(f"INVALID  {f}: {res.error}")
    return 1 if bad else 0


def verdict(sub, res, metas, base):
    meta = metas[sub.problem]
    s = base[sub.problem][sub.instance]
    if meta["kind"] == "max":
        prev = s["best"]["res"].score if s["best"] else None
        lit = s["literature_value"]
        target = max([x for x in (prev, lit) if x is not None], default=None)
        if target is None or res.score > target:
            return "🏆 **NEW WORLD RECORD**"
        if res.score == target:
            return "🤝 ties the record"
        if prev is None or res.score > prev:
            return f"⬆️ best verified result here — the published record is still ahead by {fmt(lit - res.score, 9)}"
        return "✅ valid, not a record"
    dup = next((o for o in s["atlas"] if same_orbit(o, res.extra)), None)
    if dup:
        return f"✅ valid — already in the atlas as {dup['id']}"
    if res.extra.get("catalogued"):
        return f"🗺️ new to the atlas — a published orbit: {res.extra['catalogued']}"
    cat_kin = res.extra.get("catalogue_topology") or []
    kin = next((o for o in s["atlas"] if o["word"] == res.extra["word"]), None)
    if cat_kin:
        kin_note = f" (same topology as {cat_kin[0]}, different orbit)"
    elif kin:
        kin_note = f" (same topology as {kin['id']}, different orbit)"
    else:
        kin_note = " — and its topology is not in the catalogue either"
    return "🌟 **NEW ORBIT** — not in the atlas and not in any bundled catalogue" + kin_note


def cmd_referee(args):
    root = repo_root()
    new = [Path(f) for f in args.files]
    metas, base, _ = compute(exclude=[root / f for f in new])
    lines = ["## Unsolved referee", "", "| Submission | Result | Verdict |", "|---|---|---|"]
    ok = True
    for f in new:
        sub, res = evaluate_file(f, metas)
        if not res.valid:
            ok = False
            lines.append(f"| `{f}` | ❌ rejected | {res.error} |")
            continue
        lines.append(f"| `{f}` | {res.score_text} | {verdict(sub, res, metas, base)} |")
    if args.other:
        ok = False
        lines += ["", "⚠️ This pull request also changes files outside `submissions/`: "
                  + ", ".join(f"`{o}`" for o in args.other)
                  + ". The referee only judges submissions; a maintainer has to review the rest."]
    if not new and not args.other:
        lines.append("| — | no submission files changed | — |")
    report = "\n".join(lines) + "\n"
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
    return 0 if ok else 1


def cmd_records(args):
    metas, st, entries = compute()
    invalid = [e for e in entries if not e["res"].valid]
    for e in invalid:
        print(f"warning: {e['path']} no longer verifies: {e['res'].error}", file=sys.stderr)
    if args.write:
        write_outputs(metas, st)
        print("README.md and records.json updated")
    else:
        from .records import render_markdown
        print(render_markdown(metas, st))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="unsolved", description="The open record book for unsolved problems.")
    sp = p.add_subparsers(dest="cmd", required=True)
    v = sp.add_parser("verify", help="verify submission files")
    v.add_argument("files", nargs="+")
    r = sp.add_parser("referee", help="judge the submissions of a pull request against the current records")
    r.add_argument("files", nargs="*", help="submission files added or changed by the pull request")
    r.add_argument("--other", nargs="*", default=[], help="changed files outside submissions/")
    r.add_argument("--report", help="also write the markdown report to this file")
    rec = sp.add_parser("records", help="re-verify everything and print (or --write) the record tables")
    rec.add_argument("--write", action="store_true")
    args = p.parse_args(argv)
    return {"verify": cmd_verify, "referee": cmd_referee, "records": cmd_records}[args.cmd](args)
