---
name: unslop
description: Write or rewrite work text (ticket/debug findings, Slack or email replies, documents, PR and commit text) so the answer comes first, it is short, and it uses plain words. Use only when the user runs /unslop or explicitly asks to unslop a draft.
disable-model-invocation: true
---

# Unslop

Readers skim. Put what they need in the first line, cut what they won't miss, use plain words. Short does not mean casual: keep a professional register.

## Modes

- **Rewrite:** the input is a draft. Keep every fact, number, name, ID, link, date, and commitment the reader needs.
- **Write:** the input is a request ("unslop: RCA for this ticket"). Produce the text directly under these rules.
- **Last reply:** no input, or only an output type (`/unslop slack`), or a pointer like "that" or "the last one". The draft is your most recent reply before this request. Rewrite it in Rewrite mode. Keep code blocks, commands, and file paths from it unchanged.

Pasted text longer than two sentences is a draft. Anything after the draft, or a lone type word, sets the output type ("… as a PR description", `/unslop ticket`). Type words: `slack`, `email`, `ticket`, `doc` or `document` (also `confluence`, `runbook`, `postmortem`, `design doc`), `status`, `pr`, `commit`.

In every mode, add no facts, dates, promises, or owners the source doesn't give. Don't resolve relative dates ("next Wed" stays "next Wed"). Keep the source's level of certainty: "expected Wednesday" stays "expected Wednesday", not "on track for Wednesday".

## Procedure

1. Name the reader and what they need from this text: an answer, a decision, an action, or awareness.
2. Pick the output type from the table below. Short and unclear defaults to Slack.
3. Write the first line: the answer, decision, or ask. A reader who stops there must have what they need. If the source has no answer, say that in the first line; do not invent one.
4. Add only what the reader needs to trust or act on the first line. Use the source's names for things ("nightly build" stays "nightly build"); the examples below show shape, not wording.
5. Cut pass: for each sentence ask "would the reader miss this?" If not, delete it. Delete any sentence that repeats an earlier one in other words. Then cut words inside the sentences that remain.
6. Pattern pass: using **Patterns** below, remove every Tier 1 pattern. Remove Tier 2 patterns when three or more distinct ones appear.
7. Run the checklist. Fix problems; don't explain them.
8. Output only the final text. Never print word counts or budgets. No preamble ("Here's a tighter version"), no commentary after. One exception: if you dropped something that might matter, end with a single line `Dropped: <what>`.

## Output types

| Type | Shape | Budget |
|---|---|---|
| Slack / chat | Answer or ask in the first sentence. An ask names who and by when. No headers. Bullets only for 3+ parallel items. | 60 words typical, 100 max |
| Email | A subject line that states the point, and a body whose first sentence states it again: many readers skip the subject. Keep the source's greeting and sign-off. Otherwise as Slack. | 120 words |
| Ticket / debug findings | **Cause:** one sentence. **Evidence:** 1–3 bullets (log line, commit, metric). **Fix:** what, where, status. **Open:** unresolved questions only; omit if none. | 150 words |
| Document (Confluence/wiki page, design doc, runbook, postmortem) | Follow **Documents** below. TL;DR first; each section opens with its conclusion. | As long as the content needs, no longer |
| Status update | Done / Next / Blocked, one line per item. No heading line. | Each line under 25 words |
| PR description | First line: what changes and why. `Testing:` one line. `Risk:` only if non-obvious. Don't list files or retell the diff. | 100 words |
| Commit message | Imperative subject, 72 chars max. Body only to explain why. | 3 body lines |

For debug findings, don't narrate the investigation. Mention a ruled-out cause only if the reader would otherwise re-check it, in one line.

Closing offers ("happy to discuss", "let me know") are cut. Keep one only when it names a concrete next step the reader may want, such as "I can send the cost model by Friday."

## Checklist

- Does the first line answer, decide, or ask?
- Would a reader who stops after the first line act correctly?
- Within budget? Every sentence over budget must earn its place.
- Every number, name, ID, link, and date from the source survives, with the same certainty, and none was added.
- No Tier 1 patterns remain.
- Specifics over adjectives: "p99 went from 200 ms to 2 s", not "significant latency degradation".
- Would a senior colleague, writing in a hurry, send exactly this?

## Examples

**Slack, before (118 words):**
> Great question! I've taken a deep dive into the deployment pipeline to understand what's happening here. After a thorough investigation, it appears that the failure is likely related to a timeout issue in the integration test stage. Specifically, the test suite has grown significantly over recent weeks, and it's now exceeding the 30-minute limit configured in the CI settings. There are a few potential approaches we could consider: we could increase the timeout, parallelize the tests, or identify and remove slow tests. Each of these options has its own trade-offs. I'd recommend starting with increasing the timeout as a short-term fix while we work on parallelization as a longer-term solution. Let me know if you'd like me to dig deeper into any of these!

