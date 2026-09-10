# What the emails are made of

Source: the HubSpot export of 3,630 emails, 12 September 2023 to 10 September 2026, across
264 campaigns. Figures below count sent emails (PUBLISHED or AUTOMATED) unless stated.

## 1. Naming already encodes the structure

Internal names follow `DDMMYY_TYPE_CampaignCode - Sub-type (variant)`:

| Type code | Meaning | Sent since 2023 |
|---|---|---|
| `CUS` | customer segments (past purchasers, sign-ups, exclusions) | 1,191 |
| `TRNS` | post-purchase production updates | 347 |
| `INS` | Insiders, advisor-signed | 302 |
| `GEN` | whole list | 226 |
| `AUT_…` | automated flows, cloned per campaign | ~1,200 |

Campaign codes are `ArtistSurname_Work_YY`, with `_LE_` for a limited edition allocated by
draw and `_TL_` for a time-limited edition. The tool should generate the internal name, the
subject and the preview text, not just the body.

## 2. Two mechanics, two flows

The same campaign always produces the same sequence. Below is what actually went out for
recent releases (Robert Longo, Salvador Dalí, Hank Willis Thomas for LE; Gregory Crewdson,
Ai Weiwei *Guardian*, Mickalene Thomas for TL).

### Limited edition, allocated by draw (`_LE_`)

| Step | Email | Type | When | Voice |
|---|---|---|---|---|
| 1 | Early Access (LE) | CUS, INS | 1 to 4 days before announcement, 48-hour window | hybrid: "we're offering… I thought" |
| 2 | Announcement (LE) | GEN, plus CUS clones per segment | launch day | brand "we" |
| 3 | Sustain (LE) | CUS | about a week later; behind the editions, Q&A, video | brand "we", editorial |
| 4 | Advisor outreach to entrants | CUS/TRNS | optional, days before close | advisor "I", signed |
| 5 | Last Chance (LE) | CUS | 24 hours before the draw closes | brand "we" |
| 6 | Surveys: first-time, repeat, non-purchaser | AUT | after the draw | advisor "I" (first-time), brand (others) |
| 7 | Printing → Signing → Framing → Preparing for dispatch → On track → delay variants → "Let us know everything is ok" | TRNS | production, one email per stage, framed and unframed variants | brand "we", plain |

### Time-limited edition (`_TL_`)

| Step | Email | Type | When | Voice |
|---|---|---|---|---|
| 1 | Announcement (TL Non-flow) | GEN | about three weeks before launch; "Launching 17 March", register for updates | brand "we" |
| 2 | Sign-up flow: Signup Confirmation → Welcome → TL Education → Deep dive 1 → Deep dive 2 → Framing deep dive | AUT | triggered by registration | brand "we"; deep dives editorial |
| 3 | Early Access (TL Flow) and Early Access for past purchasers | AUT, CUS | 24 hours before launch | brand "we" |
| 4 | Now Live (TL Non-flow) and Now Live (TL Flow) | GEN, AUT | the moment the window opens | brand "we" |
| 5 | Halfway / 5 days to go / 3 days to go | AUT | inside the window; headline, CTA, one paragraph | brand "we" |
| 6 | Last Chance (TL Flow) | AUT | hours before close | brand "we" |
| 7 | Edition Closed → Surveys → Edition Number Confirmed | AUT | after close | brand "we" |
| 8 | Post-purchase TRNS sequence, as above | TRNS | production | brand "we", plain |

The automated flow steps are already templates in practice: each campaign clones the previous
one and changes the artist, the work, the dates and one or two sentences. They belong in the
same brief as everything else so the dates and names are typed once.

## 3. Every marketing email is the same eight blocks

The export flattens the HubSpot modules, and the same skeleton appears every time:

1. **Kicker**, 2 to 6 words: `Enter the draw`, `Launching 17 March`, the artist's name.
2. **Headline**, one line: the artwork title, `A trio of prints by Salvador Dalí`, `48 hours, starting now`.
3. **Body**, three to five paragraphs, median 24 words each, sentences median 18 words:
   1. the announcement sentence (a frame),
   2. the hook: who the artist is and why this work (the one place with real writing),
   3. production and edition details (assembled from facts),
   4. the mechanics and deadline (a frame),
   5. in personal emails, the questions line (locked).
