#!/usr/bin/env bash
set -o errexit

python -m pip install -r requirements.txt

python manage.py collectstatic --no-input

if [ "${RUN_MAKEMIGRATIONS:-0}" = "1" ]; then
  python manage.py makemigrations
fi


if [ "${RUN_SEED_PREDICTIVE_AI_DATA:-0}" = "1" ]; then
  python manage.py seed_predictive_ai_data \
    --seed "${SEED_PREDICTIVE_AI_DATA_SEED:-42}" \
    --years "${SEED_PREDICTIVE_AI_DATA_YEARS:-2}" \
    --doctors "${SEED_PREDICTIVE_AI_DATA_DOCTORS:-1}" \
    --nurses "${SEED_PREDICTIVE_AI_DATA_NURSES:-1}" \
    --patients "${SEED_PREDICTIVE_AI_DATA_PATIENTS:-2000}" \
    --patient-records "${SEED_PREDICTIVE_AI_DATA_PATIENT_RECORDS:-20000}" \
    --reset
fi

if [ "${RUN_POPULATE_DEMO_DATA:-0}" = "1" ]; then
  args=()
  args+=(--seed "${POPULATE_DEMO_DATA_SEED:-20260516}")
  args+=(--months "${POPULATE_DEMO_DATA_MONTHS:-24}")
  args+=(--patients "${POPULATE_DEMO_DATA_PATIENTS:-120}")
  args+=(--daily-avg "${POPULATE_DEMO_DATA_DAILY_AVG:-10}")
  if [ "${POPULATE_DEMO_DATA_CLEAR_ANALYTICS:-0}" = "1" ]; then
    args+=(--clear-analytics)
  fi
  if [ "${POPULATE_DEMO_DATA_CLEAR_RECORDS:-0}" = "1" ]; then
    args+=(--clear-records)
  fi
  if [ -n "${POPULATE_DEMO_DATA_START_DATE:-}" ]; then
    args+=(--start-date "${POPULATE_DEMO_DATA_START_DATE}")
  fi
  if [ -n "${POPULATE_DEMO_DATA_END_DATE:-}" ]; then
    args+=(--end-date "${POPULATE_DEMO_DATA_END_DATE}")
  fi

  python manage.py populate_demo_data "${args[@]}"
fi
