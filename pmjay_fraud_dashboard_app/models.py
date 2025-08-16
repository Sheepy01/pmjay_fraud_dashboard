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
    patient_name = models.CharField(max_length=200, null=True, blank=True)
    patient_dob = models.CharField(max_length=20, null=True, blank=True)  # Could be DateField if always YYYY or YYYY-MM-DD
    patient_state_code = models.CharField(max_length=10, null=True, blank=True)
    patient_district_code = models.CharField(max_length=10, null=True, blank=True)
    patient_district_name = models.CharField(max_length=100, null=True, blank=True)
    patient_state_name = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    policy_code = models.CharField(max_length=100, null=True, blank=True)
    renewal_code = models.CharField(max_length=100, null=True, blank=True)
    category_details = models.CharField(max_length=500, null=True, blank=True)
    speciality_code = models.CharField(max_length=100, null=True, blank=True)
    procedure_details = models.CharField(max_length=1000, null=True, blank=True)
    procedure_code = models.CharField(max_length=200, null=True, blank=True)
    case_type = models.CharField(max_length=50, null=True, blank=True)
    status_id_pk = models.CharField(max_length=50, null=True, blank=True)
    case_status = models.CharField(max_length=200, null=True, blank=True)
    hospital_code = models.CharField(max_length=100, null=True, blank=True)
    hospital_name = models.CharField(max_length=200, null=True, blank=True)
    hosp_district_name = models.CharField(max_length=100, null=True, blank=True)
    hosp_state_name = models.CharField(max_length=100, null=True, blank=True)
    hospital_state_cd = models.CharField(max_length=10, null=True, blank=True)
    hospital_district_cd = models.CharField(max_length=10, null=True, blank=True)
    hosp_pan_number = models.CharField(max_length=20, null=True, blank=True)
    hospital_type = models.CharField(max_length=10, null=True, blank=True)
    admission_dt = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField if always date/time
    preauth_init_date = models.DateTimeField(null=True, blank=True)  # Could be DateTimeField
    amount_preauth_initiated = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    preauth_approved_date = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    amount_preauth_approved = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    preauth_rejected_date = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    surgery_dt = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    death_dt = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    discharge_dt = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    claim_init_date = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    amount_claim_initiated = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_claim_approved = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_claim_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    claim_rejected_date = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    rf_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tds_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    utr_no = models.CharField(max_length=100, null=True, blank=True)
    payment_paid_dt = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    transaction_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cpd_approved_date = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    cpd_approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cpd_user = models.CharField(max_length=100, null=True, blank=True)
    aco_approved_date = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    aco_approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    aco_user = models.CharField(max_length=100, null=True, blank=True)
    sha_approved_date = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    sha_approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sha_user = models.CharField(max_length=100, null=True, blank=True)
    json_object_perauth = models.TextField(null=True, blank=True)
    json_object_claim = models.TextField(null=True, blank=True)
    json_object_ben = models.TextField(null=True, blank=True)
    src_account_no = models.CharField(max_length=100, null=True, blank=True)
    src_ifsc_code = models.CharField(max_length=20, null=True, blank=True)
    paid_flag = models.CharField(max_length=10, null=True, blank=True)
    hosp_account_number = models.CharField(max_length=100, null=True, blank=True)
    ben_ifsc_code = models.CharField(max_length=20, null=True, blank=True)
    current_workflow_role = models.CharField(max_length=100, null=True, blank=True)
    current_workflow_user = models.CharField(max_length=100, null=True, blank=True)
    service_request_type = models.CharField(max_length=100, null=True, blank=True)
    m_flag = models.CharField(max_length=10, null=True, blank=True)
    careplan_desc = models.CharField(max_length=500, null=True, blank=True)
    discharge_type = models.CharField(max_length=100, null=True, blank=True)
    admission_type = models.CharField(max_length=100, null=True, blank=True)
    claim_approved_date = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField
    last_insert_dt = models.CharField(max_length=50, null=True, blank=True)  # Could be DateTimeField

    class Meta:
        unique_together = ('registration_id', 'preauth_init_date')
        indexes = [
            models.Index(fields=['hospital_type', 'procedure_code']),
            models.Index(fields=['admission_dt']),
            models.Index(fields=['patient_district_name']),
            models.Index(fields=['age']),
            models.Index(fields=['hospital_code']),
        ]

    def __str__(self):
        return f"{self.registration_id} - {self.patient_name}"

    
class HospitalBeds(models.Model):
    hospital_id = models.CharField(max_length=50, unique=True)
    hospital_name = models.CharField(max_length=50, null=True, blank=True)
    bed_strength = models.IntegerField()
    number_of_surgeons = models.IntegerField(null=True, blank=True)
    number_of_ot = models.IntegerField(null=True, blank=True)

class UploadHistory(models.Model):
    MODEL_CHOICES = [
        ('suspicious', 'Suspicious Hospital List'),
        ('beds',       'Hospital Beds'),
    ]
    model_type  = models.CharField(max_length=20, choices=MODEL_CHOICES, unique=True)
    filename    = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_model_type_display()} uploaded at {self.uploaded_at:%Y-%m-%d %H:%M:%S}"