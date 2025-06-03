from django.core.management.base import BaseCommand
from kindergarten.models import Student
from django.utils import timezone

class Command(BaseCommand):
    help = 'Updates the is_active status of students based on their date_of_completion'

    def handle(self, *args, **kwargs):
        students = Student.objects.all()
        updated_count = 0
        for student in students:
            original_status = student.is_active
            student.save()  # Triggers the save method to check date_of_completion
            if student.is_active != original_status:
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Updated status for {student.student_id}: is_active={student.is_active}"
                ))
        self.stdout.write(self.style.SUCCESS(
            f"Finished updating student statuses. Updated {updated_count} students."
        ))