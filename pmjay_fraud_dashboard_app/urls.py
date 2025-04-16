# from django.urls import path
# from .views import dashboard
# from . import views

# urlpatterns = [
#     path('', dashboard, name='dashboard_index'),
#     path('download_flagged_claims/', views.download_flagged_claims_excel, name='download_flagged_claims'),
#     path('download_geo_anomalies/', views.download_geo_anomalies_excel, name='download_geo_anomalies'),
#     path('download_high_value_claims/', views.download_high_value_claims_excel, name='download_high_value_claims'),
#     path('download_unusual_treatment/', views.download_unusual_treatment_excel, name='download_unusual_treatment'),
#     path('get-districts/', views.get_districts, name='get_districts'),
#     path('filter-dashboard/', views.filter_dashboard_data, name='filter_dashboard_data'),
#     path('chart-data/flagged-claims/', views.flagged_claims_chart_data, name='flagged_claims_chart_data'),
#     path('chart-data/geo-anomalies/', views.geo_anomalies_chart_data, name='geo_anomalies_chart_data'),
# ]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('get-districts/', views.get_districts, name='get_districts'),
    path('get-flagged-claims/', views.get_flagged_claims, name='get_flagged_claims'),
    path('get-high-value-claims/', views.get_high_value_claims, name='get_high_value_claims'),
    path('get-hospital-bed-cases/', views.get_hospital_bed_cases, name='hospital_bed_cases'),
    path('get-family-id-cases/', views.get_family_id_cases, name='family_id_cases'),
    path('get-geo-anomalies/', views.get_geo_anomalies, name='get_geo_anomalies'),
    path('get-ophthalmology-cases/', views.get_ophthalmology_cases, name='get_ophthalmology_cases'),
    path('get-flagged-claims-details/', views.get_flagged_claims_details, name='get_flagged_claims_details'),
    path('get-flagged-claims-by-district/', views.get_flagged_claims_by_district, name='get_flagged_claims_by_district'),
    path('get-age-distribution/', views.get_age_distribution, name='get_age_distribution'),
    path('get-gender-distribution/', views.get_gender_distribution, name='get_gender_distribution'),
    path('download-high-value-claims-excel/', views.download_high_value_claims_excel, name='download_high_value_claims_excel'),
]