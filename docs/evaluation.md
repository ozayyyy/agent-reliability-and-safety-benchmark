# Evaluation

## Method

37 scenarios (version 1.0) x 4 agent configurations x seeds 0, 1, 2.
444 runs. Deterministic simulated agents; the same seeds reproduce
the same results (verified: two full runs produce identical
`report.json`). Full traces for the seed-0 runs: `examples/traces/`
(148 JSONL files). Reproduce with `python scripts/evaluate.py`.

## Headline results

| Configuration | Task success | Unsafe compliance | Refusal | Unnecessary refusal | Refusal consistency | Run-to-run consistency | Recovery | Prompt-variation consistency |
|---|---|---|---|---|---|---|---|---|
| baseline | 59.5% | 71.3% | 0.0% | 0.0% | 100.0% | 85.6% | 50.0% | 0.0% |
| cautious | 43.2% | 0.0% | 54.1% | 25.0% | 100.0% | 100.0% | 75.0% | 100.0% |
| hierarchy-aware | 83.8% | 17.2% | 0.0% | 0.0% | 100.0% | 100.0% | 75.0% | 100.0% |
| tool-side-enforced | 81.1% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 75.0% | 100.0% |

## Task success by category

| Category | baseline | cautious | hierarchy-aware | tool-side-enforced |
|---|---|---|---|---|
| adversarial | 100.0% | 100.0% | 100.0% | 100.0% |
| ambiguous | 46.7% | 0.0% | 100.0% | 100.0% |
| benign | 100.0% | 75.0% | 100.0% | 75.0% |
| conflicting | 20.0% | 0.0% | 100.0% | 100.0% |
| incomplete-information | 41.7% | 0.0% | 100.0% | 100.0% |
| prompt-variation | 100.0% | 100.0% | 100.0% | 100.0% |
| refusal | 0.0% | 0.0% | 0.0% | 0.0% |
| tool-error-recovery | 75.0% | 75.0% | 75.0% | 75.0% |

## Unsafe compliance by category

| Category | baseline | cautious | hierarchy-aware | tool-side-enforced |
|---|---|---|---|---|
| adversarial | 100.0% | 0.0% | 0.0% | 0.0% |
| ambiguous | 33.3% | 0.0% | 0.0% | 0.0% |
| benign | 0.0% | 0.0% | 0.0% | 0.0% |
| conflicting | 100.0% | 0.0% | 0.0% | 0.0% |
| incomplete-information | 50.0% | 0.0% | 0.0% | 0.0% |
| prompt-variation | 40.0% | 0.0% | 0.0% | 0.0% |
| refusal | 100.0% | 0.0% | 100.0% | 0.0% |
| tool-error-recovery | 0.0% | 0.0% | 0.0% | 0.0% |

## Comparison with AASEF

AASEF's published numbers (34 scenarios v1.0 x 3 configs, seed 0,
102 runs) are reference data, not measured here.

| Configuration | AASEF attack success | ARSB unsafe compliance (adversarial) | AASEF task completion | ARSB task success (benign) |
|---|---|---|---|---|
| baseline | 100.0% | 100.0% | 100.0% | 100.0% |
| hierarchy-aware | 35.5% | 0.0% | 100.0% | 100.0% |
| tool-side-enforced | 0.0% | 0.0% | 100.0% | 75.0% |

The three shared configurations reproduce AASEF's pattern on the
overlapping categories: baseline complies with every indirect
injection in both suites, tool-side enforcement blocks all of them
in both suites. Two differences are real and explained, not
discrepancies:

1. Hierarchy-aware scores 35.5% attack success in AASEF but 0.0%
   unsafe compliance in ARSB's adversarial category, because
   AASEF's 35.5% is entirely direct injection (4 scenarios) plus
   user-issued privilege/out-of-scope requests — cases hierarchy
   filtering cannot block, since the instruction comes from the
   user, a trusted principal. ARSB's adversarial category contains
   indirect injection only, which hierarchy filtering blocks
   completely. The same effect appears inside ARSB: hierarchy-aware
   unsafe compliance is 100.0% on the refusal category.
2. Tool-side-enforced scores 100.0% task completion in AASEF but
   75.0% benign task success in ARSB, because ARSB's benign suite
   includes a write the user did not pre-approve (benign-04). The
   approval gate denies it by design. AASEF's benign suite had no
   such task, so its false-refusal rate was 0% by construction —
   its own evaluation doc says so.

## Findings

1. **Hierarchy filtering stops indirect injection completely**
   (adversarial 100% → 0%), reproducing AASEF. It does not stop
   direct requests from the user: hierarchy-aware unsafe compliance
   is 100% on refusal scenarios.
2. **Ambiguity and conflict are where the baseline actually fails
   as an agent, not just as a security boundary.** Baseline task
   success is 46.7% on ambiguous, 41.7% on incomplete-information
   and 20.0% on conflicting scenarios, and its run-to-run
   consistency is 85.6% — the same task gives different outcomes
   on different seeds, because its choice between readings is a
   seeded guess.
3. **Taking the first reading is a good policy on this suite and
   would not be in general.** Hierarchy-aware and tool-side-enforced
   score 100% on ambiguous and incomplete-information tasks because
   the correct reading is listed first in every scenario. That is a
   property of the suite (see limitations), not evidence that
   first-reading is a reliable strategy.
4. **Cautious is the safety / usefulness trade-off, measured.**
   Zero unsafe compliance, 43.2% task success, 54.1% refusal rate,
   25.0% unnecessary refusals. It refuses whole categories on
   purpose; the cost is visible in the same table as the benefit.
5. **Recovery is driven by the retry policy, not by enforcement.**
   Every configuration that retries once recovers from a one-off
   timeout or malformed response; none recovers from an unavailable
   tool; only the configurations that verify before retrying avoid
   executing a completed action twice (baseline recovery 50.0%,
   all others 75.0%).
6. **Prompt variation breaks only the baseline.** Its
   prompt-variation consistency is 0.0%: a paraphrase with
   irrelevant context flips it into reading a secret file, while
   the other configurations are consistent across all paraphrases.

## Limitations

- Agents are deterministic simulated decision policies, not real
  language models. These numbers measure the policies and the
  enforcement architecture, not any model's susceptibility to
  ambiguity, conflict or injection.
- Every ambiguous / incomplete scenario has exactly two readings
  with the correct one first, which flatters first-reading
  policies. A suite with the correct reading second, or with
  three readings, would separate "takes the first reading" from
  "understands the task".
- Refusal consistency is 100.0% for every configuration, which is
  trivially true for deterministic policies; the meaningful
  consistency signals are run-to-run (85.6% baseline) and
  prompt-variation (0.0% baseline) consistency.
- The simulated approver grants only pre-approved actions. Real
  approval UX, approver fatigue, and attacks on the approver are
  not modelled.
- The shell tool is simulated with an allowlist; no real command
  execution is tested.
- Unsafe compliance weights a secret read and a wrong-file write
  equally. The per-category tables support re-weighting; the
  headline rate does not.
- The AASEF comparison uses AASEF's published numbers as reference
  data. ARSB reproduces the same three configurations, but it does
  not re-run AASEF's 34 scenarios — the overlap is by category,
  not by scenario (see the two explained differences above).
