from safe_html import sanitize_html


def test_sanitizer_removes_executable_and_embedded_content():
    unsafe = (
        '<script>alert("x")</script>'
        '<style>body { display: none }</style>'
        '<iframe src="https://evil.example"></iframe>'
        '<svg><script>alert("svg")</script></svg>'
        '<p onclick="alert(1)" style="position:fixed">Safe text</p>'
    )

    cleaned = sanitize_html(unsafe)

    assert cleaned == "<p>Safe text</p>"


def test_sanitizer_keeps_markdown_formatting_and_safe_links():
    cleaned = sanitize_html(
        '<h1>Title</h1><p><strong>Bold</strong> '
        '<a href="https://example.com" title="Source">link</a></p>'
    )

    assert "<h1>Title</h1>" in cleaned
    assert "<strong>Bold</strong>" in cleaned
    assert 'href="https://example.com"' in cleaned
    assert 'rel="noopener noreferrer"' in cleaned


def test_sanitizer_rejects_unsafe_urls_and_raw_images():
    cleaned = sanitize_html(
        '<a href="javascript:alert(1)">bad</a>'
        '<img src="https://tracker.example/pixel" onerror="alert(1)">'
    )

    assert cleaned == '<a rel="noopener noreferrer">bad</a>'


def test_sanitizer_preserves_only_the_managed_placeholder_shape():
    cleaned = sanitize_html(
        '<span class="media-placeholder extra" data-media-ref="opaque-ref" '
        'onclick="alert(1)"></span>'
    )

    assert cleaned == (
        '<span class="media-placeholder" data-media-ref="opaque-ref"></span>'
    )
