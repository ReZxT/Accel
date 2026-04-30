import hashlib
import math
import re

_STOP = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could to of in for on with at by from and or but "
    "not no nor so yet both either neither each every all any few more most other "
    "some such than too very just about above after again also between down during "
    "further here how into it its itself me my myself off only out own same she "
    "that their them then there these they this those through under until up we "
    "what when where which while who whom why you your i he his him her".split()
)

_TOKEN_RE = re.compile(r"[a-z0-9_./:-]+")


def _token_id(token: str) -> int:
    return int(hashlib.md5(token.encode()).hexdigest()[:8], 16)


def sparse_vector(text: str) -> tuple[list[int], list[float]]:
    """Compute a BM25-style sparse vector from text.
    Returns (indices, values) for Qdrant SparseVector."""
    tokens = _TOKEN_RE.findall(text.lower())
    tokens = [t for t in tokens if t not in _STOP and len(t) > 1]

    if not tokens:
        return [], []

    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1

    indices = []
    values = []
    for token, count in tf.items():
        indices.append(_token_id(token))
        values.append(1.0 + math.log(count))

    return indices, values
