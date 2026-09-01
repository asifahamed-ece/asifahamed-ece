#!/usr/bin/env python3
"""Final enhancement script for contribution snake SVG."""

import re
import sys


def add_space_background(svg_content):
    """Add space nebula and starfield background."""
    background = '''<!-- Deep Space Background -->
<rect width="100%" height="100%" fill="#000000"/>
<!-- Nebula - purple/pink clouds -->
<g id="nebula" fill-opacity="0.1">
    <radialGradient id="nebula1" cx="30%" cy="20%" r="50%">
        <stop offset="0%" stop-color="#4B0082" stop-opacity="0.8"/>
        <stop offset="100%" stop-color="#4B0082" stop-opacity="0"/>
    </radialGradient>
    <ellipse cx="200" cy="80" rx="150" ry="100" fill="url(#nebula1)"/>

    <radialGradient id="nebula2" cx="70%" cy="60%" r="60%">
        <stop offset="0%" stop-color="#8A2BE2" stop-opacity="0.7"/>
        <stop offset="100%" stop-color="#8A2BE2" stop-opacity="0"/>
    </radialGradient>
    <ellipse cx="600" cy="120" rx="120" ry="80" fill="url(#nebula2)"/>
</g>
<!-- Starfield -->
<g id="stars">
    <!-- Distant stars -->
    <circle cx="100" cy="50" r="0.2" fill="#FFFFFF" fill-opacity="0.3"/>
    <circle cx="200" cy="100" r="0.3" fill="#FFFFFF" fill-opacity="0.4"/>
    <circle cx="300" cy="30" r="0.2" fill="#FFFFFF" fill-opacity="0.3"/>
    <circle cx="400" cy="150" r="0.2" fill="#FFFFFF" fill-opacity="0.5"/>
    <circle cx="500" cy="80" r="0.3" fill="#FFFFFF" fill-opacity="0.4"/>
    <circle cx="600" cy="40" r="0.2" fill="#FFFFFF" fill-opacity="0.3"/>
    <circle cx="700" cy="120" r="0.3" fill="#FFFFFF" fill-opacity="0.4"/>
    <circle cx="800" cy="60" r="0.2" fill="#FFFFFF" fill-opacity="0.2"/>
    <!-- Twinkling stars -->
    <circle cx="150" cy="80" r="0.8" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.1;1;0.1" dur="3s" repeatCount="indefinite"/>
    </circle>
    <circle cx="450" cy="100" r="0.6" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.2;0.9;0.2" dur="4s" repeatCount="indefinite"/>
    </circle>
    <circle cx="650" cy="50" r="0.9" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.15;0.85;0.15" dur="5s" repeatCount="indefinite"/>
    </circle>
</g>'''

    # Insert after opening svg tag
    svg_content = re.sub(
        r'(<svg[^>]*>)',
        r'\1\n    ' + background,
        svg_content,
        count=1
    )
    return svg_content


def enhance_snake_appearance(svg_content):
    """Enhance snake appearance with glow and persistence."""
    # Make base cells transparent initially
    svg_content = re.sub(
        r'\.c\{[^}]+\}',
        '.c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;stroke:var(--cb);animation:none 49900ms linear infinite;width:12px;height:12px;opacity:0}',
        svg_content
    )

    # Add snake styles with glow
    snake_styles = '''
/* Snake body - eaten cells remain as semi-transparent trail */
.c.snake-body{fill:#00FF9D;opacity:0.35;}

/* Snake head - currently active cell with intense glow */
.c.snake-head{fill:#00FF9D;opacity:1.0;filter:url(#snakeHeadGlow);}

/* Glow effects */
<filter id="snakeHeadGlow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="3" result="blur"/>
    <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
    </feMerge>
</filter>
<filter id="snakeBodyGlow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="1.5" result="blur"/>
    <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
    </feMerge>
</filter>'''

    # Insert before closing style tag
    svg_content = re.sub(
        r'(</style>)',
        snake_styles + r'\n\1',
        svg_content,
        count=1
    )

    return svg_content


def make_snake_grow(svg_content):
    """Modify keyframes to make snake grow with persistent trail."""
    # Extract and enhance the style section
    style_match = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_match:
        return svg_content

    style = style_match.group(1)

    # Find all keyframe definitions
    # Pattern captures: @keyframes c[ID] { [percentage]% { ... } [rest] }
    keyframe_pattern = r'(@keyframes (c[0-9a-f]+))\{([\d.]+)%\{[^}]+\}([^}]*)\}'

    def enhance_keyframe(match):
        full_prefix = match.group(1)  # @keyframes c[ID]
        keyframe_id = match.group(2)  # [ID]
        peak_pct = float(match.group(3))  # the percentage where color changes
        after_content = match.group(4)  # rest of the keyframe definition

        # The original keyframe has format like:
        # 76.74%{fill:var(--c3)}76.76%,100%{fill:var(--ce)}
        # We want to transform it to:
        # At peak_pct: SNAKE HEAD (bright, glowing)
        # Just after peak: SNAKE BODY (semi-transparent, persistent)
        # Rest of cycle: remain as snake body

        # Calculate a very brief head duration (0.05% of cycle)
        head_end = min(peak_pct + 0.05, 99.95)

        # Build enhanced keyframe
        # We need to preserve whatever was in after_content (like the 100% part)
        enhanced = (
            full_prefix + "{" +
            "{:.2f}%{{fill:var(--c3);opacity:1;filter:url(#snakeHeadGlow);class:snake-head}}".format(peak_pct) +
            "{:.2f}%{{fill:var(--c3);opacity:0.35;fill:#00FF9D;class:snake-body}}".format(head_end) +
            "100%{{fill:var(--c3);opacity:0.35;fill:#00FF9D;class:snake-body}}}" +
            after_content
        )

        return enhanced

    # Apply enhancement to all keyframes
    enhanced_style = re.sub(keyframe_pattern, enhance_keyframe, style)

    # Replace the style section
    svg_content = re.sub(
        r'<style>.*?</style>',
        f'<style>{enhanced_style}</style>',
        svg_content,
        flags=re.DOTALL,
        count=1
    )

    return svg_content


def main(input_path, output_path=None):
    """Main enhancement function."""
    if output_path is None:
        output_path = input_path

    # Read input
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {input_path} ({len(svg_content)} chars)...")

    # Apply enhancements in order
    svg_content = add_space_background(svg_content)
    svg_content = enhance_snake_appearance(svg_content)
    svg_content = make_snake_grow(svg_content)

    # Write output
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Enhanced SVG saved to {output_path} ({len(svg_content)} chars)")
        print("Enhancements applied:")
        print("  ✓ Deep space nebula and starfield background")
        print("  ✓ Snake grows with persistent trail (body remains visible)")
        print("  ✓ Snake head glows brightly when active")
        print("  ✓ Eaten contributions show as snake body (semi-transparent)")
        print("  ✓ Uneaten cells remain transparent (show space background)")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 final_snake_enhance.py <input_svg> [output_svg]")
        print("  input_svg:  Path to Platane/snk output SVG")
        print("  output_svg: Path for enhanced SVG (optional)")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)