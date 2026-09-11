# Modular release emails

A proposal, with a working proof of concept, for generating Avant Arte's release emails from
one brief per edition, with AI confined to a few named sentences under strict rules.

Built from the HubSpot export of 3,630 emails (September 2023 to September 2026). The
supporting analysis is in `docs/`, the proof of concept is `render.py` and `templates/`,
and `out/` holds two real campaigns re-rendered from a brief so you can compare them with
what was sent.

## The short version

1. Your emails are already modular. Every campaign sends the same sequence, every email
   has the same eight blocks, and a large share of the sentences are identical across
   campaigns. The team has been templating by hand, by cloning the last campaign.
2. Across a release, well under 10% of the words are written fresh. In the Robert Longo
   campaign rendered here, the four main emails total 863 words and 171 of them are new:
   the announcement hook, one technique sentence, the Early Access note, one card line and
   a subject line. The rest is house text, fixed sentences with names and dates dropped in,
   or reuse.
3. So the tool is mostly not an AI tool. It is a brief (the facts about the edition), a set
   of text templates that hold your locked copy, and a renderer that fills dates, names,
   counts and codes without ever getting them wrong. That alone removes most of the work
   and most of the errors.
4. AI, if you use it at all, fills three slots per release: the hook, the card lines and the
   subject hook. It gets the facts from the brief, eight of your own published examples of
   that slot, the banned list, a word cap, and it returns three candidates. A validator
   rejects anything that breaks a rule before a person sees it. A person picks or rewrites.
5. Start with zero AI. Phase 1 templates the post-purchase, last-chance, now-live and
   automated-flow emails, which have no free text at all. Phase 2 adds the announcement
   and early access with human-written slots. Phase 3 trials AI candidates for those slots
   against human-written ones.

## 1. What the archive shows

Details and counts are in `docs/01-email-taxonomy.md`. The points that matter for the design:

- **Two mechanics, two flows.** A limited edition allocated by draw (`_LE_`) runs Early
  Access → Announcement → Sustain → Last Chance → surveys → production updates. A
  time-limited edition (`_TL_`) runs Announcement → sign-up flow → Early Access → Now Live →
  Halfway → Last Chance → Edition Closed → Edition Number Confirmed → production updates.
  The sequence has not changed in eighteen months.
- **Eight blocks, always in the same order:** kicker, headline, body (three to five short
  paragraphs), CTA label, artwork cards, quote, footer tagline, and a sign-off in advisor
  emails. The export flattens HubSpot modules, and the skeleton is visible in every email.
- **The boilerplate is real and stable.** Some of the sentences that recur verbatim, with
  the number of distinct campaigns they appear in:

  | Sentence | Campaigns |
  |---|---|
  | If you have any questions, please don't hesitate to get in touch by replying to this email. | 70 |
  | This two-minute survey will guide our future collaborations and help us recommend the right artists and editions for your collection. | 57 |
  | Earlier orders will typically receive a lower edition number, with framed editions receiving lower edition numbers than unframed prints. | 47 |
  | Based on your order history and the artists you've expressed an interest in, I thought the edition would be a good fit for your collection. | 45 |
  | You can expect more updates along the way, but please don't hesitate to contact us if you have any questions. | 45 |
  | As soon as your order is on its way, you'll receive a separate email with tracking details and an estimated delivery date. | 40 |
  | Time-limited editions are available to purchase for a specified window of time – often 24 hours, 48 hours, or a week. | 20 |

- **The variation is in a few places.** The hook paragraph (who the artist is, why this
  work), the one-line artwork descriptions, the announcement subject, and the Early Access
  note. Everything else is a fixed sentence with slots: "Enter the draw for a chance to
  collect. Closes at 17:00 UK time on 29 September."
- **Hand-templating is leaking.** Twenty-five different formats for the dispatch window
  in 2026 post-purchase emails. Three different subject separators. Split words in sent
  copy (`o f Vote.org an d`, `A pril`, `1 5 September`). "Any Warhol" and "Amhed Mater" in
  subject lines. "Iconic" rising from 0.04 to 0.29 uses per email over three years.

## 2. Three kinds of text

Every sentence in a template is one of these, and the template says which.

| Kind | What it is | Who can change it | Example from the Longo announcement |
|---|---|---|---|
| **Locked** | Verbatim house text | Nobody, per release. Changing it is a pull request. | "Enter the draw for a chance to collect." |
| **Frame** | A fixed sentence with typed slots filled from the brief | The renderer, from the brief | "We're delighted to announce our latest collaboration with **Brooklyn-born artist Robert Longo** – **a new limited edition silkscreen print**." |
| **Menu** | A short list the human picks from | The human, from the list in `render.py` | Opener: delighted / proud / over the moon |
| **Bounded** | Free text under a contract: word cap, facts only, banned list | A human, or an AI plus the validator plus a human | "Longo is renowned for works that fiercely engage with social structures and mass media…" |
| **Verbatim** | Copied exactly from the brief | Nobody | The artist's quote; artwork titles |

