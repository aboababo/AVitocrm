#!/usr/bin/env python3
"""
Auto-fix script:
- Strip trailing whitespace
- Convert f-strings without placeholders to normal strings
- Replace bare `except:` with `except Exception as e:`

Use with project's venv python.
"""
import io
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

PY_EXCLUDE_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules"}

fstring_pattern = re.compile(r"(?P<prefix>[^\w])?f(?P<quote>['\"])((?:\\.|.)*?)(?P=quote)")
# Simpler approach: detect f"..." or f'...' where no '{' or '}' present inside

bare_except_re = re.compile(r"^(?P<indent>\s*)except\s*:\s*$")


def process_file(path):
    changed = False
    with io.open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    new_lines = []
    for i, line in enumerate(lines):
        orig = line
        # Remove trailing whitespace but preserve newline
        if line.endswith("\n"):
            stripped_line = line.rstrip("\n")
            new_line = stripped_line.rstrip() + "\n"
        else:
            new_line = line.rstrip()

        # Replace bare except
        m = bare_except_re.match(new_line)
        if m:
            indent = m.group("indent")
            new_line = f"{indent}except Exception as e:\n"

        # Convert simple f-strings without braces
        # We will look for occurrences of f"..." or f'...'
        def replace_fstring(match):
            quote = match.group("quote")
            content = match.group(3)
            # if there is any { or } inside, skip
            if "{" in content or "}" in content:
                return match.group(0)
            prefix = match.group("prefix") or ""
            # escape backslashes? keep as is
            return f"{prefix}{quote}{content}{quote}"

        # Apply replacement for f-strings on the line
        new_line2 = re.sub(r"f(\'[^\']*\'|\"[^\"]*\")", lambda m: replace_fstring(m), new_line)

        if new_line2 != new_line:
            new_line = new_line2

        new_lines.append(new_line)
        if new_line != orig:
            changed = True

    if changed:
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.writelines(new_lines)
    return changed


def iter_py_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # skip excluded dirs
        parts = set(part for part in dirpath.split(os.sep))
        if parts & PY_EXCLUDE_DIRS:
            continue
        # skip .venv inside root
        if any(p in PY_EXCLUDE_DIRS for p in dirpath.split(os.sep)):
            continue
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            yield os.path.join(dirpath, fname)


def main():
    total = 0
    changed_files = []
    for p in iter_py_files():
        total += 1
        try:
            if process_file(p):
                changed_files.append(p)
        except Exception as e:
            print("Error processing", p, e)
    print(f"Total files scanned: {total}, changed: {len(changed_files)}")
    for f in changed_files:
        print("Modified:", f)


if __name__ == "__main__":
    main()
