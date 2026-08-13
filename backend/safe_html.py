"""Allowlist sanitization for HTML rendered from question-pack Markdown."""

import nh3


_ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "del",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
_CLEAN_CONTENT_TAGS = {
    "embed",
    "iframe",
    "math",
    "object",
    "script",
    "style",
    "svg",
    "template",
}
_CLEANER = nh3.Cleaner(
    tags=_ALLOWED_TAGS,
    clean_content_tags=_CLEAN_CONTENT_TAGS,
    attributes={
        "a": {"href", "title"},
        "span": {"data-media-ref"},
    },
    allowed_classes={"span": {"media-placeholder"}},
    url_schemes={"http", "https", "mailto"},
    link_rel="noopener noreferrer",
    strip_comments=True,
)


def sanitize_html(html: str) -> str:
    """Return a safe HTML fragment while retaining managed media placeholders."""

    return _CLEANER.clean(html).strip()