Measured on the two rendered campaigns in `out/`:

| Email | Words | Bounded | Of which new for this release |
|---|---|---|---|
| Announcement (LE), Longo | 217 | 50% | all of it: hook, technique sentence, card line, subject |
| Early Access (LE), Longo | 299 | 27% | the note; the card line is reused |
| Last Chance (LE), Longo | 161 | 45% | nothing: hook and card line reused |
| Printing in progress, both variants | 186 | 0% | nothing |
| Now Live (TL), Crewdson | 188 | 56% | hook, card line, quote sentence |

The Sustain and deep-dive emails are the exception: they are editorial, 70% or more of the
words are bounded, and they should stay human-written. The tool can still supply their
frame, CTA and footer.

## 3. The brief

One file (or one form) per release. The principle is **facts, not copy**: the brief holds
what is true about the edition, and copy is either assembled from it or written from it.
See `briefs/robert-longo-le-26.yaml` for the full annotated example.

| Section | Fields | Used for |
|---|---|---|
| `release` | campaign code, mechanic (draw / timed / ranked auction), window, early access date and code, launch date, close date, framing code, fundraiser | internal names, subjects, every deadline sentence, the framing smart-content block |
| `artist` | name, surname, first name, the exact words after "collaboration with", debut / latest / second, partner estate or foundation, quote and attribution | opener frame, recap frame, quote block |
| `edition` | unit (print / sculpture / collectable), count, medium, size, how it is signed, numbered, technique facts | "a trio of new limited edition prints", the production sentence, footers |
| `artworks[]` | title, short title, series, facts, card line | headline, cards, "enter the draw for X, Y and Z" |
| `context` | opener choice, artist facts, subject hook, hook, Early Access note, recap | the bounded slots |
| `post_purchase` | update dates, framed and unframed ship windows, delay phrase | the whole TRNS sequence |

The `facts` lists are what make the constraints enforceable. A bounded sentence may only
contain numbers and proper nouns that appear in the facts. If the writer, human or AI,
wants to say "commissioned by the New York Times in 2002", that has to be in the facts
first. The validator checks it.

## 4. Where AI is allowed, and how it is held

**The contract** (`prompts/slot-contract.md`). The AI never sees a whole email and never
writes one. It fills one named slot: hook (45 words), card line (15 to 30 words), subject
hook (3 to 8 words), Early Access note (60 words), technique sentence (35 words), or a
delay reason (25 words). The prompt carries the facts, eight published examples of that
exact slot pulled from the archive, the banned list inline, twelve rules, and asks for three
candidates and nothing else.

**The validator** (`validate.py`). Mechanical, no AI. Run on every candidate and on the
assembled email. Blocks on: banned words and phrases, em dashes and unspaced dashes,
exclamation marks, questions, American spelling, 12-hour times, ordinal dates, GMT/BST,
"limited-edition" with a hyphen, sentences over 35 words, and any number or capitalised
name that is not in the brief's facts. Warns on: paragraphs over 60 words, "iconic" and
nine other words used more than once per email, and split words. When run on the real
Longo copy it warns that "iconic" appears three times in one email and blocks the Early
Access note for a 39-word sentence, which is the rule doing its job; loosen the cap if you
disagree with it.

**The review.** The output shows the email with bounded slots highlighted and everything
else read-only. The reviewer picks a candidate, edits it, or writes their own. Nothing
leaves without a person choosing it.

**Why this reads as yours and not as generated.** Generated copy gives itself away in the
structure it chooses, the adjectives it reaches for, the padding, and the invented detail.
Here the AI does not choose the structure, the opener, the CTA, the deadline sentence or
the sign-off. It cannot add a fact. It cannot use the 89 words and phrases on the banned list
or the eleven words you overuse. It gets 45 words at most, and it is imitating eight of your
own sentences of the same kind. What survives that is a sentence or two in your register,
which a person then approves. The rules are in `docs/02-voice-and-negatives.md`, each with
the evidence from the archive behind it.

**The recommendation is still to start without AI.** The templating removes most of the
work on its own, and the human-written slots become the example library the AI later
learns the register from.

## 5. The tool

