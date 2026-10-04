#!/usr/bin/env bash
# Deploys ChainTruth with the Snowflake CLI. Ideally run these steps THROUGH CoCo (see docs/COCO_PLAYBOOK.md).
set -euo pipefail
CONN="${1:-default}"
for f in sql/0*.sql; do
  echo ">> $f"
  snow sql --connection "$CONN" -f "$f"
done
snow streamlit deploy --replace --connection "$CONN"
SNOWFLAKE_CONNECTION_NAME="$CONN" python tests/persona_consistency.py
