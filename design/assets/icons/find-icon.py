#!/usr/bin/env python3
"""Поиск иконки Lucide по ключевому слову: python3 find-icon.py agent workflow"""
import json, sys, pathlib
base = pathlib.Path(__file__).parent / "lucide"
tags = json.loads((base / "tags.json").read_text())
q = [w.lower() for w in sys.argv[1:]]
if not q:
    print("укажи слово: python3 find-icon.py invoice"); sys.exit(1)
hits = []
for name, words in tags.items():
    hay = name.replace("-", " ") + " " + " ".join(words)
    score = sum(3 if w in name else 1 for w in q if w in hay)
    if score:
        hits.append((score, name))
hits.sort(key=lambda x: (-x[0], x[1]))
if not hits:
    print("ничего не найдено"); sys.exit(0)
for _, name in hits[:25]:
    print(f"{name:<32} {base/'svg'/(name + '.svg')}")
print(f"\nвсего совпадений: {len(hits)}")
