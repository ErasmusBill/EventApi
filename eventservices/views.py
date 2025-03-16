from django.shortcuts import get_object_or_404
import qrcode.constants
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import EventSerializer,Event_registration,EventRegistrationSerializer,EventCategorySerializer
from .models import Event,Event_registration,TicketType,EventCategory
from rest_framework.exceptions import PermissionDenied
from django.dispatch import receiver
from django.db.models.signals import post_save
from authservices.models import User
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view
from .permissions import IsAdmin,IsOrganizer,IsAttendee,IsOrganizerOrAdmin
from django.http import HttpResponse
import csv
from datetime import timedelta
from django.utils import timezone
from icalendar import Calendar
import stripe
from django.http import HttpResponse
from django.db.models import Q
import qrcode
from io import BytesIO
from django.core.files import File
import json
from rest_framework_simplejwt.authentication import JWTAuthentication
# Create your views here.

#For event handling
class CreateEventView(APIView):
    permission_classes = [IsAuthenticated,IsOrganizerOrAdmin]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(organizer=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class EventDuplicateView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizerOrAdmin]

    def post(self, request, pk):
        original_event = get_object_or_404(Event, pk=pk)
    
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
    permission_classes = [IsAuthenticated,IsOrganizerOrAdmin]

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
    permission_classes = [IsAuthenticated,IsOrganizerOrAdmin]

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
    
    
#Generate a qrcode for checkin
def generate_qrcode(data, file_name):
    """
    Generate a QR code image from the given data
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")  

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    file = File(buffer, name=f"{file_name}.png")
    return file
    
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
            status= Event_registration.WAITLISTED
        elif available_seats is None:
            status= Event_registration.CONFIRMED
        else:
            status = Event_registration.CONFIRMED    
            
        #Handles registration
        
        registration = Event_registration.objects.create(
            event=event,
            attendee = request.user,
            status=status
        )   
        
        #Generate qrcode for checkin
        
        qr_code_data = f"Check-in code:{registration.check_in_code}"
        qr_code_file = generate_qrcode(qr_code_data, f"qr_code_{registration.id}")   
        
        #Save qrcode
        
        registration.qr_code.save(f"qr_code_{registration.id}.png", qr_code_file, save=True)   
        
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
        
            email = send_mail(
                subject=subject,
                message = body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.attendee.email],
                fail_silently=False,
                )
            
            if instance.qr_code:
                email.attach_file(instance.qr_code.path)
        
            try:
                email.send(fail_silently=False)
            except Exception as e:
                print(f"Failed to send verification email: {e}")
        
    
class CheckInView(APIView):
    def post(self,request):
        check_in_code = request.data.get("check_in_code")
        if not check_in_code:
            return Response({"error":"Check-in code is required"},status=status.HTTP_400_BAD_REQUEST)  
        
        registration = get_object_or_404(Event_registration,check_in_code=check_in_code)  
        
        if registration.check_in_time:
            return Response({"error":"Already checked in"}, status=status.HTTP_400_BAD_REQUEST)
        
        registration.check_in_time = timezone.now()
        registration.save()
        
        return Response({"message":"Check-in successful"},status=status.HTTP_200_OK)
    
    
#Download qrcode 
class DownloadQRCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, registration_id):
        registration = get_object_or_404(Event_registration, id=registration_id, attendee=request.user)
        
        if not registration.qr_code:
            return Response({"error": "QR code not found"}, status=status.HTTP_404_NOT_FOUND)
        
        response = HttpResponse(registration.qr_code, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="qr_code_{registration.id}.png"'
        return response    
    
    


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
    title = request.query_params.get('title')
    category = request.query_params.get('category')
    location = request.query_params.get('location')
    start_date = request.query_params.get('start_date')

    filters = Q()
    if title:
        filters &= Q(title__icontains=title)
    if category:
        filters &= Q(categories__name__icontains=category)
    if location:
        filters &= Q(location__icontains=location)
    if start_date:
        filters &= Q(start_datetime__gte=start_date)

    events = Event.objects.filter(filters)
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data)    

class OrganizerDashboard(APIView):
    permission_classes = [IsOrganizer]
    def get(self, request):
        events = Event.objects.filter(organizer=request.user)
        data = {
            'total_events': events.count(),
            'upcoming_events': EventSerializer(events.filter(start_datetime__gte=timezone.now())).data,
            'analytics': {
                'total_revenue': sum(reg.total_price for reg in Event_registration.objects.filter(event__in=events)),
                'registrations_by_type': {
                    'confirmed': Event_registration.objects.filter(event__in=events, status='confirmed').count(),
                    'waitlisted': Event_registration.objects.filter(event__in=events, status='waitlisted').count(),
                }
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
    

class CreatePaymentIntent(APIView):
    def post(self, request, ticket_type_id):
        ticket_type = get_object_or_404(TicketType, pk=ticket_type_id)
        # Get or create registration (simplified)
        registration = Event_registration.objects.create(
            event=ticket_type.event,
            attendee=request.user,
            ticket_type=ticket_type,
            status=Event_registration.PENDING  # New status
        )
        payment_intent = stripe.PaymentIntent.create(
            amount=int(ticket_type.price * 100),
            currency='usd',
            metadata={'registration_id': registration.id}
        )
        return Response({'client_secret': payment_intent.client_secret})
    
# views.py
@api_view(['POST'])
def stripe_webhook(request):
    payload = request.body
    event = None
    try:
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)

    if event.type == 'payment_intent.succeeded':
        payment_intent = event.data.object
        registration_id = payment_intent.metadata.get('registration_id')
        registration = Event_registration.objects.get(id=registration_id)
        registration.status = Event_registration.CONFIRMED
        registration.save()
    return HttpResponse(status=200)   


#Event category

class CreateCategoryView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = EventCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
    
class ListCategoriesView(APIView):
    def get(self, request):
        categories = EventCategory.objects.all()
        serializer = EventCategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)    