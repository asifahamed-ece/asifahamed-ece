#!/usr/bin/env python3
import re

# Read the backup file
with open('/home/shadow/Projects/Asif/asifahamed-dev/output/github-contribution-grid-snake.svg.backup', 'r') as f:
    svg = f.read()

print(f"Read SVG: {len(svg)} chars")

# Test 1: Add space background
background = '<rect width="100%" height="100%" fill="#000000"/>'
svg = re.sub(r'(<svg[^>]*>)', r'\1\n    ' + background, svg, count=1)
print("Added background")

# Test 2: Modify .c class to be transparent
svg = re.sub(
    r'\.c\{[^}]+\}',
    '.c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;stroke:var(--cb);animation:none 49900ms linear infinite;width:12px;height:12px;opacity:0}',
    svg
)
print("Made .c transparent")

# Test 3: Add simple snake styles
snake_styles = '''
.c.snake-body{fill:#00FF9D;opacity:0.4;}
.c.snake-head{fill:#00FF9D;opacity:1.0;}'''

svg = re.sub(r'(</style>)', snake_styles + r'\n\1', svg, count=1)
print("Added snake styles")

# Save test file
with open('/home/shadow/Projects/Asif/asifahamed-dev/output/debug_test.svg', 'w') as f:
    f.write(svg)

print("Wrote debug_test.svg")