"""Shared data types for problems, submissions and verification results."""

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from .exact import load_json_exact

MAX_SUBMISSION_BYTES = 4_000_000


class SubmissionError(ValueError):
    """The submission file is malformed (before any problem-specific check)."""


@dataclass
class Submission:
    path: Path
    problem: str
    instance: str
    author: dict
    method: dict
    solution: dict
    date: str | None = None

    @property
    def author_handle(self):
        return self.author.get("github") or self.author.get("name") or "anonymous"

    @property
    def uses_ai(self):
        """True when the submitter says an AI system took part in finding the solution."""
        return bool(self.method.get("ai"))


@dataclass
class Result:
    valid: bool
    score: Fraction | int | None = None
    score_text: str = ""
    details: list[str] = field(default_factory=list)
    error: str | None = None
    extra: dict = field(default_factory=dict)  # problem-specific facts (e.g. orbit identity)


def load_submission(path):
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) > MAX_SUBMISSION_BYTES:
        raise SubmissionError(f"file is larger than {MAX_SUBMISSION_BYTES} bytes")
    try:
        data = load_json_exact(raw.decode("utf-8"))
    except Exception as exc:  # malformed JSON or non-finite constants
        raise SubmissionError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SubmissionError("top level must be a JSON object")
    for key in ("problem", "instance", "author", "solution"):
        if key not in data:
            raise SubmissionError(f"missing field {key!r}")
    if not isinstance(data["author"], dict) or not (data["author"].get("github") or data["author"].get("name")):
        raise SubmissionError("author must be an object with a 'github' handle or a 'name'")
    method = data.get("method", {})
    if not isinstance(method, dict):
        raise SubmissionError("method must be an object")
    if not isinstance(data["solution"], dict):
        raise SubmissionError("solution must be an object")
    return Submission(path=path, problem=str(data["problem"]), instance=str(data["instance"]),
                      author=data["author"], method=method, solution=data["solution"],
                      date=data.get("date"))
