#!/usr/bin/env python3
"""Dołącza dane z gov.csv (po ID == H_WP_ID) do lokale.csv -> rejestr.csv."""
import csv

# ID i recid w gov.csv duplikują H_WP_ID.
SKIP = {"ID", "recid"}

with open("gov.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    gov_cols = [c for c in reader.fieldnames if c not in SKIP]
    gov = {row["ID"]: row for row in reader}

with open("lokale.csv", newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    lokale_cols = reader.fieldnames
    lokale = list(reader)

missing = 0
with open("rejestr.csv", "w", newline="", encoding="utf-8") as out:
    w = csv.DictWriter(out, fieldnames=lokale_cols + gov_cols)
    w.writeheader()
    for row in lokale:
        g = gov.get(row["H_WP_ID"])
        if g is None:
            missing += 1
            g = {}
        row.update({c: g.get(c, "") for c in gov_cols})
        w.writerow(row)

print(f"{len(lokale)} wierszy, bez dopasowania: {missing}")
