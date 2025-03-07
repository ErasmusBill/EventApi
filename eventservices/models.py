from django.db import models
from authservices.models import User
from django.utils import timezone,timedelta

class EventCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Event Categories"
        
class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    location = models.CharField(max_length=255)
    is_virtual = models.BooleanField(default=False)
    virtual_meeting_link = models.URLField(blank=True, null=True)
    banner_image = models.ImageField(upload_to='event_banners/', null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    categories = models.ManyToManyField(EventCategory, related_name='events', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        permissions = [
            ("can_create_event","Can create event"),
            ("can_edit_all_event","Can edit all events"),
            ("can_view_all_event","Can view all events"),
            ("can_delete_event","Can delete event")
        ]
        
        def duplicate(self, new_title=None, date_offset_days=7):
            """Create a copy of the event with optional date offset"""
            new_event = self
            new_event.pk = None  # Create new database entry
            new_event.title = new_title or f"{self.title} (Copy)"
        
            # Shift dates
            new_event.start_datetime += timedelta(days=date_offset_days)
            new_event.end_datetime += timedelta(days=date_offset_days)
            new_event.save()

            # Copy M2M relationships
            new_event.categories.set(self.categories.all())
        
            # Copy ticket types
            for ticket in self.ticket_types.all():
                ticket.pk = None
                ticket.event = new_event
                ticket.save()

            return new_event
   
    
    def is_registration_open(self):
        if self.registration_deadline:
            return timezone.now() < self.registration_deadline
        return True
    
    
    def available_seats(self):
        if self.capacity is None:
            return None  
        
        registered = self.registrations.filter(status=Event_registration.CONFIRMED).count()
        return max(0, self.capacity - registered)
    
    def __str__(self):
        return self.title
    
class TicketType(models.Model):
    event = models.ForeignKey(Event, related_name='ticket_types', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField()
    available_from = models.DateTimeField()
    available_to = models.DateTimeField()        
    

class Event_registration(models.Model):
    CONFIRMED = 'confirmed'
    WAITLISTED = 'waitlisted'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (CONFIRMED, 'Confirmed'),
        (WAITLISTED, 'Waitlisted'),
        (CANCELLED, 'Cancelled'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.SET_NULL, null=True)
    attendee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=CONFIRMED)
    registration_date = models.DateTimeField(auto_now_add=True)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_in_code = models.CharField(max_length=20, blank=True)
    
    class Meta:
        unique_together = ['event', 'attendee']
        
    def __str__(self):
        return f"{self.attendee.username} - {self.event.title}"
    


class NotificationType(models.Model):
    name = models.CharField(max_length=100)
    template_subject = models.CharField(max_length=255)
    template_body = models.TextField()
    
    def __str__(self):
        return self.name

class Notification(models.Model):
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (SENT, 'Sent'),
        (FAILED, 'Failed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"
    
    