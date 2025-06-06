from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Expense, ExpenseCategory, Student, ExtraClass, ExtraClassSession, Payment, Employee, Document, User, StudentAttendance

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
    extra = 1
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

# Custom User Admin
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    date_hierarchy = 'date_joined'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields['is_superuser'].disabled = True
            form.base_fields['user_permissions'].disabled = True
            form.base_fields['groups'].disabled = True
        return form

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if change and 'is_superuser' in form.changed_data:
                obj.is_superuser = User.objects.get(pk=obj.pk).is_superuser
        super().save_model(request, obj, form, change)

admin.site.register(User, CustomUserAdmin)

# Register StudentAttendance
@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'is_present', 'remarks_summary', 'recorded_at')
    list_filter = ('is_present', 'date', 'recorded_at')
    search_fields = ('student__student_id', 'student__first_name', 'student__last_name', 'remarks')
    date_hierarchy = 'date'

    def remarks_summary(self, obj):
        if obj.remarks:
            return obj.remarks[:50] + ('...' if len(obj.remarks) > 50 else '')
        return '—'
    remarks_summary.short_description = 'Remarks'