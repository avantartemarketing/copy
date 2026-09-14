# Product pages: could AI write them, and can they feed the campaign?

A read of `data/storyblok-product-pages.csv`, the Storyblok export: 1,232 rows, of which **415 carry a
product page description**, published June 2024 to September 2026.

Two questions were asked. The short answers are **no, not from the data we hold** and **yes, and this
is the more valuable direction**.

## 1. What a product page is

Median 127 words. 87% are three or four paragraphs. The roles are fixed by position — counted across
the 248 three-paragraph pages, which are the commonest shape:

| | what it does | evidence |
|---|---|---|
| Paragraph 1 | announces the release: the work, the artist, what kind of edition | 62% state it is an edition or a release |
| Paragraph 2 | the work, and where it comes from | 70% carry art-historical context |
| Paragraph 3 | how it was made | 70% describe the making |
| `seoDescription` | one line, 25 words | 68% open "Collect a [edition phrase] by [artist]…" |

Four structured fields sit alongside it and are already close to locked house copy:
`authentication` ("Signed by the artist. Individually numbered."), `mediumDescription` ("9 colour
silkscreen with matte varnish seal on Somerset Tub Sized Radiant White 410gsm paper"),
`framingDescription`, `releaseNote`.

## 2. Could AI write them?

**Not from anything we currently hold.** The page's substance is research, and the research is not in
the export.

Counting proper nouns and dates that appear in the description but in **no** structured field on the
same row: **median 8 per page, 17 at the 90th percentile, and exactly one page of 415 has none.**
What they are:

| | pages | |
|---|---|---|
| when the original work was made | 58% | "Originally created in 2000" |
| a named series or body of work | 36% | *Men in the Cities*, *Dream House*, the Big Girl Paintings |
| the artist's life, training or place | 25% | "photographs of the artist's friends… on the roof of his New York studio" |
| a museum, gallery or exhibition | 20% | Monnaie de Paris, the Guggenheim retrospective, Reina Sofía |
| a cultural reference | 15% | "the final scenes of Fassbinder's film *The American Soldier* (1970)" |
| a previous Avant Arte release | 3% | "the first being our 2025 release of *Untitled (Eric)*" |

None of that can be invented, and `validate.py` already blocks any proper noun or number that is not
in the brief's facts. So the bottleneck is not the writing. It is that **someone has to do the
reading first**, and that is the expensive half.

**What it would need, to write one.** The same shape as a release brief, with one section added:

```
artist        name, nationality or base, one line on the practice
work          title, year of the original, medium of the original,
              the series or body of work it belongs to
provenance    where the original is, or was shown; who owns it        ← the new part
resonance     what the work refers to, or what was happening around it ← the new part
edition       unit, edition size, what is signed and numbered
making        the technique in full, from mediumDescription
lineage       our previous releases with this artist or from this series
```

`provenance` and `resonance` are the two the release brief does not carry, and they are where the
second paragraph comes from. Give AI those and the page is a slot-filling job against a fixed
three-paragraph frame — the same bounded-text arrangement the campaign already uses, and the
structure is tighter here than it is for the emails.

Worth saying plainly: at that point AI is writing around 127 words from a research note that took
longer to assemble than the 127 words take to write. The gain is consistency, not speed.

## 3. Can they feed the campaign? Yes, and this is the better direction

The product page and the campaign are describing the same things in the same order. Testing the
three releases where both exist, by word overlap between each campaign fragment and each paragraph:

| release | hook lands in | making lands in | card line lands in |
|---|---|---|---|
| Robert Longo, *Untitled (Sandy)* | paragraph 3 of 4 — 45% | paragraph 4 of 4 — 57% | paragraph 2 |
| Gregory Crewdson, *Dream House* | paragraph 2 of 3 — 83% | paragraph 2 of 3 — 36% | paragraph 3 |
| Glenn Ligon, *Stranger* | paragraph 2 of 3 — 48% | paragraph 3 of 3 — 33% | paragraph 2 |

The hook is a compression of the work paragraph. The making line is a compression of the making
paragraph. The card line and the `seoDescription` do the same job in the same register.

So the flow is:

```
product page (written by a person, ~127 words)
        │
        ├── paragraph 2  ──▶  hook      (2–3 sentences, reaches 16 slots)
        ├── paragraph 3  ──▶  making    (one sentence)
        ├── seoDescription ─▶  card line (15–30 words)
        └── mediumDescription, authentication ─▶ features, technique facts
```

This is a far safer use of AI than writing the page. Everything it produces is a shortening of text
a person has already written and approved, so it cannot invent a fact: the source text is the facts
list. `validate.py` needs no change to police it — the page becomes the fact corpus for the release.

It also fits what the tool already does. The write screen asks for the hook, the making line and a
line per card. If the product page exists first, those three arrive as suggestions to accept or
rewrite rather than as blank fields.

## 4. One thing this export cannot tell us

The file is two disjoint halves. The 415 rows with copy have **no** `launchDate`, `price`,
`editionSize` or `releaseType`; the 727 rows with those fields have no copy. There is no shared
`ga_path`, `url`, `shopify_product_id` or `subscriptionTag` between the two sets — zero overlap on
every key.

So this cannot answer **when the page is written relative to the campaign**, and the whole "page
feeds the campaign" flow depends on the page existing first. An export that joins the copy to the
launch dates would settle it.
