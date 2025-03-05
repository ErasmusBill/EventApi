from django.urls import path
from . import views

urlpatterns = [
    path('create-event/',views.CreateEventView.as_view(), name="create-event"),
    path('update-event/<int:pk>/',views.UpdateEventView.as_view(), name="update-event"),
    path('delete-event/<int:pk>/',views.DeleteEventView.as_view(),name="delete_event"),
    path('list-event/',views.ListEventView.as_view(),name='list-event'),
    path('event-detail/<int:pk>/',views.DetailEventView.as_view(),name="event-detail"),
    #Event Registration
    path('register-event/',views.EventRegistrationView.as_view(), name="register-event"),
    path('registration-list/',views.EventRegistrationList.as_view(), name="registration-list"),
    path('registration-cancellation/<int:pk>',views.EventRegistrationCancellation.as_view(), name="registration-cancellation"),
    path('registration-deletion/<int:pk>/',views.DeleteEventRegistrationView.as_view(),name='registration-deletion')
    
    
]