#!/usr/bin/env python3
"""Enhance the Platane/snk contribution snake SVG with space background,
growing snake effect, and make eaten contributions disappear to show space background."""

import re
import sys


def add_space_background(svg_content):
    """Add a starfield background to the SVG."""
    # Create a beautiful starfield background
    background = '''<!-- Space Background -->
<rect width="100%" height="100%" fill="#000000"/>
<!-- Nebula clouds -->
<g id="nebula" fill-opacity="0.08">
    <ellipse cx="200" cy="80" rx="120" ry="60" fill="#4B0082"/>
    <ellipse cx="600" cy="120" rx="100" ry="50" fill="#8A2BE2"/>
    <ellipse cx="400" cy="30" rx="80" ry="40" fill="#9400D3"/>
    <ellipse cx="750" cy="50" rx="90" ry="45" fill="#8B008B"/>
</g>
<!-- Starfield -->
<g id="stars">
    <!-- Background stars (dim) -->
    <circle cx="50" cy="30" r="0.5" fill="#FFFFFF" fill-opacity="0.3"/>
    <circle cx="120" cy="80" r="0.3" fill="#FFFFFF" fill-opacity="0.2"/>
    <circle cx="200" cy="50" r="0.4" fill="#FFFFFF" fill-opacity="0.4"/>
    <circle cx="300" cy="90" r="0.5" fill="#FFFFFF" fill-opacity="0.6"/>
    <circle cx="400" cy="20" r="0.3" fill="#FFFFFF" fill-opacity="0.2"/>
    <circle cx="450" cy="70" r="0.4" fill="#FFFFFF" fill-opacity="0.3"/>
    <circle cx="520" cy="40" r="0.5" fill="#FFFFFF" fill-opacity="0.5"/>
    <circle cx="600" cy="100" r="0.3" fill="#FFFFFF" fill-opacity="0.4"/>
    <circle cx="700" cy="60" r="0.4" fill="#FFFFFF" fill-opacity="0.3"/>
    <circle cx="750" cy="150" r="0.5" fill="#FFFFFF" fill-opacity="0.6"/>
    <circle cx="800" cy="30" r="0.3" fill="#FFFFFF" fill-opacity="0.2"/>
    <circle cx="850" cy="120" r="0.4" fill="#FFFFFF" fill-opacity="0.5"/>
    <!-- Twinkling stars -->
    <circle cx="100" cy="100" r="0.8" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.1;0.9;0.1" dur="5s" repeatCount="indefinite"/>
    </circle>
    <circle cx="500" cy="150" r="0.7" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.2;0.8;0.2" dur="7s" repeatCount="indefinite"/>
    </circle>
    <circle cx="250" cy="40" r="0.6" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.1;0.7;0.1" dur="4s" repeatCount="indefinite"/>
    </circle>
    <circle cx="650" cy="80" r="0.9" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.15;0.85;0.15" dur="6s" repeatCount="indefinite"/>
    </circle>
</g>'''

    # Insert after the <svg> opening tag but before any content
    svg_content = re.sub(
        r'(<svg[^>]*>)',
        r'\1\n    ' + background,
        svg_content,
        count=1
    )
    return svg_content


def modify_cell_styles(svg_content):
    """Modify the cell styles to make eaten cells stay visible (snake body) and uneaten cells transparent."""
    # Update the base cell style to be transparent initially (background shows through)
    svg_content = re.sub(
        r'\.c\{[^}]+\}',
        '.c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;stroke:var(--cb);animation:none 49900ms linear infinite;width:12px;height:12px;opacity:0}',
        svg_content
    )

    # Add styles for the snake body and head
    snake_styles = '''
/* Snake body - previously eaten cells remain visible (semi-transparent) */
.c.snake-body{fill:#00FF9D;opacity:0.4;}
.c.snake-body-glow{fill:#00FF9D;opacity:0.6;filter:url(#snakeBodyGlow);}

/* Snake head - current cell with bright glow */
.c.snake-head{fill:#00FF9D;opacity:1.0;filter:url(#snakeHeadGlow);}

/* Glow filters */
<filter id="snakeBodyGlow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="1" result="coloredBlur"/>
    <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
    </feMerge>
</filter>
<filter id="snakeHeadGlow" x="-80%" y="-80%" width="260%" height="260%">
    <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
    <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
    </feMerge>
</filter>'''

    # Insert styles before the closing </style> tag
    svg_content = re.sub(
        r'(</style>)',
        snake_styles + r'\n\1',
        svg_content,
        count=1
    )

    return svg_content


def enhance_keyframes_for_persistence(svg_content):
    """Enhance keyframes to make cells persist as snake body after being eaten."""
    # Find the style section
    style_match = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_match:
        return svg_content

    style = style_match.group(1)

    # Find all keyframe definitions and enhance them
    # Pattern: @keyframes c[ID]{[PCT]%{fill:var(c[COLOR])}[EXTRA]}
    keyframe_pattern = r'(@keyframes (c[0-9a-f]+))\{([\d.]+)%\{fill:var\((c\d+)\)([^}]*)\}([^}]*)\}'

    def enhance_keyframe(match):
        prefix = match.group(1)  # @keyframes c[ID]
        keyframe_id = match.group(2)  # [ID]
        peak_pct = float(match.group(3))  # peak percentage
        color_var = match.group(4)  # color variable (like c1, c2, etc.)
        before_extra = match.group(5)  # content between %{ and }
        after_extra = match.group(6)  # content after the closing } until next }

        # Enhanced keyframe:
        # At peak percentage: show as SNAKE HEAD (bright, glowing)
        # Just after peak: transition to SNAKE BODY (semi-transparent, persistent)
        # Remainder of cycle: stay as snake body

        # Calculate transition point (just after the peak)
        transition_pct = min(peak_pct + 0.1, 99.9)  # Very brief head period

        # Build the enhanced keyframe with proper brace escaping
        enhanced = '{}{{{:.2f}%{{fill:var({});opacity:1;filter:url(#snakeHeadGlow);class:snake-head}}}}{:.2f}%{{fill:var({});opacity:0.4;fill:#00FF9D;class:snake-body}}}}{}%{{fill:#00FF9D;opacity:0.4;class:snake-body}}}'.format(
            prefix, peak_pct, color_var, transition_pct, color_var, after_extra
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
    """Main function to enhance the snake SVG."""
    if output_path is None:
        output_path = input_path

    # Read the input SVG
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found")
        sys.exit(1)

    print(f"Read SVG from {input_path} ({len(svg_content)} chars)")

    # Apply enhancements
    svg_content = add_space_background(svg_content)
    svg_content = modify_cell_styles(svg_content)
    svg_content = enhance_keyframes_for_persistence(svg_content)

    # Write the enhanced SVG
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Enhanced SVG written to {output_path} ({len(svg_content)} chars)")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 enhance_snake_svg.py <input_svg> [output_svg]")
        print("  input_svg:  Path to the original Platane/snk output SVG")
        print("  output_svg: Path for enhanced SVG (optional, defaults to input_svg)")
        sys.exit(1)

    input_svg = sys.argv[1]
    output_svg = sys.argv[2] if len(sys.argv) > 2 else None
    main(input_svg, output_svg)