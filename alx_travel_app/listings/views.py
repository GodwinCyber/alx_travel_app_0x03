"""
Purpose:
Define DRF ViewSets for the Listing and Booking models.
These classes handle CRUD operations, support search, filter, and ordering,
and ensure RESTful API conventions for both models.
"""

from django.shortcuts import render
from rest_framework import viewsets, status
from .models import Listing, Booking, Payment
from .serializers import ListingSerializer, BookingSerializer, PaymentSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Avg
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.conf import settings
import requests
import uuid
from django.db import transaction
from .tasks import send_booking_confirmation_email


# Create your views here.

class ListingViewSet(viewsets.ModelViewSet):
    '''Provide CRUD operations, filtering, search, and ordering for listings.'''
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['description', 'address', 'amenities', 'title']
    ordering_fields = ['price_per_night', 'created_at']

    def get_queryset(self):
        '''
        Return listings with dynamic filtering and annotation.
        Filters by date availability, price range, and includes average rating.
        '''
        # query based on the selected host and prefered_related views
        queryset = Listing.objects.select_related('host').prefetch_related('bookings').all()

        # Filter by date range (exclude overlapping bookings)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.exclude(
                bookings__start_date__lte=end_date,
                bookings__end_date__gte=start_date
            )


        # filter if min_price and max_price is provided
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price and max_price:
            queryset = queryset.filter(price_per_night__gte=min_price, price_per_night__lte=max_price)
            queryset = queryset.annotate(average_rating=Avg('reviews__rating'))
            queryset = queryset.order_by('_average_rating')

        return queryset.distinct()
    
    def perform_create(self, serializer):
        '''Attach the currently authenticated user as the listing host.'''
        serializer.save(host=self.request.user)

    @action(detail=True, methods=['get'])
    def bookings(self, request, pk=None):
        '''Retrieve booking for specific listing'''
        listing = self.get_object()
        bookings = listing.bookings.all()
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_listings(self, request):
        '''Retrieve listings for the currently authenticated user.'''
        user = request.user
        listing = Listing.objects.filter(host=user)
        serializer = self.get_serializer(listing, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def create_booking(self, request, pk=None):
        '''Create a new booking for specific listing'''
        listing = self.get_object()
        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(listing=listing, user=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    

class BookingViewSet(viewsets.ModelViewSet):
    '''Provide CRUD operation, filtering, search and ordering for bookings'''
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['start_date', 'end_date', 'total_price']
    search_fields = ['listing__title', 'guest__username']
    ordering_fields = ['start_date', 'end_date', 'total_price']

    def get_queryset(self):
        '''Users can only view their own bookings unless they are staff'''
        user = self.request.user

        #  Fix: prevent errors for Swagger or anonymous access
        if getattr(self, 'swagger_fake_view', False) or not user.is_authenticated:
            return Booking.objects.none()

        queryset = Booking.objects.select_related('guest', 'listing').all()

        # Non-staff users only see their own bookings
        if not user.is_staff:
            queryset = queryset.filter(guest=user)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(start_date__gte=start_date, end_date__lte=end_date)

        # Filter by listing title
        listing_title = self.request.query_params.get('listing_title')
        if listing_title:
            queryset = queryset.filter(listing__title__icontains=listing_title)

        return queryset.distinct()

    def perform_create(self, serializer):
        '''Attach the currently authenticated user as the guest'''
        booking = serializer.save(guest=self.request.user)
        
        # Trigger Celery task to send booking confirmation email
        send_booking_confirmation_email.delay(
            booking.guest.email,
            booking.listing.title,
            str(booking.start_date),
            str(booking.end_date),
        )

    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        '''Retrieve bookings for the logged-in user'''
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        bookings = Booking.objects.filter(guest=user)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def host_bookings(self, request):
        '''Retrieve bookings based on listings owned by the logged-in host'''
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=401)
        listings = Listing.objects.filter(host=user)
        bookings = Booking.objects.filter(listing__in=listings)
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        '''Cancel a specific booking'''
        booking = self.get_object()
        if booking.guest != request.user and not request.user.is_staff:
            return Response({'errors': 'You do not have permission to cancel this booking'}, status=403)
        booking.delete()
        return Response({'status': 'Your booking has been cancelled successfully'}, status=204)
    
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        '''Reschedule a specific booking'''
        booking = self.get_object()
        if booking.guest != request.user and not request.user.is_staff:
            return Response({'errors': 'You are not permitted to reschedule this booking'}, status=403)
        serializer = BookingSerializer(booking, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
    @action(detail=True, methods=['get'])
    def confirm(self, request, pk=None):
        '''Confirm a specific booking for the host'''
        booking = self.get_object()
        if booking.listing.host != request.user and not request.user.is_staff:
            return Response({'errors': 'You do not have permission to confirm this booking'}, status=403)
        return Response({'status': 'Your booking has been confirmed'}, status=200)

class PaymentViewSet(viewsets.ModelViewSet):
    '''Initialise payment by making POST request to the chapa api with booking details'''
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['booking_reference', 'transaction_id', 'payment_status']
    search_fields = ['booking_reference__guest', 'booking_reference__listing']
    ordering_fields = ['payment_date', 'amount']


    def get_queryset(self):
        '''
        Custome queryset logic:
        - Role-based access: Guests, Hosts, and Admins see relevant payments.
        - Search by transaction_id or payment_status.
        - Filter by query params for flexible API querying.
        '''''
        user = self.request.user

        # Handle unauthenticated or Swagger arequest safely
        if getattr(self, 'swagger_fake-view', False) or not user.is_authenticated:
            return Payment.objects.none()
        
        # Base queryset with related objects for efficiency
        queryset = Payment.objects.select_related(
            'booking_reference__guest', 'booking_reference__listing'
        )

        # Role-based access control
        if hasattr(user, 'role'):
            if user.role == 'guest':
                queryset = queryset.filter(booking_reference__guest=user) # Guests see their own payments
            elif user.role == 'host':
                queryset = queryset.filter(booking_reference_listing__host=user) # Hosts see payments for their listings
            elif user.role == 'admin':
                pass  # Admins see all payments
            else:
                return Payment.objects.none() # Unknown roles see no payments
        elif not user.is_staff:
            return Payment.objects.none() # Non-staff users see no payments
    

        # Manuel search behavior
        search_query = self.request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(transaction_id__icontains=search_query) |
                Q(payment_status__icontains=search_query) # Search in transaction_id and payment_status
            )


        # Additional filtering based on query parameters
        transaction_id = self.request.query_params.get('transaction_id')
        payment_status = self.request.query_params.get('payment_status')

        if transaction_id:
            queryset = queryset.filter(transaction_id__iexact=transaction_id)
        if payment_status:
            queryset = queryset.filter(payment_status__iexact=payment_status)
        return queryset.distinct()


    @action(detail=False, methods=['post'])
    def initialize_payment(self, request):
        '''Send booking booking details to chapa to initialize payment process'''
        chapa_secret_key = settings.CHAPA_SECRET_KEY
        if not chapa_secret_key:
            return Response({'error': 'Chapa secret key is not configured.'}, status=500)
        
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            booking = serializer.validated_data.get('booking_reference')
            amount = serializer.validated_data.get('amount')
            user = request.user

            # check if there is already pending payment for this booking
            existing_payment = Payment.objects.filter(
                booking_reference=booking,
                payment_status='pending'
            ).first()
            if existing_payment:
                return Response({'error': 'There is already a pending payment for this booking.'}, status=status.HTTP_400_BAD_REQUEST)

            # Generate a unique transaction reference
            tx_ref = f"CHAPA-{uuid.uuid4()}"
            while Payment.objects.filter(transaction_id=tx_ref).exists():
                tx_ref = f"CHAPA-{uuid.uuid4()}"

            try:
                # USing atomic transaction to ensure data integrity
                with transaction.atomic():
                    # save payment details to database with pending status
                    payment = Payment.objects.create(
                        booking_reference=booking,
                        transaction_id=tx_ref,
                        amount=amount,
                        payment_status='pending'
                    )

                    # Prepare data for Chapa API
                    chapa_data = {
                        "amount": str(amount),
                        "currency": "ETB",  # or your preferred currency
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "tx_ref": tx_ref,
                        "callback_url": "https://yourdomain.com/api/payments/verify/",
                        "return_url": "https://yourdomain.com/payment-success",
                        "customization": {
                            "title": "Booking Payment",
                            "description": f"Payment for booking {booking.booking_id}"
                        }
                    }
                    headers = {
                        "Authorization": f"Bearer {chapa_secret_key}",
                        "Content-Type": "application/json",
                    }

                    # Call Chapa API to initialize payment
                    response = requests.post("https://api.chapa.co/v1/transaction/initialize", json=chapa_data, headers=headers)
                    chapa_response = response.json()

                    if response.status_code == 200 and chapa_response.get('status') == 'success':
                        return Response(chapa_response, status=status.HTTP_200_CREATED)
                    else:
                        payment.payment_status = 'failed'
                        payment.save()
                        return Response({'error': 'Failed to initialize payment with Chapa.', 'details': chapa_response}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                # Attempt to mark payment as failed if it was created, then return error
                try:
                    if 'payment' in locals():
                        payment.payment_status = 'failed'
                        payment.save()
                except Exception:
                    pass
                return Response({'error': 'An error occurred while initializing payment.', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def verify_payment(self, request):
        '''Verify a payment using transaction ID'''
        tx_ref = request.query_params.get('tx_ref')
        if not tx_ref:
            return Response({'error': 'Transaction reference (tx_ref) is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        headers = {
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}", 
        }

        # Verify transaction
        response = requests.get(f"https://api.chapa.co/v1/transaction/verify/{tx_ref}", headers=headers)
        chapa_response = response.json()

        if response.status_code == 200 and chapa_response.get('status') == 'success':
            # Update payment status in the database
            try:
                payment = Payment.objects.get(transaction_id=tx_ref)
                payment.payment_status = 'successful'
                payment.save()
                return Response({'status': 'Payment verified successfully.', 'details': chapa_response}, status=status.HTTP_200_OK)
            except Payment.DoesNotExist:
                return response({'error': 'Payment record not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'Payment verification failed.', 'details': chapa_response}, status=status.HTTP_400_BAD_REQUEST)

        
