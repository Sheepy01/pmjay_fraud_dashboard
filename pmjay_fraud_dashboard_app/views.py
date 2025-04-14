from django.db.models import Sum, Q, Avg, F, Func, Count
from django.shortcuts import render
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.utils.timezone import now, timedelta
from django.http import JsonResponse
from datetime import timedelta
from django.db.models import Case, When, Value, CharField
from .models import Last24Hour, SuspiciousHospital, HospitalBeds

class Upper(Func):
    function = 'UPPER'
    template = '%(function)s(%(expressions)s)'

def get_districts(request):
    districts = Last24Hour.objects.values_list('district_name', flat=True).distinct()
    district_list = [d for d in districts if d]  # Remove None/empty values
    return JsonResponse({'districts': district_list})

def get_flagged_claims(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    # Only include private hospitals (type "P")
    suspicious_hospitals = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    flagged_cases = Last24Hour.objects.filter(
        hospital_id__in=suspicious_hospitals,
        hospital_type='P'  # Add this filter
    )
    
    if districts:
        flagged_cases = flagged_cases.filter(district_name__in=districts)
    
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    thirty_days_ago = now - timedelta(days=30)
    
    data = {
        'total': flagged_cases.count(),
        'yesterday': flagged_cases.filter(
            preauth_initiated_date__date=yesterday.date()
        ).count(),
        'last_30_days': flagged_cases.filter(
            preauth_initiated_date__gte=thirty_days_ago
        ).count()
    }
    
    return JsonResponse(data)

def get_flagged_claims_details(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    # Prefetch hospital names in one query
    hospital_names = {
        h.hospital_id: h.hospital_name 
        for h in SuspiciousHospital.objects.all()
    }
    
    flagged_cases = Last24Hour.objects.filter(
        hospital_id__in=hospital_names.keys(),
        hospital_type='P'
    )
    
    if districts:
        flagged_cases = flagged_cases.filter(district_name__in=districts)
    
    data = []
    for idx, case in enumerate(flagged_cases[:500], 1):
        data.append({
            'serial_no': idx,
            'claim_id': case.registration_id or case.case_id or 'N/A',
            'patient_name': case.patient_name or f"Patient {case.member_id}" or 'N/A',
            'hospital_name': hospital_names.get(case.hospital_id, case.hospital_name or 'N/A'),
            'district_name': case.district_name or 'N/A',
            'amount': case.claim_initiated_amount or 0,
            'reason': 'Suspicious hospital'
        })
    
    return JsonResponse(data, safe=False)

# Add to views.py
def get_flagged_claims_by_district(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    queryset = Last24Hour.objects.filter(
        hospital_id__in=SuspiciousHospital.objects.values('hospital_id'),
        hospital_type='P'
    )
    
    if districts:
        queryset = queryset.filter(district_name__in=districts)
    
    district_data = queryset.values('district_name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    data = {
        'districts': [item['district_name'] or 'Unknown' for item in district_data],
        'counts': [item['count'] for item in district_data]
    }
    
    return JsonResponse(data)

def get_high_value_claims(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    # Base queryset - only private hospitals
    cases = Last24Hour.objects.filter(hospital_type='P')
    
    # Apply district filter if specified
    if districts:
        cases = cases.filter(district_name__in=districts)
    
    # Get time thresholds
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    thirty_days_ago = now - timedelta(days=30)
    
    # Surgical cases (≥100,000)
    surgical_cases = cases.filter(
        case_type__iexact='SURGICAL',
        claim_initiated_amount__gte=100000
    )
    
    # Medical cases (≥25,000)
    medical_cases = cases.filter(
        case_type__iexact='MEDICAL',
        claim_initiated_amount__gte=25000
    )
    
    # Calculate metrics
    surgical_total = surgical_cases.aggregate(
        Sum('claim_initiated_amount')
    )['claim_initiated_amount__sum'] or 0
    
    medical_total = medical_cases.aggregate(
        Sum('claim_initiated_amount')
    )['claim_initiated_amount__sum'] or 0
    
    data = {
        # Main card - show exact count (not sum of amounts)
        'total_count': surgical_cases.count() + medical_cases.count(),
        
        # Time period counts
        'yesterday_count': (
            surgical_cases.filter(preauth_initiated_date__date=yesterday.date()).count() +
            medical_cases.filter(preauth_initiated_date__date=yesterday.date()).count()
        ),
        'last_30_days_count': (
            surgical_cases.filter(preauth_initiated_date__gte=thirty_days_ago).count() +
            medical_cases.filter(preauth_initiated_date__gte=thirty_days_ago).count()
        ),
        
        # Breakdown
        'surgical': {
            'count': surgical_cases.count(),
            'amount': surgical_total,
            'yesterday': surgical_cases.filter(preauth_initiated_date__date=yesterday.date()).count(),
            'last_30_days': surgical_cases.filter(preauth_initiated_date__gte=thirty_days_ago).count()
        },
        'medical': {
            'count': medical_cases.count(),
            'amount': medical_total,
            'yesterday': medical_cases.filter(preauth_initiated_date__date=yesterday.date()).count(),
            'last_30_days': medical_cases.filter(preauth_initiated_date__gte=thirty_days_ago).count()
        }
    }
    
    return JsonResponse(data)

def get_hospital_bed_cases(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    thirty_days_ago = today - timedelta(days=30)

    # 1. Get all hospital bed data in one query
    hospitals_with_beds = HospitalBeds.objects.all().values('hospital_id', 'bed_strength')
    hospital_ids = [h['hospital_id'] for h in hospitals_with_beds]
    bed_strengths = {h['hospital_id']: h['bed_strength'] for h in hospitals_with_beds}
    
    # 2. Get all hospital names in one query
    hospital_names = dict(Last24Hour.objects.filter(
        hospital_id__in=hospital_ids
    ).values_list('hospital_id', 'hospital_name').distinct())
    
    # 3. Get today's admissions count per hospital in one query
    today_admissions = Last24Hour.objects.filter(
        Q(hospital_id__in=hospital_ids) & 
        (Q(admission_date__date=today) | 
         Q(admission_date__isnull=True, preauth_initiated_date__date=today))
    ).values('hospital_id').annotate(count=Count('id'))
    
    # 4. Find violating hospitals today
    violating_hospitals_today = [
        admission['hospital_id'] for admission in today_admissions
        if admission['count'] > bed_strengths.get(admission['hospital_id'], 0)
    ]
    
    # 5. Get cases for violating hospitals (with district filter if specified)
    cases = Last24Hour.objects.filter(
        hospital_id__in=violating_hospitals_today,
        hospital_type='P'
    )
    if districts:
        cases = cases.filter(district_name__in=districts)
    
    # 6. Get yesterday's admissions count per hospital in one query
    yesterday_admissions = Last24Hour.objects.filter(
        Q(hospital_id__in=hospital_ids) & 
        (Q(admission_date__date=yesterday) | 
         Q(admission_date__isnull=True, preauth_initiated_date__date=yesterday))
    ).values('hospital_id').annotate(count=Count('id'))
    
    # 7. Find violating hospitals yesterday
    violating_hospitals_yesterday = [
        admission['hospital_id'] for admission in yesterday_admissions
        if admission['count'] > bed_strengths.get(admission['hospital_id'], 0)
    ]
    
    # 8. Count violations in last 30 days (optimized)
    date_range = [today - timedelta(days=n) for n in range(30)]
    violations_last_30_days = 0
    
    # Get all admissions in date range
    all_admissions = Last24Hour.objects.filter(
        Q(hospital_id__in=hospital_ids) & 
        (Q(admission_date__date__in=date_range) | 
        Q(admission_date__isnull=True, preauth_initiated_date__date__in=date_range))
    ).values('hospital_id', 'admission_date', 'preauth_initiated_date')
    
    # Process in memory
    violations_by_date = set()
    for admission in all_admissions:
        day = admission['admission_date'] or admission['preauth_initiated_date']
        if day:
            # Count admissions per hospital per day
            admissions_count = Last24Hour.objects.filter(
                Q(hospital_id=admission['hospital_id']) & 
                (Q(admission_date__date=day) | 
                 Q(admission_date__isnull=True, preauth_initiated_date__date=day))
            ).count()
            
            if admissions_count > bed_strengths.get(admission['hospital_id'], 0):
                violations_by_date.add(day)
    
    violations_last_30_days = len(violations_by_date)
    
    # 9. Prepare violation details for today
    violations_today = []
    for hospital_id in violating_hospitals_today:
        admissions = next(
            (a['count'] for a in today_admissions if a['hospital_id'] == hospital_id),
            0
        )
        
        violations_today.append({
            'hospital': hospital_names.get(hospital_id, f"Hospital {hospital_id}"),
            'admissions': admissions,
            'bed_strength': bed_strengths.get(hospital_id, 0)
        })
    
    data = {
        'total': cases.count(),
        'yesterday': len(violating_hospitals_yesterday),
        'last_30_days': violations_last_30_days,
        'violations_today': violations_today
    }
    
    return JsonResponse(data)

def get_family_id_cases(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    thirty_days_ago = today - timedelta(days=30)
    
    # Find suspicious families (same family, same day, >2 cases)
    suspicious_families = (
        Last24Hour.objects
        .filter(hospital_type='P')
        .annotate(day=TruncDate('preauth_initiated_date'))
        .values('family_id', 'day')
        .annotate(count=Count('id'))
        .filter(count__gt=2)
    )
    
    # Get all cases from suspicious families
    cases = Last24Hour.objects.filter(
        Q(hospital_type='P') &
        Q(family_id__in=[x['family_id'] for x in suspicious_families]) &
        Q(preauth_initiated_date__date=today)
    )
    
    if districts:
        cases = cases.filter(district_name__in=districts)
    
    # Count yesterday's suspicious cases
    yesterday_cases = Last24Hour.objects.filter(
        Q(hospital_type='P') &
        Q(family_id__in=(
            Last24Hour.objects
            .filter(
                Q(hospital_type='P') & 
                Q(preauth_initiated_date__date=yesterday)
            )
            .annotate(day=TruncDate('preauth_initiated_date'))
            .values('family_id', 'day')
            .annotate(count=Count('id'))
            .filter(count__gt=2)
            .values_list('family_id', flat=True)
        )) &
        Q(preauth_initiated_date__date=yesterday)
    ).count()
    
    # Count violations in last 30 days
    violations_last_30_days = (
        Last24Hour.objects
        .filter(
            Q(hospital_type='P') & 
            Q(preauth_initiated_date__gte=thirty_days_ago)
        )
        .annotate(day=TruncDate('preauth_initiated_date'))
        .values('family_id', 'day')
        .annotate(count=Count('id'))
        .filter(count__gt=2)
        .values('day')
        .distinct()
        .count()
    )
    
    # Prepare violation details
    violations = []
    for family in suspicious_families:
        hospitals = (
            Last24Hour.objects
            .filter(
                Q(family_id=family['family_id']) &
                Q(preauth_initiated_date__date=family['day'])
            )
            .values_list('hospital_name', flat=True)
            .distinct()
        )
        
        violations.append({
            'family_id': family['family_id'],
            'date': family['day'],
            'count': family['count'],
            'hospitals': list(hospitals)
        })
    
    data = {
        'total': cases.count(),
        'yesterday': yesterday_cases,
        'last_30_days': violations_last_30_days,
        'violations': violations
    }
    
    return JsonResponse(data)

def get_geo_anomalies(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    thirty_days_ago = today - timedelta(days=30)

    # Base queryset - only private hospitals with state mismatches
    anomalies = Last24Hour.objects.filter(
        hospital_type='P',
        state_name__isnull=False,
        hospital_state_name__isnull=False
    ).exclude(state_name=F('hospital_state_name'))

    # Apply district filter (patient's district)
    if districts:
        anomalies = anomalies.filter(district_name__in=districts)

    # Today's count
    today_anomalies = anomalies.filter(
        Q(admission_date__date=today) | 
        Q(admission_date__isnull=True, preauth_initiated_date__date=today)
    )
    
    # Yesterday's count
    yesterday_anomalies = anomalies.filter(
        Q(admission_date__date=yesterday) | 
        Q(admission_date__isnull=True, preauth_initiated_date__date=yesterday)
    )
    
    # Last 30 days count
    last_30_days_anomalies = anomalies.filter(
        Q(admission_date__gte=thirty_days_ago) | 
        Q(admission_date__isnull=True, preauth_initiated_date__gte=thirty_days_ago)
    )

    # Get state mismatch statistics
    state_mismatches = (
        anomalies.values('state_name', 'hospital_state_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]  # Top 10 mismatch pairs
    )

    data = {
        'total': today_anomalies.count(),
        'yesterday': yesterday_anomalies.count(),
        'last_30_days': last_30_days_anomalies.count(),
        'state_mismatches': list(state_mismatches)
    }

    return JsonResponse(data)

def get_ophthalmology_cases(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    thirty_days_ago = today - timedelta(days=30)

    # Base queryset - private hospitals with cataract procedure
    base_qs = Last24Hour.objects.filter(
        hospital_type='P',
        procedure_code='SE020A'  # Ophthalmology cataract code
    )
    
    if districts:
        base_qs = base_qs.filter(district_name__in=districts)

    # 1. Age <40 cases
    age_cases = base_qs.filter(age_years__lt=40)
    
    # 2. OT Cases (more than 30 per OT per surgeon)
    ot_violations = base_qs.values('hospital_id').annotate(
        ot_count=Count('id')
    ).filter(ot_count__gt=30)
    
    # 3. Preauth time violations (outside 8AM-6PM)
    preauth_violations = base_qs.exclude(
        preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$'
    )

    # Time period filters
    def apply_time_filter(qs, day):
        return qs.filter(
            Q(admission_date__date=day) | 
            Q(admission_date__isnull=True, preauth_initiated_date__date=day)
        )
    
    # Calculate totals
    age_total = age_cases.count()
    ot_total = ot_violations.count()
    preauth_total = preauth_violations.count()
    
    # MAIN CARD VALUE = Sum of all violations
    main_card_total = age_total + ot_total + preauth_total

    data = {
        'total': main_card_total,  # Sum of all violations
        'age_under_40': {
            'total': age_total,
            'yesterday': apply_time_filter(age_cases, yesterday).count(),
            'last_30_days': apply_time_filter(age_cases, thirty_days_ago).count()
        },
        'ot_cases': {
            'total': ot_total,
            'yesterday': apply_time_filter(ot_violations, yesterday).count(),
            'last_30_days': apply_time_filter(ot_violations, thirty_days_ago).count(),
            'violations': list(ot_violations.values('hospital_name', 'ot_count')[:5])
        },
        'preauth_time': {
            'total': preauth_total,
            'yesterday': apply_time_filter(preauth_violations, yesterday).count(),
            'last_30_days': apply_time_filter(preauth_violations, thirty_days_ago).count(),
            'avg_violation_hours': "N/A" 
        }
    }
    
    return JsonResponse(data)

def get_age_distribution(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    queryset = Last24Hour.objects.filter(
        hospital_id__in=SuspiciousHospital.objects.values('hospital_id'),
        hospital_type='P'
    )
    
    if districts:
        queryset = queryset.filter(district_name__in=districts)
    
    # Define age groups
    age_groups = {
        '15-29': Count('id', filter=Q(age_years__gte=15, age_years__lte=29)),
        '30-44': Count('id', filter=Q(age_years__gte=30, age_years__lte=44)),
        '45-59': Count('id', filter=Q(age_years__gte=45, age_years__lte=59)),
        '60+': Count('id', filter=Q(age_years__gte=60))
    }
    
    # Get counts for each age group
    age_data = queryset.aggregate(**age_groups)
    
    return JsonResponse({
        'labels': list(age_data.keys()),
        'data': list(age_data.values()),
        'colors': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
    })

def get_gender_distribution(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    queryset = Last24Hour.objects.filter(
        hospital_id__in=SuspiciousHospital.objects.values('hospital_id'),
        hospital_type='P'
    )
    
    if districts:
        queryset = queryset.filter(district_name__in=districts)
    
    # Get raw gender counts
    gender_data = queryset.values('gender').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Standardize gender labels and aggregate
    standardized_data = {
        'Male': 0,
        'Female': 0,
        'Unknown': 0
    }
    
    gender_mappings = {
        'M': 'Male',
        'MALE': 'Male',
        'F': 'Female',
        'FEMALE': 'Female'
    }
    
    for item in gender_data:
        gender = str(item['gender']).strip().upper() if item['gender'] else 'Unknown'
        
        if gender in gender_mappings:
            standardized_data[gender_mappings[gender]] += item['count']
        else:
            # Only count as Unknown if not a recognized male/female value
            if gender not in ['MALE', 'FEMALE', 'M', 'F']:
                standardized_data['Unknown'] += item['count']
    
    # Remove Unknown if count is 0
    if standardized_data['Unknown'] == 0:
        del standardized_data['Unknown']
    
    # Prepare response
    labels = []
    data = []
    
    if standardized_data.get('Male', 0) > 0:
        labels.append('Male')
        data.append(standardized_data['Male'])
    
    if standardized_data.get('Female', 0) > 0:
        labels.append('Female')
        data.append(standardized_data['Female'])
    
    if standardized_data.get('Unknown', 0) > 0:
        labels.append('Unknown')
        data.append(standardized_data['Unknown'])
    
    return JsonResponse({
        'labels': labels,
        'data': data,
        'colors': ['#36A2EB', '#FF6384', '#CCCCCC'][:len(labels)]
    })

def dashboard_view(request):
    return render(request, 'dashboard.html') 

# def flagged_claims_chart_data(request):
#     district_filter = request.GET.get('district', '').strip()
#     queryset = Last24Hour.objects.filter(hospital_type="P")
#     if district_filter and district_filter.lower() != "all":
#         queryset = queryset.filter(district_name__iexact=district_filter)
#     flagged_hospitals = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
#     flagged_claims = queryset.filter(hospital_id__in=flagged_hospitals)
#     chart_data = flagged_claims.values('district_name').annotate(count=Count('id')).order_by('-count')
#     labels = [entry['district_name'] for entry in chart_data]
#     values = [entry['count'] for entry in chart_data]
#     return JsonResponse({'labels': labels, 'values': values})

# def geo_anomalies_chart_data(request):
#     district_filter = request.GET.get("district", "").strip()
#     queryset = Last24Hour.objects.filter(hospital_type="P")
#     if district_filter and district_filter.lower() != "all":
#         queryset = queryset.filter(district_name__iexact=district_filter)
#     geo_anomalies = (
#         queryset
#         .annotate(
#             state_name_upper=Upper('state_name'),
#             hospital_state_name_upper=Upper('hospital_state_name')
#         )
#         .exclude(state_name_upper=F('hospital_state_name_upper'))
#         .values('district_name')
#         .annotate(count=Count('id'))
#         .order_by('-count')
#     )
#     labels = [entry["district_name"] for entry in geo_anomalies if entry["district_name"]]
#     values = [entry["count"] for entry in geo_anomalies]

#     return JsonResponse({
#         "labels": labels,
#         "values": values
#     })

# def get_rule_counts(df, district=None):
#     """
#     Given a DataFrame (df) of Last24Hour records (already converted and cleaned),
#     optionally filters by district and returns a dictionary with counts for each of the 5 rules:
#       1) Ophthalmology OT Cases
#       2) Ophthalmology Preauth Time
#       3) Ophthalmology Age Cases
#       4) Emergency Cases
#       5) Family ID Cases
#     """
#     # Optionally filter by district if provided
#     if district and district.strip() != "":
#         # Clean district names and filter
#         df['district_name'] = df['district_name'].fillna('').astype(str).str.upper().str.strip()
#         district = district.strip().upper()
#         df = df[df['district_name'] == district]
#         if df.empty:
#             return {'ophtho_ot': 0, 'ophtho_time': 0, 'ophtho_age': 0, 'emergency': 0, 'family': 0}

#     # ---- Rule 1: Ophthalmology OT Cases ----
#     df_ophtho = df[df['procedure_code'] == 'SE020A'].copy()
#     grp = df_ophtho.groupby(['hospital_id', 'date_only']).size().reset_index(name='daily_count')
#     df_ophtho = df_ophtho.merge(grp, on=['hospital_id', 'date_only'], how='left')

#     sh_qs = SuspiciousHospital.objects.all().values('hospital_id', 'number_of_ot', 'number_of_surgeons')
#     threshold_dict = {
#         str(row['hospital_id']).upper(): (row.get('number_of_ot') or 0) * (row.get('number_of_surgeons') or 0) * 30
#         for row in sh_qs
#     }
#     df_ophtho['flag_ot'] = df_ophtho.apply(
#         lambda row: row['daily_count'] > threshold_dict.get(str(row['hospital_id']).upper(), 0),
#         axis=1
#     )
#     count_ophtho_ot = df_ophtho[df_ophtho['flag_ot']].shape[0]
#     df.loc[df_ophtho[df_ophtho['flag_ot']].index, 'is_unusual'] = True

#     # ---- Rule 2: Ophthalmology Preauth Time (8AM–6PM) ----
#     df_ophtho_time = df[(df['procedure_code'] == 'SE020A') & (df['hour'].between(8, 17))]
#     count_ophtho_time = df_ophtho_time.shape[0]
#     df.loc[df_ophtho_time.index, 'is_unusual'] = True

#     # ---- Rule 3: Ophthalmology Age Cases ----
#     df_ophtho_age = df[(df['procedure_code'] == 'SE020A') & (df['age_years'] < 40)]
#     count_ophtho_age = df_ophtho_age.shape[0]
#     df.loc[df_ophtho_age.index, 'is_unusual'] = True

#     # ---- Rule 4: Emergency Cases ----
#     df_emergency = df[(df['admission_type'] == 'E') &
#                       (df['procedure_details'].str.contains('cataract|oncology|dialysis', case=False, na=False))]
#     count_emergency = df_emergency.shape[0]
#     df.loc[df_emergency.index, 'is_unusual'] = True

#     # ---- Rule 5: Family ID Cases ----
#     if 'family_id' not in df.columns:
#         df['family_id'] = ''
#     grp_fam = df.groupby(['family_id', 'date_only']).size().reset_index(name='fam_count')
#     df = df.merge(grp_fam, on=['family_id', 'date_only'], how='left')
#     df_family_repeat = df[df['fam_count'] > 2]
#     count_family = df_family_repeat.shape[0]
#     df.loc[df_family_repeat.index, 'is_unusual'] = True

#     return {
#         'ophtho_ot': count_ophtho_ot,
#         'ophtho_time': count_ophtho_time,
#         'ophtho_age': count_ophtho_age,
#         'emergency': count_emergency,
#         'family': count_family
#     }

# def filter_dashboard_data(request):
#     district = request.GET.get('district', '').strip()
#     print(f"District: {district}")
    
#     # Start with records where hospital_type is "P"
#     queryset = Last24Hour.objects.filter(hospital_type="P")
#     if district and district.lower() != "all":
#         queryset = queryset.filter(district_name__iexact=district)
    
#     # Define time variables
#     now = timezone.now()
#     yesterday_dt = now - timedelta(days=1)
#     last_30_dt = now - timedelta(days=30)
    
#     # ----- Flagged Claims -----
#     flagged_hospitals = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
#     flagged_claims_overall = queryset.filter(
#         hospital_id__in=flagged_hospitals
#     ).count()
#     flagged_claims_last_30_days = queryset.filter(
#         hospital_id__in=flagged_hospitals,
#         preauth_initiated_date__gte=last_30_dt,
#         preauth_initiated_date__lte=now
#     ).count()
#     flagged_claims_yesterday = queryset.filter(
#         hospital_id__in=flagged_hospitals,
#         preauth_initiated_date__date=yesterday_dt.date()
#     ).count()
    
#     # ----- High Value Claims - Surgical -----
#     surgical_overall = queryset.filter(
#         case_type="SURGICAL",
#         claim_initiated_amount__gt=100000
#     ).count()
#     surgical_last_30_days = queryset.filter(
#         case_type="SURGICAL",
#         claim_initiated_amount__gt=100000,
#         preauth_initiated_date__gte=last_30_dt
#     ).count()
#     surgical_yesterday = queryset.filter(
#         case_type="SURGICAL",
#         claim_initiated_amount__gt=100000,
#         preauth_initiated_date__date=yesterday_dt.date()
#     ).count()
    
#     # ----- High Value Claims - Medical -----
#     medical_overall = queryset.filter(
#         case_type="MEDICAL",
#         claim_initiated_amount__gt=25000
#     ).count()
#     medical_last_30_days = queryset.filter(
#         case_type="MEDICAL",
#         claim_initiated_amount__gt=25000,
#         preauth_initiated_date__gte=last_30_dt
#     ).count()
#     medical_yesterday = queryset.filter(
#         case_type="MEDICAL",
#         claim_initiated_amount__gt=25000,
#         preauth_initiated_date__date=yesterday_dt.date()
#     ).count()
    
#     geo_overall = (
#         queryset
#         .annotate(
#             state_name_upper=Upper('state_name'),
#             hospital_state_name_upper=Upper('hospital_state_name')
#         )
#         .exclude(state_name_upper=F('hospital_state_name_upper'))
#         .count()
#     )
#     geo_last_30_days = (
#         queryset
#         .filter(preauth_initiated_date__gte=last_30_dt, preauth_initiated_date__lte=now)
#         .annotate(
#             state_name_upper=Upper('state_name'),
#             hospital_state_name_upper=Upper('hospital_state_name')
#         )
#         .exclude(state_name_upper=F('hospital_state_name_upper'))
#         .count()
#     )
#     geo_yesterday = (
#         queryset
#         .filter(preauth_initiated_date__date=yesterday_dt.date())
#         .annotate(
#             state_name_upper=Upper('state_name'),
#             hospital_state_name_upper=Upper('hospital_state_name')
#         )
#         .exclude(state_name_upper=F('hospital_state_name_upper'))
#         .count()
#     )
    
#     # ----- Unusual Treatment Patterns -----
#     qs = queryset.values()
#     df = pd.DataFrame(qs)
#     if not df.empty:
#         df['preauth_initiated_date'] = pd.to_datetime(df['preauth_initiated_date'], errors='coerce').dt.tz_localize(None)
#         df['date_only'] = df['preauth_initiated_date'].dt.date
#         df['procedure_code'] = df['procedure_code'].fillna('').astype(str).str.strip().str.upper()
#         df['admission_type'] = df['admission_type'].fillna('').astype(str).str.strip().str.upper()
#         df['procedure_details'] = df['procedure_details'].fillna('').astype(str).str.lower()
#         df['age_years'] = pd.to_numeric(df['age_years'], errors='coerce')
#         if 'preauth_initiated_time' in df.columns and df['preauth_initiated_time'].notna().any():
#             df['preauth_initiated_time'] = pd.to_datetime(df['preauth_initiated_time'], format='%H:%M:%S', errors='coerce')
#             df['hour'] = df['preauth_initiated_time'].dt.hour
#         else:
#             df['hour'] = df['preauth_initiated_date'].dt.hour
#     else:
#         df = pd.DataFrame()
    
#     overall_rule_counts = get_rule_counts(df, district) if not df.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
    
#     last_30_date = last_30_dt.date()
#     yesterday_date = yesterday_dt.date()
#     df_last30 = df[df['date_only'] >= last_30_date] if not df.empty else df
#     last30_rule_counts = get_rule_counts(df_last30, district) if not df_last30.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
#     df_yesterday = df[df['date_only'] == yesterday_date] if not df.empty else df
#     yesterday_rule_counts = get_rule_counts(df_yesterday, district) if not df_yesterday.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
    
#     df_unusual = get_unusual_rows(district) if not df.empty else pd.DataFrame()
#     unusual_overall = len(df_unusual)
#     df_unusual_last30 = df_unusual[df_unusual['date_only'] >= last_30_date] if not df_unusual.empty else pd.DataFrame()
#     unusual_last_30_days = len(df_unusual_last30) if not df_unusual_last30.empty else 0
#     df_unusual_yesterday = df_unusual[df_unusual['date_only'] == yesterday_date] if not df_unusual.empty else pd.DataFrame()
#     unusual_yesterday = len(df_unusual_yesterday) if not df_unusual_yesterday.empty else 0
    
#     ot_violations = overall_rule_counts.get('ophtho_ot', 0)
#     preauth_timing_issues = overall_rule_counts.get('ophtho_time', 0)
#     under_40_cataracts = overall_rule_counts.get('ophtho_age', 0)
#     emergency_cases = overall_rule_counts.get('emergency', 0)
#     same_day_claims = overall_rule_counts.get('family', 0)
    
#     return JsonResponse({
#         # Flagged Claims
#         'flagged_claims_overall': flagged_claims_overall,
#         'flagged_claims_last_30_days': flagged_claims_last_30_days,
#         'flagged_claims_yesterday': flagged_claims_yesterday,
        
#         # High Value Claims - Surgical
#         'surgical_overall': surgical_overall,
#         'surgical_last_30_days': surgical_last_30_days,
#         'surgical_yesterday': surgical_yesterday,
        
#         # High Value Claims - Medical
#         'medical_overall': medical_overall,
#         'medical_last_30_days': medical_last_30_days,
#         'medical_yesterday': medical_yesterday,
        
#         # Geographic Anomalies
#         'geo_anomaly_overall': geo_overall,
#         'geo_anomaly_last_30_days': geo_last_30_days,
#         'geo_anomaly_yesterday': geo_yesterday,
        
#         # Unusual Treatment Patterns (Main Card)
#         'unusual_overall': unusual_overall,
#         'unusual_last_30_days': unusual_last_30_days,
#         'unusual_yesterday': unusual_yesterday,
        
#         # Individual Unusual Rule Cards (from overall_rule_counts)
#         'ot_violations': ot_violations,
#         'preauth_timing_issues': preauth_timing_issues,
#         'under_40_cataracts': under_40_cataracts,
#         'emergency_cases': emergency_cases,
#         'same_day_claims': same_day_claims,
#     })

# def add_bed_violation_column(df):
#     if df.empty:
#         df['bed_violation'] = False
#         return df

#     # Group by hospital and date to get daily admissions
#     daily_grp = df.groupby(['hospital_id', 'date_only']).size().reset_index(name='daily_admissions')
#     df = df.merge(daily_grp, on=['hospital_id', 'date_only'], how='left')

#     # Load bed strength data
#     beds_qs = HospitalBeds.objects.all().values('hospital_id', 'bed_strength')
#     bed_dict = {row['hospital_id'].upper(): row['bed_strength'] for row in beds_qs}

#     # Compare with bed strength
#     def cond_bed_strength(row):
#         hosp_id = str(row['hospital_id']).upper()
#         b_strength = bed_dict.get(hosp_id, 0)
#         return row['daily_admissions'] > b_strength

#     df['bed_violation'] = df.apply(cond_bed_strength, axis=1)
#     return df

# def get_bed_violations(df):
#     if df.empty:
#         return 0

#     if 'preauth_initiated_date' in df.columns:
#         df['preauth_initiated_date'] = pd.to_datetime(df['preauth_initiated_date'], errors='coerce')
#         df['preauth_initiated_date'] = df['preauth_initiated_date'].dt.tz_localize(None)
#         df['date_only'] = df['preauth_initiated_date'].dt.date
#     else:
#         df['date_only'] = pd.to_datetime(df['date_only'], errors='coerce')

#     df = add_bed_violation_column(df)
#     return df['bed_violation'].sum()

# def get_unusual_rows(district="all"):
#     """
#     Returns a DataFrame of rows that meet ANY of these conditions:
#       1) Ophthalmology rule:
#          - procedure_code = 'SE020A'
#          - age_years < 40
#          - preauth_initiated_time in [8..18)
#          - daily count of such rows > (num_ot * num_surgeons * 30)
#       2) Emergency prebooking:
#          - admission_type = 'E'
#          - procedure_details has 'cataract','oncology','dialysis'
#       3) Family ID rule:
#          - More than 2 cases on the same day for the same family_id
#       4) Daily admissions > bed_strength => all those cases for that day/hospital
#     """
#     # Use consistent ordering to ensure same results every time
#     if district.lower() != "all" and district.strip() != "":
#         qs = Last24Hour.objects.filter(
#             hospital_type="P", district_name__iexact=district
#         ).order_by("id").values()
#     else:
#         qs = Last24Hour.objects.filter(
#             hospital_type="P"
#         ).order_by("id").values()

#     df = pd.DataFrame(qs)
#     if df.empty:
#         return df

#     # Clean and filter hospital_type
#     df['hospital_type'] = df['hospital_type'].fillna('').astype(str).str.strip().str.upper()
#     df = df[df['hospital_type'] == 'P']
#     if df.empty:
#         return df

#     # Process date and time fields
#     if 'preauth_initiated_date' in df.columns:
#         df['preauth_initiated_date'] = pd.to_datetime(df['preauth_initiated_date'], errors='coerce')
#         df['preauth_initiated_date'] = df['preauth_initiated_date'].dt.tz_localize(None)
#     df['date_only'] = df['preauth_initiated_date'].dt.date

#     if 'preauth_initiated_time' in df.columns:
#         df['preauth_initiated_time'] = df['preauth_initiated_time'].astype(str).str.strip()
#         df['preauth_initiated_time_parsed'] = pd.to_datetime(
#             df['preauth_initiated_time'], format='%H:%M:%S', errors='coerce'
#         )
#         df['hour'] = df['preauth_initiated_time_parsed'].dt.hour
#     else:
#         df['hour'] = df['preauth_initiated_date'].dt.hour

#     if 'admission_type' in df.columns:
#         df['admission_type'] = df['admission_type'].fillna('').astype(str).str.strip().str.upper()
#     if 'procedure_details' in df.columns:
#         df['procedure_details'] = df['procedure_details'].fillna('').astype(str).str.lower()

#     # Load bed strength info from HospitalBeds
#     beds_qs = HospitalBeds.objects.all().values('hospital_id','bed_strength')
#     bed_dict = {row['hospital_id'].upper(): row['bed_strength'] for row in beds_qs}

#     # Condition 4: Daily admissions > bed_strength
#     daily_grp = df.groupby(['hospital_id','date_only']).size().reset_index(name='daily_count')
#     df = df.merge(daily_grp, on=['hospital_id','date_only'], how='left')
#     df['cond4'] = df.apply(lambda row: row['daily_count'] > bed_dict.get(str(row['hospital_id']).upper(), 0), axis=1)

#     # Condition 1: Ophthalmology rules
#     df['is_cataract'] = df['procedure_details'].str.contains('cataract', na=False)
#     df['age_years'] = pd.to_numeric(df['age_years'], errors='coerce')
#     df['cond1_part_a'] = False
#     df['cond1_part_b'] = df['is_cataract'] & df['hour'].between(8, 17)
#     df['cond1_part_c'] = df['is_cataract'] & (df['age_years'] < 40)

#     if 'num_ot' in df.columns and 'num_surgeons' in df.columns:
#         cataract_df = df[df['is_cataract']]
#         if not cataract_df.empty:
#             grouped = cataract_df.groupby(['hospital_id', 'date_only'])
#             cataract_counts = grouped.size().reset_index(name='cataract_daily_count')
#             df = df.merge(cataract_counts, on=['hospital_id', 'date_only'], how='left')
#             df['cataract_daily_count'] = df['cataract_daily_count'].fillna(0)
#             df['threshold'] = df['num_ot'].fillna(0) * df['num_surgeons'].fillna(0) * 30
#             df['cond1_part_a'] = df['is_cataract'] & (df['cataract_daily_count'] > df['threshold'])

#     # Combine Rule 1 parts using AND logic
#     df['cond1'] = df['cond1_part_a'] & df['cond1_part_b'] & df['cond1_part_c']
#     df.loc[df[df['cond1']].index, 'is_unusual'] = True

#     # Condition 2: Emergency prebooking
#     df['cond2'] = df.apply(lambda row: (row['admission_type'] == 'E') and 
#                            any(k in row['procedure_details'] for k in ['cataract','oncology','dialysis']),
#                            axis=1)
#     df.loc[df[df['cond2']].index, 'is_unusual'] = True

#     # Condition 3: Family ID rule
#     if 'family_id' not in df.columns:
#         df['family_id'] = ''
#     grp_fam = df.groupby(['family_id','date_only']).size().reset_index(name='fam_count')
#     df = df.merge(grp_fam, on=['family_id','date_only'], how='left')
#     df['cond3'] = df['fam_count'] > 2
#     df.loc[df[df['cond3']].index, 'is_unusual'] = True

#     # Overall unusual treatment: OR of all conditions
#     df['is_unusual'] = df['cond1'] | df['cond2'] | df['cond3'] | df['cond4']
#     df_unusual = df[df['is_unusual'] == True].copy()
#     return df_unusual

# def dashboard(request):
#     # Define the current time
#     now = timezone.now()
#     yesterday = (now - timedelta(days=1)).date()
#     last_30_days = (now - timedelta(days=30)).date()

#     # Get the list of hospital IDs from Suspicious Hospital
#     flagged_hospitals = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    
#     #Flagged Claims
#     # Overall flagged claims:
#     flagged_overall = Last24Hour.objects.filter(
#         hospital_type="P",
#         hospital_id__in=flagged_hospitals
#     ).count()
    
#     flagged_last_30_days = Last24Hour.objects.filter(
#         hospital_type="P",
#         hospital_id__in=flagged_hospitals,
#         preauth_initiated_date__gte=last_30_days,
#         preauth_initiated_date__lte=now
#     ).count()

#     flagged_yesterday = Last24Hour.objects.filter(
#         hospital_type="P",
#         hospital_id__in=flagged_hospitals,
#         preauth_initiated_date__date=yesterday
#     ).count()

#     # Geographic Anomalies
#     # Overall Geographic Anomalies
#     geo_overall = (
#         Last24Hour.objects
#         .annotate(
#             hospital_type_upper=Upper('hospital_type'),
#             state_name_upper=Upper('state_name'),
#             hospital_state_name_upper=Upper('hospital_state_name')
#         )
#         .filter(hospital_type_upper='P')
#         .exclude(state_name_upper=F('hospital_state_name_upper'))
#         .count()
#     )
    
#     # Last 30 Days Geographic Anomalies
#     geo_last_30_days = (
#         Last24Hour.objects
#         .annotate(
#             hospital_type_upper=Upper('hospital_type'),
#             state_name_upper=Upper('state_name'),
#             hospital_state_name_upper=Upper('hospital_state_name')
#         )
#         .filter(
#             hospital_type_upper='P',
#             preauth_initiated_date__gte=last_30_days,
#             preauth_initiated_date__lte=now
#         )
#         .exclude(state_name_upper=F('hospital_state_name_upper'))
#         .count()
#     )

#     # Yesterday Geographic Anomalies
#     geo_yesterday = (
#         Last24Hour.objects
#         .annotate(
#             hospital_type_upper=Upper('hospital_type'),
#             state_name_upper=Upper('state_name'),
#             hospital_state_name_upper=Upper('hospital_state_name')
#         )
#         .filter(
#             hospital_type_upper='P',
#             preauth_initiated_date__date=yesterday
#         )
#         .exclude(state_name_upper=F('hospital_state_name_upper'))
#         .count()
#     )

#     # High Value Surgical Claims
#     surgical_overall = Last24Hour.objects.filter(
#         hospital_type="P",
#         case_type="SURGICAL",
#         claim_initiated_amount__gt=100000
#     ).count()

#     surgical_last_30_days = Last24Hour.objects.filter(
#         hospital_type="P",
#         case_type="SURGICAL",
#         claim_initiated_amount__gt=100000,
#         preauth_initiated_date__gte=last_30_days
#     ).count()

#     surgical_yesterday = Last24Hour.objects.filter(
#         hospital_type="P",
#         case_type="SURGICAL",
#         claim_initiated_amount__gt=100000,
#         preauth_initiated_date=yesterday
#     ).count()

#     # High Value Medical Claims
#     medical_overall = Last24Hour.objects.filter(
#         hospital_type="P",
#         case_type="MEDICAL",
#         claim_initiated_amount__gt=25000
#     ).count()

#     medical_last_30_days = Last24Hour.objects.filter(
#         hospital_type="P",
#         case_type="MEDICAL",
#         claim_initiated_amount__gt=25000,
#         preauth_initiated_date__gte=last_30_days
#     ).count()

#     medical_yesterday = Last24Hour.objects.filter(
#         hospital_type="P",
#         case_type="MEDICAL",
#         claim_initiated_amount__gt=25000,
#         preauth_initiated_date=yesterday
#     ).count()

#     df_unusual = get_unusual_rows()
#     # if df_unusual.empty:
#     #     context = {
#     #         'unusual_treatment_overall': 0,
#     #         'unusual_treatment_last_30_days': 0,
#     #         'unusual_treatment_yesterday': 0,
#     #     }
    
#     # Overall
#     unusual_overall = len(df_unusual)
#     thirty_days_ago = (now - timedelta(days=30)).date()
#     # yesterday = (now - timedelta(days=1)).date()

#     # Last 30 days
#     df_30 = df_unusual[df_unusual['date_only'] >= thirty_days_ago]
#     unusual_last_30_days = len(df_30)

#     # Yesterday
#     df_yest = df_unusual[df_unusual['date_only'] == yesterday]
#     unusual_yesterday = len(df_yest)
    
#     qs = Last24Hour.objects.all().values()
#     df = pd.DataFrame(qs)
#     if not df.empty:
#         # Convert preauth_initiated_date to datetime and remove timezone
#         df['preauth_initiated_date'] = pd.to_datetime(df['preauth_initiated_date'], errors='coerce').dt.tz_localize(None)
#         # Create a 'date_only' column for grouping and filtering (as date)
#         df['date_only'] = df['preauth_initiated_date'].dt.date
        
#         # Clean up required fields
#         df['hospital_type'] = df['hospital_type'].fillna('').astype(str).str.strip().str.upper()
#         df['procedure_code'] = df['procedure_code'].fillna('').astype(str).str.strip().str.upper()
#         df['admission_type'] = df['admission_type'].fillna('').astype(str).str.strip().str.upper()
#         df['procedure_details'] = df['procedure_details'].fillna('').astype(str).str.lower()
#         df['age_years'] = pd.to_numeric(df['age_years'], errors='coerce')

#         # IMPORTANT: Create the 'hour' column using 'preauth_initiated_time' if available, else fallback
#         if 'preauth_initiated_time' in df.columns and df['preauth_initiated_time'].notna().any():
#             df['preauth_initiated_time'] = pd.to_datetime(df['preauth_initiated_time'], format='%H:%M:%S', errors='coerce')
#             df['hour'] = df['preauth_initiated_time'].dt.hour
#         else:
#             df['hour'] = df['preauth_initiated_date'].dt.hour
#     else:
#         df = pd.DataFrame()

#     overall_counts = get_rule_counts(df) if not df.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
    
#     # Filter for Last 30 Days using the date_only column
#     df_last30 = df[df['date_only'] >= last_30_days] if not df.empty else df
#     last30_counts = get_rule_counts(df_last30) if not df_last30.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
    
#     # Filter for Yesterday
#     df_yesterday = df[df['date_only'] == yesterday] if not df.empty else df
#     yesterday_counts = get_rule_counts(df_yesterday) if not df_yesterday.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
    
#     # Bed strength rule violations
#     bed_violation_overall = get_bed_violations(df)

#     df_last30 = df[df['date_only'] >= last_30_days]
#     bed_violation_last30 = get_bed_violations(df_last30)

#     df_yesterday = df[df['date_only'] == yesterday]
#     bed_violation_yesterday = get_bed_violations(df_yesterday)

#     context = {
#         'flagged_claims_overall': flagged_overall,
#         'flagged_claims_last_30_days': flagged_last_30_days,
#         'flagged_claims_yesterday': flagged_yesterday,
#         'geo_overall': geo_overall,
#         'geo_last_30_days': geo_last_30_days,
#         'geo_yesterday': geo_yesterday,
#         'surgical_overall': surgical_overall,
#         'surgical_last_30_days': surgical_last_30_days,
#         'surgical_yesterday': surgical_yesterday,
#         'medical_overall': medical_overall,
#         'medical_last_30_days': medical_last_30_days,
#         'medical_yesterday': medical_yesterday,
#         'unusual_treatment_overall': unusual_overall,
#         'unusual_treatment_last_30_days': unusual_last_30_days,
#         'unusual_treatment_yesterday': unusual_yesterday,
#         # Ophthalmology OT Cases counts
#         'ophtho_ot_overall': overall_counts['ophtho_ot'],
#         'ophtho_ot_last30': last30_counts['ophtho_ot'],
#         'ophtho_ot_yesterday': yesterday_counts['ophtho_ot'],
#         # Ophthalmology Preauth Time counts
#         'ophtho_time_overall': overall_counts['ophtho_time'],
#         'ophtho_time_last30': last30_counts['ophtho_time'],
#         'ophtho_time_yesterday': yesterday_counts['ophtho_time'],
#         # Ophthalmology Age Cases counts
#         'ophtho_age_overall': overall_counts['ophtho_age'],
#         'ophtho_age_last30': last30_counts['ophtho_age'],
#         'ophtho_age_yesterday': yesterday_counts['ophtho_age'],
#         # Emergency Cases counts
#         'emergency_overall': overall_counts['emergency'],
#         'emergency_last30': last30_counts['emergency'],
#         'emergency_yesterday': yesterday_counts['emergency'],
#         # Family ID Cases counts
#         'family_overall': overall_counts['family'],
#         'family_last30': last30_counts['family'],
#         'family_yesterday': yesterday_counts['family'],
        
#         'bed_violations': {
#             'overall': bed_violation_overall,
#             'last30': bed_violation_last30,
#             'yesterday': bed_violation_yesterday,
#         },
#     }
    
#     return render(request, 'index.html', context)

# def download_flagged_claims_excel(request):
#     # Get flagged hospital IDs from SuspiciousHospital
#     flagged_hospital_ids = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    
#     # Filter Last24Hour records for flagged claims and only for Private hospitals ("P")
#     qs = Last24Hour.objects.filter(
#         hospital_type="P",
#         hospital_id__in=flagged_hospital_ids
#     )
    
#     # Convert the queryset to a list of dictionaries
#     data = list(qs.values())
    
#     # Convert the data to a Pandas DataFrame
#     df = pd.DataFrame(data)
    
#     # Convert timezone-aware datetime columns to naive datetimes
#     for col in df.columns:
#         if pd.api.types.is_datetime64_any_dtype(df[col]):
#             df[col] = df[col].dt.tz_localize(None)

#     # Drop columns that are completely null
#     df = df.dropna(axis=1, how='all')

#     print(df)

#     # Create an in-memory output file for the new workbook.
#     output = io.BytesIO()
    
#     # Write the DataFrame to an Excel file in memory
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         df.to_excel(writer, index=False, sheet_name='Flagged Claims')
    
#     output.seek(0)  # Rewind the buffer
    
#     # Create an HTTP response with the Excel file
#     response = HttpResponse(
#         output,
#         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
#     response['Content-Disposition'] = 'attachment; filename="flagged_claims.xlsx"'
#     return response

# def download_geo_anomalies_excel(request):
#     """
#     Download Geographic Anomalies data as an Excel file.
#     A record is considered an anomaly if:
#     - Hospital Type = "P"
#     - State Name != Hospital State Name
#     """

#     # Query the Last24Hour model for geographic anomalies
#     qs = (
#         Last24Hour.objects
#         .annotate(
#             hospital_type_upper=Upper('hospital_type'),
#             state_name_upper=Upper('state_name'),
#             hospital_state_name_upper=Upper('hospital_state_name')
#         )
#         .filter(hospital_type_upper='P')
#         .exclude(state_name_upper=F('hospital_state_name_upper'))
#     )

#     # Convert the queryset to a list of dictionaries
#     data = list(qs.values())

#     # Convert the data to a Pandas DataFrame
#     df = pd.DataFrame(data)

#     # If you have timezone-aware datetime fields, remove the timezone
#     for col in df.columns:
#         if pd.api.types.is_datetime64_any_dtype(df[col]):
#             df[col] = df[col].dt.tz_localize(None)

#     # Drop columns that are completely null (optional)
#     df = df.dropna(axis=1, how='all')

#     # Create an in-memory output file for the Excel workbook
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         df.to_excel(writer, index=False, sheet_name='Geo Anomalies')
#     output.seek(0)

#     # Create an HTTP response with the Excel file
#     response = HttpResponse(
#         output,
#         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
#     response['Content-Disposition'] = 'attachment; filename="geo_anomalies.xlsx"'
#     return response

# def download_high_value_claims_excel(request):
#     # Query surgical and medical
#     surgical_claims = Last24Hour.objects.filter(
#         hospital_type="P",
#         case_type="SURGICAL",
#         claim_initiated_amount__gt=100000
#     ).values()

#     medical_claims = Last24Hour.objects.filter(
#         hospital_type="P",
#         case_type="MEDICAL",
#         claim_initiated_amount__gt=25000
#     ).values()

#     df_surgical = pd.DataFrame.from_records(surgical_claims)
#     df_medical = pd.DataFrame.from_records(medical_claims)

#     # Drop columns that are all null
#     for df in [df_surgical, df_medical]:
#         df.dropna(axis=1, how="all", inplace=True)
        
#         # Convert columns to datetime if possible, then remove timezone
#         for col in df.columns:
#             # Try parsing columns as datetime if not already
#             if not pd.api.types.is_datetime64_any_dtype(df[col]):
#                 df[col] = pd.to_datetime(df[col], errors='ignore')
            
#             # If it is datetime now, strip timezone
#             if pd.api.types.is_datetime64_any_dtype(df[col]):
#                 df[col] = df[col].dt.tz_localize(None)

#     # Write to a single Excel file with two sheets
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         df_surgical.to_excel(writer, index=False, sheet_name='Surgical High Value Claims')
#         df_medical.to_excel(writer, index=False, sheet_name='Medical High Value Claims')
#     output.seek(0)

#     response = HttpResponse(
#         output,
#         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
#     response['Content-Disposition'] = 'attachment; filename="High_Value_Claims.xlsx"'
#     return response

# def download_unusual_treatment_excel(request):
#     df_unusual = get_unusual_rows()
#     if df_unusual.empty:
#         return HttpResponse("No Unusual Treatment Patterns found.")

#     # Drop columns that are all null
#     df_unusual.dropna(axis=1, how='all', inplace=True)

#     # Create an in-memory Excel file
#     import io
#     import pandas as pd
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         df_unusual.to_excel(writer, index=False, sheet_name='Unusual Patterns')
#     output.seek(0)

#     response = HttpResponse(
#         output,
#         content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
#     response['Content-Disposition'] = 'attachment; filename="Unusual_Treatment_Patterns.xlsx"'
#     return response