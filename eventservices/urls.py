from django.urls import path
from . import views

urlpatterns = [
    # Event Management
    path('create-event/', views.CreateEventView.as_view(), name="create-event"),
    path('update-event/<int:pk>/', views.UpdateEventView.as_view(), name="update-event"),
    path('delete-event/<int:pk>/', views.DeleteEventView.as_view(), name="delete-event"),
    path('list-event/', views.ListEventView.as_view(), name="list-event"),
    path('event-detail/<int:pk>/', views.DetailEventView.as_view(), name="event-detail"),
    path('events/<int:pk>/duplicate/',views.EventDuplicateView.as_view(), name='duplicate-event'),
    path('search-event/',views.search_event, name="search-event"),
    path('organizer-dashboard',views.OrganizerDashboard.as_view(), name="organizer-dashboard"),
    path('attendee-dashboard/',views.AttendeeDashboard.as_view(), name='attendee-dashboard'),
    path('events/<int:event_id>/export-attendees/',views.ExportAttendees.as_view(),name='export-attendees'),
    path('events/<int:event_id>/export-calendar/',views.EventCalendarExport.as_view(),name='export-calendar'),
    path('ticket-types/<int:ticket_type_id>/create-payment-intent/',views.CreatePaymentIntent.as_view(),
    name='create-payment-intent'),
    path('stripe-webhook/', views.stripe_webhook, name='webhook'),
    path('create-category/',views.CreateCategoryView.as_view(), name='create-category'),
    path('list-category/',views.ListCategoriesView.as_view(), name='category-list'),

    

    # Event Registration
    path('register-event/<int:event_id>/', views.EventRegistrationView.as_view(), name="register-event"),
    path('registration-list/', views.EventRegistrationList.as_view(), name="registration-list"),
    path('registration-cancel/<int:pk>/', views.EventRegistrationCancellation.as_view(), name="registration-cancel"),
    path('registration-delete/<int:pk>/', views.DeleteEventRegistrationView.as_view(), name="registration-delete"),
    path('check-in/', views.CheckInView.as_view(), name='check-in'),
    path('registrations/<int:registration_id>/download-qr-code/', views.DownloadQRCodeView.as_view(), name='download-qr-code'),
    
]