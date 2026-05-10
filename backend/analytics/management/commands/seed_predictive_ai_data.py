import json
import math
import random
import string
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from backend.admin_site.models import Hospital
from backend.analytics.models import PatientRecord, UsageEvent
from backend.operations.models import (
    AppointmentManagement,
    ConsultationNotes,
    Department,
    DoctorAvailability,
    DoctorTimeSlot,
    HospitalDepartmentDoctor,
    PatientAssignment,
    QueueManagement,
)
from backend.users.models import GeneralDoctorProfile, NurseProfile, PatientProfile, User


@dataclass(frozen=True)
class SupplierSpec:
    name: str
    lead_time_days_mean: float
    lead_time_days_sd: float
    reliability: float


@dataclass(frozen=True)
class ConditionSpec:
    name: str
    department: str
    preferred_specialties: Tuple[str, ...]
    typical_meds: Tuple[str, ...]
    seasonal_peak_months: Tuple[int, ...]
    base_weight: float


SPECIALTIES: List[str] = [
    "General Practice",
    "Internal Medicine",
    "Pediatrics",
    "Cardiology",
    "Pulmonology",
    "Orthopedics",
    "Emergency Medicine",
    "Psychiatry",
    "OB-GYN",
    "Dermatology",
]

DEPARTMENTS: List[Tuple[str, str]] = [
    ("OPD", "Out Patient Department"),
    ("Pharmacy", "Pharmacy"),
    ("Appointment", "Appointment"),
    ("ER", "Emergency Room"),
    ("ICU", "Intensive Care Unit"),
    ("Pediatrics", "Pediatrics"),
    ("Surgery", "Surgery"),
    ("Cardiology", "Cardiology"),
    ("Ward", "General Ward"),
]

SUPPLIERS: List[SupplierSpec] = [
    SupplierSpec(name="MedSupply Co.", lead_time_days_mean=4.0, lead_time_days_sd=1.5, reliability=0.93),
    SupplierSpec(name="PharmaLink Distributors", lead_time_days_mean=6.5, lead_time_days_sd=2.2, reliability=0.88),
    SupplierSpec(name="IslandCare Wholesale", lead_time_days_mean=8.0, lead_time_days_sd=3.0, reliability=0.80),
    SupplierSpec(name="RapidRx Emergency", lead_time_days_mean=1.5, lead_time_days_sd=0.8, reliability=0.97),
]

MED_CATALOG: Dict[str, Dict[str, Any]] = {
    "Paracetamol 500mg Tablet": {"category": "analgesic", "base_unit_price": Decimal("0.50")},
    "Ibuprofen 400mg Tablet": {"category": "analgesic", "base_unit_price": Decimal("0.70")},
    "Diclofenac 50mg Tablet": {"category": "analgesic", "base_unit_price": Decimal("0.65")},
    "Aspirin 81mg Tablet": {"category": "cardio", "base_unit_price": Decimal("0.35")},
    "Amoxicillin 500mg Capsule": {"category": "antibiotic", "base_unit_price": Decimal("1.20")},
    "Cefuroxime 500mg Tablet": {"category": "antibiotic", "base_unit_price": Decimal("1.80")},
    "Azithromycin 500mg Tablet": {"category": "antibiotic", "base_unit_price": Decimal("2.20")},
    "Doxycycline 100mg Capsule": {"category": "antibiotic", "base_unit_price": Decimal("1.30")},
    "Amoxicillin/Clavulanate 625mg": {"category": "antibiotic", "base_unit_price": Decimal("2.80")},
    "Amlodipine 5mg Tablet": {"category": "antihypertensive", "base_unit_price": Decimal("0.80")},
    "Losartan 50mg Tablet": {"category": "antihypertensive", "base_unit_price": Decimal("0.90")},
    "Hydrochlorothiazide 25mg Tablet": {"category": "antihypertensive", "base_unit_price": Decimal("0.75")},
    "Metformin 500mg Tablet": {"category": "antidiabetic", "base_unit_price": Decimal("0.60")},
    "Insulin Glargine 100U/mL": {"category": "antidiabetic", "base_unit_price": Decimal("12.00")},
    "Salbutamol Inhaler 100mcg": {"category": "respiratory", "base_unit_price": Decimal("5.50")},
    "Budesonide/Formoterol Inhaler": {"category": "respiratory", "base_unit_price": Decimal("9.50")},
    "Omeprazole 20mg Capsule": {"category": "gi", "base_unit_price": Decimal("0.85")},
    "ORS Packet": {"category": "gi", "base_unit_price": Decimal("0.30")},
    "Loperamide 2mg Capsule": {"category": "gi", "base_unit_price": Decimal("0.40")},
    "Atorvastatin 20mg Tablet": {"category": "cardio", "base_unit_price": Decimal("1.40")},
    "Clopidogrel 75mg Tablet": {"category": "cardio", "base_unit_price": Decimal("1.10")},
    "Warfarin 5mg Tablet": {"category": "cardio", "base_unit_price": Decimal("0.95")},
    "Folic Acid 5mg Tablet": {"category": "supplement", "base_unit_price": Decimal("0.25")},
    "Vitamin D3 1000IU Capsule": {"category": "supplement", "base_unit_price": Decimal("0.50")},
    "Calcium Carbonate 500mg Tablet": {"category": "supplement", "base_unit_price": Decimal("0.55")},
    "Iron (Ferrous Sulfate) 325mg": {"category": "supplement", "base_unit_price": Decimal("0.45")},
}

