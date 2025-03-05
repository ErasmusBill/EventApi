from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import EventSerializer,Event_registration,EventRegistrationSerializer
from .models import Event,Event_registration

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
            return Response(
                {"detail": "You do not have permission to update this event."},
                status=status.HTTP_403_FORBIDDEN
            )
        
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
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        status = Event_registration.CONFIRMED
        
        if available_seats == 0:
            status = Event_registration.WAITLISTED
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
        
        serializer = EventRegistrationSerializer(registration)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class EventRegistrationList(APIView):
    def get(self,request,event_id):
        event = get_object_or_404(Event,pk=event_id)
        if request.user != event.orgainzer:
            return Response(
                {
                    "detail":"You don't have permission to perform this action"
                }, status=status.HTTP_403_FORBIDDEN
            )    
        
        registrations = Event_registration.objects.filter(event=event)
        serializer = EventRegistrationSerializer(registrations,many=True)    
        return Response(serializer.data,status=status.HTTP_200_OK)
    
class EventRegistrationCancellation(APIView):
    def patch(request,registration_id):
        registration = get_object_or_404(Event_registration,pk=registration_id)
        
        if request.user!= registration.event.organizer or request.user != registration.attendee:
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
    
class DeleteEventRegistrationView(APIView):
    def delete(request,registration_id):
        registration = get_object_or_404(Event_registration,pk=registration_id)   
        
        if request.user!= registration.event.organizer or request.user != registration.attendee:
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
    
            
        
           