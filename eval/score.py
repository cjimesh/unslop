#!/usr/bin/env python3
"""Score /unslop output with checks that need no model.

Usage:
  score.py CASES_DIR            score every case folder under CASES_DIR
  score.py CASE_DIR             score one case folder

A case folder holds:
  input.md    the original draft, or the write-mode request
  output.md   what /unslop produced
  type        one of: slack email ticket doc status pr commit (document = doc)

Checks:
  FAIL  a Tier 1 pattern from SKILL.md
  FAIL  a number, URL, ID, or @mention in input.md missing from output.md
  FAIL  over the hard word budget for the type
  WARN  3+ distinct Tier 2 patterns
  WARN  a code span dropped (fine for a PR file list)
  WARN  a number, URL, or ID in the output that the input doesn't have
  WARN  a hedge in the input ("expected", "likely") missing from the output
  WARN  over the typical budget, or a first sentence over 30 words
  WARN  doc: no TL;DR, filler headings, paragraphs over 4 sentences
  FAIL  doc: cut under 30% on a draft over 300 words
The first sentence is printed for a person to judge: does it answer, decide, or ask?
"""
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# Mirrors the Budget column in SKILL.md: (typical, hard) in words. None = no limit.
BUDGETS = {
    "slack": (60, 100),
    "email": (120, 120),
    "ticket": (150, 150),
    "pr": (100, 100),
    "doc": (None, None),
    "status": (None, None),  # checked per line below
    "commit": (None, None),  # checked per line below
}

# Each group is one hedge; the output keeps it if it has any member of the group.
HEDGES = [["expected", "expect"], ["estimated", "estimate", "eta"], ["likely", "probably"],
          ["may", "might", "could"], ["should"], ["not confirmed", "unconfirmed"],
          ["approximately", "roughly", "about", "around", "~"], ["tentative"],
          ["pending"], ["planned"]]

NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}


def load_patterns():
    tiers, tier = {1: [], 2: []}, None
    for line in (SKILL_DIR / "SKILL.md").read_text().splitlines():
        if line.startswith("### Tier 1"):
            tier = 1
        elif line.startswith("### Tier 2"):
            tier = 2
        elif re.match(r"#{1,3} ", line):
            tier = None
        elif tier and line.startswith("**Watch for:**"):
            for p in re.findall(r"`([^`]+)`", line):
                if p.startswith("re:"):
                    rx = re.compile(p[3:], re.I)
                elif re.match(r"\w", p):
                    rx = re.compile(r"(?<!\w)" + re.escape(p) + (r"(?!\w)" if p[-1].isalnum() else ""), re.I)
                else:
                    rx = re.compile(re.escape(p))
                tiers[tier].append((p, rx))
    return tiers


