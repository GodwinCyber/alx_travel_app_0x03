"""
Purpose:
Define DRF ViewSets for the Listing and Booking models.
These classes handle CRUD operations, support search, filter, and ordering,
and ensure RESTful API conventions for both models.
"""

from django.shortcuts import render
from rest_framework import viewsets
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Avg
from rest_framework.decorators import action
from rest_framework.response import Response

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

        # 🧩 Fix: prevent errors for Swagger or anonymous access
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
        serializer.save(guest=self.request.user)

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


