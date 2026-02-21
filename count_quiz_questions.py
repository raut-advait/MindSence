#!/usr/bin/env python3
import re
from pathlib import Path

html_path = Path('templates/test.html')
content = html_path.read_text(encoding='utf-8')

# Find all input field names
pattern = r'name="(\w+)_(\d+)"'
matches = re.findall(pattern, content)

# Count questions per category
categories = {}
for category, num in matches:
    if category not in categories:
        categories[category] = []
    if num not in categories[category]:
        categories[category].append(num)

print('Questions per category in test.html:')
for cat in sorted(categories.keys()):
    nums = sorted([int(n) for n in categories[cat]])
    print(f'  {cat}: {len(nums)} questions (numbers: {nums})')
