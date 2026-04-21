# poker_ai - Current State vs Final Direction Gap Map

## Bottom line

This project is already on a strong path.

It is **not** just a parser anymore.
It is already a real **hand-history warehouse + postflop tagging + study-report system**.

The right next move is **not** to restart.
The right next move is to shift the center of gravity from:

- parser and structural tagging only

toward:

- **ICM-aware tournament context**
- **benchmarking / evaluation**
- **leak ranking**
- **deeper study workflows**

That keeps the work you already did and nudges it toward the bigger solver-adjacent MTT study vision.

---

## What is already genuinely strong

## 1. The data foundation is real

Current repo state already supports:

- raw hand-history storage
- parsed-output storage
- tournament summary import
- coverage reporting
- batch execution over matched HH/summary pairs
- optional PKO metadata sidecars

Observed corpus state:

- raw files: **242**
- parsed files: **26**
- summary files: **157**
- metadata files: **1**

Latest summary coverage report shows:

- hand-history files scanned: **237**
- summary files available: **150**
- matched tournaments: **150**
- matched hand histories: **200**
- unmatched hand histories: **32**
- hand histories missing tournament ID: **5**

That is a solid base for a real database-driven study tool.

---

## 2. The postflop taxonomy work is already serious

The project already has:

- a separate `postflop_trees.py` source of truth
- structured family tagging
- board-bucket tagging
- turn seed mapping
- river placeholder mapping
- coverage and audit scripts

Latest study-surface report shows:

- files scanned: **200**
- hands scanned: **13,689**
- tagged flop hands: **8,381**
- hands with reachable turn family: **7,448**
- hands with reachable river family: **7,448**

That means you already have a meaningful postflop study surface, not just isolated hand outputs.

---

## 3. The first tendency layer already exists

The `report_postflop_hero_flop_actions.py` layer is important.

It means the system is already starting to ask:

- what does Hero actually do?
- in which family?
- on which board bucket?
- in which immediate decision context?

Latest hero-flop-action report shows:

- tagged flop hands: **8,381**
- hands with hero flop decision: **1,511**

That is the beginning of a real self-modeling engine.

---

## 4. Tournament pressure work has already started

There is already meaningful progress toward tournament-awareness:

- summary-backed field-size signals
- broad stage / pressure hinting
- PKO bounty sidecar support
- bounded preflop nudge logic

This is good.

But it is still a **heuristic pressure layer**, not a true ICM layer.

That distinction matters for deciding what to build next.

---

## What is still missing for the bigger end-state

## 1. Exact tournament-context layer

This is the biggest missing piece.

Right now the system has:

- broad stage bands
- rough pressure hints
- field-size-aware approximations

What it still needs for a much stronger MTT engine:

- exact or better-estimated players-left context
- payout structure capture
- finish-place normalization
- tournament-type normalization
- buy-in / format metadata normalization
- better FT / bubble / pay-jump state derivation
- stronger PKO state capture

Without this, postflop study can still be useful, but solver-adjacent **ICM-aware evaluation** stays limited.

**Recommendation:** this should be the next major foundation layer.

---

## 2. A benchmark engine

The current system measures structure and Hero frequencies well.

What it does **not** yet do in a strong way is answer:

- what should Hero do here?
- how far is Hero from a baseline?
- is this a high-EV leak or just a stylistic difference?

To move toward the final vision, the project needs a benchmark layer with:

- preflop baseline packs
- ICM-aware jam/call/reshove baselines
- curated postflop node baselines
- optional trusted-reference comparisons
- confidence bands on evaluation

This does **not** require a full solver.
But it does require a deliberate baseline system.

---

## 3. Leak ranking, not just leak description

Right now reports are descriptive.
That is valuable.
But the bigger tool should become prescriptive about priority.

It should be able to rank findings by:

- frequency
- likely EV cost
- ICM sensitivity
- recurrence
- strategic importance

That is the difference between:

- “interesting report”

and

- “real study engine”.

---

## 4. Deeper action-frequency layers

The current Hero layer focuses on the **first flop decision**.
That is a good first wedge.

The next layers should extend into:

- turn follow-through frequencies
- river follow-through frequencies
- delayed cbet patterns
- probe / stab / donk patterns
- size selection frequencies
- raise-vs-call-vs-fold splits in deeper nodes

This is one of the cleanest next upgrades because it builds directly on what already exists.

---

## 5. Study workflow layer

The current reports are structurally useful, but the final tool should be more workflow-native.

It should make it easy to do things like:

- show the top 10 leak nodes this week
- show the most expensive ICM-sensitive preflop mistakes
- generate 25 example hands for one node
- compare this month vs last month
- show all examples where Hero faced a high-pressure reshove at 12 to 18 BB

This is mostly product layering on top of the data and reports already built.

---

## 6. Knowledge layer, carefully used

The repo can benefit from external poker knowledge, but this should be done carefully.

High value uses:

- curated strategy notes
- structured concept summaries
- trusted spot baselines
- definitions and explainer material

Lower value uses:

- unstructured mass ingestion of random videos
- vague blog-summary accumulation without tying it back to node families

**Recommendation:** external knowledge should be attached to your internal node taxonomy, not collected as a disconnected library.

---

## The big-picture nudge I recommend

## Do not rebuild.
## Reframe.

The right framing now is:

> `poker_ai` is becoming an **ICM-aware personal MTT study operating system**.

That means the build priority should become:

1. **truthful tournament context**
2. **benchmarking**
3. **leak ranking**
4. **deeper frequency layers**
5. **study workflow UX**

The parser and postflop-family work should now serve that direction, not remain the center of the project.

---

## Recommended next milestones

## Milestone A. Tournament context normalization

Build or strengthen:

- tournament metadata schema
- payout / finish / field-size ingestion
- better summary normalization
- exact or best-effort ICM context fields
- stronger PKO context schema

This is the highest-value foundation step.

## Milestone B. ICM-aware preflop benchmark layer

Build a first serious benchmark engine for:

- open-jams
- call-offs
- reshoves
- thin continues under pressure
- bounty-adjusted preflop spots

This is where the project can become solver-adjacent fastest.

## Milestone C. Postflop tendency deepening

Extend from first-flop decision into:

- turn follow-through
- river follow-through
- delayed cbet lines
- stab/probe lines
- size frequencies

## Milestone D. Leak prioritization engine

Add ranking logic so the system can say:

- these are the highest-frequency leaks
- these are the highest-ICM-risk leaks
- these are the best study targets right now

## Milestone E. Study products

Turn outputs into human workflows:

- node packs
- weekly leak reports
- example-hand bundles
- progress comparisons over time

---

## My honest assessment

You already built the hard boring part unusually well:

- structure
- taxonomy
- corpus coverage
- reporting discipline

That is good news.

The risk now is not “the project is weak.”
The risk is **staying too infrastructure-heavy for too long**.

So the best nudge is:

- keep the structure
- stop thinking of this as mainly a parser project
- start treating it as a **benchmark + leak-finding + study-product system**

That is the path most aligned with your long-term vision.
