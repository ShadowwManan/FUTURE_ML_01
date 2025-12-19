import csv
import json
import os
import re
import sys

def clean(s):
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"@\w+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def read_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def build_pairs(rows):
    by_id = {}
    for r in rows:
        tid = r.get("tweet_id")
        if tid:
            by_id[tid] = r
    pairs = []
    for r in rows:
        inbound = str(r.get("inbound", "")).lower() == "true"
        if not inbound:
            continue
        q_id = r.get("tweet_id") or ""
        q_text = clean(r.get("text", "") or "")
        resp_id = (r.get("response_tweet_id") or "").strip()
        a_text = ""
        if resp_id and resp_id in by_id:
            a_text = clean(by_id[resp_id].get("text", "") or "")
        else:
            # fallback: find outbound that references this inbound
            for rr in rows:
                inbound2 = str(rr.get("inbound", "")).lower() == "true"
                if inbound2:
                    continue
                if (rr.get("in_response_to_tweet_id") or "").strip() == q_id:
                    a_text = clean(rr.get("text", "") or "")
                    break
        if q_text and a_text:
            pairs.append({"question": q_text, "answer": a_text})
    # dedupe
    seen = set()
    unique = []
    for p in pairs:
        key = (p["question"], p["answer"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique

def main():
    if len(sys.argv) < 2:
        print("Usage: py -3 train.py <csv_path>")
        sys.exit(1)
    csv_path = sys.argv[1]
    rows = read_rows(csv_path)
    pairs = build_pairs(rows)
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "trained_pairs.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"count": len(pairs), "pairs": pairs}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(pairs)} pairs to {out_path}")

if __name__ == "__main__":
    main()
