from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser
#from django.contrib.postgres.fields import ArrayField

# Create your models here.
class USER_ROLE(models.TextChoices):
    '''Different roles a user can have'''
    ADMIN = 'admin', 'Admin'
    HOST = 'host', 'Host'
    GUEST = 'guest', 'Guest'

class LISTING_AMENITIES(models.TextChoices):
    '''Amenities available for a listing'''
    WIFI = 'wifi', 'WiFi'
    PARKING = 'parking', 'Parking'
    POOL = 'pool', 'Pool'
    AIR_CONDITIONING = 'air_conditioning', 'Air Conditioning'
    GYM = 'gym', 'Gym'
    PETS_ALLOWED = 'pets_allowed', 'Pets Allowed'
    BREAKFAST_INCLUDED = 'breakfast_included', 'Breakfast Included'
    KITCHEN = 'kitchen', 'Kitchen'
    WASHER = 'washer', 'Washer'
    DRYER = 'dryer', 'Dryer'
    HEATING = 'heating', 'Heating'
    TV = 'tv', 'TV'

class PROPERTY_TYPE(models.TextChoices):
    '''Different types of property for a listing'''
    APARTMENT = 'apartment', 'Apartment'
    HOUSE = 'house', 'House'
    CONDO = 'condo', 'Condo'
    TOWNHOUSE = 'townhouse', 'Townhouse'
    VILLA = 'villa', 'Villa'
    CABIN = 'cabin', 'Cabin'
    BUNGALOW = 'bungalow', 'Bungalow'
    COTTAGE = 'cottage', 'Cottage'
    LOFT = 'loft', 'Loft'
    STUDIO = 'studio', 'Studio'

class BOOKING_STATUS(models.TextChoices):
    '''Different statuses a booking can have'''
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'


class User(AbstractUser):
    '''Custom User model with additional fields'''
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=10, choices=USER_ROLE.choices, default=USER_ROLE.GUEST)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        '''String that represents the user object'''
        return f'{self.email} {self.first_name} {self.last_name}'

class Listing(models.Model):
    '''Model representing a travel listing'''
    listing_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100)
    description = models.TextField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE.choices)
    number_of_bedrooms = models.PositiveIntegerField()
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    amenities = models.JSONField(choices=LISTING_AMENITIES.choices, default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        '''String that represents the listing object'''
        return f'{self.title} in {self.city}, {self.country} - ${self.price_per_night}/night'
    
class Booking(models.Model):
    '''Model representing a booking for a listing'''
    booking_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=10, choices=BOOKING_STATUS.choices, default=BOOKING_STATUS.PENDING)
    check_in = models.DateField()
    check_out = models.DateField()
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        '''String that represents the booking object'''
        return f'Booking {self.booking_id} for {self.listing.title} by {self.guest.email}'
    
class Review(models.Model):
    '''Model representing a review for a listing'''
    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reviews')
    guest = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        '''String that represents the review object'''
        return f'Review {self.review_id} for {self.listing.title} by {self.guest.email} - Rating: {self.rating}'
    
# End of models.py




