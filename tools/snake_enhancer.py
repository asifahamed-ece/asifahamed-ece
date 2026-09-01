#!/usr/bin/env python3
"""Enhance contribution snake SVG with space background and growing snake effect."""

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

    # Insert after the opening svg tag
    return re.sub(r'(<svg[^>]*>)', r'\1\n    ' + background, svg_content, count=1)


def enhance_snake_styles(svg_content):
    """Enhance CSS styles for snake appearance."""
    # Make base cells transparent (they'll show via animation)
    svg_content = re.sub(
        r'\.c\{[^}]+\}',
        '.c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;stroke:var(--cb);animation:none 49900ms linear infinite;width:12px;height:12px;opacity:0}',
        svg_content
    )

    # Add snake body and head styles with glow effects
    snake_styles = '''
/* Snake body - eaten cells remain visible as trail */
.c.snake-body{fill:#00FF9D;opacity:0.3;}

/* Snake head - currently active cell */
.c.snake-head{fill:#00FF9D;opacity:1.0;filter:url(#snakeGlow);}

/* Glow filter for snake head */
<filter id="snakeGlow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="2" result="blur"/>
    <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
    </feMerge>
</filter>'''

    # Insert before closing style tag
    return re.sub(r'(</style>)', snake_styles + r'\n\1', svg_content, count=1)


