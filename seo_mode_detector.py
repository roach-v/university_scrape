"""
SEO Mode Detector

Determines whether to use Mode 1 (Article/Page SEO Optimization) or
Mode 2 (Full Website Audit) based on user input analysis.

Exports:
    SEOMode enum (MODE1_ARTICLE, MODE2_AUDIT, AMBIGUOUS)
    detect_mode(user_input: str, url: str | None = None) -> SEOMode
    mode_description(mode: SEOMode) -> str
"""

from enum import Enum
import re
from typing import Optional


class SEOMode(Enum):
    MODE1_ARTICLE = "Mode 1: Article/Page SEO Optimization"
    MODE2_AUDIT = "Mode 2: Full Website Audit"
    AMBIGUOUS = "Ambiguous — requires clarification"


# ── Mode 1 (Article/Page SEO Optimization) signals ──────────────────────────

_MODE1_INPUT_SIGNALS = {
    "optimize this article", "seo optimize this", "improve this for seo",
    "check this article", "make this rank", "seo check this",
    "rewrite this article", "improve this article", "polish this article",
    "review this article", "optimize article", "optimize this",
    "seo this article", "optimize the article",
}

# "check" alone is too generic ("check the weather" != SEO); it needs a
# content-related object to trigger Mode 1.
_MODE1_ACTION_VERBS = {"optimize", "improve", "rewrite", "polish"}

# Nouns that pair with Mode 1 verbs to confirm article/page focus.
_MODE1_CONTENT_NOUNS = {"article", "page", "post", "blog", "content", "draft", "writing"}

_MODE1_LONG_TEXT_THRESHOLD = 80  # words — pasted article text is usually longer


# ── Mode 2 (Full Website Audit) signals ────────────────────────────────────

_MODE2_INPUT_SIGNALS = {
    "audit my site", "full seo audit", "website seo", "site audit",
    "seo health check", "audit my website", "seo audit",
    "review my site", "review my website", "check my site",
    "check my website", "site review", "website review",
    "audit this site", "seo strategy",
}

_MODE2_AUDIT_NOUNS = {"audit", "review", "strategy"}

# A URL that looks like a root domain (no path or just "/") favours Mode 2.
_ROOT_DOMAIN_PATTERN = re.compile(
    r"^https?://[^/]+/?$", re.IGNORECASE
)


# ── Detection helpers ───────────────────────────────────────────────────────


