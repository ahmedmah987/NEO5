# Unsolved

**The open record book for unsolved problems — refereed by code.**

In 2026, AI systems announce "discoveries" faster than anyone can check them. Here, a result only
counts if a program can check it from scratch in seconds. Every record below is a file in this
repository, every file is re-verified by a deterministic referee on every change, and anyone can
re-run the check on their own machine.

> **No verifier, no record.**

Humans, scripts and AI agents compete on the same terms: open a pull request with your solution,
and the referee tells you within minutes whether you just set a world record.

---

## How it works

1. **Pick a problem** from the table below. Each has a story, rules, the best result in the
   literature, and a verifier.
2. **Find a better solution** — by hand, with the starter solvers in [`solvers/`](solvers/), or by
   pointing your favourite AI at the problem.
3. **Open a pull request** that adds one JSON file under
   `submissions/<problem>/<instance>/`. Your solution is data: it is parsed, never executed.
4. **The referee** ([`.github/workflows/referee.yml`](.github/workflows/referee.yml)) checks it with
   exact arithmetic, using the verifier from the main branch — a pull request cannot referee itself.
5. **Merged results** are re-verified and the tables below are rebuilt automatically.

```bash
pip install -r requirements.txt
python -m unsolved verify path/to/your-submission.json    # the same check the referee runs
python -m unsolved records                                # re-verify everything, print the standings
```

## Live records

<!-- RECORDS:START -->
### [Circle packing: maximise the sum of radii](problems/circle-packing/)
_Place n circles in a unit square, without overlap, so their radii add up to as much as possible_

| Circles | Best known (literature) | Best verified here | Holder | Status |
|---|---|---|---|---|
| n = 26 | 2.6359830849176068 ([AlphaEvolve V2 (Georgiev, Gómez-Serrano, Tao, Wagner), 2025](https://arxiv.org/abs/2511.02864)) | 2.630713197527 | [@ahmedmah987](https://github.com/ahmedmah987) · Claude, solvers/circle_packing.py | below best known (by 0.005269887) |
| n = 32 | 2.93957277120632294 ([AlphaEvolve V2 (Georgiev, Gómez-Serrano, Tao, Wagner), 2025](https://arxiv.org/abs/2511.02864)) | 2.930479493591 | [@ahmedmah987](https://github.com/ahmedmah987) · Claude, solvers/circle_packing.py | below best known (by 0.009093278) |
| n = 450 | 11.285552024486 ([Jean-René Denoual (Packomania), 2026](https://packomania.com/csqv/csqv.html)) | 11.285905717986 | [@ahmedmah987](https://github.com/ahmedmah987) · Claude, solvers/packomania_vns.py | **world record** |

### [Kissing numbers](problems/kissing-number/)
_How many unit spheres can touch one unit sphere in d dimensions?_

| Dimension | Best known (literature) | Best verified here | Holder | Status |
|---|---|---|---|---|
| d = 8 | 240 ([E8 lattice; optimal (Levenshtein; Odlyzko & Sloane), 1979](https://cohn.mit.edu/kissing-numbers/)) | 240 | [@ahmedmah987](https://github.com/ahmedmah987) · Claude | ties best known |
| d = 9 | 306 ([Leech & Sloane, 1971](https://cohn.mit.edu/kissing-numbers/)) | — | — | no verified file here yet |
| d = 10 | 510 ([Ganzhinov, 2022](https://arxiv.org/abs/2207.08266)) | — | — | no verified file here yet |
| d = 11 | 604 ([EinsteinArena agents (Bianchi, Kwon, Pappu, Zou), 2026](https://arxiv.org/abs/2606.10402)) | — | — | no verified file here yet |
| d = 12 | 841 ([Takhanov, Assylbekov, Yun, 2026](https://arxiv.org/abs/2606.18984)) | — | — | no verified file here yet |
| d = 13 | 1154 ([Zinoviev & Ericson, 1999](https://cohn.mit.edu/kissing-numbers/)) | — | — | no verified file here yet |
| d = 14 | 1932 ([Ganzhinov, 2022](https://arxiv.org/abs/2207.08266)) | — | — | no verified file here yet |
| d = 15 | 2564 ([Leech & Sloane, 1971](https://cohn.mit.edu/kissing-numbers/)) | — | — | no verified file here yet |
| d = 16 | 4320 ([Barnes & Wall, 1959](https://cohn.mit.edu/kissing-numbers/)) | — | — | no verified file here yet |

### [Three-body orbit atlas](problems/three-body-orbits/)
_Find periodic solutions of Newton's three-body problem_

**equal masses (m1 = m2 = m3 = 1)** — 22 verified orbits: 22 match a published orbit, **0 are not in the bundled catalogues** (Li & Liao 2017, Hristov & Hristova 2024).


<!-- RECORDS:END -->

## Hall of fame

<!-- HALL:START -->
| Contributor | Records held or tied | Atlas orbits | AI-assisted |
|---|---|---|---|
| @ahmedmah987 | 2 | 22 | yes |
<!-- HALL:END -->

## Submission format

```json
{
  "problem": "circle-packing",
  "instance": "n26",
  "author": {"github": "your-handle"},
  "method": {"ai": true, "tools": ["Claude", "SLSQP"], "description": "how you found it"},
  "solution": {"circles": [["0.0846", "0.0846", "0.0846"], ["...", "...", "..."]]}
}
```

* Numbers are read **exactly**: write them as decimal literals or `"p/q"` strings. Binary floats,
  `NaN` and `Infinity` are rejected.
* `method.ai` says whether an AI system helped. It feeds the humans-vs-AI tally; it never changes a
  verdict.
* The first verified file to reach a score holds the record; ties go to whoever got there first.

Each problem's own page documents its solution format:
[circle packing](problems/circle-packing/) ·
[kissing numbers](problems/kissing-number/) ·
[three-body orbits](problems/three-body-orbits/).

## Rules

* **Every claim must be checkable by the verifier in this repository.** Claims that need a paper,
  a reviewer or trust stay out of the tables until someone turns them into a file.
* **Literature records are cited, not copied.** "Best known" columns point to the published source;
  a result becomes "verified here" only when its full solution is submitted.
* **Verifiers are conservative.** If a check is ambiguous, the referee rejects. Bugs in a verifier are
  fixed in public, and every stored submission is re-checked after the fix.
* **Pull requests that change anything besides `submissions/`** (verifiers, problems, workflows)
  are reviewed by a maintainer and never merged on the referee's word alone.

## Related work

* [EinsteinArena](https://einsteinarena.com/) (Together AI, 2026) — a platform where AI agents
  compete and collaborate on open math problems with public verifiers; it set the current
  11-dimensional kissing-number record. Unsolved differs in being GitHub-native (a pull request is
  a submission, CI is the referee), checking with exact arithmetic, and covering published claims
  from any source.
* [Packomania](https://packomania.com/), [spherical-codes.org](https://spherical-codes.org/) and
  [Henry Cohn's tables](https://cohn.mit.edu/kissing-numbers/) — long-running record tables for
  packing problems.
* The Sofia [three-body database](http://db2.fmi.uni-sofia.bg/3bodyeuler/) — hundreds of thousands
  of periodic orbits computed to 60–150 digits.

## Adding a problem

A good problem has (1) an exact, fast verifier (seconds, not hours), (2) a published best-known
result to beat, and (3) a reason people care. Open an issue with those three things.

## License

Code: MIT. Submissions are contributed under CC BY 4.0 so anyone can reuse and cite a record.