**Prototype:** https://claude.ai/code/artifact/4155f4ed-cc63-4cff-b439-68b540568319
(private until shared from the page's share menu; source in `tool/index.html`).

It is the brief form on the left and the generated sequence on the right. Load the Robert
Longo (draw) or Gregory Crewdson (timed) brief, or start blank. Every sentence in the output
is marked as locked house text, a frame filled from your facts, or a highlighted free-text
slot. The validator runs as you type and blocks an email that breaks a rule. Each free-text
slot has a "Suggest three with Claude" button that sends the slot contract, the facts and
the published examples, and checks each candidate against the rules before you pick one.
"Copy for HubSpot" copies the email as plain text with module markers. Edits stay in your
browser; nothing is stored anywhere else. It is a proof of concept: the templates and rules
in it mirror `templates/` and `validate.py`, and would be maintained in one place in a real
build.

What is in this repository:

```
briefs/       one YAML per release: robert-longo-le-26.yaml, gregory-crewdson-tl-26.yaml
templates/    announcement-le, early-access-le, last-chance-le, now-live-tl, trns-printing
render.py     brief + template → email text, with date, count and phrase filters
validate.py   the mechanical rules
prompts/      the AI slot contract
docs/         the taxonomy of your emails, the voice rules with evidence, the brief checklist
out/          the two campaigns rendered, so you can compare with what was sent
tool/         the prototype page: brief form, generated sequence, validator, Claude suggestions
```

`templates/ig-set.txt` is the whole Instagram feed set from one skeleton (status line, substance,
edition line, action line): five status lines, three CTAs, one deadline form, three fragments,
no menus. `briefs/grayson-perry-tl-26.yaml` regenerates a real campaign with it.

Run it:

```
python3 render.py briefs/robert-longo-le-26.yaml all
python3 render.py briefs/gregory-crewdson-tl-26.yaml now-live-tl
```

Each rendered file carries the HubSpot internal name in your convention, the subject, the
preview text, and the body with module boundaries marked (`[KICKER]`, `[BODY]`, `[CTA]`,
`[CARD]`, `[QUOTE]`, `[FOOTER]`, `[SMART CONTENT]`) so it maps onto your HubSpot template
one block at a time.

How it would grow into the tool you described:

1. **Brief entry.** A form (Airtable, Notion, a small web page) that writes the YAML. The
   facts lists are the important fields; the bounded fields are optional at entry.
2. **Templates in this repo.** Plain text with Jinja tags. HubSpot's own HubL is a Jinja
   dialect, so the syntax is familiar and the locked blocks could eventually move into
   HubSpot modules. Every change to locked copy is a diff someone approves.
3. **Renderer and validator**, as here. Menus in `render.py` give controlled variation:
   add an opener to the list, never let the AI invent one.
4. **AI step**, optional, per slot, producing candidates that go through the validator.
5. **Review page** showing bounded slots highlighted. Output copied into HubSpot by module,
   or pushed through the Marketing Email API to create drafts with the right internal name.
6. **Example library.** A script over the archive that extracts, for each slot type, the
   most recent published examples. That is the few-shot material and it refreshes itself.

## 6. Rollout

| Phase | Scope | AI | What it buys |
|---|---|---|---|
| 1 | Post-purchase sequence (printing, signing, framing, dispatch, on track, delays), Last Chance, Now Live, Halfway, Edition Closed, Edition Number Confirmed, surveys, sign-up confirmation | none | These are 0% free text. Dates typed once, formats fixed, no split words, ten minutes per release instead of an afternoon |
| 2 | Announcement and Early Access, both mechanics, with human-written slots; the brief form; the example library | none | The full release runs from one brief. Writers write 170 words, not 1,500 |
| 3 | AI candidates for hook, card line, subject hook; validator; review page. Run alongside human-written for five releases and compare opens and clicks | bounded | Decide with data whether AI slots are worth keeping |
| 4 | Sustain and deep dives | checker only | Editorial stays human; the validator flags rule breaks before send |

## 7. Decisions needed from you

- **Dispatch window format.** The most common current form is `by 23 - 30 October` (103
  uses this year). `between 23 and 30 October` reads better. Pick one; the template
  enforces it.
- **Subject separators.** The pattern emerging is `Artist – …` for marketing and
  `Artist · …` for post-purchase. Confirm and it becomes a rule.
- **Announcement subjects** have two shapes: `Artist – noun phrase` and `Artist verb
  phrase` ("Yoon Hyup transforms memory into rhythm"). The template does the first. Add the
  second as a menu option if you want it.
- **The caps and the banned list.** "Iconic" once per email is the strictest call in the
  rules. The judgement-call words are listed with counts in the voice doc.
- **Advisor emails.** Insiders and outreach emails are the same body with a first-person
  opener and a sign-off. They can go through the tool with a `signed_by_advisor` field, or
  stay hand-written.
- **Who writes the brief**, and whether the facts come from the release page in your
  system rather than being retyped.
- **HubSpot integration**: paste by module first, API later.
