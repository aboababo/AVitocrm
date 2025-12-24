from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'backend' / 'app.py'

stop_tokens = ('except', 'finally', 'elif', 'else', 'return', 'def ', 'class ', '@', 'pass', 'break', 'continue', 'raise')

def in_triple_quote(s):
    return s.count("\"\"\"") % 2 == 1 or s.count("'''") % 2 == 1

text = TARGET.read_text(encoding='utf-8')
lines = text.splitlines(keepends=True)
changed = False

# Track triple-quote state
triple = False

i = 0
while i < len(lines) - 1:
    line = lines[i]
    # update triple state for this line
    if '"""' in line or "'''" in line:
        # toggle if odd occurrences
        if (line.count('"""') + line.count("'''") ) % 2 == 1:
            triple = not triple
    if triple:
        i += 1
        continue

    stripped = line.rstrip('\n')
    # ignore comments and blank lines
    if stripped.strip() == '' or stripped.lstrip().startswith('#'):
        i += 1
        continue

    # lines that end with colon (block starters)
    if stripped.rstrip().endswith(':'):
        base_indent = len(line) - len(line.lstrip(' '))
        # find next non-empty, non-comment line
        j = i + 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        if j >= len(lines):
            i += 1
            continue
        next_indent = len(lines[j]) - len(lines[j].lstrip(' '))
        next_strip = lines[j].lstrip()
        # if next line is not indented more than base, indent it and a following block
        if next_indent <= base_indent and not any(next_strip.startswith(tok) for tok in stop_tokens):
            desired = base_indent + 4
            k = j
            while k < len(lines):
                if lines[k].strip() == '':
                    k += 1
                    continue
                cur_indent = len(lines[k]) - len(lines[k].lstrip(' '))
                cur_strip = lines[k].lstrip()
                if cur_indent <= base_indent and any(cur_strip.startswith(tok) for tok in stop_tokens):
                    break
                if cur_indent < desired:
                    lines[k] = ' ' * desired + lines[k].lstrip(' ')
                    changed = True
                k += 1
            i = k
            continue
    i += 1

if changed:
    TARGET.write_text(''.join(lines), encoding='utf-8')
    print('Modified:', TARGET)
else:
    print('No changes')
