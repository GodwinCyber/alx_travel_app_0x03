# Listings App

This Django app manages travel property listings, bookings, reviews, and users for the ALX Travel platform.

## Features

- Custom user model with roles (`host`, `guest`)
- Property listing management
- Booking system
- Review system
- Database seeding for development/testing

---

## Usage

### 1. Database Migration

Run migrations to create the necessary tables:

```bash
python manage.py makemigrations listings
python manage.py migrate
```

### 2. Seeding the Database

Populate the database with sample data for development:

```bash
python manage.py seed
```

This will create sample users, listings, bookings, and reviews.

---

## Process Overview

### 1. Database Models

Models are defined in `models.py`:

- **User**: Custom user with additional fields and role.
- **Listing**: Property details, amenities, host relationship.
- **Booking**: Links guest and listing, tracks booking status and dates.
- **Review**: Guest reviews for listings.

### 2. Serialization

Serializers in `serializers.py` convert model instances to JSON for API responses and handle validation for incoming data.

- **ListingSerializer**: Serializes listing data.
- **BookingSerializer**: Serializes booking data and calculates total price.
- **ReviewSerializer**: Serializes review data.

### 3. Seeding

The custom management command in `management/commands/seed.py` uses `django_seed` and `Faker` to generate realistic sample data:

- Clears existing data
- Creates users, listings, bookings, and reviews with random but valid values

---

## Development Notes

- Uses Django REST Framework for API serialization.
- Make sure to set `AUTH_USER_MODEL = 'listings.User'` in your project settings.
- For production, switch to PostgreSQL if using `ArrayField` for amenities.

---

## License

MIT License
