from django.shortcuts import render
from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.http import HttpResponse
from django.http import JsonResponse
from django.db.models import F, Func, Count
from datetime import timedelta
from .models import Last24Hour, SuspiciousHospital, HospitalBeds
import pandas as pd
import io

class Upper(Func):
    function = 'UPPER'
    template = '%(function)s(%(expressions)s)'

def filter_dashboard_data(request):
    district = request.GET.get('district')
    queryset = Last24Hour.objects.all()

    if district:
        queryset = queryset.filter(district_name=district)

    # Sample data aggregation (you can add your actual 5 rules here)
    ot_violations = queryset.filter(rule_ot_violation=True).count()
    preauth_timing_issues = queryset.filter(rule_preauth_time=True).count()
    under_40_cataracts = queryset.filter(rule_age_cataract=True).count()
    emergency_cases = queryset.filter(rule_emergency=True).count()
    same_day_claims = queryset.filter(rule_multiple_claims=True).count()

    return JsonResponse({
        'ot_violations': ot_violations,
        'preauth_timing_issues': preauth_timing_issues,
        'under_40_cataracts': under_40_cataracts,
        'emergency_cases': emergency_cases,
        'same_day_claims': same_day_claims
    })

def get_districts(request):
    districts = Last24Hour.objects.values_list('district_name', flat=True).distinct()
    district_list = [d for d in districts if d]  # Remove None/empty values
    return JsonResponse({'districts': district_list})

def get_rule_counts(df):
    """
    Given a DataFrame (df) of Last24Hour records (already filtered to hospital_type='P' and with
    necessary columns converted), returns a dictionary with counts for each of the 5 rules:
      1) Ophthalmology OT Cases: For procedure_code='SE020A', count grouped daily cases 
         that exceed the threshold = (num_ot * num_surgeons * 30)
      2) Ophthalmology Preauth Time: For procedure_code='SE020A', count cases where the extracted
         hour (from preauth_initiated_time) is between 8 and 17 (i.e. 8AM to 5:59 PM).\n
      3) Ophthalmology Age Cases: For procedure_code='SE020A', count cases with age_years < 40\n
      4) Emergency Cases: Count cases where admission_type = 'E' and procedure_details contain any of 
         ['cataract', 'oncology', 'dialysis']\n
      5) Family ID Cases: Count cases where, for a given family_id and date, the count > 2.
    """
    # ---- Rule 1: Ophthalmology OT Cases ----
    # Filter for cataract cases (assuming procedure_code column exists and is already uppercased)
    df_ophtho = df[df['procedure_code'] == 'SE020A'].copy()
    # Group by hospital_id and date_only to compute daily counts
    grp = df_ophtho.groupby(['hospital_id', 'date_only']).size().reset_index(name='daily_count')
    df_ophtho = df_ophtho.merge(grp, on=['hospital_id', 'date_only'], how='left')
    # Load OT & Surgeon info from SuspiciousHospital into a dictionary: {hospital_id: threshold}
    sh_qs = SuspiciousHospital.objects.all().values('hospital_id', 'number_of_ot', 'number_of_surgeons')
    threshold_dict = {}
    for rowb in sh_qs:
        hosp = str(rowb['hospital_id']).upper()
        num_ot = rowb.get('number_of_ot') or 0
        num_surgeons = rowb.get('number_of_surgeons') or 0
        threshold_dict[hosp] = num_ot * num_surgeons * 30
    # For each row, mark as violating if daily_count > threshold
    def flag_ot(row):
        hosp = str(row['hospital_id']).upper()
        th = threshold_dict.get(hosp, 0)
        return row['daily_count'] > th
    df_ophtho['flag_ot'] = df_ophtho.apply(flag_ot, axis=1)
    count_ophtho_ot = df_ophtho[df_ophtho['flag_ot']].shape[0]
    
    # ---- Rule 2: Ophthalmology Preauth Time ----
    df_ophtho_time = df[df['procedure_code'] == 'SE020A'].copy()
    count_ophtho_time = df_ophtho_time[df_ophtho_time['hour'].between(8, 17)].shape[0]
    
    # ---- Rule 3: Ophthalmology Age Cases ----
    df_ophtho_age = df[df['procedure_code'] == 'SE020A'].copy()
    count_ophtho_age = df_ophtho_age[df_ophtho_age['age_years'] < 40].shape[0]
    
    # ---- Rule 4: Emergency Cases ----
    df_emergency = df.copy()
    df_emergency['emergency_flag'] = df_emergency.apply(
        lambda r: (r['admission_type'] == 'E') and 
                  any(keyword in r['procedure_details'] for keyword in ['cataract','oncology','dialysis']),
        axis=1
    )
    count_emergency = df_emergency[df_emergency['emergency_flag']].shape[0]
    
    # ---- Rule 5: Family ID Cases ----
    # Group by family_id and date_only and count how many times each appears
    grp_fam = df.groupby(['family_id', 'date_only']).size().reset_index(name='fam_count')
    df_family = df.merge(grp_fam, on=['family_id', 'date_only'], how='left')
    count_family = df_family[df_family['fam_count'] > 2].shape[0]
    
    return {
        'ophtho_ot': count_ophtho_ot,
        'ophtho_time': count_ophtho_time,
        'ophtho_age': count_ophtho_age,
        'emergency': count_emergency,
        'family': count_family
    }