CONDITIONS: List[ConditionSpec] = [
    ConditionSpec(
        name="Flu",
        department="OPD",
        preferred_specialties=("General Practice", "Internal Medicine", "Pediatrics"),
        typical_meds=("Paracetamol 500mg Tablet", "ORS Packet"),
        seasonal_peak_months=(12, 1, 2),
        base_weight=0.09,
    ),
    ConditionSpec(
        name="Pneumonia",
        department="ER",
        preferred_specialties=("Pulmonology", "Internal Medicine", "Emergency Medicine"),
        typical_meds=("Azithromycin 500mg Tablet", "Amoxicillin/Clavulanate 625mg", "Salbutamol Inhaler 100mcg"),
        seasonal_peak_months=(12, 1, 2),
        base_weight=0.04,
    ),
    ConditionSpec(
        name="Bronchitis",
        department="OPD",
        preferred_specialties=("Pulmonology", "Internal Medicine", "General Practice"),
        typical_meds=("Salbutamol Inhaler 100mcg", "Paracetamol 500mg Tablet"),
        seasonal_peak_months=(11, 12, 1, 2),
        base_weight=0.05,
    ),
    ConditionSpec(
        name="Asthma Exacerbation",
        department="ER",
        preferred_specialties=("Pulmonology", "Emergency Medicine", "Pediatrics"),
        typical_meds=("Salbutamol Inhaler 100mcg", "Budesonide/Formoterol Inhaler"),
        seasonal_peak_months=(8, 9, 10, 12),
        base_weight=0.03,
    ),
    ConditionSpec(
        name="Gastroenteritis",
        department="OPD",
        preferred_specialties=("Internal Medicine", "General Practice", "Pediatrics"),
        typical_meds=("ORS Packet", "Loperamide 2mg Capsule"),
        seasonal_peak_months=(6, 7, 8, 9),
        base_weight=0.06,
    ),
    ConditionSpec(
        name="Hypertension",
        department="OPD",
        preferred_specialties=("Internal Medicine", "Cardiology", "General Practice"),
        typical_meds=("Amlodipine 5mg Tablet", "Losartan 50mg Tablet"),
        seasonal_peak_months=(),
        base_weight=0.08,
    ),
    ConditionSpec(
        name="Diabetes",
        department="OPD",
        preferred_specialties=("Internal Medicine", "General Practice"),
        typical_meds=("Metformin 500mg Tablet", "Insulin Glargine 100U/mL"),
        seasonal_peak_months=(),
        base_weight=0.06,
    ),
    ConditionSpec(
        name="Chest Pain (Rule-out ACS)",
        department="ER",
        preferred_specialties=("Cardiology", "Emergency Medicine", "Internal Medicine"),
        typical_meds=("Aspirin 81mg Tablet", "Clopidogrel 75mg Tablet"),
        seasonal_peak_months=(),
        base_weight=0.03,
    ),
    ConditionSpec(
        name="Fracture",
        department="ER",
        preferred_specialties=("Orthopedics", "Emergency Medicine"),
        typical_meds=("Ibuprofen 400mg Tablet", "Paracetamol 500mg Tablet"),
        seasonal_peak_months=(4, 5, 6),
        base_weight=0.04,
    ),
    ConditionSpec(
        name="Sepsis",
        department="ICU",
        preferred_specialties=("Internal Medicine", "Emergency Medicine"),
        typical_meds=("Cefuroxime 500mg Tablet", "Amoxicillin/Clavulanate 625mg"),
        seasonal_peak_months=(12, 1, 2),
        base_weight=0.01,
    ),
    ConditionSpec(
        name="Depression/Anxiety",
        department="OPD",
        preferred_specialties=("Psychiatry", "General Practice"),
        typical_meds=(),
        seasonal_peak_months=(),
        base_weight=0.03,
    ),
]


FILIPINO_FIRST_NAMES = [
    "Juan", "Maria", "Jose", "Ana", "Liza", "Mark", "Grace", "Rodel", "Emmanuel",
    "Arlene", "Cesar", "Ramon", "Noel", "Glenda", "Evelyn", "Carmela", "Allan",
    "Rhea", "Alfred", "Jessa", "Arvin", "Kristine", "Jonas", "Jocelyn", "Mylene",
]
FILIPINO_LAST_NAMES = [
    "Dela Cruz", "Santos", "Reyes", "Garcia", "Mendoza", "Aquino", "Flores",
    "Ramos", "Torres", "Gonzales", "Navarro", "Fernandez", "Domingo", "Villanueva",
    "Castillo", "Bautista", "Villar", "Trinidad", "Valdez", "Marquez",
]


def _filipino_name(rng: random.Random) -> str:
    return f"{rng.choice(FILIPINO_FIRST_NAMES)} {rng.choice(FILIPINO_LAST_NAMES)}"


def _random_password(rng: random.Random) -> str:
    return "SeedPass" + "".join(rng.choices(string.ascii_letters + string.digits, k=10)) + "!"


def _create_user_safe(**kwargs) -> User:
    password = kwargs.pop("password", None)
    try:
        return User.objects.create_user(password=password, **kwargs)
    except AttributeError:
        user = User.objects.create(**kwargs)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


def _poisson_knuth(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    if lam > 80:
        return max(0, int(rng.gauss(lam, math.sqrt(lam))))
    l = math.exp(-lam)
    k = 0
    p = 1.0
    while p > l:
        k += 1
        p *= rng.random()
    return k - 1


def _clamp_int(v: float, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(round(v))))


