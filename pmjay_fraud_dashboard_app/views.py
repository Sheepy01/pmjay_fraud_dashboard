from django.db.models import Sum, Q, Avg, F, Func, Count, Subquery, Max
from .models import Last24Hour, SuspiciousHospital, HospitalBeds
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, CharField
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import login as auth_login
from django.template.loader import render_to_string
from weasyprint.text.fonts import FontConfiguration
from django.http import JsonResponse, HttpResponse
from django.db.models.functions import TruncDate
from django.utils.timezone import now, timedelta
from openpyxl.styles import PatternFill, Font
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from weasyprint import HTML
import pandas as pd
import datetime
import re
import io
from django.views.decorators.http import require_http_methods

def login_view(request):
    # If they’re already logged in, send them straight to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            error = "Invalid username or password"

    return render(request, 'login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')

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
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    districts = district_param.split(',') if district_param else []

    # Get suspicious hospitals
    suspicious_hospitals = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    
    # Base query
    flagged_cases = Last24Hour.objects.filter(
        Q(hospital_id__in=suspicious_hospitals) &
        Q(hospital_type='P')
    )
    
    if districts:
        flagged_cases = flagged_cases.filter(district_name__in=districts)
    
    # Pagination
    paginator = Paginator(flagged_cases, page_size)
    page_obj = paginator.get_page(page)
    
    data = []
    for idx, case in enumerate(page_obj.object_list, 1):
        data.append({
            'serial_no': (page_obj.number - 1) * page_size + idx,
            'claim_id': case.registration_id or case.case_id or 'N/A',
            'patient_name': case.patient_name or f"Patient {case.member_id}",
            'hospital_name': case.hospital_name or 'N/A',
            'district_name': case.district_name or 'N/A',
            'amount': case.claim_initiated_amount or 0,
            'reason': 'Suspicious hospital'
        })
    
    return JsonResponse({
        'data': data,
        'pagination': {
            'total_records': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })

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

def get_all_flagged_claims(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []

    # Get suspicious hospitals
    suspicious_hospitals = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    
    # Base query
    flagged_cases = Last24Hour.objects.filter(
        Q(hospital_id__in=suspicious_hospitals) &
        Q(hospital_type='P')
    )
    
    if districts:
        flagged_cases = flagged_cases.filter(district_name__in=districts)
    
    data = []
    for idx, case in enumerate(flagged_cases, 1):
        data.append({
            'serial_no': idx,
            'claim_id': case.registration_id or case.case_id or 'N/A',
            'patient_name': case.patient_name or f"Patient {case.member_id}",
            'hospital_name': case.hospital_name or 'N/A',
            'district_name': case.district_name or 'N/A',
            'amount': case.claim_initiated_amount or 0,
            'reason': 'Suspicious hospital'
        })
    
    return JsonResponse({'data': data})

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

def get_high_value_claims_details(request):
    case_type = request.GET.get('case_type', 'all').upper()
    district_param = request.GET.get('district', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))  # Default 50 items per page
    
    # Base query
    base_query = Last24Hour.objects.filter(hospital_type='P')
    
    # Apply case type filter
    if case_type == 'SURGICAL':
        base_query = base_query.filter(
            case_type__iexact='SURGICAL',
            claim_initiated_amount__gte=100000
        )
    elif case_type == 'MEDICAL':
        base_query = base_query.filter(
            case_type__iexact='MEDICAL',
            claim_initiated_amount__gte=25000
        )
    else:
        base_query = base_query.filter(
            Q(case_type__iexact='SURGICAL', claim_initiated_amount__gte=100000) |
            Q(case_type__iexact='MEDICAL', claim_initiated_amount__gte=25000)
        )
    
    if district_param:
        districts = district_param.split(',')
        base_query = base_query.filter(district_name__in=districts)
    
    # Create paginator
    paginator = Paginator(base_query, page_size)
    page_obj = paginator.get_page(page)
    
    # Serialize data
    data = []
    for idx, case in enumerate(page_obj.object_list, 1):
        data.append({
            'serial_no': (page_obj.number - 1) * page_size + idx,
            'claim_id': case.registration_id or case.case_id or 'N/A',
            'patient_name': case.patient_name or f"Patient {case.member_id}",
            'hospital_name': case.hospital_name or 'N/A',
            'district_name': case.district_name or 'N/A',
            'amount': case.claim_initiated_amount or 0,
            'case_type': case.case_type.upper() if case.case_type else 'N/A'
        })
    
    return JsonResponse({
        'data': data,
        'pagination': {
            'total_records': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })

def get_high_value_claims_by_district(request):
    case_type = request.GET.get('case_type', 'all').upper()
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    base_query = Last24Hour.objects.filter(hospital_type='P')
    
    # Apply value thresholds
    if case_type == 'SURGICAL':
        base_query = base_query.filter(
            case_type__iexact='SURGICAL',
            claim_initiated_amount__gte=100000
        )
    elif case_type == 'MEDICAL':
        base_query = base_query.filter(
            case_type__iexact='MEDICAL',
            claim_initiated_amount__gte=25000
        )
    else:  # All
        base_query = base_query.filter(
            Q(case_type__iexact='SURGICAL', claim_initiated_amount__gte=100000) |
            Q(case_type__iexact='MEDICAL', claim_initiated_amount__gte=25000)
        )
    
    if districts:
        base_query = base_query.filter(district_name__in=districts)
    
    district_data = base_query.values('district_name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return JsonResponse({
        'districts': [d['district_name'] or 'Unknown' for d in district_data],
        'counts': [d['count'] for d in district_data]
    })

def get_high_value_age_distribution(request):
    case_type = request.GET.get('case_type', 'all').upper()
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    base_query = Last24Hour.objects.filter(hospital_type='P')
    
    # Apply case type filter
    if case_type == 'SURGICAL':
        base_query = base_query.filter(
            case_type__iexact='SURGICAL',
            claim_initiated_amount__gte=100000
        )
    elif case_type == 'MEDICAL':
        base_query = base_query.filter(
            case_type__iexact='MEDICAL',
            claim_initiated_amount__gte=25000
        )
    else:
        base_query = base_query.filter(
            Q(case_type__iexact='SURGICAL', claim_initiated_amount__gte=100000) |
            Q(case_type__iexact='MEDICAL', claim_initiated_amount__gte=25000)
        )
    
    if districts:
        base_query = base_query.filter(district_name__in=districts)
    
    # Define age groups (match existing visualization categories)
    age_groups = Case(
        When(age_years__lt=20, then=Value('≤20')),
        When(age_years__gte=20, age_years__lt=30, then=Value('21-30')),
        When(age_years__gte=30, age_years__lt=40, then=Value('31-40')),
        When(age_years__gte=40, age_years__lt=50, then=Value('41-50')),
        When(age_years__gte=50, age_years__lt=60, then=Value('51-60')),
        When(age_years__gte=60, then=Value('60+')),
        default=Value('Unknown'),
        output_field=CharField()
    )
    
    age_data = base_query.annotate(age_group=age_groups).values('age_group') \
        .annotate(count=Count('id')).order_by('age_group')
    
    # Convert to frontend format with consistent category order
    categories = ['≤20', '21-30', '31-40', '41-50', '51-60', '60+', 'Unknown']
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF']
    
    # Create a dictionary for easy lookup
    age_dict = {item['age_group']: item['count'] for item in age_data}
    
    # Fill in missing categories with 0 count
    formatted_data = {
        'labels': categories,
        'data': [age_dict.get(cat, 0) for cat in categories],
        'colors': colors
    }
    
    return JsonResponse(formatted_data)

def get_high_value_gender_distribution(request):
    case_type = request.GET.get('case_type', 'all').upper()
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    base_query = Last24Hour.objects.filter(hospital_type='P')
    
    # Apply case type filter (same as age distribution)
    if case_type == 'SURGICAL':
        base_query = base_query.filter(
            case_type__iexact='SURGICAL',
            claim_initiated_amount__gte=100000
        )
    elif case_type == 'MEDICAL':
        base_query = base_query.filter(
            case_type__iexact='MEDICAL',
            claim_initiated_amount__gte=25000
        )
    else:
        base_query = base_query.filter(
            Q(case_type__iexact='SURGICAL', claim_initiated_amount__gte=100000) |
            Q(case_type__iexact='MEDICAL', claim_initiated_amount__gte=25000)
        )
    
    if districts:
        base_query = base_query.filter(district_name__in=districts)
    
    # Normalize gender values
    gender_groups = Case(
        When(gender__iexact='M', then=Value('Male')),
        When(gender__iexact='F', then=Value('Female')),
        When(gender__isnull=False, then=Value('Other')),
        default=Value('Unknown'),
        output_field=CharField()
    )
    
    gender_data = base_query.annotate(gender_group=gender_groups).values('gender_group') \
        .annotate(count=Count('id')).order_by('gender_group')
    
    # Maintain consistent category order
    categories = ['Male', 'Female', 'Other', 'Unknown']
    colors = ['#36A2EB', '#FF6384', '#4BC0C0', '#C9CBCF']
    
    gender_dict = {item['gender_group']: item['count'] for item in gender_data}
    
    formatted_data = {
        'labels': categories,
        'data': [gender_dict.get(cat, 0) for cat in categories],
        'colors': colors
    }
    
    return JsonResponse(formatted_data)

def get_hospital_bed_cases(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    thirty_days_ago = today - timedelta(days=30)

    # 1. Load bed strengths
    beds = HospitalBeds.objects.values('hospital_id', 'bed_strength')
    bed_strengths = {h['hospital_id']: h['bed_strength'] for h in beds}
    hospital_ids = list(bed_strengths.keys())

    # 2. Helper to fetch admissions per hospital/date
    def admissions_qs(start_date, end_date):
        return Last24Hour.objects.filter(
            Q(hospital_id__in=hospital_ids) &
            (Q(admission_date__date__range=(start_date, end_date)) |
             Q(admission_date__isnull=True, preauth_initiated_date__date__range=(start_date, end_date)))
        )

    # 3. Today: compute per-hospital counts and find violations
    today_adm = admissions_qs(today, today)
    today_counts = today_adm.values('hospital_id').annotate(count=Count('id'))
    violating_today = [a['hospital_id'] for a in today_counts
                       if a['count'] > bed_strengths.get(a['hospital_id'], 0)]

    # 4. Yesterday: similar
    yest_adm = admissions_qs(yesterday, yesterday)
    yest_counts = yest_adm.values('hospital_id').annotate(count=Count('id'))
    violating_yesterday = [a['hospital_id'] for a in yest_counts
                            if a['count'] > bed_strengths.get(a['hospital_id'], 0)]

    # 5. Last 30 days: annotate per hospital per day, then distinct hospital overflow
    range_adm = admissions_qs(thirty_days_ago, today)
    # annotate day and count
    from django.db.models.functions import Coalesce, TruncDate

    annotated = (
        range_adm
        .annotate(ts=Coalesce('admission_date', 'preauth_initiated_date'))
        .annotate(day=TruncDate('ts'))
        .values('hospital_id', 'day')
        .annotate(count=Count('id'))
        .filter(count__gt=0)  # initial filter, we'll apply bed check below
    )
    violating_30_set = set(
        rec['hospital_id']
        for rec in annotated
        if rec['count'] > bed_strengths.get(rec['hospital_id'], 0)
    )

    # 6. Fetch hospital names for today's violations
    names = Last24Hour.objects.filter(
        hospital_id__in=violating_today
    ).values_list('hospital_id', 'hospital_name').distinct()
    hospital_names = {hid: name for hid, name in names}

    # 7. Build detailed list for today's violations
    details_today = []
    for hid in violating_today:
        count = next((a['count'] for a in today_counts if a['hospital_id'] == hid), 0)
        details_today.append({
            'hospital': hospital_names.get(hid, f"Hospital {hid}"),
            'admissions': count,
            'bed_strength': bed_strengths.get(hid, 0)
        })

    # 8. Prepare response
    data = {
        'total': len(violating_today),
        'yesterday': len(violating_yesterday),
        'last_30_days': len(violating_30_set),
        'violations_today': details_today
    }
    return JsonResponse(data)

def get_hospital_bed_details(request):
    district_param = request.GET.get('district', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    
    # 1. Load bed strengths
    beds = HospitalBeds.objects.values('hospital_id', 'bed_strength')
    bed_strengths = {h['hospital_id']: h['bed_strength'] for h in beds}
    
    # 2. Get today's admissions with hospital details
    violations = (
        Last24Hour.objects
        .filter(
            Q(admission_date__date=today) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=today)
        )
        .values('hospital_id', 'hospital_name', 'district_name', 'state_name')
        .annotate(
            admissions=Count('id'),
            last_violation_date=Max('admission_date')
        )
    )
    
    if districts:
        violations = violations.filter(district_name__in=districts)
    
    # 3. Add bed capacity and filter violations
    enhanced_violations = []
    for violation in violations:
        bed_capacity = bed_strengths.get(violation['hospital_id'], 0)
        if violation['admissions'] > bed_capacity:
            enhanced_violations.append({
                **violation,
                'bed_capacity': bed_capacity,
                'excess': violation['admissions'] - bed_capacity
            })
    
    # 4. Paginate in-memory list
    paginator = Paginator(enhanced_violations, page_size)
    page_obj = paginator.get_page(page)
    
    # 5. Serialize data
    data = []
    for idx, violation in enumerate(page_obj.object_list, 1):
        data.append({
            'serial_no': (page_obj.number - 1) * page_size + idx,
            'hospital_id': violation['hospital_id'],
            'hospital_name': violation['hospital_name'],
            'district': violation['district_name'],
            'state': violation['state_name'],
            'bed_capacity': violation['bed_capacity'],
            'admissions': violation['admissions'],
            'excess': violation['excess'],
            'last_violation': violation['last_violation_date'].strftime('%Y-%m-%d') if violation['last_violation_date'] else 'N/A'
        })
    
    return JsonResponse({
        'data': data,
        'pagination': {
            'total_records': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })

def hospital_violations_by_district(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    
    result = (
        Last24Hour.objects
        .filter(
            Q(admission_date__date=today) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=today)
        )
        .values('district_name')
        .annotate(violation_count=Count('hospital_id', distinct=True))
        .order_by('-violation_count')
    )
    
    if districts:
        result = result.filter(district_name__in=districts)
    
    return JsonResponse({
        'districts': [item['district_name'] or 'Unknown' for item in result],
        'counts': [item['violation_count'] for item in result]
    })

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

def get_family_id_cases_details(request):
    district_param = request.GET.get('district', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    
    # Get all individual claims from suspicious families
    cases = Last24Hour.objects.filter(
        Q(hospital_type='P') &
        Q(family_id__in=Subquery(
            Last24Hour.objects
            .annotate(day=TruncDate('preauth_initiated_date'))
            .values('family_id', 'day')
            .annotate(count=Count('id'))
            .filter(count__gt=2)
            .values('family_id')
        )) &
        Q(preauth_initiated_date__date=today)
    ).order_by('family_id', 'preauth_initiated_date')
    
    if districts:
        cases = cases.filter(district_name__in=districts)
    
    # Pagination
    paginator = Paginator(cases, page_size)
    page_obj = paginator.get_page(page)
    
    # Serialize data
    data = []
    for idx, case in enumerate(page_obj.object_list, 1):
        data.append({
            'serial_no': (page_obj.number - 1) * page_size + idx,
            'family_id': case.family_id,
            'claim_id': case.registration_id or case.case_id or 'N/A',
            'patient_name': case.patient_name or f"Patient {case.member_id}",
            'district_name': case.district_name or 'N/A',
            'hospital_name': case.hospital_name or 'N/A',
            'date': case.preauth_initiated_date.date()
        })
    
    return JsonResponse({
        'data': data,
        'pagination': {
            'total_records': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })

def get_family_violations_by_district(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    # Get count of unique families per district
    result = (
        Last24Hour.objects
        .filter(hospital_type='P')
        .annotate(day=TruncDate('preauth_initiated_date'))
        .values('family_id', 'day', 'district_name')
        .annotate(count=Count('id'))
        .filter(count__gt=2)
        .values('district_name')
        .annotate(family_count=Count('family_id', distinct=True))
        .order_by('-family_count')
    )
    
    if districts:
        result = result.filter(district_name__in=districts)
    
    return JsonResponse({
        'districts': [item['district_name'] for item in result],
        'counts': [item['family_count'] for item in result]
    })

def get_family_violations_demographics(request, type):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    base_query = Last24Hour.objects.filter(
        Q(hospital_type='P') &
        Q(family_id__in=Subquery(
            Last24Hour.objects
            .annotate(day=TruncDate('preauth_initiated_date'))
            .values('family_id', 'day')
            .annotate(count=Count('id'))
            .filter(count__gt=2)
            .values('family_id')
        ))
    )
    
    if districts:
        base_query = base_query.filter(district_name__in=districts)
    
    if type == 'age':
        # Age distribution logic
        age_groups = Case(
            When(age_years__lt=20, then=Value('≤20')),
            When(age_years__gte=20, age_years__lt=30, then=Value('21-30')),
            When(age_years__gte=30, age_years__lt=40, then=Value('31-40')),
            When(age_years__gte=40, age_years__lt=50, then=Value('41-50')),
            When(age_years__gte=50, age_years__lt=60, then=Value('51-60')),
            When(age_years__gte=60, then=Value('60+')),
            default=Value('Unknown'),
            output_field=CharField()
        )
        
        age_data = base_query.annotate(age_group=age_groups).values('age_group') \
            .annotate(count=Count('id')).order_by('age_group')
        
        categories = ['≤20', '21-30', '31-40', '41-50', '51-60', '60+', 'Unknown']
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF']
        
        age_dict = {item['age_group']: item['count'] for item in age_data}
        
        data = {
            'labels': categories,
            'data': [age_dict.get(cat, 0) for cat in categories],
            'colors': colors
        }
        
    elif type == 'gender':
        # Gender distribution logic
        gender_data = base_query.values('gender') \
            .annotate(count=Count('id')).order_by('gender')
        
        categories = ['Male', 'Female', 'Other', 'Unknown']
        colors = ['#36A2EB', '#FF6384', '#4BC0C0', '#C9CBCF']
        
        gender_map = {
            'M': 'Male',
            'F': 'Female',
            'O': 'Other'
        }
        
        gender_dict = {}
        for item in gender_data:
            gender = gender_map.get(item['gender'], 'Unknown')
            gender_dict[gender] = item['count']
        
        data = {
            'labels': categories,
            'data': [gender_dict.get(cat, 0) for cat in categories],
            'colors': colors
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

def get_geo_anomalies_details(request):
    district_param = request.GET.get('district', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    
    cases = Last24Hour.objects.filter(
        hospital_type='P',
        state_name__isnull=False,
        hospital_state_name__isnull=False
    ).exclude(state_name=F('hospital_state_name')).filter(
        Q(admission_date__date=today) | 
        Q(admission_date__isnull=True, preauth_initiated_date__date=today)
    ).order_by('state_name', 'hospital_state_name')
    
    if districts:
        cases = cases.filter(district_name__in=districts)

    paginator = Paginator(cases, page_size)
    page_obj = paginator.get_page(page)

    data = []
    for idx, case in enumerate(page_obj.object_list, 1):
        data.append({
            'serial_no': (page_obj.number - 1) * page_size + idx,
            'claim_id': case.registration_id or case.case_id or 'N/A',
            'patient_name': case.patient_name or f"Patient {case.member_id}",
            'district_name': case.district_name or 'N/A',
            'hospital_name': case.hospital_name or 'N/A',
            'patient_state': case.state_name or 'N/A',
            'hospital_state': case.hospital_state_name or 'N/A',
        })

    return JsonResponse({
        'data': data,
        'pagination': {
            'total_records': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })

def get_geo_violations_by_state(request):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    today = timezone.now().date()
    
    cases = Last24Hour.objects.filter(
        hospital_type='P',
        state_name__isnull=False,
        hospital_state_name__isnull=False
    ).exclude(state_name=F('hospital_state_name')).filter(
        Q(admission_date__date=today) | 
        Q(admission_date__isnull=True, preauth_initiated_date__date=today)
    )
    
    if districts:
        cases = cases.filter(district_name__in=districts)

    result = cases.values('state_name').annotate(count=Count('id')).order_by('-count')
    
    return JsonResponse({
        'states': [item['state_name'] for item in result],
        'counts': [item['count'] for item in result]
    })

def get_geo_violations_demographics(request, type):
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []
    
    base_query = Last24Hour.objects.filter(
        hospital_type='P',
        state_name__isnull=False,
        hospital_state_name__isnull=False
    ).exclude(state_name=F('hospital_state_name'))
    
    if districts:
        base_query = base_query.filter(district_name__in=districts)

    if type == 'age':
        age_groups = Case(
            When(age_years__lt=20, then=Value('≤20')),
            When(age_years__gte=20, age_years__lt=30, then=Value('21-30')),
            When(age_years__gte=30, age_years__lt=40, then=Value('31-40')),
            When(age_years__gte=40, age_years__lt=50, then=Value('41-50')),
            When(age_years__gte=50, age_years__lt=60, then=Value('51-60')),
            When(age_years__gte=60, then=Value('60+')),
            default=Value('Unknown'),
            output_field=CharField()
        )
        
        age_data = base_query.annotate(age_group=age_groups).values('age_group') \
            .annotate(count=Count('id')).order_by('age_group')
        
        categories = ['≤20', '21-30', '31-40', '41-50', '51-60', '60+', 'Unknown']
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF']
        age_dict = {item['age_group']: item['count'] for item in age_data}
        
        data = {
            'labels': categories,
            'data': [age_dict.get(cat, 0) for cat in categories],
            'colors': colors
        }
        
    elif type == 'gender':
        gender_data = base_query.values('gender') \
            .annotate(count=Count('id')).order_by('gender')
        
        categories = ['Male', 'Female', 'Other', 'Unknown']
        colors = ['#36A2EB', '#FF6384', '#4BC0C0', '#C9CBCF']
        gender_map = {'M': 'Male', 'F': 'Female', 'O': 'Other'}
        gender_dict = {gender_map.get(item['gender'], 'Unknown'): item['count'] for item in gender_data}
        
        data = {
            'labels': categories,
            'data': [gender_dict.get(cat, 0) for cat in categories],
            'colors': colors
        }
    
    return JsonResponse(data)

def get_ophthalmology_cases(request):
    # 0. District filtering
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []

    # 1. Date references
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    thirty_days_ago = today - timedelta(days=30)

    # 2. Build hospital capacity map: OT_count * surgeon_count * 30
    hosp_info = SuspiciousHospital.objects.values(
        'hospital_id', 'number_of_ot', 'number_of_surgeons'
    )
    capacity_map = {
        h['hospital_id']: h['number_of_ot'] * h['number_of_surgeons'] * 30
        for h in hosp_info
    }

    # 3. Base queryset: private hospitals, cataract code SE020A
    base_qs = Last24Hour.objects.filter(
        hospital_type='P',
        procedure_code__contains='SE'
    )
    if districts:
        base_qs = base_qs.filter(district_name__in=districts)

    # 4. Age < 40 segment
    age_qs = base_qs.filter(age_years__lt=40)

    # 5. Preauth‑time violations (outside 08:00–17:59:59)
    preauth_qs = base_qs.exclude(
        Q(preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$')
    )

    # Helper: count cases per hospital for a given date
    def counts_by_hospital_for_date(day):
        qs = base_qs.filter(
            Q(admission_date__date=day) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=day)
        )
        return qs.values('hospital_id').annotate(case_count=Count('id'))

    # 6. OT violations today
    today_counts = counts_by_hospital_for_date(today)
    ot_violations_today = [
        {'hospital_id': rec['hospital_id'],
         'case_count': rec['case_count'],
         'capacity': capacity_map.get(rec['hospital_id'], 0)}
        for rec in today_counts
        if rec['case_count'] > capacity_map.get(rec['hospital_id'], 0)
    ]
    ot_total = len(ot_violations_today)

    # 7. OT violations yesterday
    yest_counts = counts_by_hospital_for_date(yesterday)
    ot_yesterday = sum(
        1 for rec in yest_counts
        if rec['case_count'] > capacity_map.get(rec['hospital_id'], 0)
    )

    # 8. OT violations in last 30 days (distinct hospital×day)
    overflow_days = set()
    for n in range(30):
        day = today - timedelta(days=n)
        for rec in counts_by_hospital_for_date(day):
            if rec['case_count'] > capacity_map.get(rec['hospital_id'], 0):
                overflow_days.add((rec['hospital_id'], day))
    ot_last_30 = len(overflow_days)

    # 9. Prepare top-5 detail list for today
    #    (also fetch hospital names)
    hosp_names = dict(
        Last24Hour.objects
        .filter(hospital_id__in=[v['hospital_id'] for v in ot_violations_today])
        .values_list('hospital_id', 'hospital_name')
        .distinct()
    )
    ot_details = []
    for rec in sorted(ot_violations_today, key=lambda x: x['case_count'], reverse=True)[:5]:
        hid = rec['hospital_id']
        ot_details.append({
            'hospital_id': hid,
            'hospital_name': hosp_names.get(hid, f"Hospital {hid}"),
            'cases': rec['case_count'],
            'capacity': rec['capacity']
        })

    # 10. Age <40 totals
    def date_count(qs, day):
        return qs.filter(
            Q(admission_date__date=day) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=day)
        ).count()

    age_total = age_qs.count()
    age_yesterday = date_count(age_qs, yesterday)
    age_last_30 = age_qs.filter(
        Q(admission_date__date__gte=thirty_days_ago, admission_date__date__lte=today) |
        Q(admission_date__isnull=True,
          preauth_initiated_date__date__gte=thirty_days_ago,
          preauth_initiated_date__date__lte=today)
    ).count()

    # 11. Preauth‑time totals
    preauth_total = preauth_qs.count()
    preauth_yesterday = date_count(preauth_qs, yesterday)
    preauth_last_30 = preauth_qs.filter(
        Q(admission_date__date__gte=thirty_days_ago, admission_date__date__lte=today) |
        Q(admission_date__isnull=True,
          preauth_initiated_date__date__gte=thirty_days_ago,
          preauth_initiated_date__date__lte=today)
    ).count()

    # 12. Calculate true unique total
    today = timezone.now().date()
    hospital_counts = base_qs.filter(
        Q(admission_date__date=today) |
        Q(admission_date__isnull=True, preauth_initiated_date__date=today)
    ).values('hospital_id').annotate(case_count=Count('id'))
    
    violating_hospitals = [
        h['hospital_id'] for h in hospital_counts 
        if h['case_count'] > capacity_map.get(h['hospital_id'], 0)
    ]
    
    unique_violations = base_qs.filter(
        Q(age_years__lt=40) |
        Q(hospital_id__in=violating_hospitals) |
        ~Q(preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$')
    ).count()

    # 13. Build Response
    data = {
        'total': unique_violations,
        'age_under_40': {
            'total': age_total,
            'yesterday': age_yesterday,
            'last_30_days': age_last_30
        },
        'ot_cases': {
            'total': ot_total,
            'yesterday': ot_yesterday,
            'last_30_days': ot_last_30,
            'violations': ot_details
        },
        'preauth_time': {
            'total': preauth_total,
            'yesterday': preauth_yesterday,
            'last_30_days': preauth_last_30,
            'avg_violation_hours': None
        }
    }

    return JsonResponse(data)

def get_ophthalmology_details(request):
    violation_type = request.GET.get('type', 'all')
    district_param = request.GET.get('district', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 50))
    
    # Get hospital capacity data
    hosp_info = SuspiciousHospital.objects.values('hospital_id', 'number_of_ot', 'number_of_surgeons')
    capacity_map = {
        h['hospital_id']: h['number_of_ot'] * h['number_of_surgeons'] * 30
        for h in hosp_info
    }

    base_qs = Last24Hour.objects.filter(
        hospital_type='P',
        procedure_code__contains='SE'
    )
    
    if district_param:
        districts = district_param.split(',')
        base_qs = base_qs.filter(district_name__in=districts)

    # Violation filters
    if violation_type == 'age':
        cases = base_qs.filter(age_years__lt=40)
    elif violation_type == 'ot':
        # Get today's OT violations
        today = timezone.now().date()
        hospital_counts = base_qs.filter(
            Q(admission_date__date=today) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=today)
        ).values('hospital_id').annotate(case_count=Count('id'))
        
        violating_hospitals = [
            h['hospital_id'] for h in hospital_counts 
            if h['case_count'] > capacity_map.get(h['hospital_id'], 0)
        ]
        cases = base_qs.filter(hospital_id__in=violating_hospitals)
    elif violation_type == 'preauth':
        cases = base_qs.exclude(
            preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$'
        )
    else:  # All
        today = timezone.now().date()
        hospital_counts = base_qs.filter(
            Q(admission_date__date=today) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=today)
        ).values('hospital_id').annotate(case_count=Count('id'))
        
        violating_hospitals = [
            h['hospital_id'] for h in hospital_counts 
            if h['case_count'] > capacity_map.get(h['hospital_id'], 0)
        ]
        
        cases = base_qs.filter(
            Q(age_years__lt=40) |
            Q(hospital_id__in=violating_hospitals) |
            ~Q(preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$')
        )

    paginator = Paginator(cases, page_size)
    page_obj = paginator.get_page(page)

    data = []
    for idx, case in enumerate(page_obj.object_list, 1):
        row = {
            'serial_no': (page_obj.number - 1) * page_size + idx,
            'claim_id': case.registration_id or case.case_id or 'N/A',
            'patient_name': case.patient_name or f"Patient {case.member_id}",
            'hospital_name': case.hospital_name or 'N/A',
            'district_name': case.district_name or 'N/A',
            'amount': case.claim_initiated_amount or 0,
            'age': case.age_years,
            'preauth_time': case.preauth_initiated_time,
        }
        
        # Determine violations
        is_ot_violation = case.hospital_id in violating_hospitals if violation_type in ['all', 'ot'] else False
        is_age_violation = case.age_years < 40 if case.age_years else False
        is_time_violation = not re.match(r'^(0[8-9]|1[0-7]):', case.preauth_initiated_time) if case.preauth_initiated_time else False
        
        if violation_type == 'all':
            row.update({
                'age_violation': is_age_violation,
                'ot_violation': is_ot_violation,
                'preauth_violation': is_time_violation
            })
        else:
            row[f'{violation_type}_violation'] = True

        data.append(row)

    return JsonResponse({
        'data': data,
        'pagination': {
            'total_records': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page_obj.number,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })

def get_ophthalmology_distribution(request):
    violation_type = request.GET.get('type', 'all')
    district_param = request.GET.get('district', '')
    
    base_qs = Last24Hour.objects.filter(
        hospital_type='P',
        procedure_code__contains='SE'
    )

    hosp_info = SuspiciousHospital.objects.values('hospital_id', 'number_of_ot', 'number_of_surgeons')
    capacity_map = {
        h['hospital_id']: h['number_of_ot'] * h['number_of_surgeons'] * 30
        for h in hosp_info
    }

    base_qs = Last24Hour.objects.filter(
        hospital_type='P',
        procedure_code='SE020A'
    )
    
    if district_param:
        districts = district_param.split(',')
        base_qs = base_qs.filter(district_name__in=districts)

    # Similar violation filtering logic as get_ophthalmology_details
    if violation_type == 'age':
        cases = base_qs.filter(age_years__lt=40)
    elif violation_type == 'ot':
        # Get today's OT violations
        today = timezone.now().date()
        hospital_counts = base_qs.filter(
            Q(admission_date__date=today) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=today)
        ).values('hospital_id').annotate(case_count=Count('id'))
        
        violating_hospitals = [
            h['hospital_id'] for h in hospital_counts 
            if h['case_count'] > capacity_map.get(h['hospital_id'], 0)
        ]
        cases = base_qs.filter(hospital_id__in=violating_hospitals)
    elif violation_type == 'preauth':
        cases = base_qs.exclude(
            preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$'
        )
    else:  # All
        today = timezone.now().date()
        hospital_counts = base_qs.filter(
            Q(admission_date__date=today) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=today)
        ).values('hospital_id').annotate(case_count=Count('id'))
        
        violating_hospitals = [
            h['hospital_id'] for h in hospital_counts 
            if h['case_count'] > capacity_map.get(h['hospital_id'], 0)
        ]
        
        cases = base_qs.filter(
            Q(age_years__lt=40) |
            Q(hospital_id__in=violating_hospitals) |
            ~Q(preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$')
        )

    district_data = base_qs.values('district_name').annotate(
        count=Count('id')
    ).order_by('-count')

    return JsonResponse({
        'districts': [d['district_name'] or 'Unknown' for d in district_data],
        'counts': [d['count'] for d in district_data]
    })

def get_ophthalmology_demographics(request, type):
    violation_type = request.GET.get('violation_type', 'all')
    district_param = request.GET.get('district', '')
    
    # Get hospital capacity data
    hosp_info = SuspiciousHospital.objects.values('hospital_id', 'number_of_ot', 'number_of_surgeons')
    capacity_map = {
        h['hospital_id']: h['number_of_ot'] * h['number_of_surgeons'] * 30
        for h in hosp_info
    }

    base_qs = Last24Hour.objects.filter(
        hospital_type='P',
        procedure_code='SE020A'
    )
    
    if district_param:
        districts = district_param.split(',')
        base_qs = base_qs.filter(district_name__in=districts)

    today = timezone.now().date()

    # Violation filters
    if violation_type == 'age':
        base_qs = base_qs.filter(age_years__lt=40)
    elif violation_type == 'ot':
        # Get today's OT violations using capacity map
        hospital_counts = base_qs.filter(
            Q(admission_date__date=today) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=today)
        ).values('hospital_id').annotate(case_count=Count('id'))
        
        violating_hospitals = [
            h['hospital_id'] for h in hospital_counts 
            if h['case_count'] > capacity_map.get(h['hospital_id'], 0)
        ]
        base_qs = base_qs.filter(hospital_id__in=violating_hospitals)
    elif violation_type == 'preauth':
        base_qs = base_qs.exclude(
            preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$'
        )
    else:  # All violations
        # Get OT violations
        hospital_counts = base_qs.filter(
            Q(admission_date__date=today) |
            Q(admission_date__isnull=True, preauth_initiated_date__date=today)
        ).values('hospital_id').annotate(case_count=Count('id'))
        
        violating_hospitals = [
            h['hospital_id'] for h in hospital_counts 
            if h['case_count'] > capacity_map.get(h['hospital_id'], 0)
        ]
        
        # Combine all violation types
        base_qs = base_qs.filter(
            Q(age_years__lt=40) |
            Q(hospital_id__in=violating_hospitals) |
            ~Q(preauth_initiated_time__regex=r'^(0[8-9]|1[0-7]):[0-5][0-9]:[0-5][0-9]$')
        )

    if type == 'age':
        age_groups = Case(
            When(age_years__lt=20, then=Value('≤20')),
            When(age_years__gte=20, age_years__lt=30, then=Value('21-30')),
            When(age_years__gte=30, age_years__lt=40, then=Value('31-40')),
            When(age_years__gte=40, age_years__lt=50, then=Value('41-50')),
            When(age_years__gte=50, age_years__lt=60, then=Value('51-60')),
            When(age_years__gte=60, then=Value('60+')),
            default=Value('Unknown'),
            output_field=CharField()
        )
        
        age_data = base_qs.annotate(age_group=age_groups).values('age_group') \
            .annotate(count=Count('id')).order_by('age_group')
        
        categories = ['≤20', '21-30', '31-40', '41-50', '51-60', '60+', 'Unknown']
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF']
        
        age_dict = {item['age_group']: item['count'] for item in age_data}
        
        return JsonResponse({
            'labels': categories,
            'data': [age_dict.get(cat, 0) for cat in categories],
            'colors': colors
        })
        
    elif type == 'gender':
        gender_data = base_qs.values('gender') \
            .annotate(count=Count('id')).order_by('gender')
        
        categories = ['Male', 'Female', 'Other', 'Unknown']
        colors = ['#36A2EB', '#FF6384', '#4BC0C0', '#C9CBCF']
        
        gender_map = {
            'M': 'Male',
            'F': 'Female',
            'O': 'Other'
        }
        
        formatted = {gender_map.get(g['gender'], 'Unknown'): g['count'] for g in gender_data}
        return JsonResponse({
            'labels': categories,
            'data': [formatted.get(cat, 0) for cat in categories],
            'colors': colors
        })

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

def download_flagged_claims_excel(request):
    # 1. Read the same filter param
    district_param = request.GET.get('district', '')
    districts = district_param.split(',') if district_param else []

    # 2. Build the same queryset (no pagination)
    suspicious_hospitals = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    qs = Last24Hour.objects.filter(
        Q(hospital_id__in=suspicious_hospitals) &
        Q(hospital_type='P')
    )
    if districts:
        qs = qs.filter(district_name__in=districts)

    # 3. Assemble data into a list of dicts
    rows = []
    for case in qs:
        rows.append({
            'Claim ID': case.registration_id or case.case_id or 'N/A',
            'Patient Name': case.patient_name or f"Patient {case.member_id}",
            'Hospital Name': case.hospital_name or 'N/A',
            'District': case.district_name or 'N/A',
            'Amount': case.claim_initiated_amount or 0,
            'Reason': 'Suspicious hospital',
        })

    # 4. Create a DataFrame
    df = pd.DataFrame(rows)

    # 5. Write to an in-memory Excel file
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Flagged Claims')
        workbook  = writer.book
        worksheet = writer.sheets['Flagged Claims']

        # Style: red fill + white font for any cell whose value matches
        red_fill   = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')
        white_font = Font(color='FFFFFFFF')

        # Find all cells in the sheet, check value
        for row in worksheet.iter_rows(min_row=2, max_row=worksheet.max_row):
            for cell in row:
                if isinstance(cell.value, str) and cell.value.strip().lower() == 'suspicious hospital':
                    cell.fill = red_fill
                    cell.font = white_font

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="flagged_claims.xlsx"'
    return response

@require_http_methods(["GET", "POST"])
def download_flagged_claims_report(request):
    # 1) Read parameters & chart images
    district = request.POST.get('district', '')
    districts = district.split(',') if district else []

    # Each value is "data:image/png;base64,XXXXX"
    def strip_prefix(data_url):
        return data_url.split('base64,', 1)[1]

    flagged_b64 = strip_prefix(request.POST.get('flagged_chart', ''))
    age_b64     = strip_prefix(request.POST.get('age_chart', ''))
    gender_b64  = strip_prefix(request.POST.get('gender_chart', ''))
    age_callouts    = request.POST.get('age_callouts', '')
    gender_callouts = request.POST.get('gender_callouts', '')

    # 2) Fetch the FULL flagged-claims data (no pagination)
    suspicious_ids = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    qs = Last24Hour.objects.filter(
        Q(hospital_id__in=suspicious_ids) &
        Q(hospital_type='P')
    )
    if districts:
        qs = qs.filter(district_name__in=districts)

    table_rows = []
    for idx, case in enumerate(qs, start=1):
        table_rows.append({
            'serial_no':     idx,
            'claim_id':      case.registration_id or case.case_id or 'N/A',
            'patient_name':  case.patient_name or f"Patient {case.member_id}",
            'hospital_name': case.hospital_name or 'N/A',
            'district_name': case.district_name or 'N/A',
            'amount':        case.claim_initiated_amount or 0,
            'reason':        'Suspicious hospital'
        })
    report_districts = sorted({
        row['district_name'] 
        for row in table_rows 
        if row['district_name'] and row['district_name'] != 'N/A'
    })

    # 3) Render HTML via a dedicated template
    context = {
        'logo_url':    request.build_absolute_uri('/static/images/pmjaylogo.png'),
        'title':       'PMJAY FRAUD DETECTION ANALYSIS REPORT',
        'date':        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'table_rows':  table_rows,
        'report_districts': report_districts,
        'flagged_b64': flagged_b64,
        'age_b64':     age_b64,
        'gender_b64':  gender_b64,
        'age_callouts':    age_callouts,
        'gender_callouts': gender_callouts,
    }
    html_string = render_to_string('flagged_claims_report.html', context)

    # 4) Generate PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
    pdf  = html.write_pdf()

    # 5) Return as attachment
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="flagged_claims_report.pdf"'
    return response

@require_http_methods(["GET"])
def download_high_value_claims(request):
    # 1) read district filter
    district_param = request.GET.get('district', '')
    districts     = district_param.split(',') if district_param else []

    # 2) base queryset for P-type hospitals
    qs = Last24Hour.objects.filter(hospital_type='P')
    if districts:
        qs = qs.filter(district_name__in=districts)

    # 3) split into surgical & medical
    surgical_qs = qs.filter(
        case_type__iexact='SURGICAL',
        claim_initiated_amount__gte=100000
    )
    medical_qs = qs.filter(
        case_type__iexact='MEDICAL',
        claim_initiated_amount__gte=25000
    )

    # 4) helper to serialize
    def serialize(qs):
        rows = []
        for idx, c in enumerate(qs, start=1):
            rows.append({
                'S.No':          idx,
                'Claim ID':      c.registration_id or c.case_id or 'N/A',
                'Patient Name':  c.patient_name or f"Patient {c.member_id}",
                'Hospital Name': c.hospital_name or 'N/A',
                'District':      c.district_name or 'N/A',
                'Amount':        c.claim_initiated_amount or 0,
                'Case Type':     c.case_type.upper() if c.case_type else 'N/A'
            })
        return rows

    df_surgical = pd.DataFrame(serialize(surgical_qs))
    df_medical  = pd.DataFrame(serialize(medical_qs))

    # 5) write to Excel with two sheets
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_surgical.to_excel(writer, index=False, sheet_name='Surgical Reports')
        df_medical.to_excel(writer, index=False, sheet_name='Medical Reports')

        wb   = writer.book
        ws_s = writer.sheets['Surgical Reports']
        ws_m = writer.sheets['Medical Reports']

        # 6) define styles
        red_fill   = PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid')
        blue_fill  = PatternFill(start_color='0000FF', end_color='0000FF', fill_type='solid')
        white_font = Font(color='FFFFFFFF')

        # 7) style only the “Case Type” cells
        def style_sheet(ws, fill):
            # find the column index of “Case Type” in the header row
            header = next(ws.iter_rows(min_row=1, max_row=1))
            col_idx = next((i+1 for i, cell in enumerate(header) if cell.value == 'Case Type'), None)
            if not col_idx:
                return
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
                cell = row[col_idx-1]
                cell.fill = fill
                cell.font = white_font

        style_sheet(ws_s, red_fill)
        style_sheet(ws_m, blue_fill)

    buffer.seek(0)
    resp = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    resp['Content-Disposition'] = 'attachment; filename="high_value_claims_excel_report.xlsx"'
    return resp

import datetime
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
from weasyprint import HTML

from .models import Last24Hour

@require_POST
@csrf_protect
def download_high_value_claims_report(request):
    # 1) Read inputs
    case_type      = request.POST.get('case_type', 'all').lower()   # 'all','surgical','medical'
    district_param = request.POST.get('district', '')
    districts      = [d for d in district_param.split(',') if d]

    # 2) Helper for charts
    def strip_b64(key):
        val = request.POST.get(key, '')
        return val.split('base64,',1)[1] if 'base64,' in val else ''

    surgical_chart_b64     = strip_b64('surgical_chart')
    surgical_age_chart_b64 = strip_b64('surgical_age_chart')
    surgical_gen_chart_b64 = strip_b64('surgical_gender_chart')
    medical_chart_b64      = strip_b64('medical_chart')
    medical_age_chart_b64  = strip_b64('medical_age_chart')
    medical_gen_chart_b64  = strip_b64('medical_gender_chart')

    # Callouts
    surgical_age_callouts = request.POST.get('surgical_age_callouts','')
    surgical_gen_callouts = request.POST.get('surgical_gender_callouts','')
    medical_age_callouts  = request.POST.get('medical_age_callouts','')
    medical_gen_callouts  = request.POST.get('medical_gender_callouts','')

    # 3) Build querysets based on case_type
    base_qs = Last24Hour.objects.filter(hospital_type='P')
    surgical_qs = base_qs.none()
    medical_qs  = base_qs.none()

    if case_type in ['all','surgical']:
        surgical_qs = base_qs.filter(case_type__iexact='SURGICAL', claim_initiated_amount__gte=100000)
    if case_type in ['all','medical']:
        medical_qs  = base_qs.filter(case_type__iexact='MEDICAL',  claim_initiated_amount__gte=25000)

    if districts:
        surgical_qs = surgical_qs.filter(district_name__in=districts)
        medical_qs  = medical_qs.filter(district_name__in=districts)

    # 4) Serialize rows
    surgical_rows = [
        {
            'serial_no':     i+1,
            'claim_id':      c.registration_id or c.case_id or 'N/A',
            'patient_name':  c.patient_name or f"Patient {c.member_id}",
            'hospital_name': c.hospital_name or 'N/A',
            'district_name': c.district_name or 'N/A',
            'amount':        c.claim_initiated_amount or 0,
            'case_type':     'SURGICAL'
        }
        for i, c in enumerate(surgical_qs)
    ]
    medical_rows = [
        {
            'serial_no':     i+1,
            'claim_id':      c.registration_id or c.case_id or 'N/A',
            'patient_name':  c.patient_name or f"Patient {c.member_id}",
            'hospital_name': c.hospital_name or 'N/A',
            'district_name': c.district_name or 'N/A',
            'amount':        c.claim_initiated_amount or 0,
            'case_type':     'MEDICAL'
        }
        for i, c in enumerate(medical_qs)
    ]

    # 5) Compute report_districts as a sorted list
    combined = [r['district_name'] for r in surgical_rows + medical_rows if r['district_name'] and r['district_name'] != 'N/A']
    report_districts = sorted(set(combined))

    # 6) Render
    context = {
        'logo_url':                request.build_absolute_uri('/static/images/pmjaylogo.png'),
        'title':                   'PMJAY FRAUD DETECTION ANALYSIS REPORT',
        'date':                    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'case_type':               case_type,
        'report_districts':        report_districts,
        'surgical_rows':           surgical_rows,
        'medical_rows':            medical_rows,
        'surgical_chart_b64':      surgical_chart_b64,
        'surgical_age_chart_b64':  surgical_age_chart_b64,
        'surgical_gen_chart_b64':  surgical_gen_chart_b64,
        'medical_chart_b64':       medical_chart_b64,
        'medical_age_chart_b64':   medical_age_chart_b64,
        'medical_gen_chart_b64':   medical_gen_chart_b64,
        'surgical_age_callouts':   surgical_age_callouts,
        'surgical_gen_callouts':   surgical_gen_callouts,
        'medical_age_callouts':    medical_age_callouts,
        'medical_gen_callouts':    medical_gen_callouts,
    }
    html_string = render_to_string('high_value_claims_report.html', context)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="High_Value_Claims_PDF_Report.pdf"'
    return response

@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html') 
