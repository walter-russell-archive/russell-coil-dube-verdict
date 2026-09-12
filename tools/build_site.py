#!/usr/bin/env python3
"""Build the static site in docs/ from this repository's Markdown and scans.

    python3 tools/build_site.py                 # full build
    python3 tools/build_site.py --skip-images   # HTML only (scans already built)
    python3 tools/build_site.py --base https://dube.walterrussellarchive.org

The Markdown in essay/, transcripts/, schematics/ and verification/ stays the
single source of truth. docs/ is generated output: never hand-edit it.
Image derivatives need Pillow. Everything else is standard library.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mdlite  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
ASSETS = Path(__file__).resolve().parent / "assets"

REPO = "https://github.com/walter-russell-archive/russell-coil-dube-verdict"
BLOB = REPO + "/blob/main"
RAW = "https://raw.githubusercontent.com/walter-russell-archive/russell-coil-dube-verdict/main"
IA_ITEM = "https://archive.org/details/fulcrum-science-journal-usp-1992-1998"
DEFAULT_BASE = "https://dube.walterrussellarchive.org"
CONTACT = "contact@walterrussellarchive.org"

PDFS = {
    "v4n3": "fulcrum_v4n3_october_1996.pdf",
    "v5n1": "fulcrum_v5n1_may_1997.pdf",
}
ISSUE_LABEL = {
    "v4n3": "Fulcrum Vol. 4 No. 3 (October 1996)",
    "v5n1": "Fulcrum Vol. 5 No. 1 (May 1997)",
}
RENDER_DIR = {"v4n3": "v4n3_renders", "v5n1": "v5n1_renders"}

NAV = [
    ("index.html", "The essay"),
    ("evidence.html", "The documents"),
    ("schematics.html", "The drawings"),
    ("provenance.html", "Provenance"),
]


# --------------------------------------------------------------------------
# scans
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Scan:
    stem: str
    issue: str
    width: int
    quality: int

    @property
    def source(self) -> Path:
        return ROOT / "sources" / RENDER_DIR[self.issue] / f"{self.stem}.png"

    @property
    def out(self) -> Path:
        return OUT / "scans" / f"{self.stem}.jpg"

    @property
    def url(self) -> str:
        return f"scans/{self.stem}.jpg"

    @property
    def full_res(self) -> str:
        return f"{RAW}/sources/{RENDER_DIR[self.issue]}/{self.stem}.png"


def scan_plan() -> list[Scan]:
    plan = [Scan(f"v4n3_d-{p}", "v4n3", 1275, 82) for p in range(18, 28)]
    plan += [Scan(f"v4n3_p-{p:02d}", "v4n3", 850, 82) for p in range(1, 5)]
    plan += [Scan(f"v5n1_p-{p:03d}", "v5n1", 1275, 82) for p in range(85, 91)]
    plan += [Scan(f"v5n1_300dpi_p-{p:03d}", "v5n1", 1500, 80) for p in range(91, 110)]
    return plan


SCANS = {s.stem: s for s in scan_plan()}


def scan_for(issue: str, pdf_page: int, hi_res: bool = False) -> Scan:
    if issue == "v4n3":
        stem = f"v4n3_d-{pdf_page}"
    elif hi_res:
        stem = f"v5n1_300dpi_p-{pdf_page:03d}"
    else:
        stem = f"v5n1_p-{pdf_page:03d}"
    scan = SCANS.get(stem)
    if scan is None:
        raise SystemExit(f"no scan planned for {issue} PDF page {pdf_page} ({stem})")
    return scan


DIMS_FILE = OUT / "scans" / "dimensions.json"
SCAN_DIMS: dict[str, list[int]] = {}


def load_dims() -> None:
    """Intrinsic scan sizes, so pages reserve space before an image loads."""
    global SCAN_DIMS
    if DIMS_FILE.exists():
        SCAN_DIMS = json.loads(DIMS_FILE.read_text(encoding="utf-8"))


def svg_size(path: Path, width: int) -> tuple[int, int]:
    box = re.search(r'viewBox="([\d.\s+-]+)"', path.read_text(encoding="utf-8"))
    if not box:
        raise SystemExit(f"{path}: no viewBox, cannot size the image")
    values = [float(v) for v in box.group(1).split()]
    return width, round(width * values[3] / values[2])


def build_scans(force: bool = False) -> int:
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        raise SystemExit("Pillow is required for the image step; use --skip-images")

    (OUT / "scans").mkdir(parents=True, exist_ok=True)
    written = 0
    for scan in SCANS.values():
        if not scan.source.exists():
            raise SystemExit(f"missing render: {scan.source}")
        stale = force or not scan.out.exists() or scan.out.stat().st_mtime < scan.source.stat().st_mtime
        if stale:
            with Image.open(scan.source) as im:
                im = im.convert("RGB")
                if im.width > scan.width:
                    height = round(im.height * scan.width / im.width)
                    im = im.resize((scan.width, height), Image.LANCZOS)
                im.save(scan.out, "JPEG", quality=scan.quality, optimize=True, progressive=True)
            written += 1
        with Image.open(scan.out) as im:
            SCAN_DIMS[scan.stem] = [im.width, im.height]
    DIMS_FILE.write_text(json.dumps(SCAN_DIMS, indent=0, sort_keys=True), encoding="utf-8")
    return written



# --------------------------------------------------------------------------
# transcripts
# --------------------------------------------------------------------------


META_BULLET = re.compile(r"^-\s+(?:\*\*)?([A-Za-z][^:*]*?)(?:\*\*)?:\s*(.*)$")


@dataclass
class Transcript:
    path: Path
    title: str
    meta: dict[str, str]
    header_notes: list[str]
    body: list[tuple[str, str]]  # (kind, text): kind in {"head", "text"}
    notes: str

    @property
    def filename(self) -> str:
        return self.path.name


def parse_transcript(path: Path) -> Transcript:
    lines = (ROOT / path).read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    title = lines[0].lstrip("#").strip()

    split = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    meta: dict[str, str] = {}
    header_notes: list[str] = []
    last_key: str | None = None
    for line in lines[1:split]:
        if not line.strip():
            continue
        found = META_BULLET.match(line.strip())
        if found:
            last_key = found.group(1).strip()
            meta[last_key] = re.sub(r"^\*\*\s*", "", found.group(2).strip()).strip()
        elif line.startswith(("  ", "\t")) and last_key:
            meta[last_key] = (meta[last_key] + "\n" + line.strip()).strip()
        else:
            header_notes.append(line.strip())

    rest = lines[split + 1 :]
    notes_at = next(
        (i for i, line in enumerate(rest) if re.match(r"^##\s+Notes\b", line.strip())), None
    )
    notes = ""
    if notes_at is not None:
        notes = "\n".join(rest[notes_at + 1 :]).strip()
        rest = rest[:notes_at]

    body: list[tuple[str, str]] = []
    chunk: list[str] = []

    def flush() -> None:
        text = "\n".join(chunk).strip("\n")
        chunk.clear()
        filled = [line for line in text.split("\n") if line.strip()]
        if not filled:
            return
        if all(line.lstrip().startswith(">") for line in filled):
            unquoted = "\n".join(re.sub(r"^\s*>\s?", "", line) for line in text.split("\n"))
            body.append(("quote", unquoted.strip("\n")))
        elif len(filled) == 1 and re.match(r"^\*[^*].*\*$", filled[0].strip()):
            body.append(("note", filled[0].strip()))
        else:
            body.append(("text", text))

    for line in rest:
        stripped = line.strip()
        if stripped == "---" or not stripped:
            flush()
            continue
        head = re.match(r"^(#{2,4})\s+(.*)$", stripped)
        if head:
            flush()
            body.append(("head", head.group(2).strip()))
            continue
        chunk.append(line.rstrip())
    flush()

    return Transcript(path, title, meta, header_notes, body, notes)


def meta_pages(value: str) -> list[int]:
    """Parse "23–25 (file.pdf)" or "18, 19" into page numbers."""
    head = value.split("\n")[0].split("(")[0]
    pages: list[int] = []
    for part in re.split(r",|\band\b", head):
        found = re.findall(r"\d+", part)
        if not found:
            continue
        if re.search(r"\d+\s*[–—-]\s*\d+", part) and len(found) >= 2:
            pages += list(range(int(found[0]), int(found[1]) + 1))
        else:
            pages.append(int(found[0]))
    return pages


def meta_get(t: Transcript, *keys: str) -> str | None:
    for key in keys:
        for have, value in t.meta.items():
            if have.lower() == key.lower():
                return value
    return None


# --------------------------------------------------------------------------
# document table (chronological)
# --------------------------------------------------------------------------


@dataclass
class Doc:
    slug: str
    title: str
    when: str
    file: str
    issue: str
    summary: str
    hi_res: bool = False
    transcript: Transcript = field(init=False)

    def load(self) -> None:
        self.transcript = parse_transcript(Path("transcripts") / self.file)

    @property
    def pdf_pages(self) -> list[int]:
        value = meta_get(self.transcript, "PDF pages", "PDF page")
        if not value:
            raise SystemExit(f"{self.file}: no PDF page metadata")
        return meta_pages(value)

    @property
    def journal_pages(self) -> str:
        value = meta_get(self.transcript, "Journal pages", "Journal page") or ""
        return value.split("(")[0].strip()

    @property
    def scans(self) -> list[Scan]:
        return [scan_for(self.issue, p, self.hi_res) for p in self.pdf_pages]


@dataclass
class Gap:
    when: str
    title: str
    note: str


TIMELINE: list[Doc | Gap] = [
    Doc(
        slug="tesla-lee",
        title="Russell and Royal Lee on Nikola Tesla",
        when="March 1954 / January 1955",
        file="v4n3_p15_russell_lee_tesla.md",
        issue="v4n3",
        summary=(
            "Two letters, plus the 1996 editor's note that calls them the only trace of the "
            "Russell–Tesla association in the USP archives. Neither letter mentions secrecy."
        ),
    ),
    Gap(
        when="August 8, 1958",
        title="Walter Russell's coil description",
        note=(
            "Dube's letter of August 25 answers a Russell \"description dated August 8th\". "
            "Neither issue reprinted that description. It survives, if at all, in USP's private archives."
        ),
    ),
    Doc(
        slug="protocol",
        title="Dube proposes the test protocol",
        when="August 25, 1958",
        file="v5n1_p83_dube_to_walter_russell_1958-08-25.md",
        issue="v5n1",
        summary=(
            "The control is stated in advance: equal core length and cross section, and the "
            "identical amount of wire of the same size. Relative pulling capability is the agreed criterion."
        ),
    ),
    Doc(
        slug="russells-approve",
        title="The Russells approve the plan",
        when="August 30, 1958",
        file="v5n1_p85_russells_to_dube_1958-08-30.md",
        issue="v5n1",
        summary=(
            "Walter and Lao Russell accept the protocol as outlined and ask for one design "
            "change, a through-hole for later transmutation work."
        ),
    ),
    Gap(
        when="October 3, 1958",
        title="Dube's letter with the revised drawings",
        note=(
            "This letter transmitted the revised test-unit drawings LO 8308-11 and -12, dated "
            "October 2, 1958. The Russells' reply of October 5 acknowledges it. Neither issue reprinted it."
        ),
    ),
    Doc(
        slug="prediction",
        title="The prediction: a 40 to 60 percent advantage",
        when="October 5, 1958",
        file="v5n1_p87_russells_to_dube_1958-10-05.md",
        issue="v5n1",
        summary=(
            "Russell commits a number to paper before the coils exist: a 40 to 60 percent "
            "increase in \"gravity power\" for his coils over the conventional pair."
        ),
    ),
    Doc(
        slug="verdict",
        title="Dube reports the result",
        when="November 21, 1958",
        file="v4n3_p17_dube_letter.md",
        issue="v4n3",
        summary=(
            "One sentence carries the verdict. Dube also returned both pairs of test coils so "
            "that Russell could check the measurements himself."
        ),
    ),
    Doc(
        slug="report",
        title="Report on Evaluation of Russell Coil",
        when="November 1958 (enclosure)",
        file="v4n3_p18_evaluation_report.md",
        issue="v4n3",
        summary=(
            "The Alco engineering report: design, two tests, results, and three conclusions. "
            "It discloses the 4 percent resistance deviation that favors the Russell coil."
        ),
    ),
    Doc(
        slug="concession",
        title="The Russells concede",
        when="November 24, 1958",
        file="v4n3_p20_russell_response.md",
        issue="v4n3",
        summary=(
            "Three pages to the funder, with a copy to Dube. The concession \"as a fact of law\" "
            "stands beside the retreat: the martyrs, the moved goalposts, and the missile-defense claim."
        ),
    ),
    Doc(
        slug="editor-1996",
        title="The 1996 editor's note",
        when="October 1996",
        file="v4n3_p23_editor_note.md",
        issue="v4n3",
        summary=(
            "USP's editor states why he printed the file, asks that the concession appear in "
            "future editions of the Home Study Course, and reports a second negative result on the Unit 11 lens bank."
        ),
    ),
    Doc(
        slug="editor-1997",
        title="The 1997 editor's introduction",
        when="May 1997",
        file="v5n1_p82_from_the_archives_intro.md",
        issue="v5n1",
        summary="The introduction to the 19 pages of engineering drawings reprinted in this issue.",
    ),
]

DOCS: list[Doc] = [d for d in TIMELINE if isinstance(d, Doc)]


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------


def page(
    *,
    title: str,
    description: str,
    current: str,
    body: str,
    base: str,
    og_image: str = "assets/og-card.png",
    noindex: bool = False,
) -> str:
    # The 404 page (the only noindex page) is served at any missing URL, at any
    # depth, so every internal reference on it must be absolute.
    prefix = f"{base}/" if noindex else ""
    nav = "\n".join(
        '      <a href="{href}"{cur}>{label}</a>'.format(
            href=prefix + href, label=label, cur=' aria-current="page"' if href == current else ""
        )
        for href, label in NAV
    )
    esc_title = html.escape(title, quote=True)
    esc_desc = html.escape(description, quote=True)
    canonical = f"{base}/{current}" if current != "index.html" else f"{base}/"
    if noindex:
        head_meta = '<meta name="robots" content="noindex">'
    else:
        head_meta = f"""<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc_title}">
