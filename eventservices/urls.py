from django.urls import path
from . import views

urlpatterns = [
    # Event Management
    path('create-event/', views.CreateEventView.as_view(), name="create-event"),
    path('update-event/<int:pk>/', views.UpdateEventView.as_view(), name="update-event"),
    path('delete-event/<int:pk>/', views.DeleteEventView.as_view(), name="delete-event"),
    path('list-event/', views.ListEventView.as_view(), name="list-event"),
    path('event-detail/<int:pk>/', views.DetailEventView.as_view(), name="event-detail"),

    # Event Registration
    path('register-event/<int:event_id>/', views.EventRegistrationView.as_view(), name="register-event"),
    path('registration-list/', views.EventRegistrationList.as_view(), name="registration-list"),
    path('registration-cancel/<int:pk>/', views.EventRegistrationCancellation.as_view(), name="registration-cancel"),
    path('registration-delete/<int:pk>/', views.DeleteEventRegistrationView.as_view(), name="registration-delete"),
]