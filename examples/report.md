# Agent Reliability and Safety Benchmark — Results

Runs: 444 (seeds 0, 1, 2).
Agents are deterministic simulated decision policies, not language models; results measure the agent policies and the enforcement architecture, not any real model's behaviour. Scoring is rule-based; no LLM judge is used.

## Headline metrics

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

## Comparison with AASEF (published results)

AASEF's headline numbers (34 scenarios v1.0 x 3 configs, seed 0, 102 runs) are reference data, not measured here. ARSB reproduces the same three configurations; its adversarial category corresponds to AASEF's indirect injection categories, and its benign category to AASEF's.

| Configuration | AASEF attack success | ARSB unsafe compliance (adversarial) | AASEF task completion | ARSB task success (benign) |
|---|---|---|---|---|
| baseline | 100.0% | 100.0% | 100.0% | 100.0% |
| hierarchy-aware | 35.5% | 0.0% | 100.0% | 100.0% |
| tool-side-enforced | 0.0% | 0.0% | 100.0% | 75.0% |

## Reading the results

- Baseline follows instructions wherever it finds them and guesses between plausible readings of ambiguous tasks, so it complies unsafely and varies run to run.
- Hierarchy-aware ignores instructions in untrusted content but still follows direct instructions from the user, a trusted principal — so disallowed requests from the user still succeed under it.
- Tool-side enforcement blocks unauthorised actions at the tool boundary and denies unapproved consequential actions, which is why its unsafe-compliance rate is the lowest — but the approval gate also refuses a benign write the user did not pre-approve.
- Cautious refuses ambiguous, conflicting, disallowed and under-specified tasks instead of guessing. Its unsafe compliance is zero, and its task success is the lowest: that is the safety / usefulness trade-off, measured.
- Recovery is driven by the retry policy, not by enforcement: every configuration that retries once recovers from a one-off timeout or malformed response, none recovers from an unavailable tool, and only the configurations that verify before retrying avoid executing a completed action twice.
