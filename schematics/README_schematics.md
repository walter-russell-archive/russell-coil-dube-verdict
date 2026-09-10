# Schematics — 1958 Alco Valve Coil-Test Engineering Package (clean vector redraws)

This folder contains hand-written SVG redraws of the freehand engineering package printed
in *Fulcrum* Vol. 5 No. 1 (May 1997), "From the Archives," journal pp. 88–106 (PDF pp.
91–109 of `sources/fulcrum_v5n1_may_1997.pdf`). The primary references are
`transcripts/v5n1_drawings_description.md` and the 300 dpi renders
`sources/v5n1_renders/v5n1_300dpi_p-091.png` … `p-109.png`.
We re-verified all values against the 300 dpi renders before we drew the files.
Nothing is invented. Uncertain or derived values are bracketed on the drawings
themselves and itemized below.

## File → source map

| File | Redraws | Source sheet(s) | Journal / PDF page |
|---|---|---|---|
| `wiring_diagram.svg` | Test wiring: 6 sections × 500 turns #30 Bondeze, 2 parallel groups of 3 in series; conventional and Russell sets side by side with measured totals 131 Ω / 126 Ω across 24 VDC | Fig. 2 "Wiring Schematic for Russell Solenoid"; unnumbered resistance sheet ("FIG,1"/"FIG.2") | j89 / PDF 92; j91 / PDF 94 |
| `coil_comparison.svg` | Cross-sections: Russell step-diameter unit (LO 8308-11) vs conventional unit (LO 8308-12); core geometry, winding envelopes, step profile, all stated dimensions | LO 8308-11, -12 (assembly concepts); details LO 8308-101, -102, -103, -104, -105, -106, -107, -108, -109; LO 8307-120, LO 8308-121, -122 | j93–j106 / PDF 96–109 |
| `pull_test_graph.svg` | Fig. 4 comparative pull test: pull (lb) vs gap (in), both curves, test-condition caption box | Fig. 4 graph-paper sheet | j92 / PDF 95 |
| `test_fixture.svg` | Pull-test fixture: two coil units axially in line, gap, fixed anchor, spring scale, PULL arrow | "FIG,3" on the resistance sheet | j91 / PDF 94 |

(We did not redraw the earlier Aug-1958 fixture sketches — Fig. 1 j88 and Fig. 3 j90, the
bolt-through-core version that Dube's Oct 2 revision superseded. `test_fixture.svg`
follows the as-tested arrangement of j91/j92.)

## Fig. 4 data extraction (`pull_test_graph.svg`)

Method: we rotated the 300 dpi render (p-095) upright and calibrated it against the
printed graph grid. We detected the major gridlines programmatically at 60.0 px per
.001 in (x) and 61.4 px per 0.25 lb (y), anchored on the labeled axis values
(0/.010/.020/.030/.040 in and 0–5 lb). We located the plotted marks by dark-pixel
centroid in ±16 px windows.

**Points read from the source (8 of 8 plotted points, read to ±.0005 in, ±0.05 lb):**

| Gap (in) | Standard coils (●) | Step diameter coils (×) |
|---|---|---|
| .000 | 5.09 lb | 4.80 lb |
| .014 | 2.62 lb | 2.38 lb |
| .028 | 1.72 lb | 1.52 lb |
| .040 | 1.32 lb | 1.21 lb |

The source plots exactly these four points per curve — at gaps 0, ≈.0141, ≈.0280 and
.040 in. The intermediate gaps measure 14.1 and 28.0 thousandths against the gridlines.
The sheet does not state why those values were chosen.

**Interpolated:** the curve shape between marks. We read two shape samples per curve
where each curve crosses the .010 and .020 gridlines (standard ≈3.0 / ≈2.2 lb, step
≈2.8 / ≈1.9 lb, ±0.1 lb — curve-line crossings, not plotted points). The drawn path is a
smooth interpolation through the points + samples. Everything between those x-positions
is interpolated, and this matches the source's hand-drawn dashed curves.

**Correction vs. the first-pass transcript description:** an earlier draft of
`v5n1_drawings_description.md` gave the .040-in endpoints as ≈2.1 lb (standard) and
≈1.4 lb (step). Those values were read from a rough scan with a stated ±0.2 lb
uncertainty. We re-read the 300 dpi render against the calibrated gridlines. This
re-read puts the .040 endpoints at **1.32 lb and 1.21 lb**. (The standard curve passes
2.1 lb near gap .020, which is the likely source of the misread.) The zero-gap values
5.09/4.80 vs the earlier ≈5.2/≈4.9 are within the stated tolerance. The corrected
ratios (standard/step = 1.06, 1.10, 1.13, 1.09 at the four points) are consistent with
the report's "5 to 10% more pulling power throughout the range" within reading
uncertainty.

