#!/usr/bin/env python3
"""Pobiera lokale (adresy) dla każdego ID z gov.csv z rdl.knf.gov.pl -> lokale.csv."""
import csv
import json
import time

import requests

BASE = "https://rdl.knf.gov.pl"
PAGE = 100
DELAY = 0.5
FIELDS = ["H_WP_ID", "ID", "LOKAL_MIEJSCOWOSC", "LOKAL_KOD", "LOKAL_ULICA", "LOKAL_NR"]

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:156.0) Gecko/20100101 Firefox/156.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "pl,en-US;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE,
})


def fetch_page(app_id, offset):
    req = {
        "cmd": "get",
        "search": [],
        "limit": PAGE,
        "offset": offset,
        "method": "LokalTable",
        "appid": app_id,
        "sort": [{"field": "LOKAL_MIEJSCOWOSC", "direction": "asc"}],
        "searchLogic": "OR",
    }
    data = {"draw": 1, "start": offset, "length": PAGE, "request": json.dumps(req)}
    r = session.post(
        f"{BASE}/JSON",
        data=data,
        headers={"Referer": f"{BASE}/detail.html?param={app_id}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def fetch_all(app_id):
    rows, offset = [], 0
    while True:
        j = fetch_page(app_id, offset)
        rows.extend(j.get("records", []))
        offset += PAGE
        if offset >= j.get("total", 0):
            return rows
        time.sleep(DELAY)


def main():
    session.get(f"{BASE}/", timeout=30)  # ciasteczko JSESSIONID

    with open("gov.csv", newline="", encoding="utf-8") as f:
        ids = [row["ID"] for row in csv.DictReader(f)]

    with open("lokale.csv", "w", newline="", encoding="utf-8") as out:
        w = csv.DictWriter(out, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for i, app_id in enumerate(ids, 1):
            try:
                records = fetch_all(int(app_id))
            except (requests.RequestException, ValueError) as e:
                print(f"[{i}/{len(ids)}] {app_id}: BŁĄD {e}")
                continue
            for rec in records:
                rec.setdefault("H_WP_ID", app_id)
                w.writerow(rec)
            out.flush()
            print(f"[{i}/{len(ids)}] {app_id}: {len(records)} lokali")
            time.sleep(DELAY)


if __name__ == "__main__":
    main()