def get_bed_violations(df):
    if df.empty:
        return 0

    # Group by hospital and date to get daily admissions
    daily_grp = df.groupby(['hospital_id', 'date_only']).size().reset_index(name='daily_admissions')
    df = df.merge(daily_grp, on=['hospital_id', 'date_only'], how='left')

    beds_qs = HospitalBeds.objects.all().values('hospital_id','bed_strength')
    bed_dict = {row['hospital_id'].upper(): row['bed_strength'] for row in beds_qs}

    # Compare with bed strength from bed_dict
    def cond_bed_strength(row):
        hosp_id = str(row['hospital_id']).upper()
        b_strength = bed_dict.get(hosp_id, 0)
        return row['daily_admissions'] > b_strength

    df['bed_violation'] = df.apply(cond_bed_strength, axis=1)

    # Count how many rows are violations
    return df['bed_violation'].sum()


def get_unusual_rows():
    """
    Returns a DataFrame of rows that meet ANY of these conditions:
      1) Ophthalmology rule:
         - procedure_code='SE020A'
         - age_years < 40
         - preauth_initiated_time in [8..18)
         - daily count of such rows > (num_ot * num_surgeons * 30)
      2) Emergency prebooking:
         - admission_type='E'
         - procedure_details has 'cataract','oncology','dialysis'
      3) Family ID rule:
         - more than 2 cases same day for the same family_id
      4) daily admissions > bed_strength => all those cases for that day/hospital
    """

    qs = Last24Hour.objects.all().values()
    df = pd.DataFrame(qs)
    if df.empty:
        return df

    if 'hospital_type' not in df.columns:
        df['hospital_type'] = ''
    else:
        df['hospital_type'] = df['hospital_type'].fillna('').astype(str).str.strip().str.upper()

    df = df[df['hospital_type'] == 'P']
    if df.empty:
        return df

    if 'preauth_initiated_date' in df.columns:
        df['preauth_initiated_date'] = pd.to_datetime(df['preauth_initiated_date'], errors='coerce')
        df['preauth_initiated_date'] = df['preauth_initiated_date'].dt.tz_localize(None)
    df['date_only'] = df['preauth_initiated_date'].dt.date

    if 'preauth_initiated_time' in df.columns:
        pass
        # print(df['preauth_initiated_time'].head())
    else:
        print("Column 'Preauth Initiated Time' is missing!")

    if 'preauth_initiated_time' in df.columns:
        df['preauth_initiated_time'] = df['preauth_initiated_time'].astype(str).str.strip()
        
        print("Raw time values:", df['preauth_initiated_time'].dropna().unique()[:5])
        
        df['preauth_initiated_time_parsed'] = pd.to_datetime(
            df['preauth_initiated_time'], 
            format='%H:%M:%S',  # 24-hour format
            errors='coerce'
        )

        df['hour'] = df['preauth_initiated_time_parsed'].dt.hour

        print(df[['preauth_initiated_time', 'preauth_initiated_time_parsed', 'hour']].head(10))
        print("Unique extracted hours:", df['hour'].dropna().unique())
        print("Missing hour values:", df['hour'].isna().sum())
    else:
        df['hour'] = None
    
    if 'admission_type' in df.columns:
        df['admission_type'] = df['admission_type'].fillna('').astype(str).str.upper()
    if 'procedure_details' in df.columns:
        df['procedure_details'] = df['procedure_details'].fillna('').astype(str).str.lower()

    beds_qs = HospitalBeds.objects.all().values('hospital_id','bed_strength')
    bed_dict = {row['hospital_id'].upper(): row['bed_strength'] for row in beds_qs}

    # Condition 4: daily admissions > bed_strength
    daily_grp = df.groupby(['hospital_id','date_only']).size().reset_index(name='daily_admissions')
    df = df.merge(daily_grp, on=['hospital_id','date_only'], how='left')

    def cond_bed_strength(row):
        hosp_id = str(row['hospital_id']).upper()
        b_strength = bed_dict.get(hosp_id, 0)
        return row['daily_admissions'] > b_strength

    df['cond4'] = df.apply(cond_bed_strength, axis=1)

    # ----------------------
    # Condition 1: Ophthalmology
    # ----------------------
    df['is_cataract'] = df['procedure_details'].str.contains('cataract', na=False)
    df['age_years'] = pd.to_numeric(df['age_years'], errors='coerce')
    df['cond1_part_a'] = False
    df['cond1_part_b'] = False
    df['cond1_part_c'] = False

    # Check if 'num_ot' and 'num_surgeons' are present
    if 'num_ot' in df.columns and 'num_surgeons' in df.columns:
        # Count rows with cataract procedure
        cataract_df = df[df['is_cataract']]
        if not cataract_df.empty:
            grouped = cataract_df.groupby(['hospital_id', 'date_only'])
            cataract_counts = grouped.size().reset_index(name='cataract_daily_count')
            df = df.merge(cataract_counts, on=['hospital_id', 'date_only'], how='left')
            df['cataract_daily_count'] = df['cataract_daily_count'].fillna(0)

            df['threshold'] = df['num_ot'].fillna(0) * df['num_surgeons'].fillna(0) * 30
            df['cond1_part_a'] = df['is_cataract'] & (df['cataract_daily_count'] > df['threshold'])

    df['cond1_part_b'] = df['is_cataract'] & df['hour'].between(8, 17)
    df['cond1_part_c'] = df['is_cataract'] & (df['age_years'] < 40)

    df['cond1'] = df['cond1_part_a'] & df['cond1_part_b'] & df['cond1_part_c']

    # Condition 2: Emergency prebooking
    def cond_emergency_prebooking(row):
        if row['admission_type'] != 'E':
            return False
        text = row['procedure_details']
        return any(k in text for k in ['cataract','oncology','dialysis'])

    df['cond2'] = df.apply(cond_emergency_prebooking, axis=1)

    # Condition 3: Family ID rule
    if 'family_id' not in df.columns:
        df['family_id'] = ''
    fam_grp = df.groupby(['family_id','date_only']).size().reset_index(name='fam_count')
    df = df.merge(fam_grp, on=['family_id','date_only'], how='left')
    df['cond3'] = df['fam_count'] > 2

    df['is_unusual'] = df['cond1'] | df['cond2'] | df['cond3'] | df['cond4']

    df_unusual = df[df['is_unusual'] == True].copy()
    return df_unusual