def enhance_keyframes_for_growth(svg_content):
    """Modify keyframes to make snake grow with true growing effect."""
    # Find the style section
    style_match = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_match:
        return svg_content

    style = style_match.group(1)

    # Find all keyframe definitions and extract info
    keyframes = []  # list of tuples (keyframe_name, content, start_idx, end_idx)
    i = 0
    while i < len(style):
        # Look for @keyframes c[ID]
        keyframe_start = style.find('@keyframes c', i)
        if keyframe_start == -1:
            break

        # Find the keyframe name (until '{')
        name_end = keyframe_start
        while name_end < len(style) and style[name_end] not in '{':
            name_end += 1

        if name_end >= len(style) or style[name_end] != '{':
            # Malformed, skip this occurrence
            i = keyframe_start + 1
            continue

        keyframe_name = style[keyframe_start:name_end]  # @keyframes c[ID]

        # Find matching closing brace
        brace_count = 0
        j = name_end
        while j < len(style):
            if style[j] == '{':
                brace_count += 1
            elif style[j] == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found the matching closing brace
                    keyframe_content = style[name_end+1:j]  # Content between braces
                    keyframes.append((keyframe_name, keyframe_content, keyframe_start, j+1))
                    i = j + 1
                    break
            j += 1
        else:
            # No matching brace found, append rest and break
            break

    # Now we have keyframes, extract activation percentage and color for each
    cell_info = []  # list of dicts: {id, activation, color_var, is_green, original_name, original_content, start_idx, end_idx}
    for keyframe_name, content, start_idx, end_idx in keyframes:
        # Extract the ID from keyframe_name: @keyframes cID
        match_id = re.search(r'@keyframes c(\d+|[a-z]+)$', keyframe_name)
        if not match_id:
            # Try to capture any non-{ characters after 'c'
            match_id = re.search(r'@keyframes c([^{]+)', keyframe_name)
            if not match_id:
                continue
        cell_id = match_id.group(1)

        # Find the first percentage block: [0-9.]+%{...}
        first_percent_match = re.search(r'([\d.]+)%\{([^}]+)\}', content)
        if not first_percent_match:
            continue
        activation = float(first_percent_match.group(1))
        color_var = first_percent_match.group(2).strip()  # e.g., "var(--c3)"

        # Determine if this is a green contribution
        # Green if color_var is one of: var(--c1), var(--c2), var(--c3), var(--c4)
        # Extract the variable name inside var()
        var_match = re.search(r'var\((--c[1-4])\)', color_var)
        is_green = bool(var_match)

        cell_info.append({
            'id': cell_id,
            'activation': activation,
            'color_var': color_var,
            'is_green': is_green,
            'original_name': keyframe_name,
            'original_content': content,
            'start_idx': start_idx,
            'end_idx': end_idx
        })

    if not cell_info:
        return svg_content

    # Sort by activation percentage (the order the snake head visits)
    cell_info.sort(key=lambda x: x['activation'])

    # Compute prefix sum of green contributions
    prefix_green = [0] * (len(cell_info) + 1)
    for idx, info in enumerate(cell_info):
        prefix_green[idx+1] = prefix_green[idx] + (1 if info['is_green'] else 0)

    # Build a mapping from original keyframe to enhanced keyframe
    enhancements = {}  # keyframe_name -> enhanced_content
    for idx, info in enumerate(cell_info):
        g_so_far = prefix_green[idx]   # green count before this cell
        current_is_green = 1 if info['is_green'] else 0
        L = 4 + (g_so_far + current_is_green) // 2  # snake length after this cell

        # Look ahead L steps in the sorted list (by activation)
        j = idx + L
        if j < len(cell_info):
            T_end = cell_info[j]['activation']
        else:
            T_end = 100.0  # stay visible until end if we run out of cells

        T_start = info['activation']
        head_end = min(T_start + 0.1, 99.9)

        # Build enhanced keyframe content
        enhanced_content = (
            f'{T_start:.2f}%{{fill:#00FF9D;opacity:1.0;filter:url(#snakeGlow);class:snake-head}}'
            f'{head_end:.2f}%{{fill:#00FF9D;opacity:0.3;class:snake-body}}'
            f'{T_end:.2f}%{{fill:#00FF9D;opacity:0.3;class:snake-body}}'
            f'{(T_end+0.01):.2f}%{{fill:#00FF9D;opacity:0}}'
            f'100%{{fill:#00FF9D;opacity:0}}'
        )

        enhancements[info['original_name']] = enhanced_content

    # Rebuild the style string by replacing the content of each keyframe we found
    if not keyframes:
        return svg_content

    # We'll build the new style by replacing the content of each keyframe
    style_chunks = []
    last_idx = 0
    for keyframe_name, content, start_idx, end_idx in keyframes:
        # Add everything before this keyframe
        style_chunks.append(style[last_idx:start_idx])

        if keyframe_name in enhancements:
            enhanced_content = enhancements[keyframe_name]
            # Add keyframe name + opening brace + enhanced content + closing brace
            style_chunks.append(keyframe_name)
            style_chunks.append('{')
            style_chunks.append(enhanced_content)
            style_chunks.append('}')
        else:
            # No enhancement, keep original keyframe as-is
            style_chunks.append(style[start_idx:end_idx])

        last_idx = end_idx

    # Add any remaining content after the last keyframe
    if last_idx < len(style):
        style_chunks.append(style[last_idx:])

    new_style = ''.join(style_chunks)

    # Replace the style section in the SVG
    svg_content = re.sub(
        r'<style>.*?</style>',
        f'<style>{new_style}</style>',
        svg_content,
        flags=re.DOTALL,
        count=1
    )

    return svg_content


def main(input_path, output_path=None):
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
    svg_content = enhance_keyframes_for_growth(svg_content)

    # Write output SVG
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        print(f"Enhanced SVG saved to {output_path} ({len(svg_content)} chars)")
        print("Enhancements applied:")
        print("  ✓ Space nebula and starfield background")
        print("  ✓ Snake grows with persistent trail (body remains visible)")
        print("  ✓ Snake head glows brightly when active")
        print("  ✓ Eaten contributions show as snake body (semi-transparent green)")
        print("  ✓ Uneaten cells remain transparent (showing space background)")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 snake_enhancer.py <input_svg> [output_svg]")
        print("  input_svg:  Path to Platane/snk output SVG")
        print("  output_svg: Path for enhanced SVG (optional, overwrites input if not provided)")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)