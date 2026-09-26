import re


_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    lowered = text.lower().strip()
    slug = _slug_re.sub("-", lowered).strip("-")
    return slug or "experience"
