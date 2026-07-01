# Lab 25 Your Turn Extensions

## Extension 1 - Reasoning Budget

| Metric | Value |
|---|---:|
| Total requests | 2,400 |
| Reasoning requests | 201 |
| Reasoning traffic share | 8.4% |
| Reasoning token share | 16.5% |
| Reasoning optimized cost share | 16.5% |
| Reasoning energy share | 94.0% |
| Estimated cost saved by capping reasoning to 5% traffic | $0.56/day |
| Estimated energy saved by cap | 12004.0 Wh/day |

Recommendation: only route to reasoning when task complexity is high or when the small/standard model confidence is low. Default traffic should stay on the cheaper non-reasoning route.

## Extension 2 - Carbon-aware Scheduling

Scenario: move interruptible jobs from `us-east-1` to `europe-north1`.

| Job | GPU | Energy (kWh) | Carbon saved (kgCO2e) | Energy cost saved |
|---|---|---:|---:|---:|
| job-train-llm | H100 | 1568.0 | 548.8 | $47.04 |
| job-train-embed | A100 | 80.0 | 28.0 | $2.40 |
| job-finetune | H100 | 25.2 | 8.8 | $0.76 |
| job-dev-sandbox | A10G | 52.8 | 18.5 | $1.58 |
| job-batch-eval | H100 | 63.0 | 22.1 | $1.89 |

| Metric | Value |
|---|---:|
| Source carbon | 679.8 kgCO2e |
| Target carbon | 53.7 kgCO2e |
| Carbon saved | 626.1 kgCO2e |
| Carbon reduction | 92.1% |
| Energy cost saved | $53.67 |

Recommendation: schedule interruptible training/eval jobs in the cleanest practical region when latency and data residency allow it. Keep latency-sensitive inference close to users.