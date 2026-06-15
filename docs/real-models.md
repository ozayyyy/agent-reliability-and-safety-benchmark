# Running the benchmark against a real model

The benchmark ships with simulated agents. `scripts/run_real_models.py`
runs the same scenarios, tools, scoring and traces against a real
model, through any service that speaks the OpenAI chat completions
format. The model is just another agent under test.

## Setup

Step 1. Tell the benchmark where your model lives. Set three things
in your terminal:

```bash
export ARSB_API_BASE_URL="https://api.example.com/v1"
export ARSB_API_KEY="your-key-here"
export ARSB_MODEL="your-model-name"
```

The first is the address of the service. The second is your secret
key for it. The third is the name of the model you want to test.
Keep the key in the environment only. Never write it in a file,
never put it in a scenario, and never share it.

Step 2. Run it:

```bash
.venv/bin/python scripts/run_real_models.py
```

That runs all 44 scenarios against all four configurations, one
seed, and writes `examples/real-models/report.json`. Useful flags:

```bash
# One configuration only
.venv/bin/python scripts/run_real_models.py --config cautious

# A different scenario folder, or a different output folder
.venv/bin/python scripts/run_real_models.py --scenarios scenarios --out /tmp/my-run

# Command-line flags win over the environment (key still prefers the environment)
.venv/bin/python scripts/run_real_models.py \
    --api-base-url "https://api.example.com/v1" --model "your-model-name"
```

Seeds default to `0` only. The model is asked with temperature 0,
so repeated seeds would repeat the same calls; pass
`--seeds 0,1,2` only if you want to measure that.

## Reading the report

`report.json` has the same shape as the simulated benchmark report
(`examples/report.json`): `runs` with one entry per scenario x
configuration x seed, and `metrics` with the same rates. It adds
four fields:

- `agent`: `"api"`.
- `model` and `base_url`: which model and service the numbers
  describe.
- `model_errors`: one entry per run whose last model call failed
  (HTTP error, timeout, or a reply that was not usable JSON). A
  failed call records an empty plan and the run still completes —
  failures are listed, not hidden and not retried.
- `note`: a plain statement of what the file is.

The API key never appears in the report, in stdout, or in any
trace. There is a test proving it
(`tests/test_run_real_models.py`).

## How it was validated without a real model

No real-model numbers exist yet: running this needs your own model
endpoint and key, which this machine does not have. Nothing in
this repo is presented as a real-model result.

What is proven, end to end, is the plumbing: the runner was run
against a tiny local stub endpoint on `127.0.0.1` that returns
canned chat-completions JSON, and it wrote a complete report
(44 runs, 0 model call failures, key absent from the report).
The same stub validation runs in the test suite
(`tests/test_run_real_models.py`), including the failure paths:
a missing endpoint is a clear error with nothing written, and an
HTTP 500 from the endpoint is recorded in `model_errors` with the
run still completing.

## Safety rules

The same rules as the rest of the benchmark: the scenarios use
fake data only. Never point a run at production data, real
credentials, live tools or real money. The model is asked only for
the task, the agent's scope and the tool observations so far — it
is never sent your key (except as the `Authorization` header to
the service itself) and never sent anything outside the scenario.
