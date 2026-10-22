"""Problem registry. Each problem has a verifier module and a metadata file under problems/<slug>/."""

import json
import os
from pathlib import Path

from . import circle_packing, kissing_number, three_body_orbits

VERIFIERS = {
    "circle-packing": circle_packing,
    "kissing-number": kissing_number,
    "three-body-orbits": three_body_orbits,
}


def repo_root():
    return Path(os.environ.get("UNSOLVED_ROOT", Path(__file__).resolve().parents[2]))


def load_meta(slug):
    with open(repo_root() / "problems" / slug / "meta.json", encoding="utf-8") as f:
        return json.load(f)


def all_problems():
    return {slug: load_meta(slug) for slug in VERIFIERS}
