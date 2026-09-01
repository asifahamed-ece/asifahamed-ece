#!/usr/bin/env python3
import re

# Read the backup file
with open('/home/shadow/Projects/Asif/asifahamed-dev/output/github-contribution-grid-snake.svg.backup', 'r') as f:
    svg = f.read()

print(f"File loaded: {len(svg)} chars")

# Test the keyframe pattern matching
style_match = re.search(r'<style>(.*?)</style>', svg, re.DOTALL)
if style_match:
    style = style_match.group(1)
    print(f"Style section: {len(style)} chars")

    # Test our pattern
    pattern = r'(@keyframes (c[0-9a-f]+))\{([\d.]+)%\{[^}]+\}([^}]*)\}'
    matches = re.findall(pattern, style)
    print(f"Found {len(matches)} matches")

    if matches:
        m = matches[0]
        print(f"First match groups: {m}")
        print(f"  Full prefix: {m[0]}")
        print(f"  Keyframe ID: {m[1]}")
        print(f"  Peak PCT: {m[2]}")
        print(f"  After content: '{m[3]}'")

        # Test the enhancement
        peak_pct = float(m[2])
        head_end = min(peak_pct + 0.05, 99.95)
        enhanced = f'''{m[0]}{{{peak_pct:.2f}%{{fill:var(--c3);opacity:1;filter:url(#snakeHeadGlow);class:snake-head}}}
{head_end:.2f}%{{fill:var(--c3);opacity:0.35;fill:#00FF9D;class:snake-body}}
100%{{fill:var(--c3);opacity:0.35;fill:#00FF9D;class:snake-body}}}{m[3]}'''

        print("\nEnhanced version:")
        print(enhanced)
else:
    print("No style section found")