4. **CTA label**, from a fixed set: `Enter the draw` (208 uses since 2025), `Buy now` (81), `Unlock early access` (51), `Discover the collaboration` (67), `Buy a print` (99).
5. **Artwork cards**: title plus one sentence of 15 to 30 words, one per work.
6. **Quote block**: the artist's words verbatim, then the attribution.
7. **Footer tagline**, one line: `Especially for you.` (162), `There's still time to add a print to your collection` (48), `Collect a limited edition signed print`, `24 hours to go`.
8. **Sign-off**, advisor emails only: `Best regards, Sam` / `Art Advisor at Avant Arte`.

Post-purchase emails are three blocks: headline, body, footer `An update on your order` (278 uses).

## 4. What is locked, what is a frame, what is written

For each email in the two flows, this is where the words come from today, judged from the
last eighteen months of sends. "Locked" is verbatim house text. "Frame" is a fixed sentence
with typed slots. "Bounded" is free text that has to be written for each release.

| Email | Locked | Frames | Bounded slots | Bounded share of words |
|---|---|---|---|---|
| Announcement (LE) | kicker, CTA | opener, deadline, production sentence, headline, footer | hook (1 to 2 sentences), card line per work, subject hook, technique sentence when no edition size is published | about 50% |
| Announcement (TL) | kicker, CTA | opener, "launches D Month for 48 hours", register line | hook, card lines, subject hook | about 50% |
| Early Access (LE) | greeting, the four mechanics paragraphs, questions line, footer | opener, code line, framing offer | one note of 1 to 3 sentences on why this release; card lines reused | about 25% |
| Early Access for Insiders | as above plus sign-off | opener | one sentence | about 15% |
| Sustain / deep dives | CTA, footer | opener, deadline | the whole body | 70% or more; keep human |
| Now Live (TL) | CTA | opener, deadline, headline | hook, card lines, optional quote sentence | about 55% |
| Halfway / days to go | everything | headline count | none | 0% |
| Last Chance (LE and TL) | CTA, headline, deadline line, footer | recap opener | none new: the Announcement hook and card lines are reused | 0% new (45% reused) |
| Edition Closed, Edition Number Confirmed, sign-up confirmation, TL education | everything | names, dates, sizes | none | 0% |
| Surveys (three) | everything | artist name | none | 0% |
| Printing, Signing, Framing, Preparing for dispatch, On track | everything | artist, framed or unframed, dates | none | 0% |
| Delay, Failed QC, New estimated dispatch | everything except one sentence | dates, "a couple of weeks" | one sentence giving the reason | about 10% |

Measured on the rendered Robert Longo campaign in `out/`: the four templated emails run to
863 words, of which 171 are written fresh for the release (hook 55, technique sentence 30,
Early Access note 62, card line 18, subject hook 6). Everything else is locked, framed or
reused. Across the full campaign of roughly fourteen emails, including the surveys and the
post-purchase sequence, fresh copy is well under 10% of the words, and it sits in three
places: the Announcement hook, the artwork card lines and the Early Access note. That is
where the writing effort, and any AI, should go.

## 5. Things the export shows that a template would fix

- **Date formats in post-purchase emails**: 25 different shapes for the dispatch window in
  2026 alone (`by 23 - 30 October`, `between 14 and 21 September`, `by 09 – 16 November`,
  `by 24 April - 01 May, 2026`, `by 08 - 1 5 September`, `28 August - 05 Septemebr`). One
  filter function ends that.
- **Subject separators**: en dash (625), hyphen (314) and middle dot (315) are all in use
  since mid-2025. The pattern that is emerging is `Artist – …` for marketing and
  `Artist · …` for post-purchase; the tool would make it a rule.
- **Split words in sent copy**: `o f Vote.org an d`, `Howeve r`, `collabora tion`,
  `A pril`, `1 5 September`. These are HubSpot editor artefacts, so the check belongs in
  the tool regardless of who writes the copy.
- **Typos in subjects**: `Any Warhol`, `Amhed Mater`. The artist name should be typed once.
- **Overuse creeping in**: "iconic" went from 0.04 per email in 2023 to 0.29 in 2026;
  "delighted" from 0.02 to 0.36. Menus and caps keep this in check.
- **Preview text is almost always empty.** A frame can fill it for free.
