from rest_framework import serializers
from .models import Listing, Booking


class ListingSerializer(serializers.ModelSerializer):
    '''Serializer for the Listing model'''
    class Meta:
        model = Listing
        fields = '__all__'
        read_only_fields = ['listing_id', 'created_at', 'updated_at']


class BookingSerializer(serializers.ModelSerializer):
    '''Serializer for the Booking model'''
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ['booking_id', 'created_at', 'total_price']

    def create(self, validated_data):
        '''Calculate total_price based on check-in and check-out dates'''
        check_in = validated_data['check_in']
        check_out = validated_data['check_out']
        nights = (check_out - check_in).days
        listing = validated_data['listing']
        validated_data['total_price'] = listing.price_per_night * nights
        return super().create(validated_data)

