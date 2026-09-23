# Eval

Checks unslop output with rules a script can apply. No model grades the result.

## Run

```bash
eval/run.sh              # regenerate every output.md with Sonnet, then score
eval/run.sh cases haiku  # another model
python3 eval/score.py eval/cases   # score existing outputs only
```

`run.sh` needs the skill installed where `claude` can find it (`~/.claude/skills/unslop`).

## Add a case

```
eval/cases/<name>/
  input.md    the draft, or a write-mode request
  type        slack | email | ticket | doc | status | pr | commit
```

Remove names, customer data, and anything internal before committing a case.

## What it checks

| Result | Check |
|---|---|
| FAIL | A Tier 1 phrase from `SKILL.md` remains |
| FAIL | A number, URL, ID, or @mention from the input is missing (WARN for documents, which may drop examples) |
| FAIL | Over the hard word budget; commit subject over 72 chars; document cut under 30% |
| WARN | Three or more distinct Tier 2 patterns |
| WARN | A number, URL, or ID in the output that the input doesn't have |
| WARN | A hedge ("expected", "likely") in the input missing from the output |
| WARN | A code span dropped |
| WARN | Over the typical budget; first sentence over 30 words |
| WARN | Document: no TL;DR near the top, filler headings, paragraphs over 4 sentences |

It prints each output's first sentence for a person to judge: does it answer, decide, or ask? It can't catch a sentence that repeats another in other words.

Warnings need a person. Expect some that don't matter, such as "as expected" being cut.

## Editing patterns

`score.py` reads the backticked phrases on each `**Watch for:**` line under `### Tier 1` and `### Tier 2` in `SKILL.md`. Keep that format. A phrase starting with `re:` is a regular expression.
