# The Dube Verdict — the 1958 Russell Coil Test

This repository publishes the only known controlled outside test of a Walter Russell
device, with complete primary sources. In 1958, John E. Dube, president of the Alco
Valve Company of St. Louis, tested Russell's "step diameter" coil design against
conventional solenoid coils. Russell predicted, on the record, a 40–60% advantage
for his design. The test measured a 5–10% deficit at every gap. Within three days
of the report, Russell conceded the result in writing "as a fact of law."

The movement's own journal, *Fulcrum*, printed the full correspondence in 1996–97 to
"set the record straight." The journal published it as image-only scans with no text
layer. No search engine could read the scans, and the episode stayed invisible for
almost thirty years. This repository transcribes every document verbatim and puts the
text where readers and search engines can reach it.

## Read it

**Web:** https://walterrussellarchive.org — the essay typeset, every document beside
its page scan, the drawings, and the provenance chain.

**In this repository:** [essay/the-dube-verdict.md](essay/the-dube-verdict.md) — the full
annotated account: the test, the prediction, the concession, and the burial.

## The evidence chain

Every claim in the essay is checkable inside this repository:

    essay → transcripts/ (verbatim text) → sources/*_renders/ (page images)
          → sources/*.pdf (complete issue scans) → Wayback/SharePoint provenance

- `transcripts/` — verbatim transcriptions of all nine documents: the Aug–Nov 1958
  Dube–Russell correspondence, the Alco evaluation report, the 1954–55 Russell–Lee
  (Tesla) exchange, and the 1996–97 *Fulcrum* editor's notes. Two INDEX files map
  every journal page to its PDF page.
- `transcripts/v5n1_drawings_description.md` — all 19 reprinted engineering pages
  described: Figs. 1–4 and drawings LO 8308-11/-12 with detail parts, including the
  full winding specification.
- `schematics/` — clean vector redraws: the test wiring, the coil cross-sections,
  the pull-test graph, and the test fixture. The README lists every interpolated or
  uncertain value.
- `sources/` — the two complete *Fulcrum* issue scans (V4N3 Oct 1996, V5N1 May 1997)
  and page renders at 100–300 dpi.
- `verification/` — independent biographical verification of John E. Dube and
  Russell Maguire, with negative findings stated. `fulcrum_mirror_checksums.tsv`
  carries the SHA256 of all 21 mirrored issues.
- `docs/` — the generated website. It is build output: edit the Markdown above, then
  run `python3 tools/build_site.py` (Pillow is the only dependency, and only for the
  page images).

## Replicate the test

The test is replicable from this repository. The winding specification: six sections
of 500 turns of #30 Bondeze wire, two parallel groups of three in series. The as-built
resistances: 126 Ω (Russell pair) against 131 Ω (conventional pair). The procedure:
24 VDC, breakaway pull against gap at 0/.014/.028/.040 in. All dimensions are in the
drawings description and the schematics. Four coils and a spring scale settle it.

## Provenance

The scans come from Internet Archive Wayback captures of philosophy.org (capture
20240922235101). The original philosophy.org URLs have returned 404 at least since
7 November 2025 (last observed live 5 August 2025). USP's rebuilt site still serves
the same files through personal-account SharePoint links. The SharePoint copy of
V4N3 verifies byte-identical (SHA256 `4ff27b21…`) to the Wayback capture. Full
details are in the essay's Sources Appendix. A complete mirror of all 21 *Fulcrum*
issues (1992–1998), with SHA256 checksums, is on the Internet Archive:
https://archive.org/details/fulcrum-science-journal-usp-1992-1998

## What this repository is not

This is not a debunking site, and it is not an advocacy site. The documents show a
fair test, an honest concession, and a human retreat. Both facts stay in view.
Russell, faced with data in November 1958, behaved better than his modern legend
does. The record deserves to be readable.

## License

Original work in this repository (essay, transcription formatting, editorial notes,
schematics) is licensed CC BY 4.0. The reproduced historical documents and scans
keep their own copyright status — see [LICENSE](LICENSE) for the provenance notice.
