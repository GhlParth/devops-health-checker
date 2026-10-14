import re


TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "crashloopbackoff": ("crash", "loop", "backoff"),
    "oomkilled": ("oom", "killed"),
}


def tokenize(text: str) -> list[str]:
    """Tokenize text and expand common infrastructure status terms."""
    terms: list[str] = []
    for term in re.findall(r"[a-z0-9]+", text.lower()):
        terms.append(term)
        terms.extend(TERM_ALIASES.get(term, ()))
    return terms
