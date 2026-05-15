"""
Seed generator for analytics dashboards.

This command creates statistically consistent time-series patient admissions spanning multiple months,
then computes analytics results (demographics, trends, forecasts) using the existing analytics pipeline
when available. It is designed to populate dashboards with non-empty, realistic-looking data while
matching the current database schema (PatientRecord + AnalyticsResult).
"""

import math
import random
import secrets
from datetime import datetime, timedelta, date
from typing import Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from backend.analytics.models import AnalyticsResult, PatientRecord
from backend.users.models import User
try:
    from backend.users.models import PatientProfile
except Exception:
    PatientProfile = None


class Command(BaseCommand):
    help = "Populate realistic seed data for analytics dashboards (server-side)."

    def add_arguments(self, parser):
        parser.add_argument("--months", type=int, default=24, help="Number of months of time-series data to generate (min 24 recommended).")
        parser.add_argument("--patients", type=int, default=120, help="Target number of patient users to sample from (creates demo patients if needed).")
        parser.add_argument("--daily-avg", type=float, default=10.0, help="Approximate average daily admissions to generate.")
        parser.add_argument("--seed", type=int, default=20260516, help="Seed for deterministic generation.")

        # Backward compatible volume control
        parser.add_argument("--records", type=int, default=None, help="Legacy: approximate number of patient records to generate (overrides --daily-avg).")

        # Date range overrides
        parser.add_argument("--start-date", type=str, default=None, help="Start date (YYYY-MM-DD). Overrides --months.")
        parser.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD). Defaults to today.")

        # Cleanup toggles
        parser.add_argument("--clear-analytics", action="store_true", help="Clear existing AnalyticsResult before seeding.")
        parser.add_argument("--clear-records", action="store_true", help="Clear existing PatientRecord before seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        seed = int(options.get("seed") or 0) or 20260516
        rng = random.Random(seed)

        months = int(options.get("months") or 24)
        patients_target = int(options.get("patients") or 0)
        daily_avg = float(options.get("daily_avg") or 0.0) or 10.0

        legacy_records = options.get("records")
        start_date_str = options.get("start_date")
        end_date_str = options.get("end_date")

        # Date range parsing (timezone-aware)
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else timezone.now()
        if timezone.is_naive(end_dt):
            end_dt = timezone.make_aware(end_dt)

        if start_date_str:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        else:
            months = max(1, months)
            start_dt = end_dt - timedelta(days=int(30.5 * months))
        if timezone.is_naive(start_dt):
            start_dt = timezone.make_aware(start_dt)

        if start_dt > end_dt:
            raise CommandError("start-date must be before end-date")

        # Legacy record count mapping
        total_days = max(1, (end_dt.date() - start_dt.date()).days + 1)
        if legacy_records is not None:
            try:
                legacy_n = int(legacy_records)
            except Exception:
                legacy_n = 0
            legacy_n = max(0, legacy_n)
            if legacy_n:
                daily_avg = max(0.1, float(legacy_n) / float(total_days))

        # Cleanup based on flags
        if options.get("clear_analytics"):
            AnalyticsResult.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing analytics results"))
        if options.get("clear_records"):
            PatientRecord.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing patient records"))

        # Ensure we have patient users to attach records to
        patients_qs = User.objects.filter(role="patient")
        existing_patients = int(patients_qs.count())
        created_patients = 0
        if patients_target and existing_patients < patients_target:
            created_patients = self._ensure_demo_patients(
                rng=rng,
                target_count=patients_target,
                end_dt=end_dt,
            )
            patients_qs = User.objects.filter(role="patient")

        # Seed patient records (24+ month time-series with seasonal/weekly patterns)
        created_records = self._seed_patient_records_time_series(
            rng=rng,
            daily_avg=daily_avg,
            start_dt=start_dt,
            end_dt=end_dt,
        )

        # Compute and store analytics results using the same analytics models where possible
        created_results = self._compute_and_store_analytics(
            start_dt=start_dt,
            end_dt=end_dt,
            seed=seed,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded analytics data: patients_created={created_patients}, patient_records_created={created_records}, analytics_results_created={created_results}"
        ))

    # --- Patient Records ---
    def _ensure_demo_patients(self, rng: random.Random, target_count: int, end_dt: datetime) -> int:
        regions = [
            {"name": "MediSync General - Manila", "address": "Manila, NCR", "w": 34},
            {"name": "MediSync General - Cebu", "address": "Cebu City, Cebu", "w": 22},
            {"name": "MediSync General - Davao", "address": "Davao City, Davao del Sur", "w": 18},
            {"name": "MediSync General - Baguio", "address": "Baguio City, Benguet", "w": 14},
            {"name": "MediSync General - Iloilo", "address": "Iloilo City, Iloilo", "w": 12},
        ]
        region_choices = [r["name"] for r in regions]
        region_weights = [r["w"] for r in regions]
        region_address = {r["name"]: r["address"] for r in regions}

        def sample_gender() -> str:
            return rng.choices(["Male", "Female", "Other"], weights=[49, 50, 1])[0]

        def sample_age() -> int:
            group = rng.choices(
                ["0-18", "19-35", "36-50", "51-65", "65+"],
                weights=[18, 32, 23, 17, 10],
            )[0]
            if group == "0-18":
                return rng.randint(0, 18)
            if group == "19-35":
                return rng.randint(19, 35)
            if group == "36-50":
                return rng.randint(36, 50)
            if group == "51-65":
                return rng.randint(51, 65)
            return rng.randint(66, 88)

        def dob_from_age(age: int) -> date:
            base_year = end_dt.date().year - age
            m = rng.randint(1, 12)
            d = rng.randint(1, 28)
            return date(base_year, m, d)

        existing = int(User.objects.filter(role="patient").count())
        needed = max(0, int(target_count) - existing)
        if needed <= 0:
            return 0

        created = 0
        for i in range(needed):
            email = f"demo_patient_{secrets.token_hex(4)}@seed.local"
            full_name = f"Demo Patient {existing + i + 1:04d}"
            gender = sample_gender()
            age = sample_age()
            dob = dob_from_age(age)
            hosp = rng.choices(region_choices, weights=region_weights)[0]
            pwd = secrets.token_urlsafe(18)
            try:
                u = User.objects.create_user(
                    email=email,
                    password=pwd,
                    full_name=full_name,
                    role=User.Role.PATIENT,
                    date_of_birth=dob,
                    gender=gender,
                    hospital_name=hosp,
                    hospital_address=region_address.get(hosp, ""),
                    verification_status="approved",
                    is_verified=True,
                    is_active=True,
                )
                if PatientProfile is not None:
                    try:
                        PatientProfile.objects.get_or_create(user=u, defaults={"hospital": hosp})
                    except Exception:
                        pass
                created += 1
            except Exception:
                continue
        return created

    def _seed_patient_records_time_series(self, rng: random.Random, daily_avg: float, start_dt: datetime, end_dt: datetime) -> int:
        patients = list(User.objects.filter(role="patient").only("id", "date_of_birth", "gender", "hospital_name"))
        if not patients:
            self.stdout.write(self.style.ERROR("No patient users found. Create patient accounts first or use --patients to generate demo patients."))
            return 0

        chronic_conditions = [
            "Hypertension",
            "Diabetes",
            "Heart Disease",
            "Asthma",
            "Arthritis",
            "Depression",
            "Anxiety",
            "Obesity",
            "High Cholesterol",
            "Migraine",
        ]
        acute_conditions = [
            "Pneumonia",
            "Bronchitis",
            "Flu",
            "Cold",
            "Fever",
            "Gastroenteritis",
            "Appendicitis",
            "Fracture",
            "Sprain",
            "Burn",
        ]

        meds_by_condition: dict[str, list[str]] = {
            "Hypertension": ["Lisinopril", "Amlodipine", "Losartan"],
            "Diabetes": ["Metformin", "Insulin"],
            "Heart Disease": ["Atorvastatin", "Aspirin", "Warfarin", "Furosemide"],
            "Asthma": ["Albuterol", "Prednisone"],
            "Arthritis": ["Ibuprofen", "Naproxen"],
            "Depression": ["Sertraline", "Fluoxetine"],
            "Anxiety": ["Lorazepam", "Sertraline"],
            "Obesity": ["Orlistat"],
            "High Cholesterol": ["Atorvastatin"],
            "Migraine": ["Sumatriptan", "Acetaminophen"],
            "Pneumonia": ["Amoxicillin", "Azithromycin"],
            "Bronchitis": ["Albuterol", "Amoxicillin"],
            "Flu": ["Oseltamivir", "Acetaminophen"],
            "Cold": ["Acetaminophen"],
            "Fever": ["Acetaminophen", "Ibuprofen"],
            "Gastroenteritis": ["Oral Rehydration Salts", "Ondansetron"],
            "Appendicitis": ["Ceftriaxone"],
            "Fracture": ["Ibuprofen", "Tramadol"],
            "Sprain": ["Ibuprofen"],
            "Burn": ["Silver sulfadiazine", "Ibuprofen"],
        }

        def age_at(dt: datetime, dob: date | None) -> int:
            if not dob:
                return int(rng.randint(18, 85))
            years = dt.date().year - dob.year - ((dt.date().month, dt.date().day) < (dob.month, dob.day))
            return max(0, min(95, int(years)))

        def month_factor(dt: datetime) -> float:
            m = dt.month
            seasonal = 1.0 + 0.18 * math.sin((2.0 * math.pi * (m - 1)) / 12.0)
            winter_boost = 1.10 if m in (12, 1, 2) else 1.0
            return max(0.6, seasonal * winter_boost)

        dow_weights = {0: 1.18, 1: 1.10, 2: 1.05, 3: 1.05, 4: 1.12, 5: 0.82, 6: 0.62}

        def daily_count(dt: datetime) -> int:
            base = float(daily_avg)
            f = month_factor(dt) * dow_weights.get(dt.weekday(), 1.0)
            noise = rng.gauss(0.0, 0.18)
            return max(0, int(round(base * f * max(0.0, 1.0 + noise))))

        # Patient-level chronic profile to induce correlations/revisits
        patient_chronic: dict[int, list[str]] = {}
        for p in patients:
            a = age_at(end_dt, getattr(p, "date_of_birth", None))
            profile: list[str] = []
            if a >= 50 and rng.random() < 0.55:
                profile.append(rng.choice(["Hypertension", "High Cholesterol", "Diabetes"]))
            if a >= 60 and rng.random() < 0.28:
                profile.append("Heart Disease")
            if rng.random() < 0.18:
                profile.append(rng.choice(["Asthma", "Migraine", "Arthritis"]))
            if rng.random() < 0.15:
                profile.append(rng.choice(["Depression", "Anxiety"]))
            if rng.random() < 0.12:
                profile.append("Obesity")
            patient_chronic[p.id] = list(dict.fromkeys(profile)) or [rng.choice(chronic_conditions)]

        def seasonal_acute_choice(dt: datetime) -> str:
            m = dt.month
            if m in (12, 1, 2):
                return rng.choices(["Flu", "Cold", "Bronchitis", "Pneumonia", "Fever"], weights=[28, 32, 16, 10, 14])[0]
            if m in (6, 7, 8, 9):
                return rng.choices(["Gastroenteritis", "Fever", "Cold", "Sprain", "Burn"], weights=[26, 24, 18, 18, 14])[0]
            return rng.choices(acute_conditions, weights=[10, 10, 10, 12, 10, 12, 6, 10, 10, 10])[0]

        def pick_condition(p: User, dt: datetime) -> str:
            chronic = patient_chronic.get(p.id) or [rng.choice(chronic_conditions)]
            if rng.random() < 0.62:
                return rng.choice(chronic)
            return seasonal_acute_choice(dt)

        def severity_for(condition: str, age_years: int) -> str:
            base = {"Low": 40, "Medium": 38, "High": 18, "Critical": 4}
            if condition in ("Pneumonia", "Heart Disease", "Appendicitis"):
                base["High"] += 8
                base["Critical"] += 3
                base["Low"] = max(5, base["Low"] - 10)
            if condition in ("Flu", "Bronchitis") and age_years >= 65:
                base["High"] += 6
                base["Critical"] += 2
            if age_years >= 75:
                base["High"] += 4
                base["Critical"] += 2
                base["Low"] = max(5, base["Low"] - 8)
            weights = [base["Low"], base["Medium"], base["High"], base["Critical"]]
            return rng.choices(["Low", "Medium", "High", "Critical"], weights=weights)[0]

        def outcome_for(sev: str) -> str:
            if sev == "Critical":
                return rng.choices(["Recovered", "Ongoing", "Transferred", "Deceased"], weights=[22, 42, 24, 12])[0]
            if sev == "High":
                return rng.choices(["Recovered", "Ongoing", "Transferred", "Deceased"], weights=[52, 30, 16, 2])[0]
            if sev == "Medium":
                return rng.choices(["Recovered", "Ongoing", "Transferred", "Deceased"], weights=[70, 24, 6, 0])[0]
            return rng.choices(["Recovered", "Ongoing", "Transferred", "Deceased"], weights=[84, 14, 2, 0])[0]

        def medication_for(condition: str, sev: str) -> str | None:
            meds = meds_by_condition.get(condition) or []
            if not meds:
                return None
            if sev in ("High", "Critical") and len(meds) >= 2 and rng.random() < 0.5:
                pick = rng.sample(meds, k=min(2, len(meds)))
                return ", ".join(pick)
            return rng.choice(meds)

        created = 0
        buf: list[PatientRecord] = []
        batch_size = 1000

        day = datetime(start_dt.year, start_dt.month, start_dt.day, tzinfo=start_dt.tzinfo)
        last_day = datetime(end_dt.year, end_dt.month, end_dt.day, tzinfo=end_dt.tzinfo)

        self.stdout.write(f"Creating time-series patient records from {day.date()} to {last_day.date()} (avg/day≈{daily_avg:.2f})...")
        while day <= last_day:
            n = daily_count(day)
            if n <= 0:
                day = day + timedelta(days=1)
                continue

            for _ in range(n):
                p = rng.choice(patients)
                visit_dt = day + timedelta(hours=rng.randint(7, 20), minutes=rng.randint(0, 59))
                a = age_at(visit_dt, getattr(p, "date_of_birth", None))
                condition = pick_condition(p, visit_dt)
                sev = severity_for(condition, a)
                out = outcome_for(sev)
                med = medication_for(condition, sev)
                buf.append(
                    PatientRecord(
                        patient=p,
                        date_of_admission=visit_dt,
                        medical_condition=condition,
                        age=a,
                        gender=(getattr(p, "gender", None) or rng.choices(["Male", "Female", "Other"], weights=[49, 50, 1])[0]),
                        medication=med,
                        severity=sev,
                        treatment_outcome=out,
                    )
                )
                created += 1

            if len(buf) >= batch_size:
                PatientRecord.objects.bulk_create(buf, batch_size=batch_size)
                buf.clear()

            day = day + timedelta(days=1)

        if buf:
            PatientRecord.objects.bulk_create(buf, batch_size=batch_size)
            buf.clear()

        return created

    # --- Analytics ---
    def _compute_and_store_analytics(self, start_dt: datetime, end_dt: datetime, seed: int) -> int:
        qs = PatientRecord.objects.filter(date_of_admission__range=(start_dt, end_dt))
        if not qs.exists():
            return 0

        # Prefer the existing analytics implementation to ensure alignment with models
        try:
            import pandas as pd  # type: ignore
            from backend.analytics.predictive_analytics import (
                get_data_from_queryset,
                analyze_patient_demographics,
                perform_patient_health_trends,
                analyze_illness_prediction_chi_square,
                analyze_common_medications,
                predict_patient_volume_confidence,
                predict_illness_surge,
                predict_weekly_illness_forecast,
                predict_monthly_illness_forecast,
            )
            analytics_available = True
        except Exception:
            analytics_available = False

        created = 0

        def json_sanitize(v: Any) -> Any:
            if v is None or isinstance(v, (str, bool, int)):
                return v
            if isinstance(v, float):
                return v if math.isfinite(v) else None
            if isinstance(v, (datetime, date)):
                try:
                    return v.isoformat()
                except Exception:
                    return str(v)
            if isinstance(v, dict):
                return {str(k): json_sanitize(val) for k, val in v.items()}
            if isinstance(v, list):
                return [json_sanitize(x) for x in v]
            if isinstance(v, tuple):
                return [json_sanitize(x) for x in v]
            item = getattr(v, "item", None)
            if callable(item):
                try:
                    return json_sanitize(item())
                except Exception:
                    return None
            return None

        def upsert(analysis_type: str, results: dict) -> None:
            nonlocal created
            AnalyticsResult.objects.create(
                analysis_type=analysis_type,
                status="completed",
                results=json_sanitize(results),
            )
            created += 1

        seed_meta = {
            "_seed_meta": {
                "generated_by": "populate_demo_data",
                "seed": seed,
                "start": start_dt.date().isoformat(),
                "end": end_dt.date().isoformat(),
                "records": int(qs.count()),
                "notes": "Generated time-series admissions with seasonal + weekly patterns; computed analytics using existing model logic where available.",
            }
        }

        if analytics_available:
            df = get_data_from_queryset(qs)
            if not getattr(df, "empty", True):
                df = df.copy()
                df.columns = df.columns.str.lower().str.replace(" ", "_")

            pd_res = analyze_patient_demographics(df)
            if isinstance(pd_res, dict):
                upsert("patient_demographics", {**pd_res, **seed_meta})

            ht_res = perform_patient_health_trends(df) if not getattr(df, "empty", True) else {"error": "No data"}
            if isinstance(ht_res, dict):
                upsert("patient_health_trends", {**ht_res, **seed_meta})

            ip_res = analyze_illness_prediction_chi_square(df) if not getattr(df, "empty", True) else {"error": "No data"}
            if isinstance(ip_res, dict):
                upsert("illness_prediction", {**ip_res, **seed_meta})

            ma_res = analyze_common_medications(df)
            if isinstance(ma_res, dict):
                upsert("medication_analysis", {**ma_res, **seed_meta})

            # Volume prediction with confidence intervals (monthly) to support forecasting dashboards
            vp_res = predict_patient_volume_confidence(df, history_months=24, horizon_months=6) if not getattr(df, "empty", True) else {"error": "No data"}
            if isinstance(vp_res, dict):
                upsert("patient_volume_prediction", {**vp_res, **seed_meta})

            sp_res = predict_illness_surge(df) if not getattr(df, "empty", True) else {"error": "No data"}
            if isinstance(sp_res, dict):
                upsert("illness_surge_prediction", {**sp_res, **seed_meta})

            wf_res = predict_weekly_illness_forecast(df) if not getattr(df, "empty", True) else {"error": "No data"}
            if isinstance(wf_res, dict):
                upsert("weekly_illness_forecast", {**wf_res, **seed_meta})

            mf_res = predict_monthly_illness_forecast(df) if not getattr(df, "empty", True) else {"error": "No data"}
            if isinstance(mf_res, dict):
                # Add regional breakdown for "spread" style exploration (uses existing schema as extra keys only)
                region_breakdown = self._build_regional_illness_breakdown(start_dt, end_dt)
                upsert("monthly_illness_forecast", {**mf_res, **region_breakdown, **seed_meta})

            return created

        # Fallback: store minimal but schema-compatible results derived directly from records
        total = qs.count()
        age_groups = {"0-18": 0, "19-35": 0, "36-50": 0, "51-65": 0, "65+": 0}
        genders = {"Male": 0, "Female": 0, "Other": 0}
        ages = []
        for r in qs.values("age", "gender"):
            a = int(r["age"] or 0)
            ages.append(a)
            if a <= 18:
                age_groups["0-18"] += 1
            elif a <= 35:
                age_groups["19-35"] += 1
            elif a <= 50:
                age_groups["36-50"] += 1
            elif a <= 65:
                age_groups["51-65"] += 1
            else:
                age_groups["65+"] += 1
            g = r["gender"] or "Other"
            genders[g] = genders.get(g, 0) + 1

        demographics_data = {
            "age_distribution": age_groups,
            "gender_proportions": genders,
            "total_patients": int(total),
            "average_age": round((sum(ages) / max(1, len(ages))), 1) if ages else 0,
            **seed_meta,
        }
        upsert("patient_demographics", demographics_data)

        # Medication analysis
        med_counts: Dict[str, int] = {}
        for r in qs.values_list("medication", flat=True):
            if r:
                med_counts[str(r)] = med_counts.get(str(r), 0) + 1
        pareto = sorted(
            [{"medication": k, "prescriptions": v} for k, v in med_counts.items()],
            key=lambda x: x["prescriptions"],
            reverse=True,
        )
        upsert("medication_analysis", {"medication_pareto_data": pareto[:20], "medication_usage": pareto, **seed_meta})

        # Volume prediction: monthly comparison points
        counts: Dict[str, int] = {}
        for dt in qs.values_list("date_of_admission", flat=True):
            if not dt:
                continue
            counts[dt.strftime("%Y-%m")] = counts.get(dt.strftime("%Y-%m"), 0) + 1
        points = [{"date": k, "predicted": v, "actual": v} for k, v in sorted(counts.items())]
        upsert("patient_volume_prediction", {"comparison_data": points, "evaluation_metrics": {"mae": 0.0, "rmse": 0.0}, **seed_meta})

        # Health trends: top illnesses in the most recent window
        cond_counts: Dict[str, int] = {}
        for c in qs.values_list("medical_condition", flat=True):
            if not c:
                continue
            cond_counts[str(c)] = cond_counts.get(str(c), 0) + 1
        common = [c for c, _ in sorted(cond_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        upsert(
            "patient_health_trends",
            {
                "top_illnesses_by_week": [{"medical_condition": c, "count": int(cond_counts.get(c, 0)), "week": "Current"} for c in common],
                "trend_analysis": {"increasing_conditions": common[:2], "decreasing_conditions": common[2:4], "stable_conditions": common[4:5]},
                **seed_meta,
            },
        )

        # Minimal surge + forecasts placeholders
        upsert("illness_surge_prediction", {"forecasted_monthly_cases": [], "evaluation_metrics": {}, "warning": "Analytics modules unavailable; install analytics deps to compute forecasts.", **seed_meta})
        upsert("weekly_illness_forecast", {"weekly_illness_forecast": [], "evaluation_metrics": {}, "summary": {}, **seed_meta})
        upsert("monthly_illness_forecast", {"monthly_illness_forecast": [], "evaluation_metrics": {}, "summary": {}, **seed_meta})

        return created

    def _build_regional_illness_breakdown(self, start_dt: datetime, end_dt: datetime) -> dict[str, Any]:
        qs = PatientRecord.objects.select_related("patient").filter(date_of_admission__range=(start_dt, end_dt))
        region_counts: dict[str, dict[str, int]] = {}
        for row in qs.values_list("patient__hospital_name", "medical_condition"):
            region = (row[0] or "Unknown").strip() or "Unknown"
            cond = (row[1] or "Unknown").strip() or "Unknown"
            bucket = region_counts.setdefault(region, {})
            bucket[cond] = bucket.get(cond, 0) + 1
        top_by_region = []
        for region, conds in sorted(region_counts.items(), key=lambda x: sum(x[1].values()), reverse=True):
            top = sorted(conds.items(), key=lambda x: x[1], reverse=True)[:5]
            top_by_region.append(
                {
                    "region": region,
                    "total_cases": int(sum(conds.values())),
                    "top_illnesses": [{"illness": k, "cases": int(v)} for k, v in top],
                }
            )
        return {"regional_spread": {"regions": top_by_region}}

    # Inventory seeding removed.
