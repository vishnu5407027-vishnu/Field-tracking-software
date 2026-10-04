from django.urls import path

from . import views

urlpatterns = [
    path("auth/login", views.LoginView.as_view()),
    path("me", views.MeView.as_view()),
    path("me/password", views.ChangePasswordView.as_view()),
    path("users", views.UsersView.as_view()),
    path("users/<uuid:pk>", views.UserDetailView.as_view()),
    path("users/<uuid:pk>/role", views.UserRoleView.as_view()),
    path("users/<uuid:pk>/password", views.UserPasswordView.as_view()),
    path("owner/analytics", views.OwnerAnalyticsView.as_view()),
    path("owner/tenants", views.OwnerTenantsView.as_view()),
    path("owner/tenants/<uuid:pk>", views.OwnerTenantDetailView.as_view()),
    path("owner/tenants/<uuid:pk>/status", views.OwnerTenantStatusView.as_view()),
]