def dashboard(request):
    # Define the current time
    now = timezone.now()
    yesterday = (now - timedelta(days=1)).date()
    last_30_days = (now - timedelta(days=30)).date()

    # Get the list of hospital IDs from Suspicious Hospital
    flagged_hospitals = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    
    #Flagged Claims
    # Overall flagged claims:
    flagged_overall = Last24Hour.objects.filter(
        hospital_type="P",
        hospital_id__in=flagged_hospitals
    ).count()
    
    flagged_last_30_days = Last24Hour.objects.filter(
        hospital_type="P",
        hospital_id__in=flagged_hospitals,
        preauth_initiated_date__gte=last_30_days,
        preauth_initiated_date__lte=now
    ).count()

    flagged_yesterday = Last24Hour.objects.filter(
        hospital_type="P",
        hospital_id__in=flagged_hospitals,
        preauth_initiated_date__date=yesterday
    ).count()

    # Geographic Anomalies
    # Overall Geographic Anomalies
    geo_overall = (
        Last24Hour.objects
        .annotate(
            hospital_type_upper=Upper('hospital_type'),
            state_name_upper=Upper('state_name'),
            hospital_state_name_upper=Upper('hospital_state_name')
        )
        .filter(hospital_type_upper='P')
        .exclude(state_name_upper=F('hospital_state_name_upper'))
        .count()
    )
    
    # Last 30 Days Geographic Anomalies
    geo_last_30_days = (
        Last24Hour.objects
        .annotate(
            hospital_type_upper=Upper('hospital_type'),
            state_name_upper=Upper('state_name'),
            hospital_state_name_upper=Upper('hospital_state_name')
        )
        .filter(
            hospital_type_upper='P',
            preauth_initiated_date__gte=last_30_days,
            preauth_initiated_date__lte=now
        )
        .exclude(state_name_upper=F('hospital_state_name_upper'))
        .count()
    )

    # Yesterday Geographic Anomalies
    geo_yesterday = (
        Last24Hour.objects
        .annotate(
            hospital_type_upper=Upper('hospital_type'),
            state_name_upper=Upper('state_name'),
            hospital_state_name_upper=Upper('hospital_state_name')
        )
        .filter(
            hospital_type_upper='P',
            preauth_initiated_date__date=yesterday
        )
        .exclude(state_name_upper=F('hospital_state_name_upper'))
        .count()
    )

    # High Value Surgical Claims
    surgical_overall = Last24Hour.objects.filter(
        hospital_type="P",
        case_type="SURGICAL",
        claim_initiated_amount__gt=100000
    ).count()

    surgical_last_30_days = Last24Hour.objects.filter(
        hospital_type="P",
        case_type="SURGICAL",
        claim_initiated_amount__gt=100000,
        preauth_initiated_date__gte=last_30_days
    ).count()

    surgical_yesterday = Last24Hour.objects.filter(
        hospital_type="P",
        case_type="SURGICAL",
        claim_initiated_amount__gt=100000,
        preauth_initiated_date=yesterday
    ).count()

    # High Value Medical Claims
    medical_overall = Last24Hour.objects.filter(
        hospital_type="P",
        case_type="MEDICAL",
        claim_initiated_amount__gt=25000
    ).count()

    medical_last_30_days = Last24Hour.objects.filter(
        hospital_type="P",
        case_type="MEDICAL",
        claim_initiated_amount__gt=25000,
        preauth_initiated_date__gte=last_30_days
    ).count()

    medical_yesterday = Last24Hour.objects.filter(
        hospital_type="P",
        case_type="MEDICAL",
        claim_initiated_amount__gt=25000,
        preauth_initiated_date=yesterday
    ).count()

    df_unusual = get_unusual_rows()
    # if df_unusual.empty:
    #     context = {
    #         'unusual_treatment_overall': 0,
    #         'unusual_treatment_last_30_days': 0,
    #         'unusual_treatment_yesterday': 0,
    #     }
    
    # Overall
    unusual_overall = len(df_unusual)
    thirty_days_ago = (now - timedelta(days=30)).date()
    # yesterday = (now - timedelta(days=1)).date()

    # Last 30 days
    df_30 = df_unusual[df_unusual['date_only'] >= thirty_days_ago]
    unusual_last_30_days = len(df_30)

    # Yesterday
    df_yest = df_unusual[df_unusual['date_only'] == yesterday]
    unusual_yesterday = len(df_yest)
    
    qs = Last24Hour.objects.all().values()
    df = pd.DataFrame(qs)
    if not df.empty:
        # Convert preauth_initiated_date to datetime and remove timezone
        df['preauth_initiated_date'] = pd.to_datetime(df['preauth_initiated_date'], errors='coerce').dt.tz_localize(None)
        # Create a 'date_only' column for grouping and filtering (as date)
        df['date_only'] = df['preauth_initiated_date'].dt.date
        
        # Clean up required fields
        df['hospital_type'] = df['hospital_type'].fillna('').astype(str).str.strip().str.upper()
        df['procedure_code'] = df['procedure_code'].fillna('').astype(str).str.strip().str.upper()
        df['admission_type'] = df['admission_type'].fillna('').astype(str).str.strip().str.upper()
        df['procedure_details'] = df['procedure_details'].fillna('').astype(str).str.lower()
        df['age_years'] = pd.to_numeric(df['age_years'], errors='coerce')

        # IMPORTANT: Create the 'hour' column using 'preauth_initiated_time' if available, else fallback
        if 'preauth_initiated_time' in df.columns and df['preauth_initiated_time'].notna().any():
            df['preauth_initiated_time'] = pd.to_datetime(df['preauth_initiated_time'], format='%H:%M:%S', errors='coerce')
            df['hour'] = df['preauth_initiated_time'].dt.hour
        else:
            df['hour'] = df['preauth_initiated_date'].dt.hour
    else:
        df = pd.DataFrame()

    overall_counts = get_rule_counts(df) if not df.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
    
    # Filter for Last 30 Days using the date_only column
    df_last30 = df[df['date_only'] >= last_30_days] if not df.empty else df
    last30_counts = get_rule_counts(df_last30) if not df_last30.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
    
    # Filter for Yesterday
    df_yesterday = df[df['date_only'] == yesterday] if not df.empty else df
    yesterday_counts = get_rule_counts(df_yesterday) if not df_yesterday.empty else {key: 0 for key in ['ophtho_ot', 'ophtho_time', 'ophtho_age', 'emergency', 'family']}
    
    # Bed strength rule violations
    bed_violation_overall = get_bed_violations(df)

    df_last30 = df[df['date_only'] >= last_30_days]
    bed_violation_last30 = get_bed_violations(df_last30)

    df_yesterday = df[df['date_only'] == yesterday]
    bed_violation_yesterday = get_bed_violations(df_yesterday)

    context = {
        'flagged_claims_overall': flagged_overall,
        'flagged_claims_last_30_days': flagged_last_30_days,
        'flagged_claims_yesterday': flagged_yesterday,
        'geo_overall': geo_overall,
        'geo_last_30_days': geo_last_30_days,
        'geo_yesterday': geo_yesterday,
        'surgical_overall': surgical_overall,
        'surgical_last_30_days': surgical_last_30_days,
        'surgical_yesterday': surgical_yesterday,
        'medical_overall': medical_overall,
        'medical_last_30_days': medical_last_30_days,
        'medical_yesterday': medical_yesterday,
        'unusual_treatment_overall': unusual_overall,
        'unusual_treatment_last_30_days': unusual_last_30_days,
        'unusual_treatment_yesterday': unusual_yesterday,
        # Ophthalmology OT Cases counts
        'ophtho_ot_overall': overall_counts['ophtho_ot'],
        'ophtho_ot_last30': last30_counts['ophtho_ot'],
        'ophtho_ot_yesterday': yesterday_counts['ophtho_ot'],
        # Ophthalmology Preauth Time counts
        'ophtho_time_overall': overall_counts['ophtho_time'],
        'ophtho_time_last30': last30_counts['ophtho_time'],
        'ophtho_time_yesterday': yesterday_counts['ophtho_time'],
        # Ophthalmology Age Cases counts
        'ophtho_age_overall': overall_counts['ophtho_age'],
        'ophtho_age_last30': last30_counts['ophtho_age'],
        'ophtho_age_yesterday': yesterday_counts['ophtho_age'],
        # Emergency Cases counts
        'emergency_overall': overall_counts['emergency'],
        'emergency_last30': last30_counts['emergency'],
        'emergency_yesterday': yesterday_counts['emergency'],
        # Family ID Cases counts
        'family_overall': overall_counts['family'],
        'family_last30': last30_counts['family'],
        'family_yesterday': yesterday_counts['family'],
        
        'bed_violations': {
            'overall': bed_violation_overall,
            'last30': bed_violation_last30,
            'yesterday': bed_violation_yesterday,
        },
    }
    
    return render(request, 'index.html', context)

