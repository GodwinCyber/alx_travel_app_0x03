"""
Celery task for sending booking confrimation email asynchronously.
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_booking_confirmation_email(to_email, listing_name, start_date, end_date):
    '''Background task to send booking confirmation email asynchronously'''
    subject = "Booking Confirmation for {listing_name}"
    message = (
        f"Hi there, \n\n"
        f"Your booking for {listing_name} has been confirmed!\n"
        f"Start date: {start_date}\n"
        f"End date: {end_date}\n\n"
         f"Thank you for choosing travel app. "
        f"Best regards, \nTravel App Team"
       
    )

    send_mail(
        subject,
        message,
        settings.DEFUALT_FROM_EMAIL, # Here you can use a default email,
        [to_email],
        fail_silently=False,
    )

    return f"Booking confirmation sent to {to_email}"