**Cross-check:** the graph header reads "VOLTAGE = 24 VDC, WATTAGE = 4.4 WATTS". The
report wattages are 4.4 W (conventional) / 4.6 W (Russell). 24²/131 Ω = 4.40 W and
24²/126 Ω = 4.57 W. Thus the measured set resistances reproduce both reported wattages.
This corroborates the 131/126 Ω readings. It also corroborates that the readings are the
totals of each two-unit set as tested.

## Values that are uncertain, interpolated, or derived

Every such value is bracketed on the drawings. The complete list is:

1. **Fig. 4 endpoints/date** — curve values as above (±0.05 lb, ±.0005 in). The two
   zero-gap markers overlap the y-axis line and each other, so read them as ±0.1 lb.
   The sheet date "17 NOV '58" and the initials "JSY" are uncertain readings
   [transcript flag 3].
2. **131 Ω / 126 Ω assignment** — the j91 sheet does not name the coil types. The
   assignment (131 = round-drawn "FIG,1" = standard, 126 = step-drawn "FIG.2" = Russell)
   is by the drawn coil shapes [transcript flag 7]. The wattage cross-check above and the
   report's "Russell resistance 4% lower" corroborate it.
3. **Group composition** — we read "2 groups of 3 sections" as one hemisphere per group
   (SM+MED+LG in series). This is the natural reading, and it is marked [INFERENCE] on
   `wiring_diagram.svg`.
4. **LO 8308-101 axial mapping** — the freehand leaders overlap. The diameters
   (.446/.521/.708/.765±.001/.891) are secure. We mapped the axial figures
   (.188/.281/.281/.469/.843) as three winding lands of .281 each (sum .843, matching
   the two ".281" callouts and the ".843" chain) + a .188 spigot (.469 = .281 + .188
   exactly). The mapping is internally consistent but still interpretive
   [transcript flag 2].
5. **".521 DIA" feature** — we drew it on `coil_comparison.svg` as a dashed internal
   outline from the equatorial face, explicitly labeled [interpretive]. (In the 300 dpi
   render its solid outline begins where the tap-drill dashes end, which suggests an
   internal bore/relief.) It cannot be an external winding step (the three bobbin bores
   match .446/.708/.891).
6. **Core sleeve LO 8308-102 ID/OD** — the source gives ".688 DIA" (the leader suggests
   ID) and a ".767±.001" press-fit bore. The two cannot both be inside diameters, and
   the sheet does not resolve which is OD [transcript flag re: -102]. We drew the sleeve
   schematically (bore .767 over the .765 spigots, OD undimensioned). Only ".312 LG"
   appears as text.
7. **Conventional wound OD** — LO 8308-122 carries no wound-diameter dimension ("CHECK
   WITH TILNEY FOR NO OF TURNS"). We drew the winding outer edge **dashed** and labeled
   it "wound OD not dimensioned in source." Per Dube's letter, the wire quantity equals
   the Russell set.
8. **Conventional winding length ≈1.500** — derived: 1.625 sleeve − 2 × .062 end
   protrusion. The source does not dimension it.
9. **LO 8307-120 prefix** — "8307" as written. It is probably a slip for 8308
   [transcript flag 1].
10. **Turns per section ≈500** — nominal per Dube's Aug 25 letter and the Fig. 2 note.
    The assembly sheets say "record no. of turns", and the final counts are not stated
    anywhere.
11. **Sleeve-vs-spigot axial fit** — the .312-long sleeve over two .188 spigots implies
    that the spigot faces butt at the equator, with ~.032 axial clearance to each .891
    shoulder. The source does not make this explicit (we drew it accordingly and show
    no dimension).

Values **not** listed above (all diameters, land heights, lengths, thread callouts,
materials, turn/group counts, resistances, voltages) come verbatim from the sheets.

## Rendering

All four files are plain SVG 1.1, black-on-white, with `viewBox` set and no external
resources. We validated them as well-formed XML and rendered them in Chromium at
800–1000 px wide for legibility.
