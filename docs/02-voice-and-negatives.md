# House voice, and what it never does

Derived from the 836 marketing emails sent since January 2025 (153,000 words). Every rule
below is either something the corpus does almost without exception, or something it almost
never does. Where a rule is a judgement call, the evidence is given so you can overrule it.

The rules apply to **bounded text** (the hook, card lines, subject hook, Early Access note,
technique sentence, delay reason). Locked house text is exempt by definition. `validate.py`
enforces the mechanical ones.

## 1. Shape

| Rule | Evidence |
|---|---|
| Sentences of 18 words on average, never more than 35 | median 18, 90th percentile 31 |
| Paragraphs of about 25 words, never more than 60 | median 24, 90th percentile 50 |
| Three to five paragraphs, no bullet lists in the body | no bulleted body copy in the corpus |
| One idea per paragraph: who the artist is, what the work is, how it was made, how to get it | every announcement follows this order |
| Reuse, don't rewrite: Last Chance repeats the Announcement hook | 122 last-chance emails, all recaps |

## 2. Punctuation and typography

| Rule | Evidence |
|---|---|
| The house dash is a spaced en dash ( – ). No em dashes, no unspaced dashes | 1,020 spaced en dashes vs 244 em dashes; the em dashes are almost all in the advisor-written Monthly Preview |
| No exclamation marks | 0.1 per email, nearly all in two locked lines ("Great choice!", "and we will!") |
| No questions in the body. Questions belong only in survey subject lines ("Any feedback?") | 0.07 per email |
| No emoji in the body. The only emoji anywhere is 🔓 in Early Access subjects | 0 in bodies |
| Curly quotes for quotations, single quotes for series names in subjects (`'Dream House'`) | consistent since 2025 |
| No colons for drama, no ellipses, no ALL CAPS, no bold for emphasis | none in the corpus |

## 3. Spelling and formats

| Rule | Example |
|---|---|
| British spelling | colour, colourway, realise, centre, grey, programme |
| Times: 24-hour, always followed by "UK time" | `17:00 UK time`, never 5pm, never GMT or BST (312 vs 2) |
| Dates in marketing emails: day then month, no ordinal, no year | `29 September`, never 29th, never 2026 |
| Dates in post-purchase emails: two-digit day | `by 23 - 30 October`, `by 26 October - 03 November` |
| Weekday only in Now Live deadlines | `Thursday, 02 July` |
| Durations in words or figures as the house does | `48 hours`, `24 hours`, `one week`, `a trio of`, `an edition of 400`, `20-colour silkscreen`, `22-karat` |
| `limited edition` without a hyphen, `Make-Ready` with one, `pre-order`, `silkscreen`, `colourway`, `artwork` | 99% consistent |
| Artist's full name on first mention, surname alone after that; single-name artists stay as they are (LY, Parra, Pejac, Backside works.) | consistent |

## 4. Vocabulary the house uses

Descriptors that appear regularly and are safe: signature, seminal, landmark, defining,
celebrated, renowned, acclaimed, striking, bold, luminous, enigmatic, pioneering,
groundbreaking, legendary, beloved, rare, bespoke, faithfully, carefully, closely, archival,
hand-finished, individually numbered, signed by the artist.

Nouns: collector (never customer or shopper), edition, artwork, print, sculpture,
collectable, collaboration, release, launch, draw, window. "Collect" is the verb in body
copy; "Buy now" is allowed as a CTA label for timed editions.

Capped at once per email, because they are drifting into tics: iconic (260 uses since 2025,
rising every year), truly, unique, meticulous, very, celebrated, renowned, landmark, seminal,
striking.

Openers are a menu, not a choice the writer makes each time: "delighted to announce"
(102), "delighted to share" (96), "excited to offer" (79), "proud to present" (6),
"over the moon" (5). Rotate them.

## 5. Vocabulary the house never uses

The banned list in `validate.py`. Counts are hits in 3,327 sent emails over three years.

**Never appeared, or three times or fewer** (safe to ban outright): hurry, act now, act
fast, grab, snag, shop now, get yours, secure yours, treat yourself, last call, final hours,
ends soon, selling fast, going fast, almost gone, while stocks last, limited time offer,
appreciate in value, elevate, unleash, delve, embark, journey through, effortlessly, nestled,
must-have, prestigious, world-class, cutting-edge, game-changing, look no further, picture
this, perfect for, the perfect gift, what are you waiting for, excitingly, we hope you'll
agree, in a world where, it's not just.

**Used, but only in ways a template makes unnecessary** (ban in bounded text): "don't miss
out" and "miss out" (36, almost all advisor outreach), "exclusive offer" (7, old advisor
emails), "own a piece of" (8), "one-of-a-kind" (10), "truly special" (4), "as you know" (4).

**Used in 2023 to 2024 and since retired** (ban): "thrilled to" (85 uses, now 0.01 per
email), "we're thrilled" (38), "excited to announce" (22).

**Judgement calls** (banned in the validator; overrule if you disagree): "not only" (20),
"showcases" (18), "tapestry of" (16, one of them about an actual tapestry), "at the heart
of" (13), "seamless" (12, mostly the survey), "stunning" (10), "imagine" (10), "amazing"
(8), "mesmerising" (8), "realm" (7), "testament to" (6), "in today's" (6), "unmissable"
(5), "whether you're" (5), "dive into" (5), "captivating" (4).

**Wrong nouns**: product, item, merch, drop, raffle, lottery, giveaway, customer, shopper.
("customer cancellations" survives in one locked sentence; that is fine because locked text
is exempt.) Never talk about value, investment or resale. The corpus never does.

## 6. Constructions to refuse

These are the tells that make copy read as generated. None of them appear in the house
emails at any frequency.

- Three adjectives in a row ("bold, luminous and striking"). One adjective per noun.
- "Not just X, but Y" and "from X to Y" sweeps.
- A sentence that restates the previous one.
- A closing line that summarises ("A must for any collection").
- A rhetorical question as an opener.
- Sentence fragments for drama. Every sentence has a verb.
- Starting consecutive sentences with the same word.
- Claims about the reader's feelings ("you'll love", "you won't want to miss").
- Any fact not in the brief: no invented years, dimensions, exhibition history, awards,
  comparisons to other artists, or superlatives ("first ever", "most celebrated") unless the
  brief states them.
- Any change to an artwork title, an artist's name, or a quotation.

## 7. Voice by email

- **Brand emails** (Announcement, Now Live, Last Chance, post-purchase): "we". Plain, warm,
  factual. Apologies in delay emails are direct: "We're very sorry for this slight delay."
- **Advisor emails** (Insiders, outreach, first-time survey, draw results): "I", first name
  sign-off, "Art Advisor at Avant Arte". Sam, Curtis, Sofiya.
- **Early Access (LE)**: deliberately hybrid. "We're offering a small group of collectors a
  first look… I thought the edition would be a good fit for your collection." This reads as
  a quirk but it has been stable for two years. Keep it.
