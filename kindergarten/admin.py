from django.contrib import admin
from .models import Expense, ExpenseCategory, Student, ExtraClass, ExtraClassSession, Payment, Employee, Document

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'description', 'date')
    list_filter = ('category', 'date')
    search_fields = ('category__name', 'description')
    date_hierarchy = 'date'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'first_name', 'last_name', 'group', 'is_active', 'created_at')
    list_filter = ('group', 'is_active', 'created_at')
    search_fields = ('student_id', 'first_name', 'last_name', 'parent_email')
    date_hierarchy = 'created_at'

@admin.register(ExtraClass)
class ExtraClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)

@admin.register(ExtraClassSession)
class ExtraClassSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'extra_class', 'session_date', 'session_count')
    list_filter = ('extra_class', 'session_date')
    search_fields = ('student__student_id', 'extra_class__name')
    date_hierarchy = 'session_date'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'student', 'amount', 'status', 'date', 'due_date')
    list_filter = ('status', 'date', 'due_date')
    search_fields = ('payment_id', 'student__student_id')
    date_hierarchy = 'date'

# Inline for Documents
class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1  # Number of empty forms to display
    fields = ('title', 'file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'full_name', 'employee_type', 'date_joined', 'contact_number', 'email', 'salary', 'bonus', 'is_active')
    list_filter = ('employee_type', 'is_active', 'date_joined')
    search_fields = ('employee_id', 'first_name', 'last_name', 'email')
    date_hierarchy = 'date_joined'
    inlines = [DocumentInline]

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'