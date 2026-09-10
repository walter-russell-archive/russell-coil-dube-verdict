"""Minimal Markdown renderer for the Dube Verdict site build.

Supports exactly the constructs the repository's Markdown uses: ATX headings,
paragraphs, thematic breaks, blockquotes, ordered/unordered nested lists,
pipe tables, code spans, strong, emphasis, links, and underline.

Convention: `_word_` marks text that is UNDERLINED in a source document, so it
renders as <u>, not <em>. `*word*` renders as <em>.

Standard library only.
"""

from __future__ import annotations

import html
import re

_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_STRONG = re.compile(r"\*\*(.+?)\*\*", re.S)
_EM = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?!\w)")
_UNDER = re.compile(r"(?<![\w_])_([^_\n]+)_(?!\w)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_HR = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$")
_ULI = re.compile(r"^(\s*)[-*]\s+(.*)$")
_OLI = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
_TABLE_SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")

_PLACEHOLDER = "\x00%d\x00"


def slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.lower().replace("&amp;", "and")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def inline(text: str, links: dict[str, str] | None = None) -> str:
    """Render inline Markdown. `links` rewrites link targets."""
    spans: list[str] = []

    def stash(m: re.Match[str]) -> str:
        spans.append(html.escape(m.group(1), quote=False))
        return _PLACEHOLDER % (len(spans) - 1)

    text = _CODE.sub(stash, text)
    text = html.escape(text, quote=False)

    def link(m: re.Match[str]) -> str:
        label, target = m.group(1), m.group(2)
        if links and target in links:
            target = links[target]
        external = target.startswith(("http://", "https://"))
        attrs = ' rel="noopener"' if external else ""
        return f'<a href="{html.escape(target, quote=True)}"{attrs}>{label}</a>'

    text = _LINK.sub(link, text)
    text = _STRONG.sub(r"<strong>\1</strong>", text)
    text = _EM.sub(r"<em>\1</em>", text)
    text = _UNDER.sub(r'<u class="src-underline">\1</u>', text)

    for i, code in enumerate(spans):
        text = text.replace(_PLACEHOLDER % i, f"<code>{code}</code>")
    return text


def _dedent(lines: list[str], width: int) -> list[str]:
    out = []
    for line in lines:
        if not line.strip():
            out.append("")
        elif len(line) - len(line.lstrip()) >= width:
            out.append(line[width:])
        else:
            out.append(line.lstrip())
    return out


def render(
    text: str,
    links: dict[str, str] | None = None,
    shift: int = 0,
    anchors: bool = False,
) -> str:
    """Render a Markdown block. `shift` lowers heading levels."""
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        m = _HEADING.match(stripped)
        if m:
            level = min(6, len(m.group(1)) + shift)
            body = inline(m.group(2), links)
            if anchors:
                anchor = slug(m.group(2))
                out.append(f'<h{level} id="{anchor}">{body}</h{level}>')
            else:
                out.append(f"<h{level}>{body}</h{level}>")
            i += 1
            continue

        if _HR.match(stripped):
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith(">"):
            block: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                block.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            quoted = render("\n".join(block), links)
            out.append(f"<blockquote>{quoted}</blockquote>")
            continue

        if line.startswith("|"):
            rows: list[str] = []
            while i < n and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(_table(rows, links))
            continue

        if _ULI.match(line) or _OLI.match(line):
            block_html, i = _list(lines, i, links)
            out.append(block_html)
            continue

        para: list[str] = []
        while i < n and lines[i].strip():
            nxt = lines[i]
            if _HEADING.match(nxt.strip()) or _HR.match(nxt.strip()):
                break
            if nxt.startswith("|") or nxt.strip().startswith(">"):
                break
            if para and (_ULI.match(nxt) or _OLI.match(nxt)):
                break
            para.append(nxt.strip())
            i += 1
        if para:
            out.append(f'<p>{inline(" ".join(para), links)}</p>')

    return "\n".join(out)


def _table(rows: list[str], links: dict[str, str] | None) -> str:
    def cells(row: str) -> list[str]:
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]
        return [c.strip() for c in row.split("|")]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]] if len(rows) > 1 and _TABLE_SEP.match(rows[1].strip()) else [cells(r) for r in rows[1:]]

    parts = ["<div class=\"table-wrap\"><table>", "<thead><tr>"]
    parts += [f"<th>{inline(c, links)}</th>" for c in head]
    parts.append("</tr></thead><tbody>")
    for row in body:
        parts.append("<tr>" + "".join(f"<td>{inline(c, links)}</td>" for c in row) + "</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def _list(lines: list[str], start: int, links: dict[str, str] | None) -> tuple[str, int]:
    first = _ULI.match(lines[start]) or _OLI.match(lines[start])
    assert first is not None
    indent = len(first.group(1))
    ordered = _OLI.match(lines[start]) is not None
    # Each item is (paragraph lines of the item itself, nested block lines).
    items: list[tuple[list[str], list[str]]] = []
    i = start
    n = len(lines)
    blanks = 0

    while i < n:
        line = lines[i]
        if not line.strip():
            blanks += 1
            i += 1
            continue

        m_u = _ULI.match(line)
        m_o = _OLI.match(line)
        m = m_u or m_o
        marker_indent = len(m.group(1)) if m else -1
        line_indent = len(line) - len(line.lstrip())

        if m and marker_indent == indent:
            body = m.group(2) if m_u else m.group(3)  # type: ignore[union-attr]
            items.append(([body], []))
            blanks = 0
            i += 1
            continue

        if not items:
            break

        head, block = items[-1]
        nested = m is not None and marker_indent > indent
        indented = line_indent > indent

        if nested:
            block.extend([""] * blanks + [line])
        elif blanks == 0 and not block:
            # Lazy continuation: the line belongs to the item's own paragraph.
            head.append(line.strip())
        elif indented:
            block.extend([""] * blanks + [line])
        else:
            break
        blanks = 0
        i += 1

    tag = "ol" if ordered else "ul"
    parts = [f"<{tag}>"]
    for head, block in items:
        text = inline(" ".join(head), links)
        rest = _dedent(block, indent + 2)
        nested_html = render("\n".join(rest), links) if any(r.strip() for r in rest) else ""
        parts.append(f"<li>{text}{nested_html}</li>")
    parts.append(f"</{tag}>")
    return "".join(parts), i
