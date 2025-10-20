from django_seed import Seed
from django.core.management.base import BaseCommand
from listings.models import User, Listing, Booking, Review
import random
from faker import Faker

class Command(BaseCommand):
    '''Custom command to seed the database with sample data'''
    help = 'Seed the database with sample data'

    def handle(self, *args, **kwargs):
        seeder = Seed.seeder()
        fake = Faker()

        # Clear existing data
        Review.objects.all().delete()
        Booking.objects.all().delete()
        Listing.objects.all().delete()
        User.objects.all().delete()

        # Create sample users
        seeder.add_entity(User, 10, {
            'email': lambda x: fake.unique.email(),
            'username': lambda x: fake.unique.user_name(),
            'first_name': lambda x: fake.first_name(),
            'last_name': lambda x: fake.last_name(),
            'phone_number': lambda x: fake.phone_number(),
            'role': lambda x: random.choice(['host', 'guest']),
        })

        # Create sample listings
        seeder.add_entity(Listing, 20, {
            'title': lambda x: fake.sentence(nb_words=6),
            'description': lambda x: fake.text(max_nb_chars=200),
            'address': lambda x: fake.street_address(),
            'city': lambda x: fake.city(),
            'state': lambda x: fake.state(),
            'country': lambda x: fake.country(),
            'price_per_night': lambda x: round(random.uniform(50.0, 500.0), 2),
            'property_type': lambda x: random.choice(['apartment', 'house', 'condo']),
            'number_of_bedrooms': lambda x: random.randint(1, 5),
            'host': lambda x: random.choice(User.objects.values_list('pk', flat=True)),
            'amenities': lambda x: random.sample(['wifi', 'kitchen', 'parking', 'pool', 'air_conditioning'], k=random.randint(1,5)),
        })

        # Create sample bookings
        seeder.add_entity(Booking, 30, {
            'listing_id': lambda x: random.choice(Listing.objects.values_list('pk', flat=True)),
            'guest': lambda x: random.choice(User.objects.values_list('pk', flat=True)),
            'status': lambda x: random.choice(['pending', 'confirmed', 'cancelled']),
            'check_in': lambda x: fake.date_between(start_date='today', end_date='+30d'),
            'check_out': lambda x: fake.date_between(start_date='+31d', end_date='+60d'),
            'total_price': lambda x: round(random.uniform(100.0, 2000.0), 2),
        })

        # Create sample reviews
        seeder.add_entity(Review, 40, {
            'listing': lambda x: random.choice(Listing.objects.values_list('pk', flat=True)),
            'guest': lambda x: random.choice(User.objects.values_list('pk', flat=True)),
            'rating': lambda x: random.randint(1, 5),
            'comment': lambda x: fake.text(max_nb_chars=100),
        })
        seeder.execute()
     
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