**After (34 words):**
> Deploys fail because integration tests now run past the 30-min CI timeout. Suggest raising the timeout as a stopgap and parallelizing the suite as the real fix. OK to go ahead?

**Ticket, before (excerpt):**
> After extensive investigation into the reported issue, I was able to identify that the root cause appears to be related to how the session cache handles expiry. Initially I suspected the load balancer, but after reviewing the logs this was ruled out. It's worth noting that the issue only manifests under specific conditions...

**After:**
> **Cause:** Session cache entries expire 60 s before the auth token, so requests in that window get a 401.
> **Evidence:**
> - 401s cluster in the last minute of each token's life (auth-svc logs, Sep 18–20).
> - Cache TTL is 3540 s, token TTL 3600 s (`session/config.yaml`).
>
> **Fix:** Set cache TTL from the token's `exp` claim. PR open, not merged.

## Documents

For pages people read on Confluence, Notion, Google Docs, or a wiki. Readers arrive from a link, read the top, and scan headings for the part they need. Most never read the whole page.

### Every document

- **Title** says what the page is about and, for a decision, what was decided: "Webhook retries: move to exponential backoff", not "Webhook Retry Strategy Design Document".
- **TL;DR** right under the title, labeled `**TL;DR:**`, 60 words max: the recommendation or answer, the main reason, and the ask (who decides what, by when). A reader who stops here knows what the page says and what's needed from them.
- **Metadata line** under the TL;DR if the source has it: owner, status (draft / in review / decided), last updated. Don't invent any of these.
- **Headings are statements** when the section has a conclusion: "Backoff caps at 5 minutes", not "Backoff Parameters". State the claim plainly, with no "not X" contrast. Plain nouns are fine for reference sections ("Rollout plan", "Open questions").
- **Each section's first sentence is its conclusion.** Supporting detail follows.
- **Paragraphs:** 4 sentences max. Bullets for parallel items. A table when comparing options or listing values against the same attributes.
- **Background** only as much as the reader needs to follow the argument, usually one paragraph. Link to other pages instead of re-explaining them.
- **No section repeats another.** Cut "Overview", "Introduction", and "Summary" sections that restate the TL;DR, and conclusion sections that restate the body.
- **Open questions** as a list, each with an owner if the source names one.
- Sentence-case headings. No emoji in headings.
- **Length:** as long as the content needs. For a rewrite, a 40–60% cut is typical; under 30% means the page was edited in place, not rebuilt.

### Rewriting a document

Rebuild it; don't edit it in place. Pick the skeleton below that matches the kind of document, move each fact from the source into the section where it belongs, and drop what has no home. Don't keep the source's headings or order. Its "Introduction", "Overview", "Goals", and "Conclusion" sections usually fold into the TL;DR and the Problem section.

Keep every number, name, date, and decision from the source; examples and illustrations may go.

### Shapes by kind

Use the matching skeleton. Omit a section the source has nothing for; don't fill it.