def _date_range(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _seasonal_multiplier(day: date) -> float:
    month = day.month
    if month in (12, 1, 2):
        return 1.25
    if month in (6, 7, 8, 9):
        return 1.15
    return 1.0


def _weekday_multiplier(day: date) -> float:
    wd = day.weekday()
    if wd == 0:
        return 1.20
    if wd in (1, 2, 3):
        return 1.05
    if wd == 4:
        return 0.95
    return 0.75


def _holiday_staff_shortage(day: date) -> float:
    if day.month == 12 and 20 <= day.day <= 31:
        return 0.70
    if day.month == 1 and day.day <= 7:
        return 0.85
    return 1.0


def _emergency_spike_days(rng: random.Random, start: date, end: date, count_per_year: int = 6) -> set[date]:
    days = list(_date_range(start, end))
    years = sorted({d.year for d in days})
    emergency_days: set[date] = set()
    for y in years:
        pool = [d for d in days if d.year == y]
        if not pool:
            continue
        k = min(count_per_year, len(pool))
        emergency_days.update(rng.sample(pool, k=k))
    return emergency_days


def _pick_condition(rng: random.Random, day: date) -> ConditionSpec:
    weights = []
    for c in CONDITIONS:
        w = c.base_weight
        if c.seasonal_peak_months and day.month in c.seasonal_peak_months:
            w *= 1.7
        weights.append(w)
    total = sum(weights) or 1.0
    weights = [w / total for w in weights]
    return rng.choices(CONDITIONS, weights=weights, k=1)[0]


def _severity_for(rng: random.Random, condition: ConditionSpec, is_emergency_day: bool) -> str:
    if condition.department in ("ICU",):
        return rng.choices(["High", "Critical"], weights=[60, 40])[0]
    if is_emergency_day and condition.department in ("ER",):
        return rng.choices(["Medium", "High", "Critical"], weights=[40, 45, 15])[0]
    if condition.department == "ER":
        return rng.choices(["Low", "Medium", "High", "Critical"], weights=[10, 45, 35, 10])[0]
    return rng.choices(["Low", "Medium", "High", "Critical"], weights=[40, 42, 15, 3])[0]


def _outcome_for(rng: random.Random, severity: str, wait_minutes: int, medicine_shortage: bool) -> str:
    base = {
        "Low": (0.92, 0.07, 0.009, 0.001),
        "Medium": (0.82, 0.14, 0.03, 0.01),
        "High": (0.64, 0.25, 0.08, 0.03),
        "Critical": (0.40, 0.32, 0.18, 0.10),
    }.get(severity, (0.80, 0.15, 0.04, 0.01))
    recovered, ongoing, transferred, deceased = base
    if wait_minutes >= 180:
        recovered *= 0.90
        ongoing *= 1.10
        transferred *= 1.15
        deceased *= 1.25
    if medicine_shortage:
        recovered *= 0.92
        ongoing *= 1.06
        transferred *= 1.10
        deceased *= 1.20
    weights = [recovered, ongoing, transferred, deceased]
    s = sum(weights) or 1.0
    weights = [w / s for w in weights]
    return rng.choices(["Recovered", "Ongoing", "Transferred", "Deceased"], weights=weights, k=1)[0]


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "NA"
    if len(parts) == 1:
        return (parts[0][:2] or "NA").upper()
    return (parts[0][0] + parts[-1][0]).upper()


class Command(BaseCommand):
    help = "Seed comprehensive, realistic, 2+ year time-series datasets for predictive AI testing (staff + usage)."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--years", type=int, default=2)
        parser.add_argument("--end-date", type=str, default=None, help="End date (YYYY-MM-DD). Defaults to today.")

        parser.add_argument("--hospital-name", type=str, default="Catanduanes Medical Hospital")
        parser.add_argument("--hospital-address", type=str, default="San Isidro Village, Virac, Catanduanes")

        parser.add_argument("--doctors", type=int, default=40)
        parser.add_argument("--nurses", type=int, default=80)
        parser.add_argument("--patients", type=int, default=2000)
        parser.add_argument("--patient-records", type=int, default=20000)
        parser.add_argument("--reset", action="store_true", help="Delete previously seeded data for the specified seed before re-seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        seed = int(options["seed"])
        years = int(options["years"])
        if years < 2:
            raise CommandError("--years must be at least 2 to satisfy the time-series requirement.")

        end_date_str = options.get("end_date")
        if end_date_str:
            end_day = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_day = timezone.localdate()
        start_day = end_day - timedelta(days=365 * years)
        if (end_day - start_day).days < 730:
            raise CommandError("Generated range must span at least 2 years.")

        rng = random.Random(seed)

        hospital_name = options["hospital_name"].strip()
        hospital_address = options["hospital_address"].strip()
        doctors_n = max(1, int(options["doctors"]))
        nurses_n = max(1, int(options["nurses"]))
        patients_n = max(1, int(options["patients"]))
        patient_records_n = max(1, int(options["patient_records"]))
        reset = bool(options["reset"])

        hospital = self._get_or_create_hospital(hospital_name, hospital_address)
        dept_objs = self._ensure_departments()

        doctors = self._ensure_doctors(rng, seed, hospital_name, hospital_address, doctors_n)
        nurses = self._ensure_nurses(rng, seed, hospital_name, hospital_address, nurses_n, dept_objs)
        patients = self._ensure_patients(rng, seed, hospital_name, hospital_address, patients_n, doctors)

        if reset:
            self._reset_seeded_data(seed, doctors, nurses, patients, start_day, end_day)

        mapping = self._ensure_hospital_department_doctors(rng, hospital, dept_objs, doctors)
        self._seed_doctor_availability(rng, doctors, start_day, end_day)

        emergency_days = _emergency_spike_days(rng, start_day, end_day, count_per_year=6)

        self._emit_provider_schedules(seed, start_day, doctors, nurses, mapping)

        self._seed_time_series(
            rng=rng,
            seed=seed,
            start_day=start_day,
            end_day=end_day,
            patient_records_target=patient_records_n,
            hospital=hospital,
            dept_objs=dept_objs,
            doctors=doctors,
            nurses=nurses,
            patients=patients,
            mapping=mapping,
            emergency_days=emergency_days,
        )

        self._validate_seed(seed, start_day, end_day, doctors, nurses, patients)
        self.stdout.write(self.style.SUCCESS("Predictive AI dataset seeding completed."))

    def _get_or_create_hospital(self, name: str, address: str) -> Hospital:
        hospital, _ = Hospital.objects.get_or_create(
            official_name=name,
            defaults={
                "address": address,
                "license_id": f"SEED-LIC-{slugify(name)[:24]}",
                "license_document": "seed/license.pdf",
                "status": Hospital.Status.ACTIVE,
            },
        )
        if hospital.address != address:
            hospital.address = address
            hospital.save(update_fields=["address"])
        return hospital

    def _ensure_departments(self) -> Dict[str, Department]:
        dept_objs: Dict[str, Department] = {}
        for slug, label in DEPARTMENTS:
            obj, _ = Department.objects.get_or_create(
                slug=slugify(slug),
                defaults={
                    "name": label,
                    "description": f"{label} department",
                },
            )
            if obj.name != label:
                obj.name = label
                obj.save(update_fields=["name"])
            dept_objs[slug] = obj
        return dept_objs

    def _ensure_doctors(
        self,
        rng: random.Random,
        seed: int,
        hospital_name: str,
        hospital_address: str,
        count: int,
    ) -> List[GeneralDoctorProfile]:
        profiles: List[GeneralDoctorProfile] = []
        specialty_weights = [0.22, 0.16, 0.10, 0.08, 0.08, 0.08, 0.10, 0.07, 0.06, 0.05]
        for i in range(count):
            email = f"seed{seed}.doctor{i:03d}@medisync.local"
            full_name = f"Dr. {_filipino_name(rng)}"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "role": User.Role.DOCTOR,
                    "gender": rng.choice(["Male", "Female", "Other"]),
                    "hospital_name": hospital_name,
                    "hospital_address": hospital_address,
                    "verification_status": "approved",
                    "is_verified": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(_random_password(rng))
                user.save(update_fields=["password"])
            if user.full_name != full_name:
                user.full_name = full_name
                user.save(update_fields=["full_name"])
            profile, _ = GeneralDoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "license_number": f"SEED-DR-{seed}-{i:04d}",
                    "specialization": rng.choices(SPECIALTIES, weights=specialty_weights, k=1)[0],
                    "available_for_consultation": True,
                },
            )
            if not profile.specialization:
                profile.specialization = rng.choices(SPECIALTIES, weights=specialty_weights, k=1)[0]
                profile.save(update_fields=["specialization"])
            profiles.append(profile)
        return profiles

    def _ensure_nurses(
        self,
        rng: random.Random,
        seed: int,
        hospital_name: str,
        hospital_address: str,
        count: int,
        dept_objs: Dict[str, Department],
    ) -> List[NurseProfile]:
        profiles: List[NurseProfile] = []
        dept_slugs = [k for k in dept_objs.keys()]
        dept_weights = []
        for d in dept_slugs:
            if d in ("OPD", "ER", "Ward", "Pharmacy"):
                dept_weights.append(0.16)
            elif d in ("ICU", "Pediatrics", "Appointment"):
                dept_weights.append(0.10)
            else:
                dept_weights.append(0.06)
        s = sum(dept_weights) or 1.0
        dept_weights = [w / s for w in dept_weights]

        for i in range(count):
            email = f"seed{seed}.nurse{i:03d}@medisync.local"
            full_name = f"Nurse {_filipino_name(rng)}"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "role": User.Role.NURSE,
                    "gender": rng.choice(["Male", "Female", "Other"]),
                    "hospital_name": hospital_name,
                    "hospital_address": hospital_address,
                    "verification_status": "approved",
                    "is_verified": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(_random_password(rng))
                user.save(update_fields=["password"])
            chosen_dept = rng.choices(dept_slugs, weights=dept_weights, k=1)[0]
            profile, _ = NurseProfile.objects.get_or_create(
                user=user,
                defaults={
                    "license_number": f"SEED-RN-{seed}-{i:04d}",
                    "department": chosen_dept,
                },
            )
            if profile.department != chosen_dept:
                profile.department = chosen_dept
                profile.save(update_fields=["department"])
            profiles.append(profile)
        return profiles

    def _ensure_patients(
        self,
        rng: random.Random,
        seed: int,
        hospital_name: str,
        hospital_address: str,
        count: int,
        doctors: List[GeneralDoctorProfile],
    ) -> List[PatientProfile]:
        profiles: List[PatientProfile] = []
        for i in range(count):
            email = f"seed{seed}.patient{i:05d}@medisync.local"
            full_name = _filipino_name(rng)
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "role": User.Role.PATIENT,
                    "gender": rng.choices(["Male", "Female", "Other"], weights=[49, 49, 2], k=1)[0],
                    "hospital_name": hospital_name,
                    "hospital_address": hospital_address,
                    "verification_status": "approved",
                    "is_verified": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(_random_password(rng))
                user.save(update_fields=["password"])
            try:
                assigned_doctor = rng.choice(doctors).user
            except Exception:
                assigned_doctor = None
            profile, _ = PatientProfile.objects.get_or_create(
                user=user,
                defaults={
                    "blood_type": rng.choice([bt for bt, _ in PatientProfile.BloodType.choices]),
                    "medical_condition": "",
                    "hospital": hospital_name,
                    "insurance_provider": rng.choice(["Blue Shield", "Medicare", "Private", "PhilHealth"]),
                    "billing_amount": Decimal(str(_clamp_int(rng.gauss(5500, 2200), 500, 25000))),
                    "room_number": str(100 + (i % 250)),
                    "admission_type": rng.choice(["scheduled", "emergency"]),
                    "assigned_doctor": assigned_doctor,
                },
            )
            profiles.append(profile)
        return profiles

    def _reset_seeded_data(
        self,
        seed: int,
        doctors: List[GeneralDoctorProfile],
        nurses: List[NurseProfile],
        patients: List[PatientProfile],
        start_day: date,
        end_day: date,
    ) -> None:
        doctor_users = [d.user_id for d in doctors]
        nurse_users = [n.user_id for n in nurses]
        patient_users = [p.user_id for p in patients]
        patient_ids = [p.id for p in patients]

        PatientRecord.objects.filter(
            patient_id__in=patient_users,
            date_of_admission__date__range=(start_day, end_day),
        ).delete()
        UsageEvent.objects.filter(context__seed=seed).delete()

        ConsultationNotes.objects.filter(patient_id__in=patient_ids).delete()
        PatientAssignment.objects.filter(patient_id__in=patient_ids).delete()
        AppointmentManagement.objects.filter(patient_id__in=patient_ids).delete()
        QueueManagement.objects.filter(patient_id__in=patient_ids).delete()
        DoctorAvailability.objects.filter(doctor_id__in=[d.id for d in doctors], date__range=(start_day, end_day)).delete()
        DoctorTimeSlot.objects.filter(
            hospital_department_doctor__doctor_id__in=[d.id for d in doctors],
            date__range=(start_day, end_day),
        ).delete()
        self.stdout.write(self.style.WARNING(f"Reset completed for seed={seed}."))

    def _ensure_hospital_department_doctors(
        self,
        rng: random.Random,
        hospital: Hospital,
        dept_objs: Dict[str, Department],
        doctors: List[GeneralDoctorProfile],
    ) -> List[HospitalDepartmentDoctor]:
        dept_keys = list(dept_objs.keys())
        mappings: List[HospitalDepartmentDoctor] = []
        for idx, d in enumerate(doctors):
            if d.specialization == "Pediatrics":
                preferred = ["Pediatrics", "OPD"]
            elif d.specialization == "Cardiology":
                preferred = ["Cardiology", "ER", "OPD"]
            elif d.specialization == "Emergency Medicine":
                preferred = ["ER"]
            elif d.specialization == "Orthopedics":
                preferred = ["Surgery", "ER"]
            elif d.specialization == "Pulmonology":
                preferred = ["ER", "OPD"]
            elif d.specialization == "Psychiatry":
                preferred = ["OPD"]
            else:
                preferred = ["OPD", "Appointment"]

            k = 1 if rng.random() < 0.65 else 2
            chosen = []
            for dkey in preferred:
                if dkey in dept_keys:
                    chosen.append(dkey)
            while len(chosen) < k:
                chosen.append(rng.choice(dept_keys))
            chosen = list(dict.fromkeys(chosen))[:k]

            for dkey in chosen:
                obj, _ = HospitalDepartmentDoctor.objects.get_or_create(
                    hospital=hospital,
                    department=dept_objs[dkey],
                    doctor=d,
                    defaults={"status": "active", "capacity_limit": None},
                )
                mappings.append(obj)
        return mappings

    def _seed_doctor_availability(self, rng: random.Random, doctors: List[GeneralDoctorProfile], start_day: date, end_day: date) -> None:
        total_days = (end_day - start_day).days
        for d in doctors:
            blocked_days: set[date] = set()
            for _ in range(2):
                start = start_day + timedelta(days=rng.randint(0, max(1, total_days - 14)))
                for i in range(rng.randint(5, 10)):
                    blocked_days.add(start + timedelta(days=i))
            for _ in range(rng.randint(4, 10)):
                blocked_days.add(start_day + timedelta(days=rng.randint(0, total_days)))

            for day in blocked_days:
                DoctorAvailability.objects.get_or_create(
                    doctor=d,
                    date=day,
                    defaults={"reason": rng.choice(["Vacation", "Sick leave", "Training", "On-call recovery"]), "is_blocked": True},
                )

    def _emit_provider_schedules(
        self,
        seed: int,
        start_day: date,
        doctors: List[GeneralDoctorProfile],
        nurses: List[NurseProfile],
        mappings: List[HospitalDepartmentDoctor],
    ) -> None:
        occurred_at = timezone.make_aware(datetime.combine(start_day, time(8, 0)))
        dept_by_doctor: Dict[int, List[str]] = {}
        for m in mappings:
            dept_by_doctor.setdefault(m.doctor_id, []).append(m.department.slug)

        for d in doctors:
            local_rng = random.Random((seed << 32) ^ (d.id << 8))
            days = sorted(local_rng.sample([0, 1, 2, 3, 4, 5, 6], k=local_rng.choice([4, 5, 6])))
            shift = local_rng.choice([("08:00", "16:00"), ("09:00", "17:00"), ("10:00", "18:00")])
            self._log_usage_event(
                seed=seed,
                user=d.user,
                event_type="provider_schedule",
                created_at=occurred_at,
                context={
                    "provider_role": "doctor",
                    "doctor_profile_id": d.id,
                    "specialization": d.specialization or "General Practice",
                    "weekly_days": days,
                    "shift_start": shift[0],
                    "shift_end": shift[1],
                    "preferred_departments": dept_by_doctor.get(d.id, []),
                },
            )

        for n in nurses:
            local_rng = random.Random((seed << 32) ^ (n.id << 8) ^ 0xBEEF)
            days = sorted(local_rng.sample([0, 1, 2, 3, 4, 5, 6], k=local_rng.choice([4, 5, 6])))
            shift = local_rng.choice([("07:00", "15:00"), ("14:00", "22:00"), ("22:00", "06:00")])
            self._log_usage_event(
                seed=seed,
                user=n.user,
                event_type="provider_schedule",
                created_at=occurred_at,
                context={
                    "provider_role": "nurse",
                    "nurse_profile_id": n.id,
                    "department": n.department or "OPD",
                    "weekly_days": days,
                    "shift_start": shift[0],
                    "shift_end": shift[1],
                },
            )

    def _seed_time_series(
        self,
        *,
        rng: random.Random,
        seed: int,
        start_day: date,
        end_day: date,
        patient_records_target: int,
        hospital: Hospital,
        dept_objs: Dict[str, Department],
        doctors: List[GeneralDoctorProfile],
        nurses: List[NurseProfile],
        patients: List[PatientProfile],
        mapping: List[HospitalDepartmentDoctor],
        emergency_days: set[date],
    ) -> None:
        days = list(_date_range(start_day, end_day))
        target_per_day = patient_records_target / max(1, len(days))
        base_lambda = max(1.0, target_per_day)

        doctor_by_specialty: Dict[str, List[GeneralDoctorProfile]] = {}
        for d in doctors:
            doctor_by_specialty.setdefault(d.specialization or "General Practice", []).append(d)

        nurses_by_department: Dict[str, List[NurseProfile]] = {}
        for n in nurses:
            nurses_by_department.setdefault(n.department or "OPD", []).append(n)

        day_doctor_load: Dict[Tuple[int, date], int] = {}
        day_nurse_load: Dict[Tuple[int, date], int] = {}
        appt_sequence_by_day: Dict[date, int] = {}

        created_records = 0
        created_appointments = 0
        created_assignments = 0
        created_notes = 0
        created_usage_events = 0

        for day in days:
            is_emergency_day = day in emergency_days
            vol_mult = _seasonal_multiplier(day) * _weekday_multiplier(day)
            if is_emergency_day:
                vol_mult *= 1.8
            staff_mult = _holiday_staff_shortage(day)
            lam = base_lambda * vol_mult
            admissions = _poisson_knuth(rng, lam)
            if admissions <= 0 and rng.random() < 0.2:
                admissions = 1
            admissions = min(admissions, 250)

            if is_emergency_day or staff_mult < 0.9 or _seasonal_multiplier(day) > 1.0:
                scenario = "emergency" if is_emergency_day else ("staff_shortage" if staff_mult < 0.9 else "seasonal_peak")
                self._log_usage_event(
                    seed=seed,
                    user=None,
                    event_type="scenario_marker",
                    created_at=timezone.make_aware(datetime.combine(day, time(6, 0))),
                    context={
                        "scenario": scenario,
                        "date": day.isoformat(),
                        "seasonal_multiplier": float(_seasonal_multiplier(day)),
                        "weekday_multiplier": float(_weekday_multiplier(day)),
                        "staff_multiplier": float(staff_mult),
                        "expected_lambda": round(lam, 3),
                        "admissions": admissions,
                    },
                )

            available_doctors = self._available_doctors_for_day(rng, doctors, day, staff_mult)
            if not available_doctors:
                available_doctors = doctors[: max(1, len(doctors) // 4)]
            available_nurses = self._available_nurses_for_day(rng, nurses, day, staff_mult)
            if not available_nurses:
                available_nurses = nurses[: max(1, len(nurses) // 5)]

            base_wait = int((admissions / max(1, len(available_doctors))) * rng.uniform(9.0, 14.0))
            if is_emergency_day:
                base_wait = int(base_wait * 1.25)
            base_wait = _clamp_int(base_wait, 5, 240)

            day_metrics_doctor: Dict[int, Dict[str, Any]] = {}
            day_metrics_nurse: Dict[int, Dict[str, Any]] = {}

            for _ in range(admissions):
                patient = rng.choice(patients)
                condition = _pick_condition(rng, day)
                severity = _severity_for(rng, condition, is_emergency_day)

                dept_key = condition.department if condition.department in dept_objs else "OPD"
                doctor = self._assign_doctor(rng, condition, available_doctors, day_doctor_load, day)
                nurse = self._assign_nurse(rng, dept_key, available_nurses, nurses_by_department, day_nurse_load, day)

                wait_minutes = _clamp_int(base_wait * rng.uniform(0.6, 1.5), 0, 420)
                shortage_hit = False

                admit_dt = datetime.combine(day, time(rng.randint(7, 20), rng.choice([0, 15, 30, 45])))
                admit_dt = timezone.make_aware(admit_dt) if timezone.is_naive(admit_dt) else admit_dt

                meds_administered: List[str] = []
                if condition.typical_meds:
                    meds_administered.extend(list(condition.typical_meds))
                if severity in ("High", "Critical") and rng.random() < 0.35:
                    meds_administered.append("Omeprazole 20mg Capsule")
                if severity == "Critical" and rng.random() < 0.40:
                    meds_administered.append("Insulin Glargine 100U/mL" if rng.random() < 0.2 else "Cefuroxime 500mg Tablet")
                meds_administered = [m for m in meds_administered if m in MED_CATALOG]
                meds_administered = meds_administered[: rng.randint(0, 3)]

                for med in meds_administered:
                    patient.add_mar_entry(
                        {
                            "datetime_administered": (admit_dt + timedelta(minutes=rng.randint(0, 90))).isoformat(),
                            "name": med,
                            "dose": "1 unit",
                            "route": rng.choice(["PO", "IV", "IM", "INH"]),
                            "nurse_initials": _initials(nurse.user.full_name),
                            "prn_reason": "Symptom management" if rng.random() < 0.4 else None,
                            "prn_response": "Improved" if rng.random() < 0.6 else None,
                            "withheld_reason": None,
                        }
                    )
                    patient.save(update_fields=["medication_administration_records"])

                outcome = _outcome_for(rng, severity, wait_minutes, shortage_hit)
                patient.medical_condition = condition.name
                patient.medication = ", ".join(meds_administered)
                patient.date_of_admission = day
                if outcome in ("Recovered", "Transferred") and rng.random() < 0.75:
                    patient.discharge_date = day + timedelta(days=rng.randint(1, 12))
                    patient.set_discharge_summary(
                        {
                            "understanding_confirmed": rng.random() < 0.9,
                            "follow_up_appointments_made": rng.random() < 0.7,
                            "transportation_status": rng.choice(["family", "ambulance", "self"]),
                            "nurse_signature": _initials(nurse.user.full_name),
                            "patient_acknowledgment": rng.random() < 0.92,
                            "discharged_at": (datetime.combine(patient.discharge_date, time(10, 0))).isoformat(),
                        }
                    )
                patient.save(update_fields=["medical_condition", "medication", "date_of_admission", "discharge_date", "discharge_checklist_summary"])

                PatientRecord.objects.create(
                    patient_id=patient.user_id,
                    date_of_admission=admit_dt,
                    medical_condition=condition.name,
                    age=_clamp_int(rng.gauss(44, 18), 1, 92),
                    gender=rng.choices(["Male", "Female", "Other"], weights=[49, 49, 2], k=1)[0],
                    medication=rng.choice(meds_administered) if meds_administered and rng.random() < 0.8 else None,
                    severity=severity,
                    treatment_outcome=outcome,
                )
                created_records += 1

                assignment = PatientAssignment.objects.create(
                    specialization_required=rng.choice(condition.preferred_specialties) if condition.preferred_specialties else "General Practice",
                    assignment_reason=f"{condition.name} triage; severity={severity}; wait={wait_minutes}m",
                    status="completed" if outcome in ("Recovered", "Transferred") else rng.choice(["in_progress", "accepted"]),
                    priority=("urgent" if severity == "Critical" else ("high" if severity == "High" else "medium")),
                    assigned_by=nurse.user,
                    doctor=doctor,
                    patient=patient,
                )
                created_assignments += 1

                appt_status = "completed"
                if outcome == "Deceased":
                    appt_status = "completed"
                elif rng.random() < 0.06:
                    appt_status = "cancelled"
                elif rng.random() < 0.05:
                    appt_status = "no_show"
                elif rng.random() < 0.03:
                    appt_status = "rescheduled"

                appt_dt = admit_dt + timedelta(minutes=_clamp_int(wait_minutes * rng.uniform(0.6, 1.3), 0, 360))
                appt_time = time(appt_dt.hour, appt_dt.minute, 0)
                appt_sequence_by_day[day] = appt_sequence_by_day.get(day, 0) + 1
                appt_queue_number = int(f"{day.strftime('%y%m%d')}{appt_sequence_by_day[day]:04d}")

                time_slot = self._get_or_create_time_slot(
                    rng=rng,
                    doctor=doctor,
                    hospital=hospital,
                    dept_objs=dept_objs,
                    dept_key=dept_key,
                    appt_date=day,
                    appt_time=appt_time,
                )

                appt = AppointmentManagement.objects.create(
                    appointment_date=appt_dt,
                    appointment_type="emergency" if dept_key == "ER" or is_emergency_day else rng.choice(["consultation", "follow_up"]),
                    appointment_time=appt_time,
                    queue_number=appt_queue_number,
                    status=appt_status,
                    doctor=doctor,
                    patient=patient,
                    department=dept_key,
                    time_slot=time_slot,
                    reschedule_reason="Capacity constraint" if appt_status == "rescheduled" else None,
                    cancellation_reason="Staff shortage" if appt_status == "cancelled" and staff_mult < 0.9 else None,
                    checked_in_at=appt_dt if appt_status in ("checked_in", "in_progress", "completed") else None,
                    consultation_started_at=appt_dt + timedelta(minutes=rng.randint(1, 25)) if appt_status in ("in_progress", "completed") else None,
                    consultation_finished_at=appt_dt + timedelta(minutes=rng.randint(10, 55)) if appt_status == "completed" else None,
                )
                created_appointments += 1

                if appt_status in ("scheduled", "rescheduled", "completed") and rng.random() < 0.55:
                    try:
                        QueueManagement.objects.create(
                            patient=patient,
                            queue_number=rng.randint(1, 5000),
                            total_patients=admissions,
                            estimated_wait_time=timedelta(minutes=wait_minutes),
                            actual_wait_time=timedelta(minutes=_clamp_int(wait_minutes * rng.uniform(0.7, 1.4), 0, 480)),
                            expected_patients=admissions,
                            department="OPD" if dept_key not in ("Pharmacy", "Appointment") else dept_key,
                            status="completed" if appt_status == "completed" else "waiting",
                            position_in_queue=rng.randint(1, max(1, admissions)),
                            enqueue_time=admit_dt,
                            dequeue_time=appt_dt if appt_status == "completed" else None,
                            started_at=appt_dt if appt_status in ("in_progress", "completed") else None,
                            is_priority=(severity in ("High", "Critical") and rng.random() < 0.45),
                            priority_level=("senior" if rng.random() < 0.55 else "pwd"),
                            priority_position=rng.randint(0, 20),
                        )
                    except Exception:
                        pass

                note = ConsultationNotes.objects.create(
                    chief_complaint=f"{condition.name} symptoms",
                    history_of_present_illness=f"Onset within {rng.randint(1, 10)} day(s). Worsening with exertion." if condition.department != "OPD" else "Intermittent symptoms with mild progression.",
                    physical_examination=rng.choice(
                        [
                            "Vitals stable; no acute distress.",
                            "Febrile; tachycardic; mild dehydration.",
                            "Respiratory distress; wheezing noted.",
                            "Localized tenderness; guarding present.",
                        ]
                    ),
                    diagnosis=f"{condition.name} ({severity})",
                    treatment_plan=rng.choice(
                        [
                            "Supportive care; follow-up in 7 days.",
                            "Start antibiotic course; reassess in 48 hours.",
                            "Admit for observation; monitor vitals and labs.",
                            "Escalate to specialist; consider imaging and labs.",
                        ]
                    ),
                    medications_prescribed=", ".join(meds_administered),
                    follow_up_instructions="Return immediately if symptoms worsen. Maintain hydration and adherence to medications.",
                    additional_notes="Consider seasonal trends and local outbreak alerts.",
                    status="completed",
                    completed_at=appt_dt + timedelta(minutes=rng.randint(15, 90)),
                    assignment=assignment,
                    doctor=doctor,
                    patient=patient,
                )
                created_notes += 1

                day_metrics_doctor.setdefault(doctor.id, {"patients": 0, "critical": 0, "avg_wait_sum": 0, "outcomes": {"Recovered": 0, "Ongoing": 0, "Transferred": 0, "Deceased": 0}})
                dmet = day_metrics_doctor[doctor.id]
                dmet["patients"] += 1
                dmet["avg_wait_sum"] += wait_minutes
                if severity == "Critical":
                    dmet["critical"] += 1
                dmet["outcomes"][outcome] += 1

                day_metrics_nurse.setdefault(nurse.id, {"meds": 0, "patients_touched": 0})
                nmet = day_metrics_nurse[nurse.id]
                nmet["patients_touched"] += 1
                nmet["meds"] += len(meds_administered)

            created_usage_events += self._emit_daily_provider_metrics(seed, day, day_metrics_doctor, day_metrics_nurse, is_emergency_day, staff_mult)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created: patient_records={created_records}, appointments={created_appointments}, assignments={created_assignments}, notes={created_notes}, usage_events={created_usage_events}"
            )
        )

    def _available_doctors_for_day(self, rng: random.Random, doctors: List[GeneralDoctorProfile], day: date, staff_mult: float) -> List[GeneralDoctorProfile]:
        blocked_ids = set(
            DoctorAvailability.objects.filter(doctor_id__in=[d.id for d in doctors], date=day, is_blocked=True).values_list("doctor_id", flat=True)
        )
        pool = [d for d in doctors if d.id not in blocked_ids]
        if staff_mult < 1.0:
            keep = max(1, int(round(len(pool) * staff_mult)))
            pool = rng.sample(pool, k=min(keep, len(pool)))
        return pool

    def _available_nurses_for_day(self, rng: random.Random, nurses: List[NurseProfile], day: date, staff_mult: float) -> List[NurseProfile]:
        pool = nurses[:]
        if staff_mult < 1.0:
            keep = max(1, int(round(len(pool) * staff_mult)))
            pool = rng.sample(pool, k=min(keep, len(pool)))
        return pool

    def _assign_doctor(
        self,
        rng: random.Random,
        condition: ConditionSpec,
        available_doctors: List[GeneralDoctorProfile],
        load: Dict[Tuple[int, date], int],
        day: date,
    ) -> GeneralDoctorProfile:
        preferred = [d for d in available_doctors if d.specialization in condition.preferred_specialties]
        candidates = preferred or available_doctors
        if not candidates:
            return rng.choice(available_doctors)
        candidates = sorted(candidates, key=lambda d: load.get((d.id, day), 0))
        pick = candidates[: max(2, min(8, len(candidates)))]
        chosen = rng.choice(pick)
        load[(chosen.id, day)] = load.get((chosen.id, day), 0) + 1
        return chosen

    def _assign_nurse(
        self,
        rng: random.Random,
        dept_key: str,
        available_nurses: List[NurseProfile],
        nurses_by_department: Dict[str, List[NurseProfile]],
        load: Dict[Tuple[int, date], int],
        day: date,
    ) -> NurseProfile:
        preferred = [n for n in available_nurses if (n.department or "OPD") == dept_key]
        candidates = preferred or available_nurses
        if not candidates:
            candidates = nurses_by_department.get("OPD") or available_nurses
        candidates = sorted(candidates, key=lambda n: load.get((n.id, day), 0))
        pick = candidates[: max(2, min(10, len(candidates)))]
        chosen = rng.choice(pick)
        load[(chosen.id, day)] = load.get((chosen.id, day), 0) + 1
        return chosen

    def _get_or_create_time_slot(
        self,
        *,
        rng: random.Random,
        doctor: GeneralDoctorProfile,
        hospital: Hospital,
        dept_objs: Dict[str, Department],
        dept_key: str,
        appt_date: date,
        appt_time: time,
    ) -> Optional[DoctorTimeSlot]:
        dept_key = dept_key if dept_key in dept_objs else "OPD"
        mapping = HospitalDepartmentDoctor.objects.filter(
            hospital=hospital,
            doctor=doctor,
            department=dept_objs[dept_key],
            status="active",
        ).first()
        if not mapping:
            return None

        start_hour = appt_time.hour
        slot_start = time(start_hour, 0, 0)
        slot_end = time(min(23, start_hour + 1), 0, 0)
        capacity = 1
        if dept_key in ("OPD", "Appointment"):
            capacity = 4
        elif dept_key in ("ER",):
            capacity = 6
        elif dept_key in ("ICU",):
            capacity = 2

        slot, _ = DoctorTimeSlot.objects.get_or_create(
            hospital_department_doctor=mapping,
            date=appt_date,
            start_time=slot_start,
            end_time=slot_end,
            defaults={"capacity": capacity, "booked_count": 0, "is_available": True},
        )
        if slot.capacity != capacity:
            slot.capacity = capacity
            slot.save(update_fields=["capacity"])
        if slot.booked_count < slot.capacity:
            slot.booked_count += 1
            slot.is_available = slot.booked_count < slot.capacity
            slot.save(update_fields=["booked_count", "is_available"])
        return slot

    def _log_usage_event(self, *, seed: int, user: Optional[User], event_type: str, created_at: datetime, context: Dict[str, Any]) -> int:
        ctx = dict(context or {})
        ctx["seed"] = seed
        ctx["occurred_at"] = created_at.isoformat()
        UsageEvent.objects.create(
            user=user,
            event_type=event_type,
            source="seed_predictive_ai_data",
            session_id=f"seed-{seed}",
            context=ctx,
        )
        return 1

    def _emit_daily_provider_metrics(
        self,
        seed: int,
        day: date,
        doctor_metrics: Dict[int, Dict[str, Any]],
        nurse_metrics: Dict[int, Dict[str, Any]],
        is_emergency_day: bool,
        staff_mult: float,
    ) -> int:
        created = 0
        ts = timezone.make_aware(datetime.combine(day, time(23, 10)))
        for doctor_id, m in doctor_metrics.items():
            patients = int(m.get("patients") or 0)
            avg_wait = float(m.get("avg_wait_sum") or 0) / max(1, patients)
            outcome_counts = m.get("outcomes") or {}
            recovered = int(outcome_counts.get("Recovered") or 0)
            deceased = int(outcome_counts.get("Deceased") or 0)
            score = max(0.0, min(1.0, (recovered / max(1, patients)) - (deceased / max(1, patients)) * 0.6))
            overtime_min = max(0, int(round((patients - 12) * 6 * (1.0 / max(0.55, staff_mult)))))

            doctor_user = (
                GeneralDoctorProfile.objects.select_related("user")
                .filter(id=doctor_id)
                .values_list("user", flat=True)
                .first()
            )

            created += self._log_usage_event(
                seed=seed,
                user=User.objects.filter(id=doctor_user).first() if doctor_user else None,
                event_type="provider_daily_metrics",
                created_at=ts,
                context={
                    "provider_role": "doctor",
                    "doctor_profile_id": doctor_id,
                    "date": day.isoformat(),
                    "patients_seen": patients,
                    "avg_wait_minutes": round(avg_wait, 1),
                    "critical_cases": int(m.get("critical") or 0),
                    "outcomes": outcome_counts,
                    "performance_score": round(score, 3),
                    "overtime_minutes": overtime_min,
                    "scenario": "emergency" if is_emergency_day else ("staff_shortage" if staff_mult < 0.9 else "normal"),
                },
            )

        for nurse_id, m in nurse_metrics.items():
            meds = int(m.get("meds") or 0)
            patients_touched = int(m.get("patients_touched") or 0)
            overtime_min = max(0, int(round((patients_touched - 18) * 4 * (1.0 / max(0.55, staff_mult)))))
            local_rng = random.Random((seed << 32) ^ (nurse_id << 16) ^ int(day.strftime("%Y%m%d")))
            med_error = max(0.0, min(0.06, local_rng.random() * 0.02 + (0.02 if overtime_min > 60 else 0.0)))
            nurse_user = (
                NurseProfile.objects.select_related("user")
                .filter(id=nurse_id)
                .values_list("user", flat=True)
                .first()
            )
            created += self._log_usage_event(
                seed=seed,
                user=User.objects.filter(id=nurse_user).first() if nurse_user else None,
                event_type="provider_daily_metrics",
                created_at=ts,
                context={
                    "provider_role": "nurse",
                    "nurse_profile_id": nurse_id,
                    "date": day.isoformat(),
                    "patients_touched": patients_touched,
                    "meds_administered": meds,
                    "med_error_rate_est": round(med_error, 4),
                    "overtime_minutes": overtime_min,
                    "scenario": "emergency" if is_emergency_day else ("staff_shortage" if staff_mult < 0.9 else "normal"),
                },
            )
        return created

    def _validate_seed(
        self,
        seed: int,
        start_day: date,
        end_day: date,
        doctors: List[GeneralDoctorProfile],
        nurses: List[NurseProfile],
        patients: List[PatientProfile],
    ) -> None:
        if not PatientRecord.objects.filter(date_of_admission__date__range=(start_day, end_day)).exists():
            raise CommandError("No PatientRecord created in the expected range.")
        sample = patients[: min(40, len(patients))]
        errs = 0
        for p in sample:
            ok, errors = p.validate_nurse_forms_minimal()
            if not ok:
                errs += len(errors)
        if errs:
            raise CommandError(f"Seeded nurse forms failed minimal validation with {errs} error(s).")
        if not UsageEvent.objects.filter(context__seed=seed).exists():
            raise CommandError("No UsageEvent created with the seed marker.")