def download_flagged_claims_excel(request):
    # Get flagged hospital IDs from SuspiciousHospital
    flagged_hospital_ids = SuspiciousHospital.objects.values_list('hospital_id', flat=True)
    
    # Filter Last24Hour records for flagged claims and only for Private hospitals ("P")
    qs = Last24Hour.objects.filter(
        hospital_type="P",
        hospital_id__in=flagged_hospital_ids
    )
    
    # Convert the queryset to a list of dictionaries
    data = list(qs.values())
    
    # Convert the data to a Pandas DataFrame
    df = pd.DataFrame(data)
    
    # Convert timezone-aware datetime columns to naive datetimes
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    # Drop columns that are completely null
    df = df.dropna(axis=1, how='all')

    print(df)

    # Create an in-memory output file for the new workbook.
    output = io.BytesIO()
    
    # Write the DataFrame to an Excel file in memory
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Flagged Claims')
    
    output.seek(0)  # Rewind the buffer
    
    # Create an HTTP response with the Excel file
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="flagged_claims.xlsx"'
    return response

def download_geo_anomalies_excel(request):
    """
    Download Geographic Anomalies data as an Excel file.
    A record is considered an anomaly if:
    - Hospital Type = "P"
    - State Name != Hospital State Name
    """

    # Query the Last24Hour model for geographic anomalies
    qs = (
        Last24Hour.objects
        .annotate(
            hospital_type_upper=Upper('hospital_type'),
            state_name_upper=Upper('state_name'),
            hospital_state_name_upper=Upper('hospital_state_name')
        )
        .filter(hospital_type_upper='P')
        .exclude(state_name_upper=F('hospital_state_name_upper'))
    )

    # Convert the queryset to a list of dictionaries
    data = list(qs.values())

    # Convert the data to a Pandas DataFrame
    df = pd.DataFrame(data)

    # If you have timezone-aware datetime fields, remove the timezone
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    # Drop columns that are completely null (optional)
    df = df.dropna(axis=1, how='all')

    # Create an in-memory output file for the Excel workbook
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Geo Anomalies')
    output.seek(0)

    # Create an HTTP response with the Excel file
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="geo_anomalies.xlsx"'
    return response

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

def download_unusual_treatment_excel(request):
    df_unusual = get_unusual_rows()
    if df_unusual.empty:
        return HttpResponse("No Unusual Treatment Patterns found.")

    # Drop columns that are all null
    df_unusual.dropna(axis=1, how='all', inplace=True)

    # Create an in-memory Excel file
    import io
    import pandas as pd
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_unusual.to_excel(writer, index=False, sheet_name='Unusual Patterns')
    output.seek(0)

    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Unusual_Treatment_Patterns.xlsx"'
    return response


