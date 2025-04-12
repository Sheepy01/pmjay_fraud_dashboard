from django.urls import path
from .views import dashboard
from . import views

urlpatterns = [
    path('', dashboard, name='dashboard_index'),
    path('download_flagged_claims/', views.download_flagged_claims_excel, name='download_flagged_claims'),
    path('download_geo_anomalies/', views.download_geo_anomalies_excel, name='download_geo_anomalies'),
    path('download_high_value_claims/', views.download_high_value_claims_excel, name='download_high_value_claims'),
    path('download_unusual_treatment/', views.download_unusual_treatment_excel, name='download_unusual_treatment'),
    path('get-districts/', views.get_districts, name='get_districts'),
    path('filter-dashboard/', views.filter_dashboard_data, name='filter_dashboard_data'),
    path('chart-data/flagged-claims/', views.flagged_claims_chart_data, name='flagged_claims_chart_data'),
    path('chart-data/geo-anomalies/', views.geo_anomalies_chart_data, name='geo_anomalies_chart_data'),
]