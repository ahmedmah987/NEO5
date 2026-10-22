"""Standings: re-verify every submission and work out who holds each record."""

import json
import subprocess
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from .exact import fmt, to_fraction
from .model import SubmissionError, load_submission
from .problems import VERIFIERS, all_problems, repo_root

ATLAS_TSTAR_TOL = 1e-6   # one orbit has one T*; verified orbits give it to ~1e-9


def first_added(path):
    """Date the file first entered git history (None if it is not committed yet)."""
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cI", "--", str(path)],
                             capture_output=True, text=True, cwd=repo_root(), check=False).stdout.split()
        return out[-1] if out else None
    except OSError:
        return None


def expected_location(sub):
    return Path("submissions") / sub.problem / sub.instance


def evaluate_file(path, metas):
    """Load and verify one submission. Returns (submission or None, Result-like dict)."""
    from .model import Result
    path = Path(path)
    try:
        sub = load_submission(path)
    except SubmissionError as exc:
        return None, Result(False, error=str(exc))
    meta = metas.get(sub.problem)
    if meta is None:
        return sub, Result(False, error=f"unknown problem {sub.problem!r}")
    spec = meta["instances"].get(sub.instance)
    if spec is None:
        return sub, Result(False, error=f"unknown instance {sub.instance!r} for {sub.problem}")
    try:
        rel = path.resolve().relative_to(repo_root().resolve())
    except ValueError:
        rel = None                     # a file outside the repository: verify it, but it cannot hold a record
    if rel is not None and rel.parent != expected_location(sub):
        return sub, Result(False, error=f"file must live in {expected_location(sub)}/")
    try:
        return sub, VERIFIERS[sub.problem].verify(sub, spec)
    except Exception as exc:  # a verifier bug must never crash the referee
        return sub, Result(False, error=f"verifier error: {type(exc).__name__}: {exc}")


def all_submission_files(exclude=()):
    root = repo_root()
    excluded = {Path(p).resolve() for p in exclude}
    return [p.relative_to(root) for p in sorted((root / "submissions").rglob("*.json"))
            if p.resolve() not in excluded]


def compute(exclude=(), extra_dates=None):
    """Verify every committed submission (minus `exclude`) and build the standings."""
    metas = all_problems()
    entries = []
    for rel in all_submission_files(exclude):
        sub, res = evaluate_file(rel, metas)
        date = (extra_dates or {}).get(str(rel)) or first_added(rel) or (sub.date if sub else None)
        entries.append(dict(path=str(rel), sub=sub, res=res, date=date or "9999"))
    entries.sort(key=lambda e: (e["date"], e["path"]))
    return metas, standings(metas, entries), entries


def standings(metas, entries):
    out = {}
    for slug, meta in metas.items():
        out[slug] = {}
        for inst, spec in meta["instances"].items():
            mine = [e for e in entries if e["sub"] and e["sub"].problem == slug
                    and e["sub"].instance == inst and e["res"].valid]
            if meta["kind"] == "max":
                out[slug][inst] = max_standing(spec, mine)
            else:
                out[slug][inst] = atlas_standing(mine)
    return out


def max_standing(spec, entries):
    best = None
    for e in entries:                       # entries are in date order: the first to reach a score keeps it
        if best is None or e["res"].score > best["res"].score:
            best = e
    lit = spec.get("best_known")
    lit_value = to_fraction(lit["value"]) if lit and lit.get("value") is not None else None
    st = dict(best=best, literature=lit, literature_value=lit_value, count=len(entries))
    if best is None:
        st["status"] = "open"
    elif lit_value is None or best["res"].score > lit_value:
        st["status"] = "record"
    elif best["res"].score == lit_value:
        st["status"] = "ties"
    else:
        st["status"] = "below"
    return st


def same_orbit(a, b):
    return (a["word"], a["power"]) == (b["word"], b["power"]) and \
        abs(a["tstar"] - b["tstar"]) <= ATLAS_TSTAR_TOL * max(1.0, a["tstar"])


def atlas_standing(entries):
    atlas = []
    for e in sorted(entries, key=lambda e: (e["date"], e["res"].extra["tstar"])):
        x = e["res"].extra
        dup = next((o for o in atlas if same_orbit(o, x)), None)
        if dup:
            dup["rediscoveries"] += 1
            continue
        atlas.append(dict(id=f"O{len(atlas) + 1:04d}", entry=e, rediscoveries=0, **x))
    for o in atlas:
        parent = next((p for p in atlas if p is not o and p["word"] == o["word"] and p["tstar"] < o["tstar"]), None)
        o["satellite_of"] = parent["id"] if parent else None
    return dict(atlas=atlas, count=len(atlas),
                catalogued=sum(1 for o in atlas if o["catalogued"]),
                uncatalogued=sum(1 for o in atlas if not o["catalogued"]))


# ---------------------------------------------------------------- rendering

def holder(e):
    sub = e["sub"]
    who = f"[@{sub.author['github']}](https://github.com/{sub.author['github']})" if sub.author.get("github") \
        else sub.author.get("name", "anonymous")
    tools = sub.method.get("tools") or []
    return who + (f" · {', '.join(tools)}" if tools else "")


def lit_text(lit):
    if not lit or lit.get("value") is None:
        return "—"
    src = f"[{lit['holder']}, {lit['year']}]({lit['source']})" if lit.get("source") else f"{lit['holder']}, {lit['year']}"
    return f"{lit['value']} ({src})"


