from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import EventSerializer,Event_registration,EventRegistrationSerializer
from .models import Event,Event_registration
from rest_framework.exceptions import PermissionDenied
from django.dispatch import receiver
from django.db.models.signals import post_save
from authservices.models import User
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
# Create your views here.

#For event handling
class CreateEventView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(organizer=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateEventView(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
    def get(self,request,event_id):
        event = get_object_or_404(Event,pk=event_id)
        if request.user != event.organizer:
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
    
            
        
           