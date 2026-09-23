# unslop

A Claude skill that rewrites work writing so the answer comes first, it is short, and it uses plain words. It covers Slack and email replies, ticket findings, Confluence-style documents, status updates, PR descriptions, and commit messages.

**Before (118 words):**
> Great question! I've taken a deep dive into the deployment pipeline to understand what's happening here. After a thorough investigation, it appears that the failure is likely related to a timeout issue in the integration test stage. Specifically, the test suite has grown significantly over recent weeks, and it's now exceeding the 30-minute limit configured in the CI settings. There are a few potential approaches we could consider: […] Let me know if you'd like me to dig deeper into any of these!

**After (34 words):**
> Deploys fail because integration tests now run past the 30-min CI timeout. Suggest raising the timeout as a stopgap and parallelizing the suite as the real fix. OK to go ahead?

## Install

**Claude Code, as a skill:**
```bash
git clone https://github.com/cjimesh/unslop ~/.claude/skills/unslop
```
Invoke with `/unslop`. Update with `git pull`.

**Claude Code, as a plugin:**
```text
/plugin marketplace add cjimesh/unslop
/plugin install unslop@unslop
```
Invoke with `/unslop:unslop`.

**claude.ai / Claude Desktop:** run `python3 scripts/package-claude-ai.py`, then upload `dist/unslop.zip` under Settings → Capabilities → Skills. There are no slash commands there, so ask for it by name: "unslop that as a Slack reply".

## Use

| You type | It does |
|---|---|
| `/unslop` | Rewrites Claude's previous reply |
| `/unslop ticket` | Rewrites the previous reply as ticket findings |
| `/unslop <draft>` | Rewrites a pasted draft |
| `/unslop <draft> as an email to my VP` | Rewrites it as that type |
| `/unslop: status update. <notes>` | Writes from notes |
| `/unslop doc` | Turns the previous reply into a Confluence-style page |

Types: `slack`, `email`, `ticket`, `doc` (also `document`, `confluence`, `runbook`, `postmortem`, `design doc`), `status`, `pr`, `commit`. Without one, it picks; short text defaults to Slack.

The skill runs only when you invoke it.

## What it does

- **First line answers, decides, or asks.** A reader who stops there has what they need.
- **Budgets per type:** Slack 60 words (100 max), email 120, ticket findings 150, PR 100, status lines under 25 words. Documents are as long as the content needs.
- **Keeps every fact:** numbers, names, IDs, links, dates, and the source's certainty ("expected Wednesday" stays expected). Adds nothing the source doesn't say.
- **Removes AI filler** in two tiers: always-cut phrases (chat wrappers, "it's worth noting", "delve", "not just X but Y") and weaker tells cut only when several cluster.
- **Rebuilds documents** on a skeleton (design doc, decision record, runbook, postmortem, explainer, status page) with a TL;DR on top and statement headings, instead of editing them in place.
- **Stays formal.** Short, not casual.

Everything is in [`SKILL.md`](SKILL.md).

## Testing

`eval/` scores rewrites without a model: Tier 1 phrases left, facts lost or added, hedges dropped, budget overruns, and for documents a missing TL;DR or filler headings. See [`eval/README.md`](eval/README.md).

Current cases (Sonnet, one run each):

| Case | Words | Result |
|---|---|---|
| Design doc | 2455 → 1279 | Warn: illustrative numbers dropped, one dash |
| Headcount email | 187 → 82 | Warn: harmless hedge flag |
| PR description | 188 → 76 | Warn: harmless hedge flag |
| Status update (from notes) | 43 → 33 | Pass |

Output varies between runs. During development the design doc failed 2 of 4 runs (a leftover "not just", a missing TL;DR label) before the rules were tightened. Run the eval more than once before trusting a change.

The cases are synthetic. Real work examples, sanitized, make better ones.

## Credits

Pattern tiers and phrase lists adapted from [blader/humanizer](https://github.com/blader/humanizer) and [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop), both MIT. Those target long-form prose; unslop targets short workplace text and adds answer-first structure, per-type budgets, and fact checks.

## License

MIT