def atlas_note(o, atlas):
    """How an orbit that is not in the published catalogue relates to known topologies."""
    kin = o.get("catalogue_topology") or []
    if kin:
        return f"different orbit, same topology as {kin[0]}"
    if o["satellite_of"]:
        parent = next(p for p in atlas if p["id"] == o["satellite_of"])
        label = f" = {parent['catalogued']}" if parent["catalogued"] else ""
        return f"different orbit, same topology as {o['satellite_of']}{label}"
    return "**topology not in the catalogue**"


STATUS = {"record": "**world record**", "ties": "ties best known", "open": "no verified file here yet",
          "below": "below best known"}


def render_markdown(metas, st):
    lines = []
    for slug, meta in metas.items():
        lines.append(f"### [{meta['title']}](problems/{slug}/)")
        lines.append(f"_{meta['tagline']}_\n")
        if meta["kind"] == "max":
            lines.append(f"| {meta['instance_header']} | Best known (literature) | Best verified here | Holder | Status |")
            lines.append("|---|---|---|---|---|")
            for inst, s in st[slug].items():
                spec = meta["instances"][inst]
                b = s["best"]
                status = STATUS[s["status"]]
                if s["status"] == "below" and b:
                    gap = s["literature_value"] - b["res"].score
                    status += f" (by {fmt(gap, 9)})" if isinstance(gap, Fraction) else f" (by {gap})"
                lines.append(f"| {spec['label']} | {lit_text(spec.get('best_known'))} | "
                             f"{b['res'].score_text if b else '—'} | {holder(b) if b else '—'} | {status} |")
        else:
            for inst, s in st[slug].items():
                spec = meta["instances"][inst]
                lines.append(f"**{spec['label']}** — {s['count']} verified orbits: {s['catalogued']} match a published "
                             f"orbit, **{s['uncatalogued']} are not in the bundled catalogues** "
                             f"({', '.join(c['name'] for c in spec.get('catalogues', []))}).\n")
                fresh = [o for o in s["atlas"] if not o["catalogued"]]
                if fresh:
                    lines.append("| Orbit | T* | Syzygies | Found by | Note |")
                    lines.append("|---|---|---|---|---|")
                    for o in fresh:
                        lines.append(f"| {o['id']} | {o['tstar']:.6f} | {o['syzygies']} | {holder(o['entry'])} | "
                                     f"{atlas_note(o, s['atlas'])} |")
        lines.append("")
    return "\n".join(lines)


def hall_of_fame(st):
    people = {}
    for slug, insts in st.items():
        for inst, s in insts.items():
            if "atlas" in s:
                for o in s["atlas"]:
                    sub = o["entry"]["sub"]
                    p = people.setdefault(sub.author_handle, dict(records=0, orbits=0, ai=False))
                    p["orbits"] += 1
                    p["ai"] |= sub.uses_ai
            elif s.get("best") and s["status"] in ("record", "ties"):
                sub = s["best"]["sub"]
                p = people.setdefault(sub.author_handle, dict(records=0, orbits=0, ai=False))
                p["records"] += 1
                p["ai"] |= sub.uses_ai
    rows = sorted(people.items(), key=lambda kv: (-kv[1]["records"], -kv[1]["orbits"], kv[0]))
    lines = ["| Contributor | Records held or tied | Atlas orbits | AI-assisted |", "|---|---|---|---|"]
    for who, p in rows:
        lines.append(f"| @{who} | {p['records']} | {p['orbits']} | {'yes' if p['ai'] else 'no'} |")
    return "\n".join(lines)


def to_json(metas, st):
    out = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "problems": {}}
    for slug, insts in st.items():
        out["problems"][slug] = {}
        for inst, s in insts.items():
            if "atlas" in s:
                out["problems"][slug][inst] = {
                    "verified_orbits": s["count"], "published": s["catalogued"],
                    "orbits": [dict(id=o["id"], tstar=round(o["tstar"], 9), word=o["word"], power=o["power"],
                                    published_as=o["catalogued"], same_topology_as=o.get("catalogue_topology") or [],
                                    satellite_of=o["satellite_of"],
                                    found_by=o["entry"]["sub"].author_handle, file=o["entry"]["path"],
                                    date=o["entry"]["date"]) for o in s["atlas"]]}
            else:
                b = s["best"]
                out["problems"][slug][inst] = {
                    "status": s["status"],
                    "best_verified": b["res"].score_text if b else None,
                    "holder": b["sub"].author_handle if b else None,
                    "file": b["path"] if b else None,
                    "best_known_literature": (s["literature"] or {}).get("value")}
    return out


def write_outputs(metas, st):
    root = repo_root()
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8")
    for marker, body in (("RECORDS", render_markdown(metas, st)), ("HALL", hall_of_fame(st))):
        start, end = f"<!-- {marker}:START -->", f"<!-- {marker}:END -->"
        if start in text and end in text:
            head, rest = text.split(start, 1)
            _, tail = rest.split(end, 1)
            text = f"{head}{start}\n{body}\n{end}{tail}"
    readme.write_text(text, encoding="utf-8")
    (root / "records.json").write_text(json.dumps(to_json(metas, st), indent=2) + "\n", encoding="utf-8")
