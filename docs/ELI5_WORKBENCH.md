# DESi Workbench - ELI5

DESi Workbench is like a lab-notebook checker for texts.

You give it a paper or some text. It reads it and asks three simple
questions:

1. **Which claims are being made?**
   It finds the sentences that assert something — "we propose…", "we
   show…", "this is the first…", "our method solves…" — and sorts them
   into kinds (main claim, method, evidence, result, limitation, novelty,
   generalization).

2. **Which evidence is missing?**
   For strong claims it checks whether there is any inline support nearby
   (a number, a table/figure, a citation). If a big claim stands alone
   with no support, it marks an **evidence gap**.

3. **Where does the text sound stronger than the data can carry?**
   Words like "novel", "first", "significant", "robust", "solves",
   "state of the art" are flagged as **overclaim risks** — especially
   when there is no comparison or statistics to back them up.

It also points out **reproducibility risks** (no code link, no data, no
baselines, no hyperparameters, vague dataset, metrics without a method),
draws a little **claim graph**, and writes a **report** you can download.

## What it is NOT

- It is **not** a peer reviewer. It never says "accept" or "reject".
- It does **not** decide what is true.
- It only reads the text you give it — no internet, no magic.

Its only verdict is: **REVIEW_ASSISTANCE_ONLY** — "here are things a human
reviewer might want to look at."

## Why is it careful?

Because being *transparently simple* is better than being *magically
wrong*. Every flag comes from a rule you can read. A human always makes
the final call.
