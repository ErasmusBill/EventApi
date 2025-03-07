from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import EventSerializer,Event_registration,EventRegistrationSerializer
from .models import Event,Event_registration,TicketType
from rest_framework.exceptions import PermissionDenied
from django.dispatch import receiver
from django.db.models.signals import post_save
from authservices.models import User
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view
from .permissions import IsAdmin,IsOrganizer,IsAttendee
from django.http import HttpResponse
from django.utils import timezone,now
import csv
from datetime import timedelta
from icalendar import Calendar
import stripe
from django.http import HttpResponse
from django.utils import timedelta
from django.db.models import Q
# Create your views here.

#For event handling
class CreateEventView(APIView):
    permission_classes = [IsAuthenticated,IsOrganizer,IsAdmin]

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(organizer=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class EventDuplicateView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizer|IsAdmin]

    def post(self, request, pk):
        original_event = get_object_or_404(Event, pk=pk)
        
        # Validate ownership
        if original_event.organizer != request.user:
            return Response(
                {"detail": "You can only duplicate your own events"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Duplicate with 7-day offset by default
        new_event = original_event.duplicate()
        return Response(
            EventSerializer(new_event).data,
            status=status.HTTP_201_CREATED
        )    


class UpdateEventView(APIView):
    permission_classes = [IsAuthenticated,IsOrganizer,IsAdmin]

    def put(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        
        if event.organizer != request.user:
            raise PermissionDenied("You do not have permission to update this event.")

        serializer = EventSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteEventView(APIView):
    permission_classes = [IsAuthenticated,IsOrganizer,IsAdmin]

    def delete(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if event.organizer != request.user:
            return Response(
                {"detail": "You do not have permission to delete this event."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        event.delete()
        return Response(
            {"message": "Event deleted successfully."},
            status=status.HTTP_200_OK
        )


class ListEventView(APIView):
    def get(self, request):
        events = Event.objects.all()
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginated_events = paginator.paginate_queryset(events,request)
        serializer = EventSerializer(paginated_events, many=True)
        return paginator.get_paginated_response(serializer.data)


class DetailEventView(APIView):
    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        serializer = EventSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
#For event registration
class EventRegistrationView(APIView):
    def post(self,request,event_id):
        event = get_object_or_404(Event,pk=event_id)
        
        if Event_registration.objects.filter(event=event,attendee=request.user).exists():
            return Response(
                {"detail":"You are already registered for this event"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not event.is_registration_open():
            return Response(
                {
                "detail":"Registration for this event has closed"
                },
                status=status.HTTP_400_BAD_REQUEST
            )    
            
        #Handle seat
        
        available_seats = event.available_seats()   
        status_code = Event_registration.CONFIRMED
        
        if available_seats == 0:
            status_code = Event_registration.WAITLISTED
        elif available_seats is None:
            status_code= Event_registration.CONFIRMED
        else:
            status_code = Event_registration.CONFIRMED    
            
        #Handles registration
        
        registration = Event_registration.objects.create(
            event=event,
            attendee = request.user,
            status_code=status_code
        )         
        
        serializer = EventRegistrationSerializer(registration)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

@receiver(post_save, sender=Event_registration)
def send_event_registration_mail(sender, instance, created, **kwargs):
    if created: 
        subject = f"Confirmation of Registration for {instance.event.title}"
        body = f"""
        Hello {instance.attendee.username},

        Thank you for registering to attend the event: {instance.event.title}.
        The event will take place on {instance.event.start_datetime}.

        Best regards,
        Event Team
        """
        
        send_mail(
            subject=subject,
            message = body,
             from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.attendee.email],
            fail_silently=False,
  
        )
        

class EventRegistrationList(APIView):
    permission_classes = [IsAuthenticated,IsOrganizer,IsAdmin]
    def get(self,request,event_id):
        event = get_object_or_404(Event,pk=event_id)
        if request.user != event.organizer or request.user != event.admin:
            return Response(
                {
                    "detail":"You don't have permission to perform this action"
                }, status=status.HTTP_403_FORBIDDEN
            )    
        
        registrations = Event_registration.objects.filter(event=event )
        
        paginator = PageNumberPagination()
        paginator.page_size = 10
        paginated_registration = paginator.paginate_queryset(registrations,request)
        serializer = EventRegistrationSerializer(paginated_registration,many=True)    
        return paginator.get_paginated_response(serializer.data)
    
class EventRegistrationCancellation(APIView):
    permission_classes = [IsAuthenticated,IsOrganizer,IsAdmin,IsAttendee]
    def patch(self,request,registration_id):
        registration = get_object_or_404(Event_registration,pk=registration_id)
        
        if request.user != registration.event.organizer or request.user != registration.attendee:
            return Response(
                {
                    "detail":"You don't have permission to perform this action"
                },
                status=status.HTTP_403_FORBIDDEN
            )  
        
        registration.status = Event_registration.CANCELLED
        registration.save()    

        serializer = EventRegistrationSerializer(registration)
        return Response(serializer.data,status=status.HTTP_200_OK)    
    
@receiver(post_save, sender=Event_registration)
def send_cancellation_email(sender, instance, **kwargs):
    """Sends email when registration status is set to 'CANCELLED'"""
    
    if instance.status == Event_registration.CANCELLED:
        subject = f"Registration Cancellation Confirmation for {instance.event.title}"
        body = f"""
        Hello {instance.attendee.username},

        Your registration for the event "{instance.event.title}" has been successfully cancelled. 
        You will no longer be attending the event scheduled for {instance.event.start_datetime}.

        Best regards,
        Event Management Team
        """
        
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.attendee.email],
            fail_silently=False,
        )    
    
class DeleteEventRegistrationView(APIView):
    permission_classes = [IsAuthenticated,IsOrganizer,IsAdmin,IsAttendee]
    def delete(self,request,registration_id):
        registration = get_object_or_404(Event_registration,pk=registration_id)   
        
        if request.user != registration.event.organizer or request.user != registration.attendee:
            return Response(
                {
                    "detail":"You don't have permission to perform this action"
                },status=status.HTTP_403_FORBIDDEN
            )  
            
        registration.delete()

        return Response(
            {"message": "Registration deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
    
@api_view(["GET"])
def search_event(request): 
    if request.method == "GET":
        title = request.query_params.get('title')
        events = Event.objects.filter(title__icontains=title)
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data)    
    
class OrganizerDashboard(APIView):
    permission_classes = [IsOrganizer]
    
    def get(self, request):
        events = Event.objects.filter(organizer=request.user)
        data = {
            'total_events': events.count(),
            'upcoming_events': EventSerializer(events.filter(start_datetime__gte=now())), 
            'registration_stats': {
                'total': Event_registration.objects.filter(event__in=events).count(),
                'attended': Event_registration.objects.filter(event__in=events, check_in_time__isnull=False).count()
            }
        }
        return Response(data)    
        
class AttendeeDashboard(APIView):
    permission_classes = [IsAttendee]
    
    def get(self, request):
        registrations = Event_registration.objects.filter(attendee=request.user)
        return Response(EventRegistrationSerializer(registrations, many=True).data)     
    
class ExportAttendees(APIView):
    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        registrations = event.registrations.all()
        
        response = HttpResponse(content_type='text/csv')
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Check-in Time'])
        
        for reg in registrations:
            writer.writerow([reg.attendee.name, reg.attendee.email, reg.check_in_time])
            
        response['Content-Disposition'] = f'attachment; filename="{event.slug}_attendees.csv"'
        return response      
    
    

class EventCalendarExport(APIView):
    def get(self, request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        cal = Calendar()
        cal.add('vevent', {
            'summary': event.title,
            'dtstart': event.start_datetime,
            'dtend': event.end_datetime,
            'location': event.location,
        })
        
        return HttpResponse(cal.to_ical(), content_type='text/calendar')  
    
# views.py
class CreatePaymentIntent(APIView):
    def post(self, request, ticket_type_id):
        ticket_type = get_object_or_404(TicketType, pk=ticket_type_id)
        
        payment_intent = stripe.PaymentIntent.create(
            amount=int(ticket_type.price * 100),
            currency='usd',
            metadata={'ticket_type_id': ticket_type_id}
        )
        
        return Response({'client_secret': payment_intent.client_secret})          