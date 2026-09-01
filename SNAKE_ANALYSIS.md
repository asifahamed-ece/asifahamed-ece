# Snake Growth Mechanism Analysis

## Status: FIXED (Pac-Man style)

The two reported bugs are resolved in `tools/snake_growth_enhancer.py`:

1. **The snake wasn't growing visibly** — the base `.c` cells were forced to
   `opacity:0`, so you never saw the contribution graph at rest; the whole body
   was a flat, uniform-luminance neon field with no "from small to long" signal.
2. **Green blocks weren't disappearing** — cells never showed their real
   contribution colors, and eaten cells just stayed lit as one uniform green
   mass with no "present -> gone" transition.

## Root Causes Found

### A. snk cell IDs are full alphanumeric, not just hex

The original parser used `c[0-9a-f]+`, but snk names the 75 contribution cells
across `c0..c9`, `ca..cz`, `c10..c1z`, ... (e.g. `cg`, `c1k`). Only the 35 cells
whose IDs used only hex letters were enhanced; the other **40 dots kept snk's
default animation** and never joined the growing snake or disappeared. Fixed by
matching `c[0-9a-zA-Z]+` everywhere (parse + split + id extraction).

### B. Old effect was a uniform trail, not eat-and-disappear

Cells were invisible at rest and lit as a single flat green trail. There was no
"dot in real color -> eaten -> gone" lifecycle.

## New Pac-Man-Style Lifecycle (per cell, one `@keyframes cXX`)

```
0% .. T:           fill:var(--cN); opacity:1   # real contribution color (rest)
T:                 fill:#00FF9D, +glow          # snake head arrives
T .. T+0.15%:      neon head (bright)
T+0.15% .. fade:   neon body opacity 0.7        # covers / consumes the dot
fade:              opacity:0                    # eaten -> space background
100%:              opacity:0
```

* The snake head arrives at loop time `T` (its snk activation percentage).
* Body length at time index `i` is `L(i) = initial_length + (i // growth_rate)`
  -> starts at 4, +1 every 2 dots eaten.
* A dot eaten at index `i` is consumed when the tail passes, i.e. when the head
  reaches index `i + L(i)` — a two-pass look-ahead over the time-sorted cells.
* Cells near the end of the loop are never consumed within the loop: they stay
  as body until 100% and reset to their real color at 0% on the next loop.

## Validation

A timing simulation over the regenerated SVG confirms:
* `t=0.5%` -> all 75 dots visible in real colors (rest state);
* body length grows across the loop (3 -> 17 segments);
* dots get eaten over time (gone 0 -> 44) while uneaten dots remain visible
  simultaneously (real + body + gone coexist at t=20%);
* `t=0` resets to all-real for the next loop.

## Modeled after pacman-contribution-graph

The design is inspired by `abozanona/pacman-contribution-graph`. That project's
SVG export drives every contribution dot with a discrete per-frame fill
timeline: the dot keeps its real color until the moving character eats it, then
`checkAndEatPoint` permanently flips it to the empty background color and it
stays gone for the rest of the animation. Our per-cell `@keyframes` mirrors the
same lifecycle:

| pacman repo mechanism | how we map it |
| --- | --- |
| `getCellAnimationData` -> `<animate attributeName="fill" calcMode="discrete">` | one `@keyframes cX` per dot, discrete fill/opacity states |
| dot real color until eating frame | `0%..T` shows `var(--cN)` at opacity 1 |
| `cell.color = intensityColors[0]` eaten, stays | tail passes -> `opacity:0` (space bg) through `100%` |
| sprite moved on top (pacman) | snake head + growing body |

A reusable check `tools/snake_validator.py` parses the final SVG, simulates the
keyframe timeline, and asserts these invariants (visible-at-rest, eaten-stays-
gone, snake-grows, mid-loop mix, next-loop reset). It is wired into the
workflow so every regeneration is verified.

## Files Related

- `tools/snake_growth_enhancer.py` — production generator (used by `.github/workflows/snake.yml`)
- `tools/add_snake_counter.py` — eaten-dots counter
- `tools/snake_validator.py` — reproducible Pac-Man-model check (wired into the workflow)
- `output/github-contribution-grid-snake-enhanced.svg` — regenerated artifact rendered in the README