def _normalize(text: str) -> str:
    """Lowercase, strip extra whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _is_article_text(text: str) -> bool:
    """
    Heuristic: if the user pastes a lot of raw text without a URL,
    treat it as article content.
    """
    words = text.split()
    # A short phrase like "audit my site" is not article text.
    if len(words) < _MODE1_LONG_TEXT_THRESHOLD:
        return False
    # Crude check: no obvious URL in the text itself.
    if re.search(r"https?://", text, re.IGNORECASE):
        return False
    return True


def _has_mode1_verbs(text: str) -> bool:
    """Check for action verbs that signal Mode 1."""
    words = set(text.split())
    return bool(words & _MODE1_ACTION_VERBS)


def _has_mode2_nouns(text: str) -> bool:
    """Check for nouns that signal Mode 2."""
    words = set(text.split())
    return bool(words & _MODE2_AUDIT_NOUNS)


# ── Public API ──────────────────────────────────────────────────────────────


# A pattern to find a URL anywhere in the input string.
_URL_IN_TEXT_PATTERN = re.compile(
    r"https?://[^\s]+", re.IGNORECASE
)


def _extract_url_from_text(text: str) -> Optional[str]:
    """If the text contains a URL, return the first one found."""
    m = _URL_IN_TEXT_PATTERN.search(text)
    return m.group(0) if m else None


def detect_mode(user_input: str, url: Optional[str] = None) -> SEOMode:
    """
    Determine which SEO mode to use based on the user's natural-language
    input and an optional URL.

    Parameters
    ----------
    user_input : str
        The raw text provided by the user (message, prompt, etc.).
    url : str or None
        An optional URL the user included.

    Returns
    -------
    SEOMode
        MODE1_ARTICLE, MODE2_AUDIT, or AMBIGUOUS.
    """
    text = _normalize(user_input)

    # If no separate URL was provided, try to extract one from the input text.
    if url is None:
        url = _extract_url_from_text(user_input)

    # When the *only* content is a bare URL (no surrounding words),
    # treat the URL as the effective input for classification.
    if url and _normalize(url) == text:
        user_input_for_text = ""
    else:
        user_input_for_text = user_input

    text = _normalize(user_input_for_text)

    # ── Exact / near-exact signal match ────────────────────────────────

    if text in _MODE1_INPUT_SIGNALS:
        return SEOMode.MODE1_ARTICLE

    if text in _MODE2_INPUT_SIGNALS:
        return SEOMode.MODE2_AUDIT

    # ── Plain article text (no URL, long block of text) ────────────────

    if not url and _is_article_text(text):
        return SEOMode.MODE1_ARTICLE

    # ── URL-based heuristics ───────────────────────────────────────────

    if url:
        url_lower = url.strip().lower()

        # Root domain → likely a site audit
        if _ROOT_DOMAIN_PATTERN.match(url_lower):
            # But if the user also says "optimize", lean Mode 1
            if _has_mode1_verbs(text) and not _has_mode2_nouns(text):
                return SEOMode.MODE1_ARTICLE
            return SEOMode.MODE2_AUDIT

        # Specific page URL (has path) – could be either
        # "optimize" + URL → Mode 1
        if _has_mode1_verbs(text) and not _has_mode2_nouns(text):
            return SEOMode.MODE1_ARTICLE

        # "audit" + URL → Mode 2
        if _has_mode2_nouns(text):
            return SEOMode.MODE2_AUDIT

        # Just a URL with no clear verb → ambiguous when it's a page URL
        return SEOMode.AMBIGUOUS

    # ── No URL – analyse the text itself ───────────────────────────────

    # "audit", "review", "strategy" → Mode 2
    if _has_mode2_nouns(text):
        return SEOMode.MODE2_AUDIT

    # "optimize", "improve", "rewrite" → Mode 1
    if _has_mode1_verbs(text):
        return SEOMode.MODE1_ARTICLE

    # Nothing decisive → ambiguous
    return SEOMode.AMBIGUOUS


def mode_description(mode: SEOMode) -> str:
    """Return a human-readable description of the mode."""
    descriptions = {
        SEOMode.MODE1_ARTICLE: (
            "Mode 1: Optimise a single article or page for search engines. "
            "Focus on on-page SEO, keyword placement, meta tags, readability."
        ),
        SEOMode.MODE2_AUDIT: (
            "Mode 2: Perform a full website SEO audit. "
            "Analyse site-wide issues, architecture, multiple pages."
        ),
        SEOMode.AMBIGUOUS: (
            "The request is ambiguous. "
            "Please clarify whether you want (1) to optimise a single "
            "article/page, or (2) a full website audit."
        ),
    }
    return descriptions[mode]


# ── Example usage (if run directly) ─────────────────────────────────────────

if __name__ == "__main__":
    import sys

    test_cases = [
        # (user_input, url, expected_mode_name)
        # Mode 1 examples
        ("optimize this article", None, "MODE1_ARTICLE"),
        ("seo optimize this", None, "MODE1_ARTICLE"),
        ("improve this for SEO", None, "MODE1_ARTICLE"),
        ("check this article", None, "MODE1_ARTICLE"),
        ("make this rank", None, "MODE1_ARTICLE"),
        ("Can you rewrite this blog post about hiking gear?", None, "MODE1_ARTICLE"),
        ("Here is my draft: " + "words " * 100, None, "MODE1_ARTICLE"),
        ("optimize https://example.com/page-title", None, "MODE1_ARTICLE"),
        # Mode 2 examples
        ("audit my site", None, "MODE2_AUDIT"),
        ("full SEO audit", None, "MODE2_AUDIT"),
        ("website SEO", None, "MODE2_AUDIT"),
        ("site audit", None, "MODE2_AUDIT"),
        ("SEO health check", None, "MODE2_AUDIT"),
        ("https://example.com", None, "MODE2_AUDIT"),
        ("review my site https://example.com", None, "MODE2_AUDIT"),
        ("Can you audit this website?", None, "MODE2_AUDIT"),
        # Ambiguous
        ("hello", None, "AMBIGUOUS"),
        ("some random text", None, "AMBIGUOUS"),
        ("https://example.com/about", None, "AMBIGUOUS"),
        ("check this", None, "AMBIGUOUS"),
        ("https://example.com", "https://example.com/about", "AMBIGUOUS"),
    ]

    passed = 0
    failed = 0

    for inp, url, expected_name in test_cases:
        result = detect_mode(inp, url)
        expected = SEOMode[expected_name]
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(
            f"  {status} detect_mode({inp!r}, {url!r})"
            f"\n       → {result.value}  (expected {expected_name})"
        )

    print(f"\n{'='*60}")
    print(f"  {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)