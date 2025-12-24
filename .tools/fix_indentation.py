import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
py_files = list((ROOT / 'backend').rglob('*.py'))

def indent_block(lines, start_idx, base_indent):
    # Indent contiguous block starting at start_idx by 4 spaces until we hit
    # a line that has indent <= base_indent and starts with one of stop tokens
    stop_tokens = ('except', 'finally', 'return', '@', 'def ', 'class ', 'with ', '#')
    i = start_idx
    changed = False
    while i < len(lines):
        line = lines[i]
        if line.strip() == '':
            # keep blank line but continue
            i += 1
            continue
        stripped = line.lstrip('\n')
        cur_indent = len(line) - len(line.lstrip(' '))
        starts = stripped.lstrip()
        # If we encounter a dedent to or above base_indent and the line starts with stop token,
        # we stop indenting.
        if cur_indent <= base_indent and any(starts.startswith(tok) for tok in stop_tokens):
            break
        # Otherwise, ensure it's indented at least base_indent + 4
        desired = base_indent + 4
        if cur_indent < desired:
            lines[i] = ' ' * desired + line.lstrip(' ')
            changed = True
        i += 1
    return changed

pattern_with = re.compile(r"^(?P<indent>\s*)with\s+get_connection\(\)\s+as\s+conn:\s*$")
pattern_try = re.compile(r"^(?P<indent>\s*)try:\s*$")

modified_files = []
for p in py_files:
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines(keepends=True)
    changed_any = False
    i = 0
    while i < len(lines):
        m = pattern_with.match(lines[i])
        if m:
            base_indent = len(m.group('indent'))
            # find next non-empty line index
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines):
                cur_indent = len(lines[j]) - len(lines[j].lstrip(' '))
                if cur_indent <= base_indent:
                    if indent_block(lines, j, base_indent):
                        changed_any = True
            i = j
            continue
        # also fix bare 'try:' followed by non-indented block
        m2 = pattern_try.match(lines[i])
        if m2:
            base_indent = len(m2.group('indent'))
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines):
                cur_indent = len(lines[j]) - len(lines[j].lstrip(' '))
                if cur_indent <= base_indent:
                    if indent_block(lines, j, base_indent):
                        changed_any = True
            i = j
            continue
        i += 1
    if changed_any:
        p.write_text(''.join(lines), encoding='utf-8')
        modified_files.append(str(p.relative_to(ROOT)))

print('Modified files:', modified_files)
