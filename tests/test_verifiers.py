import json
from pathlib import Path

import pytest

from unsolved.exact import ExactnessError, load_json_exact, to_fraction
from unsolved.model import Submission, SubmissionError, load_submission
from unsolved.problems import all_problems, circle_packing, kissing_number, three_body_orbits
from unsolved.records import evaluate_file

ROOT = Path(__file__).resolve().parents[1]


def sub(problem, instance, solution):
    return Submission(path=Path("x.json"), problem=problem, instance=instance,
                      author={"github": "tester"}, method={}, solution=solution)


# ---------------------------------------------------------------- exact numbers

def test_numbers_are_read_exactly():
    data = load_json_exact('{"a": 0.1, "b": 3}')
    assert to_fraction(data["a"]) * 10 == 1
    assert to_fraction("2/6") == to_fraction("0.3333333333333333333333") + to_fraction("1/3") - to_fraction(
        "0.3333333333333333333333")


@pytest.mark.parametrize("bad", ['{"a": NaN}', '{"a": Infinity}'])
def test_non_finite_json_is_rejected(bad):
    with pytest.raises(Exception):
        load_json_exact(bad)


@pytest.mark.parametrize("bad", [True, 0.5, "nan", "1/0", "abc", None])
def test_bad_numbers_are_rejected(bad):
    with pytest.raises(ExactnessError):
        to_fraction(bad)


# ---------------------------------------------------------------- circle packing

TWO = {"n": 2}


def test_two_touching_circles_are_valid():
    res = circle_packing.verify(sub("circle-packing", "n2", {"circles": [["0.25", "0.25", "0.25"], ["0.75", "0.25", "0.25"]]}), TWO)
    assert res.valid and res.score == to_fraction("0.5")


def test_overlap_by_a_hair_is_rejected():
    res = circle_packing.verify(sub("circle-packing", "n2", {"circles": [["0.25", "0.25", "0.25"],
                                                                         ["0.75", "0.25", "0.2500000000000000001"]]}), TWO)
    assert not res.valid


@pytest.mark.parametrize("circles", [
    [["0.2", "0.5", "0.25"], ["0.75", "0.5", "0.2"]],        # sticks out of the square
    [["0.25", "0.25", "-0.1"], ["0.75", "0.25", "0.2"]],     # negative radius
    [["0.25", "0.25", "0.1"]],                               # wrong count
    [["0.25", "0.25", 0.1], ["0.75", "0.25", "0.2"]],        # binary float smuggled in through Python
])
def test_invalid_packings(circles):
    assert not circle_packing.verify(sub("circle-packing", "n2", {"circles": circles}), TWO).valid


# ---------------------------------------------------------------- kissing numbers

def test_e8_has_240_neighbours():
    s = load_submission(ROOT / "submissions/kissing-number/d8/e8-roots.json")
    res = kissing_number.verify(s, {"d": 8})
    assert res.valid and res.score == 240


@pytest.mark.parametrize("vectors,why", [
    ([[1, 0], [1, 0]], "duplicate"),
    ([[2, 0], [1, 1]], "unequal norms"),
    ([[5, 0], [4, 3]], "closer than 60 degrees"),
    ([[0, 0], [1, 0]], "zero vector"),
    ([[1, 0], [0, "1"]], "non-integer"),
])
def test_invalid_kissing_configurations(vectors, why):
    assert not kissing_number.verify(sub("kissing-number", "d2", {"vectors": vectors}), {"d": 2}).valid, why


def test_hexagon_kisses_six():
    hexagon = [[2, 0], [1, 1], [-1, 1], [-2, 0], [-1, -1], [1, -1]]   # in a sheared basis: |v|^2 is not equal
    assert not kissing_number.verify(sub("kissing-number", "d2", {"vectors": hexagon}), {"d": 2}).valid
    square = [[1, 0], [0, 1], [-1, 0], [0, -1]]
    assert kissing_number.verify(sub("kissing-number", "d2", {"vectors": square}), {"d": 2}).score == 4


# ---------------------------------------------------------------- three-body orbits

EQUAL = json.loads((ROOT / "problems/three-body-orbits/meta.json").read_text())["instances"]["equal-mass"]


def test_figure_eight_is_verified_and_recognised():
    res = three_body_orbits.verify(sub("three-body-orbits", "equal-mass",
                                       {"p1": "0.3471168881", "p2": "0.5327249454", "T": "6.3259139829"}), EQUAL)
    assert res.valid
    assert res.extra["catalogued"] == "I.A-1 (Li & Liao 2017)"
    assert (res.extra["word"], res.extra["power"]) == ("123", 2)


def test_figure_eight_traversed_twice_is_reduced_to_one_period():
    res = three_body_orbits.verify(sub("three-body-orbits", "equal-mass",
                                       {"p1": "0.3471168881", "p2": "0.5327249454", "T": "12.6518279658"}), EQUAL)
    assert res.valid and abs(res.extra["T_min"] - 6.3259139829) < 1e-8


@pytest.mark.parametrize("solution", [
    {"p1": "0.3471168881", "p2": "0.5327249454", "T": "6.3"},     # wrong period: does not close
    {"p1": "0.9", "p2": "0.9", "T": "5"},                          # unbound
    {"p1": "0.3471168881", "p2": "0.5327249454", "T": "500"},      # period too long
])
def test_bad_orbits_are_rejected(solution):
    assert not three_body_orbits.verify(sub("three-body-orbits", "equal-mass", solution), EQUAL).valid


def test_topology_is_invariant_under_relabelling_reversal_and_rotation():
    w = three_body_orbits.canonical_word
    s = "3121323"
    relabelled = s.translate(str.maketrans("123", "231"))
    reversed_ = relabelled[::-1]
    rotated = reversed_[3:] + reversed_[:3]
    assert w(s) == w(relabelled) == w(reversed_) == w(rotated)
    assert w("123123") == ("123", 2)
    assert w("1213") != w("1123")


# ---------------------------------------------------------------- repository-level checks

def test_every_committed_submission_verifies():
    metas = all_problems()
    for f in sorted((ROOT / "submissions").rglob("*.json")):
        _, res = evaluate_file(f, metas)
        assert res.valid, f"{f}: {res.error}"


def test_submission_in_the_wrong_folder_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("UNSOLVED_ROOT", str(tmp_path))
    for slug in ("circle-packing", "kissing-number", "three-body-orbits"):
        (tmp_path / "problems" / slug).mkdir(parents=True)
        (tmp_path / "problems" / slug / "meta.json").write_text((ROOT / "problems" / slug / "meta.json").read_text())
    wrong = tmp_path / "submissions" / "kissing-number" / "d9" / "e8.json"
    wrong.parent.mkdir(parents=True)
    wrong.write_text((ROOT / "submissions/kissing-number/d8/e8-roots.json").read_text())
    _, res = evaluate_file(wrong, all_problems())
    assert not res.valid and "must live in" in res.error


def test_malformed_files_are_rejected(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"problem": "circle-packing", "instance": "n26", "solution": {}}))
    with pytest.raises(SubmissionError):
        load_submission(f)
