from django.db.models import Sum, Q, Avg, F, Func, Count, Subquery, Max
from .models import Last24Hour, SuspiciousHospital, HospitalBeds
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, CharField
from django.contrib.auth import login as auth_login
from django.http import JsonResponse, HttpResponse
from django.db.models.functions import TruncDate
from django.utils.timezone import now, timedelta
from openpyxl.styles import PatternFill, Font
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import re
import io
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import plotly.express as px
import json
from io import BytesIO
import base64
import time
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
import datetime

@require_POST
@csrf_protect
def download_flagged_claims_report(request):
    # 1) Read parameters & chart images
    district = request.POST.get('district', '')
    districts = district.split(',') if district else []

    # Each value is "data:image/png;base64,XXXXX"
    def strip_prefix(data_url):
        return data_url.split('base64,', 1)[1]

    flagged_b64 = strip_prefix(request.POST['flagged_chart'])
    age_b64     = strip_prefix(request.POST['age_chart'])
    gender_b64  = strip_prefix(request.POST['gender_chart'])
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

    # 3) Render HTML via a dedicated template
    context = {
        'logo_url':    request.build_absolute_uri('/static/images/pmjaylogo.png'),
        'title':       'PMJAY FRAUD DETECTION ANALYSIS REPORT',
        'date':        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'table_rows':  table_rows,
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

def download_flagged_claims(request):
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

@login_required(login_url='login')
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

def download_high_value_claims_excel(request):
    # Query surgical and medical
    surgical_claims = Last24Hour.objects.filter(
        hospital_type="P",
        case_type="SURGICAL",
        claim_initiated_amount__gt=100000
    ).values()

    medical_claims = Last24Hour.objects.filter(
        hospital_type="P",
        case_type="MEDICAL",
        claim_initiated_amount__gt=25000
    ).values()

    df_surgical = pd.DataFrame.from_records(surgical_claims)
    df_medical = pd.DataFrame.from_records(medical_claims)

    # Drop columns that are all null
    for df in [df_surgical, df_medical]:
        df.dropna(axis=1, how="all", inplace=True)
        
        # Convert columns to datetime if possible, then remove timezone
        for col in df.columns:
            # Try parsing columns as datetime if not already
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col], errors='ignore')
            
            # If it is datetime now, strip timezone
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None)

    # Write to a single Excel file with two sheets
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_surgical.to_excel(writer, index=False, sheet_name='Surgical High Value Claims')
        df_medical.to_excel(writer, index=False, sheet_name='Medical High Value Claims')
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="High_Value_Claims.xlsx"'
    return response

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