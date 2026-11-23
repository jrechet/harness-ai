"""How `harness flow` reads a JSON file it is given: a definition, an event or a run. One rule more
than `json.load`: a key written twice in one object is refused, since JSON keeps only its last value
without a word, and the file then does not say one thing (docs/workflow-harness/flow-spec.md,
section 2). `flow_fit.parse` refuses such a key in the answers the same way, as a problem to fix."""
from __future__ import annotations

from typing import Any


class KeyWrittenTwice(ValueError):
    """A key appears more than once in one object of the file."""


def once(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """The `object_pairs_hook` of `json.load`: the object, or KeyWrittenTwice on its first repeated key."""
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise KeyWrittenTwice(f'the key "{key}" is written twice in one object; JSON keeps only the last one, '
                                  "without a word. Write it once.")
        seen.add(key)
    return dict(pairs)
