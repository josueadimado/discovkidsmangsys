from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import datetime

class User(AbstractUser):
    pass

class ExtraClass(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class Student(models.Model):
    GROUP_CHOICES = (
        ('nursery', 'Nursery'),
        ('reception_1', 'Reception 1'),
        ('reception_2', 'Reception 2'),
        ('preschool_1', 'Preschool 1'),
        ('preschool_2', 'Preschool 2'),
    )

    student_id = models.CharField(max_length=10, unique=True)
    group = models.CharField(max_length=20, choices=GROUP_CHOICES)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    father_name = models.CharField(max_length=100)
    mother_name = models.CharField(max_length=100)
    parent_contact = models.CharField(max_length=15)
    parent_email = models.EmailField()
    picture = models.ImageField(upload_to='student_pictures/', null=True, blank=True)
    extra_classes = models.ManyToManyField(ExtraClass, blank=True)
    date_of_admission = models.DateField(null=True, blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    has_allergy = models.BooleanField(default=False)
    allergy_details = models.CharField(max_length=255, blank=True, null=True, help_text="Specify the allergy details if applicable.")
    date_of_completion = models.DateField(null=True, blank=True, help_text="The date when the student will graduate, after which they will be automatically deactivated.")

    def save(self, *args, **kwargs):
        if self.date_of_completion and self.is_active:
            current_date = timezone.now().date()
            if current_date > self.date_of_completion:
                self.is_active = False
        super().save(*args, **kwargs)

    def total_extra_class_fee(self, month=None, year=None):
        sessions = ExtraClassSession.objects.filter(student=self)
        if month and year:
            sessions = sessions.filter(session_date__month=month, session_date__year=year)
        total = sum(session.session_count * session.extra_class.price for session in sessions)
        return total

    def total_amount_due(self, month=None, year=None):
        extra_class_fee = self.total_extra_class_fee(month=month, year=year)
        return self.fee + extra_class_fee

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"

class ExtraClassSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    extra_class = models.ForeignKey(ExtraClass, on_delete=models.CASCADE)
    session_date = models.DateField()
    session_count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.student} - {self.extra_class} on {self.session_date}"

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    def __str__(self):
        return f"{self.category} - {self.description} ({self.date})"

class Payment(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    payment_id = models.CharField(max_length=20, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    due_date = models.DateField()
    receipt = models.FileField(upload_to='payment_receipts/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Added field

    def __str__(self):
        return f"{self.payment_id} - {self.student} ({self.date})"

class Employee(models.Model):
    EMPLOYEE_TYPE_CHOICES = (
        ('manager', 'Manager'),
        ('front_desk', 'Front Desk Personnel'),
        ('cleaner', 'Cleaner'),
        ('teacher', 'Teacher'),
        ('gardener', 'Gardener'),
        ('cook', 'Cook'),
    )

    employee_id = models.CharField(max_length=10, unique=True)
    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPE_CHOICES)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_joined = models.DateField()
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True)
    id_document = models.FileField(upload_to='employee_documents/id/', null=True, blank=True)
    passport = models.FileField(upload_to='employee_documents/passport/', null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"

class Document(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='employee_documents/other/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} for {self.employee}"

class EmployeePayment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('salary', 'Salary'),
        ('bonus', 'Bonus'),
    )
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.payment_type.capitalize()} Payment for {self.employee} on {self.date}"