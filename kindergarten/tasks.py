from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Student, Payment
import uuid

@shared_task
def generate_monthly_payments():
    today = timezone.now().date()
    # This task should run on the 25th, so we calculate for the previous month
    if today.day == 25:
        # Get the previous month and year
        last_month_date = today - timedelta(days=30)
        month = last_month_date.month
        year = last_month_date.year

        # Due date is the 25th of the current month (today)
        due_date = today

        # Get all active students
        active_students = Student.objects.filter(is_active=True)

        for student in active_students:
            # Calculate the total amount due for the previous month
            amount_due = student.total_amount_due(month=month, year=year)

            # Generate a unique payment ID
            payment_id = f"PAY-{uuid.uuid4().hex[:8].upper()}"

            # Create a payment record due on the 25th of the current month
            Payment.objects.create(
                payment_id=payment_id,
                student=student,
                date=today,
                amount=amount_due,
                status='pending',
                due_date=due_date,
                receipt=None
            )

@shared_task
def send_payment_reminders():
    # Placeholder for sending payment reminders (to be implemented later)
    pass

@shared_task
def backup_database():
    # Placeholder for database backup (to be implemented later)
    pass