#!/usr/bin/env python3
"""Enhance contribution snake to grow progressively as it eats contributions."""

import re
import sys


def add_space_background(svg_content):
    """Add a space-themed background to the SVG."""
    background = '''<!-- Space Background -->
<rect width="100%" height="100%" fill="#000000"/>
<!-- Nebula -->
<g id="nebula" fill-opacity="0.05">
    <circle cx="200" cy="80" r="80" fill="#4B0082"/>
    <circle cx="600" cy="120" r="70" fill="#8A2BE2"/>
    <circle cx="400" cy="30" r="60" fill="#9400D3"/>
    <circle cx="750" cy="50" r="50" fill="#8B008B"/>
</g>
<!-- Stars -->
<g id="stars" fill-opacity="0.6">
    <!-- Background stars -->
    <circle cx="100" cy="50" r="0.5" fill="#FFFFFF"/>
    <circle cx="200" cy="100" r="0.3" fill="#FFFFFF"/>
    <circle cx="300" cy="30" r="0.4" fill="#FFFFFF"/>
    <circle cx="400" cy="150" r="0.2" fill="#FFFFFF"/>
    <circle cx="500" cy="80" r="0.3" fill="#FFFFFF"/>
    <circle cx="600" cy="40" r="0.5" fill="#FFFFFF"/>
    <circle cx="700" cy="120" r="0.2" fill="#FFFFFF"/>
    <circle cx="800" cy="60" r="0.4" fill="#FFFFFF"/>
    <!-- Twinkling stars -->
    <circle cx="150" cy="80" r="0.8" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.2;1;0.2" dur="3s" repeatCount="indefinite"/>
    </circle>
    <circle cx="450" cy="100" r="0.6" fill="#FFFFFF">
        <animate attributeName="fill-opacity" values="0.3;0.9;0.3" dur="4s" repeatCount="indefinite"/>
    </circle>
</g>'''
    return re.sub(r'(<svg[^>]*>)', r'\1\n    ' + background, svg_content, count=1)


def enhance_snake_styles(svg_content):
    """Enhance CSS styles for snake appearance."""
    # Make base cells transparent
    svg_content = re.sub(
        r'\.c\{[^}]+\}',
        '.c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;stroke:var(--cb);animation:none 49900ms linear infinite;width:12px;height:12px;opacity:0}',
        svg_content
    )

    # Add snake styles with glow effects
    snake_styles = '''
/* Glow filter for snake head */
<filter id="snakeGlow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="2" result="blur"/>
    <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
    </feMerge>
</filter>'''

    return re.sub(r'(</style>)', snake_styles + r'\n\1', svg_content, count=1)


def parse_snake_path(svg_content):
    """Parse the snake animation path to find all cells and their activation times."""
    # Find the style section
    style_match = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_match:
        return []

    style = style_match.group(1)

    # Extract all keyframe definitions with their activation percentages
    # Matches: @keyframes c[ID]{[PCT]%{...}
    keyframe_pattern = r'@keyframes (c[0-9a-f]+)\{([\d.]+)%'
    matches = re.findall(keyframe_pattern, style)

    # Sort by activation time
    cells = sorted(matches, key=lambda x: float(x[1]))
    return cells