**Design doc / RFC / proposal**
TL;DR → Problem (what's broken, with numbers) → Proposal → Alternatives considered (table: option, why not) → Risks → Rollout → Open questions

**Decision record**
TL;DR (the decision) → Context → Options (table) → Decision and why → Consequences

**Runbook / how-to**
TL;DR (what this fixes and when to use it) → Prerequisites → Numbered steps, one action each, commands in code blocks → How to verify → Rollback. Imperative mood ("Restart the pod"). No explanation inside steps beyond what prevents a mistake.

**Postmortem / incident report**
TL;DR (what broke, impact, cause, status) → Impact (who, how many, how long) → Timeline (table: time, event) → Root cause → What went well / what didn't (short bullets) → Action items (table: action, owner, due). No blame language.

**Explainer / onboarding page**
TL;DR (what this system does, in one sentence) → How it works (diagram or short numbered flow) → Key concepts (table: term, meaning) → Common tasks (links) → Who to ask.

**Status / project page**
TL;DR (on track / at risk / blocked, and why) → Done → Next → Risks and blockers (with owners) → Decisions needed.

### Format

Output Markdown: `#` title, `##` sections, tables, fenced code blocks. It pastes into Confluence, Notion, and Google Docs with light cleanup.

## Patterns

Two tiers. **Tier 1:** act on one sighting. **Tier 2:** weak alone; act only when three or more distinct Tier 2 patterns appear in the same text, or one appears repeatedly.

Leave a phrase alone inside a quotation, a code span, a proper name, or text that discusses the phrase instead of using it. Technical senses are fine: "robust estimator", "gated rollout", "key" as in API key.

### Tier 1

#### Chat wrapper
**Watch for:** `great question`, `certainly!`, `of course!`, `absolutely!`, `happy to help`, `i hope this helps`, `hope this helps`, `let me know if you have any questions`, `let me know if you'd like`, `feel free to reach out`, `would you like me to`, `want me to`, `shall i`, `should i dig`, `here's a tighter version`, `here is a revised`, `you're absolutely right`, `i hope this email finds you well`, `i wanted to reach out`, `discuss further`, `at your convenience`, `let me know your thoughts`, `please let me know`, `don't hesitate to`
**Fix:** delete the wrapper and keep the content.

#### Run-up before the point
**Watch for:** `let's dive in`, `let's break this down`, `let me break this down`, `let me walk you through`, `here's what you need to know`, `here's the thing`, `without further ado`, `to be clear`, `the short answer is`, `in this document, we`, `this document aims to`, `the purpose of this`
**Fix:** delete it and start with the point.

#### Signpost filler
**Watch for:** `it's worth noting`, `it is worth noting`, `it's important to note`, `it is important to note`, `it's important to`, `notably,`, `importantly,`, `interestingly,`, `in summary`, `to summarize`, `in conclusion`, `at the end of the day`, `when it comes to`
**Fix:** delete it. If the sentence after it matters, it stands without the signpost.

#### Staged contrast
**Watch for:** `not just`, `not only`, `not merely`, `re:\bit'?s not (?:about )?\w+[^.]{0,40}, it'?s\b`, `re:\bisn'?t (?:just )?about\b`
**Fix:** state the point directly. Keep a contrast only when the reader actually holds the belief being corrected.

#### Saying that sounds deep
**Watch for:** `at its core`, `the real question is`, `the real issue is`, `what really matters`, `the heart of the matter`, `fundamentally,`, `the reality is`
**Fix:** replace it with the specific claim.

#### Inflated significance
**Watch for:** `pivotal`, `game-changer`, `game changer`, `plays a key role`, `plays a crucial role`, `stands as a testament`, `testament to`, `paving the way`, `setting the stage`, `the future looks bright`, `a step in the right direction`, `evolving landscape`
**Fix:** keep the fact and drop the significance. End on the last concrete fact.

#### Overused AI words
**Watch for:** `delve`, `delving`, `tapestry`, `leverage`, `leveraging`, `utilize`, `utilizing`, `facilitate`, `seamless`, `seamlessly`, `meticulous`, `meticulously`, `underscore`, `underscores`, `showcase`, `showcasing`, `fostering`, `intricate`, `interplay`, `holistic`, `synergy`, `deep dive`, `comprehensive`
**Fix:** use the plain word (use, help, look at, smooth) or the specific fact.

#### Wordy stock phrases
**Watch for:** `in order to`, `due to the fact that`, `at this point in time`, `for the purpose of`, `in the event that`, `a number of`, `with regard to`, `with respect to`, `is able to`, `has the ability to`
**Fix:** to · because · now · for · if · the number, or "some" · about · about · can · can.

### Tier 2

#### Hedge stacks
**Watch for:** `could potentially`, `may potentially`, `might potentially`, `it appears that`, `it seems that`, `it seems like`, `likely related to`, `arguably`, `to some extent`
**Fix:** one hedge at most, only where the doubt is real, and say how sure you are ("probably, not confirmed").

#### Vague intensifiers
**Watch for:** `significant`, `significantly`, `substantial`, `considerable`, `robust`, `crucial`, `critical`, `key`, `valuable`, `enhance`, `enhanced`, `thorough`, `thoroughly`, `extensive`, `extensively`
**Fix:** replace with the number or the specific consequence ("p99 went from 200 ms to 2 s").

#### Time filler
**Watch for:** `moving forward`, `going forward`
**Fix:** cut it, unless it marks a real change in time ("new keys use this format going forward").

#### Long verbs for is/has
**Watch for:** `serves as`, `stands as`, `functions as`, `boasts`
**Fix:** is, are, has.

#### Vague link
**Watch for:** `associated with`, `in connection with`, `related to`, `linked to`
**Fix:** say how the two things are connected, if the source says. Otherwise keep it.

#### Dashes and decoration
**Watch for:** `—`, ` -- `, `→`, `🚀`, `✅`, `💡`
**Fix:** replace a dash with a period, comma, colon, or parentheses. Drop emoji and arrows unless the source used them.

### Not tells in workplace text

Other anti-slop guides ban these. Keep them here:

- **Passive voice** when the actor is unknown or irrelevant ("the job was retried").
- **Adverbs** that carry meaning ("roughly 40%", "only on Android").
- **Lists of three** when there really are three items.
- **Bold labels** in ticket findings (`**Cause:**`), because they are a scanning aid.

### Sources

Adapted, with changes for short workplace text, from:
- blader/humanizer, https://github.com/blader/humanizer. MIT License, Copyright (c) 2025 Siqi Chen. Severity tiers, pattern groups.
- hardikpandya/stop-slop, https://github.com/hardikpandya/stop-slop. MIT License, Copyright (c) 2025 Hardik Pandya. Phrase lists.
