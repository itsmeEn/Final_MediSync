#!/usr/bin/env bash
set -o errexit

python -m pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

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