def create_growing_snake_keyframes(svg_content, initial_length=4, growth_rate=2):
    """
    Create keyframes where snake grows by 1 segment for every growth_rate contributions.

    Args:
        initial_length: Starting snake length (default 4: head + 3 body)
        growth_rate: Number of contributions needed to grow by 1 segment (default 2)
    """
    # Parse the snake path
    cells = parse_snake_path(svg_content)
    if not cells:
        return svg_content

    # Find the style section
    style_match = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_match:
        return svg_content

    style = style_match.group(1)

    # Calculate snake length at each cell
    snake_lengths = {}
    for i, (cell_id, activation_pct) in enumerate(cells):
        # Snake grows by 1 for every growth_rate contributions
        current_length = initial_length + (i // growth_rate)
        snake_lengths[cell_id] = (i, float(activation_pct), current_length)

    # Generate new keyframes using string replacement
    def create_keyframe_for_cell(cell_id, index, activation_pct, snake_length):
        """Create a keyframe that shows head, then body, then fades when tail passes."""
        # Head appears at activation time
        head_end = min(activation_pct + 0.1, 99.9)

        # Calculate when this cell should fade (when it's beyond snake_length cells back)
        fade_index = index + snake_length

        if fade_index < len(cells):
            # Cell fades when tail reaches it
            fade_cell_id, fade_pct = cells[fade_index]
            fade_pct = float(fade_pct)
            fade_start = min(fade_pct - 0.05, 99.95)
            fade_end = min(fade_pct + 0.05, 99.95)

            keyframe = (
                f'{activation_pct:.2f}%{{fill:#00FF9D;opacity:1.0;filter:url(#snakeGlow)}}' +
                f'{head_end:.2f}%{{fill:#00FF9D;opacity:0.3}}' +
                f'{fade_start:.2f}%{{fill:#00FF9D;opacity:0.3}}' +
                f'{fade_end:.2f}%{{fill:#00FF9D;opacity:0}}' +
                f'100%{{fill:#00FF9D;opacity:0}}'
            )
        else:
            # Cell stays visible until end (part of final snake)
            keyframe = (
                f'{activation_pct:.2f}%{{fill:#00FF9D;opacity:1.0;filter:url(#snakeGlow)}}' +
                f'{head_end:.2f}%{{fill:#00FF9D;opacity:0.3}}' +
                f'100%{{fill:#00FF9D;opacity:0.3}}'
            )

        return f'@keyframes {cell_id}{{{keyframe}}}'

    # Replace keyframes using a more robust pattern that handles the actual structure
    # Pattern matches: @keyframes cXX{...}...} where the content can have nested {}
    enhanced_style = style

    # Split by @keyframes and rebuild
    keyframe_blocks = re.split(r'(@keyframes c[0-9a-f]+\{)', enhanced_style)
    result_parts = [keyframe_blocks[0]]  # Keep everything before first keyframe

    i = 1
    while i < len(keyframe_blocks):
        if i + 1 < len(keyframe_blocks):
            keyframe_start = keyframe_blocks[i]  # "@keyframes cXX{"
            # Extract cell_id from keyframe_start
            cell_id_match = re.search(r'c[0-9a-f]+', keyframe_start)
            if cell_id_match:
                cell_id = cell_id_match.group(0)

                # Find the end of this keyframe block
                remaining = keyframe_blocks[i + 1]
                # Find the matching closing brace
                brace_count = 1
                pos = 0
                while pos < len(remaining) and brace_count > 0:
                    if remaining[pos] == '{':
                        brace_count += 1
                    elif remaining[pos] == '}':
                        brace_count -= 1
                    pos += 1

                # Get the content after the keyframe
                after_keyframe = remaining[pos:]

                # Check if this cell_id needs replacement
                if cell_id in snake_lengths:
                    index, activation_pct, snake_length = snake_lengths[cell_id]
                    new_keyframe = create_keyframe_for_cell(cell_id, index, activation_pct, snake_length)
                    result_parts.append(new_keyframe)
                else:
                    # Keep original
                    result_parts.append(keyframe_start + remaining[:pos])

                result_parts.append(after_keyframe)
                i += 2
            else:
                result_parts.append(keyframe_start)
                i += 1
        else:
            result_parts.append(keyframe_blocks[i])
            i += 1

    enhanced_style = ''.join(result_parts)

    # Replace the style section
    svg_content = re.sub(
        r'<style>.*?</style>',
        f'<style>{enhanced_style}</style>',
        svg_content,
        flags=re.DOTALL,
        count=1
    )

    return svg_content


def main(input_path, output_path=None, growth_rate=2):
    """Main enhancement function."""
    if output_path is None:
        output_path = input_path

    # Read input SVG
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {input_path} ({len(svg_content)} chars)...")

    # Apply enhancements
    svg_content = add_space_background(svg_content)
    svg_content = enhance_snake_styles(svg_content)
    svg_content = create_growing_snake_keyframes(svg_content, initial_length=4, growth_rate=growth_rate)

    # Write output SVG
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Enhanced SVG saved to {output_path} ({len(svg_content)} chars)")
        print("Enhancements applied:")
        print("  ✓ Space nebula and starfield background")
        print(f"  ✓ Snake grows by 1 segment every {growth_rate} contributions")
        print("  ✓ Snake head glows brightly when active")
        print("  ✓ Old segments fade out as snake grows")
        print("  ✓ Uneaten cells remain transparent (showing space background)")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 snake_growth_enhancer.py <input_svg> [output_svg] [growth_rate]")
        print("  input_svg:   Path to Platane/snk output SVG")
        print("  output_svg:  Path for enhanced SVG (optional)")
        print("  growth_rate: Contributions per growth segment (default: 2)")
        sys.exit(1)

    growth_rate = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, growth_rate)
