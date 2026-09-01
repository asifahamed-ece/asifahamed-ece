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
    """Modify keyframes to make snake grow with persistent trail."""
    # Find the style section
    style_match = re.search(r'<style>(.*?)</style>', svg_content, re.DOTALL)
    if not style_match:
        return svg_content

    style = style_match.group(1)

    # Find all keyframe definitions and enhance them
    # Pattern to capture the full keyframe including internal percentage blocks
    def enhance_keyframe_match(match):
        full_prefix = match.group(1)  # @keyframes c[ID]
        keyframe_content = match.group(2)  # Everything inside the outer {}

        # We need to parse the internal structure carefully
        # Look for patterns like: 76.74%{fill:var(--c3)}76.76%,100%{fill:var(--ce)}
        # This means there can be percentage blocks followed by other percentages

        # Find all percentage blocks with their content
        # Pattern: ([0-9.]+)%\{([^}]+)\}
        percent_pattern = r'([\d.]+)%\{([^}]+)\}'
        percent_matches = list(re.finditer(percent_pattern, keyframe_content))

        if not percent_matches:
            # No percentage blocks found, return original
            return match.group(0)

        # Get the first percentage block (where the snake head should be)
        first_match = percent_matches[0]
        peak_pct = float(first_match.group(1))
        color_var = first_match.group(2)  # e.g., "var(--c3)"

        # Calculate transition point (brief head duration - 0.1% of cycle)
        head_end = min(peak_pct + 0.1, 99.9)

        # Build enhanced keyframe content:
        # At peak_pct: SNAKE HEAD (bright, glowing)
        # From peak_pct to head_end: SNAKE HEAD (same as above for smooth transition)
        # From head_end to 100%: SNAKE BODY (semi-transparent, persistent)
        # At 100%: SNAKE BODY

        # We need to preserve any content that comes after the last percentage block
        # Find where the last percentage block ends
        last_match = percent_matches[-1]
        last_end = last_match.end()
        trailing_content = keyframe_content[last_end:]  # Content after last %}

        # Build the enhanced internal content
        enhanced_internal = (
            '{:.2f}%{{fill:{};opacity:1;filter:url(#snakeGlow);class:snake-head}}'.format(peak_pct, color_var) +
            '{:.2f}%{{fill:{};opacity:0.3;fill:#00FF9D;class:snake-body}}'.format(head_end, color_var) +
            '100%{{fill:{};opacity:0.3;fill:#00FF9D;class:snake-body}}'.format(color_var) +
            trailing_content
        )

        # Return the full keyframe with enhanced content
        return '{}{}'.format(full_prefix, '{' + enhanced_internal + '}')

    # Find all keyframe definitions - pattern that captures content between braces properly
    # We need to handle nested braces, so we'll use a different approach
    # Find @keyframes c[ID] and then find the matching closing brace
    def find_keyframes_and_enhance(text):
        result = []
        i = 0
        while i < len(text):
            # Look for @keyframes c[ID]
            keyframe_start = text.find('@keyframes c', i)
            if keyframe_start == -1:
                result.append(text[i:])
                break

            # Add text before this keyframe
            result.append(text[i:keyframe_start])

            # Find the keyframe name
            name_end = keyframe_start
            while name_end < len(text) and text[name_end] not in '{':
                name_end += 1

            if name_end >= len(text) or text[name_end] != '{':
                # Malformed, skip
                result.append(text[keyframe_start:])
                break

            keyframe_name = text[keyframe_start:name_end]  # @keyframes c[ID]

            # Find matching closing brace
            brace_count = 0
            j = name_end
            while j < len(text):
                if text[j] == '{':
                    brace_count += 1
                elif text[j] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Found the matching closing brace
                        keyframe_content = text[name_end+1:j]  # Content between braces

                        # Enhance this keyframe content
                        enhanced_content = enhance_keyframe_content(keyframe_content)

                        # Add the enhanced keyframe
                        result.append('{}{{{}}}'.format(keyframe_name, enhanced_content))

                        # Continue after the closing brace
                        i = j + 1
                        break
                j += 1
            else:
                # No matching brace found, append rest and break
                result.append(text[keyframe_start:])
                break

        return ''.join(result)

    def enhance_keyframe_content(content):
        """Enhance the content inside a keyframe definition."""
        # Find all percentage blocks: [0-9.]+%{...}
        percent_pattern = r'([\d.]+)%\{([^}]+)\}'
        percent_matches = list(re.finditer(percent_pattern, content))

        if not percent_matches:
            return content

        # Get the first percentage block (activation point)
        first_match = percent_matches[0]
        peak_pct = float(first_match.group(1))
        # Extract just the variable name from "fill:var(--c3)" -> "var(--c3)"
        fill_content = first_match.group(2).strip()
        if fill_content.startswith('fill:'):
            color_var = fill_content[5:]  # Remove "fill:" prefix
        else:
            color_var = fill_content

        # Calculate transition point
        head_end = min(peak_pct + 0.1, 99.9)

        # Find where the last percentage block ends to preserve trailing content
        last_match = percent_matches[-1]
        last_end = last_match.end()
        trailing_content = content[last_end:]

        # Build enhanced content
        enhanced = (
            '{:.2f}%{{fill:{};opacity:1;filter:url(#snakeGlow);class:snake-head}}'.format(peak_pct, color_var) +
            '{:.2f}%{{fill:{};opacity:0.3;fill:#00FF9D;class:snake-body}}'.format(head_end, color_var) +
            '100%{{fill:{};opacity:0.3;fill:#00FF9D;class:snake-body}}'.format(color_var) +
            trailing_content
        )

        return enhanced

    # Apply enhancement to all keyframes in the style
    enhanced_style = find_keyframes_and_enhance(style)

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