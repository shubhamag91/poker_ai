# Project Plan

## Goal

- Define what the poker AI should do.

## Inputs

- Hand histories
- Reference materials
- Strategy notes

## Outputs

- Parsed hands
- Analysis summaries
- Models / heuristics / reports
- A growing poker hand-history database that can later support self-tendency and pattern analysis

## Milestones

- [ ] Collect hand histories
- [ ] Keep importing older PokerCraft histories plus future hands into the repo so the sample keeps compounding
- [ ] Build parser pipeline
- [x] Finish preflop and flop coverage before starting the turn layer
- [x] Expand the remaining complex preflop path types
- [x] Deepen the coarse complex flop families into real flop trees before starting turn
- [ ] Keep 4-plus player postflop buckets deferred for now, with a reminder to revisit them after the 2-way and 3-way flop layers are more complete
- [x] Complete the first conservative river-side pruning pass across the current river placeholder families
- [x] Build the first study-oriented postflop surface report on top of the family / board-bucket / turn-family / river-family tagging layer
- [x] Add the next study layer that measures actual hero action frequencies against the tagged family / board-bucket / turn-family / river-family surface
- [ ] Extend the hero-action study layer beyond the first flop decision into deeper line-frequency and sizing reports
- [ ] Define feature extraction
- [ ] Build first evaluation loop
- [ ] Add future database-analysis tooling for Mose's own tendencies and recurring leaks
- [ ] Test on real sessions
