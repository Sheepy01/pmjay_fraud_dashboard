
from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('get-districts/', views.get_districts, name='get_districts'),
    path('get-flagged-claims/', views.get_flagged_claims, name='get_flagged_claims'),
    path('get-flagged-claims-details/', views.get_flagged_claims_details, name='get_flagged_claims_details'),
    path('get-flagged-claims-by-district/', views.get_flagged_claims_by_district, name='get_flagged_claims_by_district'),
    path('get-all-flagged-claims/', views.get_all_flagged_claims, name="get_all_flagged_claims"),
    path('get-age-distribution/', views.get_age_distribution, name='get_age_distribution'),
    path('get-gender-distribution/', views.get_gender_distribution, name='get_gender_distribution'),
    path('get-high-value-claims/', views.get_high_value_claims, name='get_high_value_claims'),
    path('get-high-value-claims-details/', views.get_high_value_claims_details, name='get_high_value_claims_details'),
    path('get-high-value-claims-by-district/', views.get_high_value_claims_by_district, name='get_high_value_claims_by_district'),
    path('get-high-value-age-distribution/', views.get_high_value_age_distribution, name='get_high_value_age_distribution'),
    path('get-high-value-gender-distribution/', views.get_high_value_gender_distribution, name='get_high_value_gender_distribution'),
    path('get-hospital-bed-cases/', views.get_hospital_bed_cases, name='hospital_bed_cases'),
    path('get-hospital-bed-details/', views.get_hospital_bed_details),
    path('hospital-violations-by-district/', views.hospital_violations_by_district),
    path('get-family-id-cases/', views.get_family_id_cases, name='family_id_cases'),
    path('get-family-id-cases-details/', views.get_family_id_cases_details),
    path('get-family-violations-by-district/', views.get_family_violations_by_district),
    path('get-family-age-distribution/', views.get_family_violations_demographics, {'type': 'age'}),
    path('get-family-gender-distribution/', views.get_family_violations_demographics, {'type': 'gender'}),
    path('get-geo-anomalies/', views.get_geo_anomalies, name='get_geo_anomalies'),
    path('get-geo-anomalies-details/', views.get_geo_anomalies_details, name='get_geo_anomalies_details'),
    path('get-geo-violations-by-state/', views.get_geo_violations_by_state, name='get_geo_violations_by_state'),
    path('get-geo-demographics/<str:type>/', views.get_geo_violations_demographics, name='get_geo_violations_demographics'),
    path('get-ophthalmology-cases/', views.get_ophthalmology_cases, name='get_ophthalmology_cases'),
    path('get-ophthalmology-details/', views.get_ophthalmology_details, name='ophth_details'),
    path('get-ophthalmology-distribution/', views.get_ophthalmology_distribution, name='ophth_distribution'),
    path('get-ophthalmology-demographics/<str:type>/', views.get_ophthalmology_demographics, name='ophth_demographics'),
    path('flagged-claims/download/', views.download_flagged_claims, name='download_flagged_claims'),
    path(
      'download_flagged_claims_report/',
      views.download_flagged_claims_report,
      name='download_flagged_claims_report'
    ),
    path('download-high-value-claims-excel/', views.download_high_value_claims_excel, name='download_high_value_claims_excel'),
]