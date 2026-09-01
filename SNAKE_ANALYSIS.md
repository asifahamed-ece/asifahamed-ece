# Rigid-Body Contribution Snake Analysis

## Status: RIGID GROWING BODY (no trails)

`tools/snake_growth_enhancer.py` turns a Platane/snk contribution grid into a
Pac-Man-style animation. The head slithers through the contribution dots and a
solid purple body follows it exactly while growing one block per dot eaten.

## Design Overview

### One closed path = one rigid body

snk moves the head sprite (`.s`) through waypoints with CSS `translate`
keyframes. We build **ONE closed `<path>` through those waypoints** (offset to
the cell centers, closing back to the start so the loop wraps seamlessly) and
render it as a purple stroke onto the grid, under the head sprite.

A single CSS `stroke-dasharray` / `stroke-dashoffset` animation limits the
visible part of the stroke to exactly the `length` cells of route behind the
moving head:

```
visible window = [head_arc - body_length, head_arc]
stroke-dashoffset = body_length - head_arc
stroke-dasharray  = body_length, route_total - body_length
```

Because dashoffset keyframes are emitted at every head waypoint plus every
growth instant, the window tracks the head exactly — pauses, corner turns, and
the glide back to the start included. This is geometrically **a rigid body**:
every point of it is exactly k cells behind the head along the route at all
times. No trails, no per-segment hacks, no neon.

### Growth

Each contribution dot's activation percentage is when the head crosses that
cell. At every dot-eat instant the visible dash length grows by exactly one cell
(16px):

```
body_length(t) = (INITIAL_BLOCKS - 1 + dots_eaten(t)) * CELL
```

The snake starts at 4 blocks (head + 3 body) and ends at `4 + total_dots`
blocks (79 with the current 75-dot grid).

### Dots vanish instantly

Each dot keeps its real contribution color at rest and is flipped to the
empty-grid color (`var(--ce)`) the instant the head touches it:

```
0% .. T:      fill:var(--cN); opacity:1   # real contribution color (rest)
T .. T+EPS:   fill:var(--ce); opacity:0   # eaten -> space background
100%:         fill:var(--ce); opacity:0
```

Once gone, a dot never re-appears within the loop. The base `.c` rule is
`opacity:0`, so only the animated contribution dots are ever visible.

### Slower loop + counter

All loop durations (`.c` cells, `.s` head, `.snakeBody`, `.snkcnt`) are scaled
by a speed factor (default 1.5x -> ~74.85s with the current 49900ms base). The
eaten-dots counter (`tools/add_snake_counter.py`) derives its duration from the
SVG's head-sprite animation instead of a hardcoded value, so it stays in sync
with the slowed loop.

## Validation

`tools/snake_validator.py` simulates the CSS keyframes over the loop and asserts:

- every dot shows its real color at rest, vanishes right after the head
  touches it, and never re-appears;
- a rigid `.snakeBody` path with an `sb0` dash animation exists;
- the body starts at 4 blocks and grows exactly +1 block (16px) per dot;
- the body's visible window equals `[head_arc - length, head_arc]` at every
  sampled loop time (rigid follow, in sync with the head sprite);
- all loop durations are identical and slower than the stock 49900ms;
- the empty grid cells are hidden (base `.c` `opacity:0`);
- the counter duration matches the loop.

It is wired into `.github/workflows/snake.yml` so every daily regeneration is
verified. For the current grid the simulation shows the body going
**4 -> 7 -> 32 -> 49 -> 60 -> 73 -> 79 blocks** while the head glides across
the whole board and the tail follows rigidly behind.

## Files Related

- `tools/snake_growth_enhancer.py` — production generator (used by `.github/workflows/snake.yml`)
- `tools/add_snake_counter.py` — eaten-dots counter (duration derived from the SVG)
- `tools/snake_validator.py` — reproducible rigid-body check (wired into the workflow)
- `output/github-contribution-grid-snake-enhanced.svg` — regenerated artifact rendered in the README
