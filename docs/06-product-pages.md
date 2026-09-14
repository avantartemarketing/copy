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

The product page and the campaign describe the same things. The material is there. **What is not
there is a paragraph-to-fragment map** — an earlier draft of this note claimed one, and the three
releases where both exist do not support it.

**The hook sometimes sits in one paragraph and sometimes is spliced from two.** Word overlap between
the hook and the best single paragraph, against the hook and the whole page:

| release | best single paragraph | whole page | |
|---|---|---|---|
| Gregory Crewdson, *Dream House* | 82% | 85% | one paragraph, cleanly |
| Glenn Ligon, *Stranger* | 48% | 54% | mostly one paragraph |
| Robert Longo, *Untitled (Sandy)* | 42% | 73% | **spliced**: the figure from paragraph 2, "only the second time it has been editioned" from paragraph 3 |

**The making line often has no paragraph to come from.** Crewdson's page has no making paragraph at
all — its third paragraph is atmosphere ("Meticulous, still and unsettling…"), and the email's making
line was written from the facts in paragraph 2 plus house copy. Across all 415 pages:

| | pages | |
|---|---|---|
| mentions how it was made, anywhere on the page | 78% | |
| …and it is in the final paragraph | **51%** | so half the time the position is wrong |
| `mediumDescription` filled in | 49% | the other source |
| one or the other | 85% | |
| **neither — nothing to write a making line from** | **14%** | 62 pages |

So the flow is not a map. It is: give the model the whole page and the technique fields, and let it
select.

```
product page (written by a person, ~127 words)  ─┐
mediumDescription, authentication               ─┤──▶  hook      (2–3 sentences, 16 slots)
                                                 │      making    (one sentence, absent 14% of the time)
                                                 └──▶  card line (15–30 words)
```

`seoDescription` is the exception and is a true one-to-one: it does the card line's job in the card
line's register, on every page that has a description.

This is a far safer use of AI than writing the page. Everything it produces is a shortening of text
a person has already written and approved, so it cannot invent a fact: the source text is the facts
list. `validate.py` needs no change to police it — the page becomes the fact corpus for the release.

The 14% with no making detail anywhere are the case to design for. There the model should say it has
nothing rather than write around the gap, and the writer fills that one field by hand.

It also fits what the tool already does. The write screen asks for the hook, the making line and a
line per card. If the product page exists first, those three arrive as suggestions to accept or
rewrite rather than as blank fields.

## 4. When a release has several artworks

On Storyblok a page is per product, so a three-print release has three pages. Diffing the siblings
paragraph by paragraph:

| release | paragraph 1 | paragraph 2, the work | paragraph 3 | SEO line | medium |
|---|---|---|---|---|---|
| Ligon, two prints | identical | 79% similar: the title swapped | identical | identical | **differ** |
| Dalí, three prints | identical | 8% similar: written per work | 45%: provenance per painting | per work | identical |
| Crewdson, six prints | identical | identical | identical | identical | identical |

So the siblings are edits of one page. The announcement and the authentication are the release's;
the work paragraph, sometimes the provenance, the SEO line and even the medium are the artwork's.
The tool keeps them that way: the first artwork's page is the release's page and the others start as
copies of it, with a line saying what has been changed ("Differs from the first artwork's page in
paragraph 2") or that nothing has ("Identical … so its card line would have to be written by hand").

That last case is Crewdson: six prints, six identical pages, nothing to draw a per-card line from.
The suggestion returns those cards empty and says why.

**Ligon's mediums differ, and the email did not know.** *Untitled (White on White)* is a 26-layer
silkscreen; *Untitled (Black on Black)* is printed in 5 layers. The making line that went out says
"a 26-layer silkscreen" for the edition, which is true of one print. With the mediums held per
artwork, the suggestion prompt is told when they differ and that the one making line must be true
of every artwork, or come back empty.

## 5. One thing this export cannot tell us

The file is two disjoint halves. The 415 rows with copy have **no** `launchDate`, `price`,
`editionSize` or `releaseType`; the 727 rows with those fields have no copy. There is no shared
`ga_path`, `url`, `shopify_product_id` or `subscriptionTag` between the two sets — zero overlap on
every key.

So this cannot answer **when the page is written relative to the campaign**, and the whole "page
feeds the campaign" flow depends on the page existing first. An export that joins the copy to the
launch dates would settle it.
