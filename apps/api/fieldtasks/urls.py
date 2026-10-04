from django.urls import path

from . import views

urlpatterns = [
    path("tasks", views.TasksView.as_view()),
    path("tasks/<uuid:pk>", views.TaskDetailView.as_view()),
    path("tasks/<uuid:pk>/route", views.TaskRouteView.as_view()),
    path("staff/tasks", views.StaffTasksView.as_view()),
    path("staff/tasks/<uuid:pk>", views.StaffTaskDetailView.as_view()),
    path("staff/tasks/<uuid:pk>/proofs", views.StaffTaskProofsView.as_view()),
    path("staff/tasks/<uuid:pk>/photo", views.StaffTaskPhotoView.as_view()),
]
