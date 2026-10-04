from django.urls import path

from . import views

urlpatterns = [
    path("staff/status", views.StaffStatusView.as_view()),
    path("staff/clock", views.StaffClockView.as_view()),
    path("staff/locations", views.StaffLocationsView.as_view()),
    path("locations/live", views.LiveLocationsView.as_view()),
    path("locations/history", views.LocationHistoryView.as_view()),
    path("geofences", views.GeofencesView.as_view()),
    path("geofences/events", views.GeofenceEventsView.as_view()),
    path("geofences/<uuid:pk>", views.GeofenceDetailView.as_view()),
    path("reports/performance", views.PerformanceReportView.as_view()),
]
