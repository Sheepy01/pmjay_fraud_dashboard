from django.db import models

class SuspiciousHospital(models.Model):
    hospital_id = models.CharField(max_length=50, unique=True)
    hospital_name = models.CharField(max_length=200)
    number_of_surgeons = models.IntegerField(null=True, blank=True)
    number_of_ot = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.hospital_name

class Last24Hour(models.Model):
    registration_id = models.CharField(max_length=100, null=True, blank=True)
    case_id = models.CharField(max_length=100, null=True, blank=True)
    member_id = models.CharField(max_length=100, null=True, blank=True)
    family_id = models.CharField(max_length=100, null=True, blank=True)
    district_name = models.CharField(max_length=100, null=True, blank=True)
    state_name = models.CharField(max_length=100, null=True, blank=True)
    patient_name = models.CharField(max_length=200, null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    age_years = models.IntegerField(null=True, blank=True)
    patient_mobile_number = models.CharField(max_length=50, null=True, blank=True)
    speciality_code = models.CharField(max_length=100, null=True, blank=True)
    category_details = models.CharField(max_length=200, null=True, blank=True)
    procedure_code = models.CharField(max_length=100, null=True, blank=True)
    procedure_details = models.CharField(max_length=500, null=True, blank=True)
    case_status = models.CharField(max_length=100, null=True, blank=True)
    hospital_code = models.CharField(max_length=100, null=True, blank=True)
    hospital_name = models.CharField(max_length=200, null=True, blank=True)
    hospital_district_name = models.CharField(max_length=100, null=True, blank=True)
    hospital_state_name = models.CharField(max_length=100, null=True, blank=True)
    admission_type = models.CharField(max_length=50, null=True, blank=True)
    admission_date = models.DateTimeField(null=True, blank=True)
    preauth_initiated_date_time = models.DateTimeField(null=True, blank=True)
    preauth_initiated_time = models.CharField(max_length=50, null=True, blank=True)
    preauth_amount_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    preauth_approve_date = models.DateTimeField(null=True, blank=True)
    preauth_approved_amount_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    preauth_rejected_date = models.DateTimeField(null=True, blank=True)
    surgery_date = models.DateTimeField(null=True, blank=True)
    death_date = models.DateTimeField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    claim_initiated_date = models.DateTimeField(null=True, blank=True)
    claim_approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    claim_paid_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    claim_rejected_date = models.DateTimeField(null=True, blank=True)
    rf_amount_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tds_amount_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cpd_approved_date = models.DateTimeField(null=True, blank=True)
    cpd_approved_amount_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sha_approved_date = models.DateTimeField(null=True, blank=True)
    sha_approved_amount_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    aco_approved_date = models.DateTimeField(null=True, blank=True)
    aco_approved_amount_rs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    utr = models.CharField(max_length=100, null=True, blank=True)
    hospital_pan = models.CharField(max_length=100, null=True, blank=True)
    hospital_account_no = models.CharField(max_length=100, null=True, blank=True)
    hospital_ifsc_no = models.CharField(max_length=100, null=True, blank=True)
    payment_paid_date = models.DateTimeField(null=True, blank=True)
    transaction_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    hospital_id = models.CharField(max_length=50)
    hospital_type = models.CharField(max_length=10)  # "P" for Private, "G" for Government
    preauth_initiated_date = models.DateTimeField()
    case_type = models.CharField(max_length=50)  # e.g., "SURGERY" or "MEDICAL"
    claim_initiated_amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.hospital_id} at {self.preauth_initiated_date}"
    
class HospitalBeds(models.Model):
    hospital_id = models.CharField(max_length=50, unique=True)
    bed_strength = models.IntegerField()
