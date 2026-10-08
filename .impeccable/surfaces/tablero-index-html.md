---
version: 1
slug: "tablero-index-html"
primary_target: "tablero/index.html"
related_targets: []
---

# Tablero semáforos SAST — surface brief

Scope: `tablero/` (single page, hash routes). Visitor mode: Operate, with a presentation ritual.
Audience and job: the STTV head of office and technical team understand the signal cycles of the 5 SAST intersections. They see it projected in a meeting, on a desk and on a phone.
Proof/content: controller plans (`tablero/data/semaforos.json`), 15 SAST cameras and their baseline (`sast.json`), OSM geometry (`geometria.json`).
Constraints: decisions 27–30 in CLAUDE.md; vehicles only on validated intersections; "illustrative phase" label always visible.

## Direction contract
THESIS: The STTV control room on screen. The map is the wall's large screen, and each intersection is a monitor with its cycle running live. It refuses the side list plus floating card.
OWN-WORLD: Room black, graphite monitor bezels, and an operator label (controller · crossing) in the bottom corner of each screen. Real red, amber and green LED glow, 7-segment counters, Barlow Condensed for labels and Public Sans for text. The only colors are signal indications plus SAST orange.
STORY: He sees all five pulsing at once, sends one to the main screen and understands within one turn of the clock who goes, for how long, and why the cycle shortens at night.
FIRST VIEWPORT: A 3×2 wall. The large screen spans 2×2 with the dark map, live signals and cameras. A column of 5 monitors each shows its ring, plan and countdown. The operator bar carries the Bogotá time, the day type and «Presentar». Primary action: a monitor or signal goes to the main screen.
FORM: Control-room video wall (pick chosen by Santiago); seed 5b8fbd6d. Signature: the monitor flies to the main screen (Flip) and the intersection draws itself.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