def strip_code(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.sub(r"`[^`]*`", " ", text)


def normalize_apostrophes(text):
    return text.replace("’", "'").replace("‘", "'")


def facts(text):
    """Tokens a rewrite must keep: numbers, URLs, code spans, IDs, mentions."""
    t = normalize_apostrophes(text).lower()
    found = set()
    found |= {"url:" + u for u in re.findall(r"https?://\S+", t)}
    found |= {"code:" + c for c in re.findall(r"`([^`]+)`", text)}
    found |= {"id:" + i for i in re.findall(r"\b[a-z]{2,10}-\d+\b|#\d+\b", t)}
    for word, digit in NUMBER_WORDS.items():  # after IDs, so "one-by-one" isn't an ID
        t = re.sub(rf"\b{word}\b", digit, t)
    found |= {"mention:" + m for m in re.findall(r"@\w+", t)}
    no_urls = re.sub(r"https?://\S+", " ", t)
    # "1 offer" -> "an offer" loses nothing, so 1 is not tracked.
    found |= {"num:" + n for n in re.findall(r"\d+(?:\.\d+)?", no_urls) if n != "1"}
    return found


def words(text):
    return len(re.findall(r"\S+", text))


def first_line(text):
    for line in text.splitlines():
        s = line.strip().lstrip("#>*- ").strip()
        salutation = s.endswith(",") and len(s.split()) <= 3  # "Hi Priya," / "Priya,"
        if s and not s.lower().startswith("subject:") and not salutation:
            return re.split(r"(?<=[.!?])\s+", s)[0]  # first sentence
    return ""


def score(case, tiers):
    inp = (case / "input.md").read_text()
    out = (case / "output.md").read_text()
    kind = (case / "type").read_text().strip().lower()
    kind = {"document": "doc", "confluence": "doc", "runbook": "doc", "postmortem": "doc"}.get(kind, kind)
    fails, warns = [], []

    prose = normalize_apostrophes(strip_code(out))
    t1 = sorted({p for p, rx in tiers[1] if rx.search(prose)})
    t2 = sorted({p for p, rx in tiers[2] if rx.search(prose)})
    if t1:
        fails.append("Tier 1: " + ", ".join(t1))
    if len(t2) >= 3:
        warns.append("Tier 2 cluster: " + ", ".join(t2))

    missing = sorted(facts(inp) - facts(out))
    hard_missing = [m for m in missing if not m.startswith("code:")]
    soft_missing = [m for m in missing if m.startswith("code:")]
    if hard_missing and kind == "doc":  # documents.md lets examples go; a person checks
        warns.append("missing facts (check each was only an example): " + ", ".join(hard_missing))
    elif hard_missing:
        fails.append("missing facts: " + ", ".join(hard_missing))
    added = sorted(m for m in facts(out) - facts(inp) if m.startswith(("num:", "url:", "id:")))
    if added:
        warns.append("new in output, check not invented: " + ", ".join(added))
    if soft_missing:  # a PR's file list is meant to be dropped
        warns.append("code spans dropped: " + ", ".join(soft_missing))

    low_in, low_out = normalize_apostrophes(inp).lower(), normalize_apostrophes(out).lower()
    def has(text, group):
        return any(re.search(rf"(?<!\w){re.escape(h)}(?!\w)" if h[0].isalnum() else re.escape(h), text)
                   for h in group)
    dropped = [g[0] for g in HEDGES if has(low_in, g) and not has(low_out, g)]
    if dropped:
        warns.append("hedges dropped (check certainty): " + ", ".join(dropped))

    n_in, n_out = words(inp), words(out)
    typical, hard = BUDGETS.get(kind, (None, None))
    if hard and n_out > hard:
        fails.append(f"{n_out} words, hard budget {hard}")
    elif typical and n_out > typical:
        warns.append(f"{n_out} words, typical budget {typical}")
    lines = [l for l in out.splitlines() if l.strip()]
    if kind == "status":
        long = [l for l in lines if words(l) > 25]
        if long:
            warns.append(f"{len(long)} status line(s) over 25 words")
    if kind == "commit" and lines and len(lines[0]) > 72:
        fails.append(f"commit subject {len(lines[0])} chars, max 72")

    if kind == "doc":
        top = "\n".join(lines[:8]).lower()
        if "tl;dr" not in top and "tldr" not in top:
            warns.append("no TL;DR near the top")
        filler = [h.strip("# ").strip() for h in lines if h.startswith("#") and re.fullmatch(
            r"#+\s*(introduction|overview|summary|conclusion|conclusions|final thoughts)\s*", h.strip().lower())]
        if filler:
            warns.append("filler headings: " + ", ".join(filler))
        long_paras = [p for p in re.split(r"\n\s*\n", out)
                      if not p.lstrip().startswith(("#", "|", "-", "*", "```", ">")) and not re.match(r"\s*\d+\.", p)
                      and len(re.findall(r"[.!?](?:\s|$)", p)) > 4]
        if long_paras:
            warns.append(f"{len(long_paras)} paragraph(s) over 4 sentences")
        if n_in > 300 and n_out > 0.7 * n_in:
            fails.append("cut under 30%: edited in place, not rebuilt")

    lead = first_line(out)
    if words(lead) > 30:
        warns.append(f"first sentence {words(lead)} words")

    status = "FAIL" if fails else "WARN" if warns else "PASS"
    cut = f"{n_in} -> {n_out} words ({100 - round(100 * n_out / n_in)}% cut)" if n_in else ""
    print(f"{status}  {case.name}  [{kind}]  {cut}")
    print(f"      first sentence: {lead}")
    for m in fails:
        print(f"      FAIL {m}")
    for m in warns:
        print(f"      WARN {m}")
    return status


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = Path(sys.argv[1])
    cases = [root] if (root / "type").exists() else sorted(
        p for p in root.iterdir() if (p / "type").exists())
    if not cases:
        sys.exit(f"no case folders under {root}")
    tiers = load_patterns()
    results = [score(c, tiers) for c in cases]
    print(f"\n{results.count('PASS')} pass, {results.count('WARN')} warn, "
          f"{results.count('FAIL')} fail, of {len(results)}")
    sys.exit(1 if "FAIL" in results else 0)


if __name__ == "__main__":
    main()
