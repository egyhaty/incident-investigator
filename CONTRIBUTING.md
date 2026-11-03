# Contributing

This project is intentionally small and inspectable. Changes should preserve the synthetic-data boundary and the distinction between the deterministic reference demo and live local-model evaluation.

Before opening a pull request:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/evaluate.py --output artifacts/demo-evaluation.json
node --check investigator/web/app.js
```

Do not commit credentials, private cluster data, model weights, raw incident exports, or generated debug traces. New tools must be read-only, schema-validated, and covered by tests before they are exposed to a provider.