<meta property="og:description" content="{esc_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{base}/{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{esc_title}</title>
<meta name="description" content="{esc_desc}">
{head_meta}
<link rel="stylesheet" href="{prefix}assets/site.css">
<script>document.documentElement.classList.add("js");try{{var t=localStorage.getItem("theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t;}}catch(e){{}}</script>
</head>
<body>
<header class="masthead">
  <div class="masthead-inner">
    <a class="wordmark" href="{prefix}index.html">Walter Russell Archive</a>
    <nav>
{nav}
      <button class="theme-toggle" type="button" data-theme-toggle aria-pressed="false"
              aria-label="Switch to the dark theme" title="Switch to the dark theme">
        <svg class="icon icon-moon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
        <svg class="icon icon-sun" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4.6"/><path d="M12 1.4v2.4M12 20.2v2.4M4.4 4.4l1.7 1.7M17.9 17.9l1.7 1.7M1.4 12h2.4M20.2 12h2.4M4.4 19.6l1.7-1.7M17.9 6.1l1.7-1.7"/></svg>
      </button>
    </nav>
  </div>
</header>
<main>
{body}
</main>
<footer class="site">
  <div class="footer-inner">
    <p>Primary sources for the 1958 Alco Valve test of the Russell coil. Transcripts are verbatim.
       Uncertain readings carry their uncertainty.</p>
    <p>Original work (essay, transcription formatting, editorial notes, schematics) is licensed
       <a href="{BLOB}/LICENSE" rel="noopener">CC BY 4.0</a>. The reproduced historical documents
       and scans keep their own copyright status.</p>
    <p>Repository: <a href="{REPO}" rel="noopener">github.com/walter-russell-archive/russell-coil-dube-verdict</a>
       &middot; Journal mirror: <a href="{IA_ITEM}" rel="noopener">Internet Archive</a>
       &middot; Contact: <a href="mailto:{CONTACT}">{CONTACT}</a></p>
    <p>The pages are generated from the repository Markdown by <code>tools/build_site.py</code>.</p>
  </div>
</footer>
<div id="lightbox" role="dialog" aria-label="Page scan"><img alt=""><div class="lb-caption"></div></div>
<script src="{prefix}assets/site.js"></script>
</body>
</html>
"""


def title_block(kicker: str, heading: str, subtitle: str, tools: list[tuple[str, str]]) -> str:
    buttons = "".join(
        '<a href="{href}"{rel}>{label}</a>'.format(
            href=href,
            label=html.escape(label),
            rel=' rel="noopener"' if href.startswith("http") else "",
        )
        for label, href in tools
    )
    return f"""<div class="title-block">
  <p class="kicker">{kicker}</p>
  <h1>{heading}</h1>
  <p class="subtitle">{subtitle}</p>
  <div class="toolbar">{buttons}</div>
</div>"""


def figure(
    scan: Scan,
    caption: str,
    *,
    wide: bool = False,
    lazy: bool = True,
) -> str:
    cls = "figure-wide" if wide else ""
    loading = ' loading="lazy" decoding="async"' if lazy else ""
    alt = html.escape(html.unescape(re.sub(r"<[^>]+>", "", caption))[:180], quote=True)
    dims = SCAN_DIMS.get(scan.stem)
    if not dims:
        raise SystemExit(f"no recorded size for {scan.stem}; run the image step first")
    size = f'width="{dims[0]}" height="{dims[1]}"'
    return f"""<figure class="{cls}">
  <div class="scan-frame"><img src="{scan.url}" alt="{alt}" {size}{loading}></div>
  <figcaption>{caption} <a href="{scan.full_res}" rel="noopener">Full-resolution PNG</a>.</figcaption>
</figure>"""


def insert_after(doc: str, needle: str, closing: str, block: str, where: str) -> str:
    at = doc.find(needle)
    if at < 0:
        raise SystemExit(f"{where}: anchor text not found: {needle[:60]!r}")
    end = doc.find(closing, at)
    if end < 0:
        raise SystemExit(f"{where}: no {closing} after anchor {needle[:40]!r}")
    end += len(closing)
    return doc[:end] + "\n" + block + doc[end:]


def drop_h1(path: Path) -> str:
    """Read a Markdown file without its top-level heading."""
    lines = path.read_text(encoding="utf-8").split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# link rewriting for repository-relative Markdown links
# --------------------------------------------------------------------------


def link_map() -> dict[str, str]:
    links = {
        "essay/the-dube-verdict.md": "index.html",
        "schematics/README_schematics.md": "schematics.html#reading-the-graph",
        "transcripts/INDEX_v4n3.md": "provenance.html#concordance",
        "transcripts/INDEX_v5n1.md": "provenance.html#concordance",
        "verification/maguire-dube-verification.md": "provenance.html#context-verification",
        "LICENSE": f"{BLOB}/LICENSE",
    }
    for doc in DOCS:
        links[f"transcripts/{doc.file}"] = f"evidence.html#{doc.slug}"
    return links


def link_code_refs(doc_html: str) -> str:
    """Turn <code>transcript.md</code> mentions into links to the document."""
    targets = {doc.file: f"evidence.html#{doc.slug}" for doc in DOCS}
    targets["v5n1_drawings_description.md"] = "schematics.html#the-nineteen-sheets"
    targets["INDEX_v4n3.md"] = "provenance.html#concordance"
    targets["INDEX_v5n1.md"] = "provenance.html#concordance"
    targets["schematics/README_schematics.md"] = "schematics.html#reading-the-graph"
    for name, href in targets.items():
        doc_html = doc_html.replace(
            f"<code>{name}</code>", f'<a href="{href}"><code>{name}</code></a>'
        )
    return doc_html


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------


def build_index(base: str) -> str:
    text = (ROOT / "essay" / "the-dube-verdict.md").read_text(encoding="utf-8")
    lines = text.split("\n")
    heading = lines[0].lstrip("#").strip()
    subtitle = next(line.lstrip("#").strip() for line in lines[1:] if line.startswith("### "))
    lede_line = next(line for line in lines if line.startswith("*All quotations"))
    body_start = next(i for i, line in enumerate(lines) if line.strip() == "---")
    body_md = "\n".join(lines[body_start + 1 :])

    links = link_map()
    body = mdlite.render(body_md, links=links, anchors=True)
    body = link_code_refs(body)

    graph_w, graph_h = svg_size(ROOT / "schematics" / "pull_test_graph.svg", 900)
    graph_fig = f"""<figure class="figure-wide">
  <div class="svg-frame"><img src="schematics/pull_test_graph.svg" alt="Redrawn Fig. 4: pull force against gap for both coil types. The conventional curve is above the Russell curve at every gap." width="{graph_w}" height="{graph_h}"></div>
  <figcaption>Fig. 4 redrawn from the 1958 sheet: breakaway pull against gap, 24 VDC. The conventional
    coils out-pull the Russell step-diameter coils at all four plotted gaps. Readings carry
    &plusmn;0.05&nbsp;lb, and &plusmn;0.1&nbsp;lb at zero gap where the two markers overlap the axis.
    <a href="schematics.html#reading-the-graph">Extraction method</a> &middot;
    <a href="{scan_for('v5n1', 95, hi_res=True).full_res}" rel="noopener">Source sheet, 300&nbsp;dpi</a>.</figcaption>
</figure>"""

    verdict_scan = scan_for("v4n3", 20)
    verdict_fig = f"""<figure>
  <div class="scan-frame"><img src="{verdict_scan.url}" alt="Scan of Dube's letter of November 21, 1958 on Alco Valve Company letterhead." width="{verdict_scan.width}" loading="lazy" decoding="async"></div>
  <figcaption>Dube's cover letter, 21 November 1958, as printed in <em>Fulcrum</em> V4N3 (journal p. 17).
    <a href="evidence.html#verdict">Verbatim transcript</a> &middot;
    <a href="{verdict_scan.full_res}" rel="noopener">Full-resolution PNG</a>.</figcaption>
</figure>"""

    concession_scan = scan_for("v4n3", 23)
    concession_fig = f"""<figure>
  <div class="scan-frame"><img src="{concession_scan.url}" alt="Scan of the first page of the Russells' letter of November 24, 1958." width="{concession_scan.width}" loading="lazy" decoding="async"></div>
  <figcaption>Page 1 of the concession letter, 24 November 1958 (<em>Fulcrum</em> V4N3, journal p. 20).
    <a href="evidence.html#concession">Verbatim transcript, all three pages</a> &middot;
    <a href="{concession_scan.full_res}" rel="noopener">Full-resolution PNG</a>.</figcaption>
</figure>"""

    body = insert_after(
        body,
        "unable to detect any advantage for the Russell coil.",
        "</blockquote>",
        verdict_fig,
        "index: verdict figure",
    )
    body = insert_after(
        body,
        "gridline-calibrated from the 300 dpi scan",
        "</p>",
        graph_fig,
        "index: Fig. 4 figure",
    )
    body = insert_after(
        body,
        "can admit it as a fact of law, as you have proved it to be.",
        "</blockquote>",
        concession_fig,
        "index: concession figure",
    )

    contents = "\n".join(
        f'    <li><a href="#{m.group(1)}">{m.group(2)}</a></li>'
        for m in re.finditer(r'<h2 id="([^"]+)">(.*?)</h2>', body)
    )

    head = title_block(
        "The 1958 Russell coil test",
        heading,
        subtitle,
        [
            ("The documents", "evidence.html"),
            ("The drawings", "schematics.html"),
            ("Provenance", "provenance.html"),
            ("Repository", REPO),
        ],
    )

    lede = mdlite.render(lede_line, links=links)
    lede = lede.replace("<p>", '<p class="lede">', 1)

    body_html = f"""{head}
<article class="prose">
{lede}
<nav class="callout toc" aria-label="Contents">
  <h2>Contents</h2>
  <ul>
{contents}
  </ul>
</nav>
{body}
</article>"""
    return page(
        title="The Dube Verdict — the 1958 Russell coil test",
        description=(
            "In 1958 Walter Russell predicted a 40 to 60 percent advantage for his coil design. "
            "A controlled test at the Alco Valve Company measured a 5 to 10 percent deficit at every gap, "
            "and Russell conceded the result in writing three days later. Complete primary sources."
        ),
        current="index.html",
        body=body_html,
        base=base,
    )


def transcript_html(t: Transcript) -> str:
    parts: list[str] = []
    for kind, text in t.body:
        if kind == "head":
            parts.append(f"<h3>{mdlite.inline(text)}</h3>")
        elif kind == "quote":
            parts.append(f'<blockquote class="src-quote">{mdlite.render(text)}</blockquote>')
        elif kind == "note":
            parts.append(f'<p class="src-note">{mdlite.inline(text)}</p>')
        else:
            parts.append(f'<pre class="verbatim">{mdlite.inline(text)}</pre>')
    return "\n".join(parts)


META_ORDER = ["Date", "From", "To", "CC", "Documents"]


def for_web(note: str) -> str:
    """Adapt a Markdown-file convention note to the rendered page.

    The transcripts state that underlined source words are written `_word_`.
    On these pages they are underlined, so the statement is restated. Nothing
    else in a transcript is altered.
    """
    return re.sub(
        r"(?:are |is )?rendered (?:as )?`_word_`",
        "appear underlined here",
        note,
    )


def build_evidence(base: str) -> str:
    links = link_map()
    rows: list[str] = []
    for item in TIMELINE:
        if isinstance(item, Gap):
            rows.append(
                f'  <li class="is-gap"><span class="when">{html.escape(item.when)}</span>'
                f'<span class="what">{html.escape(item.title)} — not reprinted</span></li>'
            )
        else:
            rows.append(
                f'  <li><span class="when">{html.escape(item.when)}</span>'
                f'<span class="what"><a href="#{item.slug}">{html.escape(item.title)}</a></span></li>'
            )
    timeline = "\n".join(rows)

    sections: list[str] = []
    number = 0
    for item in TIMELINE:
        if isinstance(item, Gap):
            sections.append(
                f"""<div class="gap">
  <b>Gap in the record — {html.escape(item.when)}: {html.escape(item.title)}.</b>
  {html.escape(item.note)}
</div>"""
            )
            continue

        number += 1
        t = item.transcript
        meta_items = []
        for key in META_ORDER:
            value = meta_get(t, key)
            if value:
                value_html = "<br>".join(mdlite.inline(line) for line in value.split("\n"))
                meta_items.append(f"<li><b>{key}:</b> {value_html}</li>")
        meta_items.append(
            f"<li><b>Printed in:</b> {ISSUE_LABEL[item.issue]}, journal p. {html.escape(item.journal_pages)}</li>"
        )
        meta_items.append(
            "<li><b>Scan:</b> PDF p. "
            + ", ".join(str(p) for p in item.pdf_pages)
            + f' of <a href="{BLOB}/sources/{PDFS[item.issue]}" rel="noopener">{PDFS[item.issue]}</a></li>'
        )
        meta = "\n    ".join(meta_items)

        conventions = meta_get(t, "Conventions")
        notes_before = [for_web(n) for n in t.header_notes]
        if conventions:
            notes_before.append("Conventions: " + for_web(conventions))
        pre_note = ""
        if notes_before:
            pre_note = (
                '<p class="doc-conventions">'
                + " ".join(mdlite.inline(n) for n in notes_before)
                + "</p>"
            )

        scans = "\n".join(
            figure(scan, f"{item.title} — journal p. {page_no - 3}, PDF p. {page_no}.")
            for scan, page_no in zip(item.scans, item.pdf_pages)
        )

        notes_html = ""
        if t.notes:
            notes_html = f"""<div class="doc-notes">
  <h3>Editorial notes</h3>
  {mdlite.render(t.notes, links=links, shift=1)}
</div>"""

        sections.append(
            f"""<section class="doc" id="{item.slug}">
  <div class="doc-head">
    <h2>{number}. {html.escape(item.title)}</h2>
    <p class="doc-summary">{html.escape(item.summary)}</p>
    <ul class="doc-meta">
    {meta}
    </ul>
    <div class="toolbar doc-tools">
      <a href="{BLOB}/transcripts/{item.file}" rel="noopener">Transcript source</a>
      <a href="{item.scans[0].full_res}" rel="noopener">Full-resolution scan</a>
    </div>
  </div>
  <div class="doc-body">
    <div class="doc-text">
      {pre_note}
      {transcript_html(t)}
    </div>
    <div class="scans">
{scans}
    </div>
  </div>
{notes_html}
</section>"""
        )

    head = title_block(
        "Primary documents",
        "The documents",
        "Nine documents from 1954 to 1997, transcribed verbatim and set beside the page scans they come from.",
        [
            ("The essay", "index.html"),
            ("The drawings", "schematics.html"),
            ("Provenance", "provenance.html"),
        ],
    )

    intro = """<div class="prose">
<p>The transcripts are verbatim. <code>[illegible]</code> marks unreadable text, <code>[word?]</code>
marks an uncertain reading, <code>[sic]</code> marks an error that is in the original, and square
brackets restore characters that the scan crops. Underlined words in a source document appear
<u class="src-underline">underlined</u> here. Click any page image to enlarge it.</p>
<p>Two letters in the exchange were never reprinted. They appear below as gaps, in date order.
The engineering sheets from the May 1997 issue are on <a href="schematics.html">the drawings page</a>.</p>
</div>"""

    body_html = f"""{head}
{intro}
<div class="prose">
<h2 id="timeline">Timeline</h2>
<ul class="timeline">
{timeline}
</ul>
</div>
{"".join(sections)}"""

    return page(
        title="The documents — the 1958 Russell coil test",
        description=(
            "Verbatim transcripts of the nine documents of the 1958 Alco Valve test of the Russell coil, "
            "each set beside the Fulcrum page scan it comes from."
        ),
        current="evidence.html",
        body=body_html,
        base=base,
    )


SHEET_PAIRS = [
    (
        "wiring_diagram.svg",
        "Test wiring",
        [(92, "Fig. 2, wiring schematic for the Russell solenoid (journal p. 89)"),
         (94, "Resistance sheet: 131 &#937; and 126 &#937; across 24 VDC (journal p. 91)")],
        "Six sections of 500 turns of #30 Bondeze wire. Two parallel groups of three sections in "
        "series. The measured set totals are 131 &#937; for the conventional pair and 126 &#937; for the "
        "Russell pair. The group composition is the natural reading of the source and is marked as an "
        "inference on the drawing.",
    ),
    (
        "coil_comparison.svg",
        "Coil cross-sections",
        [(96, "LO 8308-11, proposed test unit for the Russell solenoid coil (journal p. 93)"),
         (97, "LO 8308-12, the conventional comparison unit (journal p. 94)")],
        "Both units, drawn to the dimensions on the detail sheets. Bracketed values on the drawing are "
        "interpretive or derived: the .521 diameter feature, the core sleeve diameters, and the "
        "conventional wound diameter, which the source never dimensions.",
    ),
    (
        "pull_test_graph.svg",
        "Fig. 4, the comparative pull test",
        [(95, "Fig. 4 on graph paper, 24 VDC, November 1958 (journal p. 92)")],
        "Four plotted points per curve, at gaps of 0, .014, .028 and .040 in. Standard coils: 5.09, "
        "2.62, 1.72 and 1.32 lb. Step-diameter coils: 4.80, 2.38, 1.52 and 1.21 lb.",
    ),
    (
        "test_fixture.svg",
        "The pull-test fixture",
        [(94, "\"FIG,3\" on the resistance sheet: the as-tested arrangement (journal p. 91)")],
        "Two coil units in line on one axis, with the gap between the buttons, a fixed anchor and a "
        "spring scale. The August 1958 bolt-through-core sketches, which the October 2 revision "
        "superseded, are not redrawn.",
    ),
]


def build_schematics(base: str) -> str:
    links = link_map()
    index_rows = {}
    index_md = (ROOT / "transcripts" / "INDEX_v5n1.md").read_text(encoding="utf-8")
    for line in index_md.split("\n"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[1].isdigit():
            index_rows[int(cells[1])] = cells[2]

    pairs: list[str] = []
    for svg, name, sources, note in SHEET_PAIRS:
        shutil.copyfile(ROOT / "schematics" / svg, OUT / "schematics" / svg)
        svg_w, svg_h = svg_size(ROOT / "schematics" / svg, 900)
        source_figs = "\n".join(
            figure(scan_for("v5n1", p, hi_res=True), caption) for p, caption in sources
        )
        pairs.append(
            f"""<section class="prose-wide">
  <h2 id="{mdlite.slug(name)}">{name}</h2>
  <p>{note}</p>
  <div class="pair">
    <figure>
      <div class="svg-frame"><img src="schematics/{svg}" alt="Redrawn schematic: {html.escape(name)}." width="{svg_w}" height="{svg_h}" loading="lazy" decoding="async"></div>
      <figcaption>Redrawn: <code>schematics/{svg}</code>.
        <a href="{BLOB}/schematics/{svg}" rel="noopener">SVG source</a>.</figcaption>
    </figure>
{source_figs}
  </div>
</section>"""
        )

    gallery = "\n".join(
        figure(
            scan_for("v5n1", p, hi_res=True),
            f"Journal p. {p - 3} / PDF p. {p}: {index_rows.get(p, '')}",
        )
        for p in range(91, 110)
    )

    readme = (ROOT / "schematics" / "README_schematics.md").read_text(encoding="utf-8")
    readme_body = "\n".join(readme.split("\n")[1:])
    readme_html = link_code_refs(mdlite.render(readme_body, links=links, anchors=True))
    generated = 'id="fig-4-data-extraction-pull-test-graph-svg"'
    if generated not in readme_html:
        raise SystemExit("schematics: the Fig. 4 extraction heading changed; update the anchor")
    readme_html = readme_html.replace(generated, 'id="reading-the-graph"')

    drawings = (ROOT / "transcripts" / "v5n1_drawings_description.md").read_text(encoding="utf-8")
    drawings_body = "\n".join(drawings.split("\n")[1:])
    drawings_html = link_code_refs(mdlite.render(drawings_body, links=links, shift=1))

    head = title_block(
        "Engineering package",
        "The drawings",
        "Nineteen sheets of 1958 Alco Valve drawings, redrawn as clean vector schematics beside the "
        "sheets they come from. Every uncertain value is listed.",
        [
            ("The essay", "index.html"),
            ("The documents", "evidence.html"),
            ("Provenance", "provenance.html"),
        ],
    )

    body_html = f"""{head}
<div class="prose">
<p>The May 1997 issue of <em>Fulcrum</em> reprinted 19 pages of the Alco Valve engineering package:
freehand sketches, the pull-test graph, and the detail drawings for both test units. The sheets are
photocopies of pencil and ink originals, most signed "Tilney" and marked "2X SIZE".</p>
<p>The four redraws below carry nothing that the sheets do not state. Interpolated, derived, or
uncertain values are bracketed on the drawings and itemized in
<a href="#values-that-are-uncertain-interpolated-or-derived">the list of uncertain values</a>.
The build specification is complete enough to repeat the 1958 test.</p>
</div>
{"".join(pairs)}
<div class="prose-wide">
<h2 id="the-nineteen-sheets">The nineteen reprinted sheets</h2>
<p>All 19 pages at 300&nbsp;dpi, in journal order. Click a sheet to enlarge it.</p>
<div class="gallery">
{gallery}
</div>
</div>
<div class="prose">
<h2 id="how-the-redraws-were-made">How the redraws were made</h2>
{readme_html}
</div>
<div class="prose">
<h2 id="sheet-by-sheet">Sheet-by-sheet description</h2>
<p>The full description of all 19 sheets, dimension by dimension, from
<a href="{BLOB}/transcripts/v5n1_drawings_description.md" rel="noopener"><code>transcripts/v5n1_drawings_description.md</code></a>.</p>
{drawings_html}
</div>"""

    return page(
        title="The drawings — 1958 Alco Valve coil-test package",
        description=(
            "The 19 reprinted 1958 Alco Valve engineering sheets for the Russell coil test, with clean "
            "vector redraws, the Fig. 4 data extraction, and every uncertain value listed."
        ),
        current="schematics.html",
        body=body_html,
        base=base,
    )


def mirror_table() -> str:
    tsv = (ROOT / "verification" / "fulcrum_mirror_checksums.tsv").read_text(encoding="utf-8")
    rows = [line.split("\t") for line in tsv.strip().split("\n")[1:]]
    ocr_tsv = (ROOT / "verification" / "fulcrum_mirror_ocr_checksums.tsv").read_text(encoding="utf-8")
    ocr_names = {line.split("\t")[0] for line in ocr_tsv.strip().split("\n")[1:]}
    dl = IA_ITEM.replace("/details/", "/download/")
    out = ['<div class="table-wrap"><table>', "<thead><tr><th>Issue file</th><th class=\"num\">Bytes</th><th class=\"num\">Pages</th><th>SHA256</th><th>Source</th><th>Searchable copy</th></tr></thead><tbody>"]
    for name, size, pages, digest, source in rows:
        stem = name.removesuffix(".pdf")
        if f"{stem}_ocr.pdf" not in ocr_names:
            raise SystemExit(f"no OCR checksum entry for {name}")
        out.append(
            f"<tr><td><code>{name}</code></td><td class=\"num\">{int(size):,}</td>"
            f"<td class=\"num\">{pages}</td><td class=\"hash\">{digest}</td>"
            f"<td>{html.escape(source)}</td>"
            f"<td><a href=\"{dl}/{stem}_ocr.pdf\" rel=\"noopener\">PDF</a> &middot; "
            f"<a href=\"{dl}/{stem}_ocr.txt\" rel=\"noopener\">text</a></td></tr>"
        )
    out.append("</tbody></table></div>")
    return "".join(out)


def build_provenance(base: str) -> str:
    links = link_map()
    tsv = (ROOT / "verification" / "fulcrum_mirror_checksums.tsv").read_text(encoding="utf-8")
    by_name = {line.split("\t")[0]: line.split("\t") for line in tsv.strip().split("\n")[1:]}

    used_rows = []
    for issue in ("v4n3", "v5n1"):
        name, size, pages, digest, _source = by_name[PDFS[issue]]
        used_rows.append(
            f"""<tr>
  <td>{ISSUE_LABEL[issue]}<br><code>sources/{name}</code></td>
  <td class="num">{int(size):,}</td>
  <td class="num">{pages}</td>
  <td class="hash">{digest}</td>
  <td><a href="{BLOB}/sources/{name}" rel="noopener">In this repository</a></td>
</tr>"""
        )
    used_table = (
        '<div class="table-wrap"><table><thead><tr><th>Issue</th><th class="num">Bytes</th>'
        '<th class="num">Pages</th><th>SHA256</th><th>Copy</th></tr></thead><tbody>'
        + "".join(used_rows)
        + "</tbody></table></div>"
    )

    chain_md = f"""
## The chain

1. **Print, 1996 and 1997.** *Fulcrum*, the journal of the University of Science and Philosophy
   (USP), printed the 1958 file: the correspondence and the Alco report in Vol. 4 No. 3 (October
   1996), and the engineering sheets in Vol. 5 No. 1 (May 1997).
2. **Scans on philosophy.org.** USP later put the issues online as image-only PDF scans. The
   scans carry no OCR text layer, so no search engine could read the words in them. The Wayback
   Machine holds no capture of any *Fulcrum* PDF on philosophy.org before 2016, and none of V4N3
   before 2022.
3. **Wayback capture 20240922235101 (22 September 2024).** These captures are the only complete
   copies of the issues that a third-party archive holds. This project recovered both issues from
   them.
4. **The old URLs died.** The philosophy.org `/uploads/` URLs have returned 404 at least since
   7 November 2025. The last date on which this project observed them live is 5 August 2025.
5. **USP's rebuilt site.** It stays live and still serves complete PDFs, through per-issue
   "DOWNLOAD ATTACHMENT" links to a contractor's personal SharePoint account
   (`netorg242520-my.sharepoint.com`). On 9 September 2026 this project verified the SharePoint
   copy of V4N3 as byte-identical to the Wayback capture.
6. **This repository and the Internet Archive mirror.** Both issues are in `sources/` here. All
   21 issues (1992&ndash;1998) are mirrored as an
   [Internet Archive item]({IA_ITEM}) with checksums, in the original form and in a searchable
   copy.

### Cautions

- Two other capture sets are incomplete. A 2022 Common Crawl fetch of V4N3 is truncated at 1 MiB.
  Common Crawl refetched both issues on 5 August 2025, and those captures are capped near 5 MiB.
  Neither set is usable. Scribd re-uploads of V4N3 exist, and this project did not verify their
  completeness.
- The SharePoint host is a personal account, so it can vanish without notice.
- Vol. 5 No. 2 (November 1997) has no complete third-party capture at all. The only known complete
  copy came from USP's SharePoint links, and it is in the Internet Archive mirror above.
- The 1958 test survives on the movement's own testimony. No source independent of *Fulcrum*
  documents the test, the drawings LO 8308-11 and -12, or the Maguire funding link. Both principals
  are real, and the biographical details check out, but the episode itself has one source.
"""

    check_md = """
## How to check a copy

Every file here is verifiable against the checksums on this page.

```
shasum -a 256 sources/fulcrum_v4n3_october_1996.pdf
shasum -a 256 sources/fulcrum_v5n1_may_1997.pdf
```

The transcripts are checkable against the page scans. Each document on
[the documents page](evidence.html) shows the scan beside the text, and each scan links to its
full-resolution PNG. The page renders in `sources/v4n3_renders/` and `sources/v5n1_renders/` come
from the PDFs above.
"""

    concordance_md = """
## Page concordance and document map

In both issues the journal page number and the PDF page number differ by three: **journal page N
is PDF page N+3**. The two index files below carry the full document maps, the section boundaries,
and the negative findings from the page-by-page search.
"""

    index_v4n3 = drop_h1(ROOT / "transcripts" / "INDEX_v4n3.md")
    index_v5n1 = drop_h1(ROOT / "transcripts" / "INDEX_v5n1.md")
    index_v4n3_html = link_code_refs(mdlite.render(index_v4n3, links=links, shift=1))
    index_v5n1_html = link_code_refs(mdlite.render(index_v5n1, links=links, shift=1))
    verification = (ROOT / "verification" / "maguire-dube-verification.md").read_text(encoding="utf-8")

    issue_gallery = "\n".join(
        figure(SCANS[stem], caption)
        for stem, caption in [
            ("v4n3_p-01", "V4N3 cover, October 1996"),
            ("v4n3_p-03", "V4N3 contents, with \"From The Archives\" at p. 15"),
            ("v4n3_p-04", "V4N3 masthead page"),
        ]
    )

    head = title_block(
        "Chain of custody",
        "Provenance",
        "Where the scans came from, what they hash to, and what no independent source confirms.",
        [
            ("The essay", "index.html"),
            ("The documents", "evidence.html"),
            ("Internet Archive mirror", IA_ITEM),
        ],
    )

    body_html = f"""{head}
<div class="prose">
<p>This project holds no original paper. It holds scans, and the scans have a traceable path from
USP's print journal to this repository. The path has one weak link, and this page states it plainly:
almost every complete copy of these issues comes from USP itself.</p>
{mdlite.render(chain_md, links=links, anchors=True)}
<h2 id="the-two-issues">The two issues used here</h2>
<p>Both files are image-only scans with no text layer. The checksums are of the exact files in this
repository.</p>
{used_table}
{mdlite.render(check_md, links=links, anchors=True)}
<h2 id="the-mirror">The complete journal mirror</h2>
<p>All 21 issues of <em>Fulcrum</em> (April 1992 to December 1998) are mirrored, with checksums, as
one <a href="{IA_ITEM}" rel="noopener">Internet Archive item</a>. The full SHA256 list is in
<a href="{BLOB}/verification/fulcrum_mirror_checksums.tsv" rel="noopener"><code>verification/fulcrum_mirror_checksums.tsv</code></a>.</p>
<p>The mirror is searchable. Each issue has a second copy with the suffix <code>_ocr.pdf</code>:
the same pages, with a machine-read text layer added, and the plain text of that layer beside it
as <code>_ocr.txt</code>. The original files are unchanged, so every checksum below still
verifies. The text layer is for search. For quotation, the transcripts on this site stay the text
of record, because the machine reading has small errors on faint typescript. Checksums for the
searchable set are in
<a href="{BLOB}/verification/fulcrum_mirror_ocr_checksums.tsv" rel="noopener"><code>verification/fulcrum_mirror_ocr_checksums.tsv</code></a>.</p>
</div>
<div class="prose-wide">
{mirror_table()}
</div>
<div class="prose">
{mdlite.render(concordance_md, links=links, anchors=True)}
</div>
<div class="prose-wide">
<h3 id="concordance">Vol. 4 No. 3 (October 1996)</h3>
{index_v4n3_html}
<h3>Vol. 5 No. 1 (May 1997)</h3>
{index_v5n1_html}
</div>
<div class="prose">
<h2 id="the-issues-as-printed">The issues as printed</h2>
<div class="gallery">
{issue_gallery}
</div>
<h2 id="context-verification">Context verification</h2>
<p>The biographical checks below are independent of <em>Fulcrum</em>. They are reproduced from
<a href="{BLOB}/verification/maguire-dube-verification.md" rel="noopener"><code>verification/maguire-dube-verification.md</code></a>.</p>
<div class="callout">
{mdlite.render(verification, links=links)}
</div>
</div>"""

    return page(
        title="Provenance — the 1958 Russell coil test scans",
        description=(
            "The custody chain from USP's print journal to this repository: Wayback capture "
            "20240922235101, the dead philosophy.org URLs, the SharePoint copies, SHA256 checksums for "
            "all 21 Fulcrum issues, and the negative findings."
        ),
        current="provenance.html",
        body=body_html,
        base=base,
    )


def build_notfound(base: str) -> str:
    body_html = f"""<div class="title-block">
  <p class="kicker">404</p>
  <h1>Page not found</h1>
  <p class="subtitle">There is no page at this address.</p>
  <div class="toolbar"><a href="{base}/">The essay</a><a href="{base}/evidence.html">The documents</a><a href="{base}/schematics.html">The drawings</a><a href="{base}/provenance.html">Provenance</a></div>
</div>
<div class="prose">
<p>Possibly the page moved, or the link has an error. The four pages above hold all the content of
this site. If a link on this site sent you here, please tell
<a href="mailto:{CONTACT}">{CONTACT}</a>.</p>
</div>"""
    return page(
        title="Page not found — Walter Russell Archive",
        description="There is no page at this address.",
        current="404.html",
        body=body_html,
        base=base,
        noindex=True,
    )


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE, help="canonical site base URL")
    parser.add_argument("--skip-images", action="store_true", help="do not rebuild scan JPEGs")
    parser.add_argument("--force-images", action="store_true", help="rebuild every scan JPEG")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    for doc in DOCS:
        doc.load()

    OUT.mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "schematics").mkdir(exist_ok=True)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    for asset in ("site.css", "site.js", "og-card.png"):
        shutil.copyfile(ASSETS / asset, OUT / "assets" / asset)

    # A custom base means a custom domain: Pages needs the CNAME file in docs/.
    host = base.split("//", 1)[-1].split("/")[0]
    if host.endswith(".github.io"):
        (OUT / "CNAME").unlink(missing_ok=True)
    else:
        (OUT / "CNAME").write_text(host + "\n", encoding="utf-8")

    if args.skip_images:
        load_dims()
        print("scans: skipped")
    else:
        print(f"scans: {build_scans(force=args.force_images)} written, {len(SCANS)} total")

    write(OUT / "index.html", build_index(base))
    write(OUT / "evidence.html", build_evidence(base))
    write(OUT / "schematics.html", build_schematics(base))
    write(OUT / "provenance.html", build_provenance(base))
    write(OUT / "404.html", build_notfound(base))

    urls = "".join(
        f"  <url><loc>{base}/{'' if href == 'index.html' else href}</loc></url>\n"
        for href, _ in NAV
    )
    write(
        OUT / "sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n",
    )
    write(OUT / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")

    for name in ("index.html", "evidence.html", "schematics.html", "provenance.html", "404.html"):
        size = (OUT / name).stat().st_size
        print(f"{name}: {size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
