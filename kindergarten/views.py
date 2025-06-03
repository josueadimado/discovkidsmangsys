from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count
from django.contrib import messages
from django.core.paginator import Paginator
import openpyxl
from django.utils import timezone
from datetime import datetime, timedelta
from .forms import StudentForm, ExtraClassForm, ExpenseForm, ExtraClassSessionForm, BulkExtraClassSessionForm
from .models import ExtraClass, Payment, Student, Expense, ExtraClassSession, ExpenseCategory, Employee, Document, EmployeePayment
from django.db.models.functions import TruncDay, TruncMonth, TruncQuarter, TruncYear

@login_required
def dashboard(request):
    # Current date and period
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year

    # Get period filter from request
    period_type = request.GET.get('period_type', 'current_month')
    selected_month = request.GET.get('month', str(current_month))
    selected_year = request.GET.get('year', str(current_year))
    selected_quarter = request.GET.get('quarter', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Determine the date range based on the selected period
    if period_type == 'current_month':
        start_date = datetime(current_year, current_month, 1).date()
        next_month = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        end_date = next_month - timedelta(days=1)
    elif period_type == 'month':
        try:
            selected_month = int(selected_month)
            selected_year = int(selected_year)
            start_date = datetime(selected_year, selected_month, 1).date()
            next_month = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1)
            end_date = next_month - timedelta(days=1)
        except ValueError:
            messages.error(request, "Invalid month or year selected.")
            start_date = datetime(current_year, current_month, 1).date()
            end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif period_type == 'quarter':
        try:
            selected_quarter = int(selected_quarter)
            selected_year = int(selected_year)
            if selected_quarter == 1:
                start_date = datetime(selected_year, 1, 1).date()
                end_date = datetime(selected_year, 3, 31).date()
            elif selected_quarter == 2:
                start_date = datetime(selected_year, 4, 1).date()
                end_date = datetime(selected_year, 6, 30).date()
            elif selected_quarter == 3:
                start_date = datetime(selected_year, 7, 1).date()
                end_date = datetime(selected_year, 9, 30).date()
            elif selected_quarter == 4:
                start_date = datetime(selected_year, 10, 1).date()
                end_date = datetime(selected_year, 12, 31).date()
            else:
                messages.error(request, "Invalid quarter selected.")
                start_date = datetime(current_year, current_month, 1).date()
                end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        except ValueError:
            messages.error(request, "Invalid quarter or year selected.")
            start_date = datetime(current_year, current_month, 1).date()
            end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif period_type == 'year':
        try:
            selected_year = int(selected_year)
            start_date = datetime(selected_year, 1, 1).date()
            end_date = datetime(selected_year, 12, 31).date()
        except ValueError:
            messages.error(request, "Invalid year selected.")
            start_date = datetime(current_year, current_month, 1).date()
            end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif period_type == 'custom':
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            if start_date > end_date:
                messages.error(request, "Start date cannot be after end date.")
                start_date = datetime(current_year, current_month, 1).date()
                end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        except ValueError:
            messages.error(request, "Invalid date range selected.")
            start_date = datetime(current_year, current_month, 1).date()
            end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Active students and employees (snapshot, not period-based)
    active_students = Student.objects.filter(is_active=True)
    for student in active_students:
        student.save()
    active_students_count = active_students.count()
    active_employees_count = Employee.objects.filter(is_active=True).count()

    # Total expected amount (base fees + extra class fees) for the selected period
    total_base_fees = sum(student.fee for student in active_students)
    total_extra_class_fees = 0
    for student in active_students:
        try:
            sessions = ExtraClassSession.objects.filter(
                student=student,
                session_date__gte=start_date,
                session_date__lte=end_date
            )
            total = sum(session.session_count * session.extra_class.price for session in sessions)
            total_extra_class_fees += total
        except Exception as e:
            continue
    total_expected_amount = total_base_fees + total_extra_class_fees

    # Total revenue from completed student payments in the selected period
    total_revenue = Payment.objects.filter(
        status='completed',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Total expenses in the selected period (including employee payments, recorded as expenses)
    total_expenses = Expense.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Breakdown of expenses: Salaries vs Other Expenses
    salaries_expenses = Expense.objects.filter(
        category__name='Salaries',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    other_expenses = total_expenses - salaries_expenses

    # Total employee payments in the selected period
    total_employee_payments = EmployeePayment.objects.filter(
        status='completed',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Net profit (Total Revenue - Total Expenses) for the selected period
    net_profit = total_revenue - total_expenses

    # Overdue and upcoming payments (adjust to consider the selected period)
    if today.day <= 25:
        next_due_date = today.replace(day=25)
    else:
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        next_due_date = next_month.replace(day=25)

    overdue_payments = Payment.objects.filter(
        due_date__lt=today,
        status='pending'
    ).count()

    upcoming_payments = Payment.objects.filter(
        due_date__gte=today,
        due_date__lte=today + timedelta(days=7),
        status='pending'
    ).count()

    # Extra class attendance breakdown for the selected period
    student_attendance = []
    for student in active_students:
        try:
            extra_classes = student.extra_classes.all()
            attendance_details = []
            for extra_class in extra_classes:
                sessions = ExtraClassSession.objects.filter(
                    student=student,
                    extra_class=extra_class,
                    session_date__gte=start_date,
                    session_date__lte=end_date
                )
                total_sessions = sum(session.session_count for session in sessions)
                total_fee = extra_class.price * total_sessions
                attendance_details.append({
                    'extra_class': extra_class.name,
                    'total_sessions': total_sessions,
                    'total_fee': total_fee,
                })
            student_attendance.append({
                'student': student,
                'attendance_details': attendance_details,
                'base_fee': student.fee,
                'total_extra_class_fee': sum(detail['total_fee'] for detail in attendance_details),
                'total_due': student.fee + sum(detail['total_fee'] for detail in attendance_details),
            })
        except Exception as e:
            continue

    context = {
        'active_students_count': active_students_count,
        'total_expected_amount': total_expected_amount,
        'total_base_fees': total_base_fees,
        'total_extra_class_fees': total_extra_class_fees,
        'total_expenses': total_expenses,
        'salaries_expenses': salaries_expenses,
        'other_expenses': other_expenses,
        'total_revenue': total_revenue,
        'net_profit': net_profit,
        'active_employees_count': active_employees_count,
        'total_employee_payments': total_employee_payments,
        'overdue_payments': overdue_payments,
        'upcoming_payments': upcoming_payments,
        'next_due_date': next_due_date,
        'today': today,
        'student_attendance': student_attendance,
        'current_month': current_month,
        'current_year': current_year,
        'period_type': period_type,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_quarter': selected_quarter,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'dashboard.html', context)

@login_required
def admit_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        print("Form submitted with data:", request.POST, request.FILES)
        if form.is_valid():
            print("Form is valid")
            try:
                # Generate student_id based on group
                group = form.cleaned_data['group']
                prefix_map = {
                    'nursery': 'NUR',
                    'reception_1': 'REC1',
                    'reception_2': 'REC2',
                    'preschool_1': 'PRE1',
                    'preschool_2': 'PRE2',
                }
                prefix = prefix_map.get(group, 'STU')
                existing_students = Student.objects.filter(group=group, student_id__startswith=prefix).order_by('-student_id')
                if existing_students.exists():
                    last_id = existing_students.first().student_id
                    number = int(last_id.replace(prefix, '')) + 1
                else:
                    number = 1
                student_id = f"{prefix}{number:03d}"
                print("Generated student_id:", student_id)

                # Create the student instance but don't save it yet
                student = form.save(commit=False)
                student.student_id = student_id
                student.save()
                form.save_m2m()  # Save many-to-many relationships (e.g., extra_classes)
                print("Student saved:", student)

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    print("Returning AJAX success response")
                    return JsonResponse({'success': True})
                print("Redirecting to student list")
                messages.success(request, "Student admitted successfully.")
                return redirect('kindergarten:student_list')
            except Exception as e:
                print("Error saving student:", str(e))
                messages.error(request, f"Error saving student: {str(e)}")
                return render(request, 'admit_student.html', {'form': form})
        else:
            print("Form is invalid. Errors:", form.errors)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                print("Returning AJAX error response")
                return JsonResponse({'success': False, 'errors': form.errors})
            return render(request, 'admit_student.html', {'form': form})
    else:
        form = StudentForm()
    return render(request, 'admit_student.html', {'form': form})


    
@login_required
def student_list(request):
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status_filter', 'active')
    print(f"Status Filter: {status_filter}")
    
    students = Student.objects.all()
    for student in students:
        student.save()
    
    print(f"Total students in database: {students.count()}")
    active_students_count = students.filter(is_active=True).count()
    inactive_students_count = students.filter(is_active=False).count()
    print(f"Active students in database: {active_students_count}")
    print(f"Inactive students in database: {inactive_students_count}")
    
    if status_filter == "active":
        students = students.filter(is_active=True)
    elif status_filter == "inactive":
        students = students.filter(is_active=False)
    print(f"Students after status filter: {students.count()}")
    
    if query:
        students = students.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(student_id__icontains=query)
        )
    print(f"Students after search filter: {students.count()}")
    
    students = students.order_by('student_id')
    paginator = Paginator(students, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    print(f"Students in current page: {page_obj.object_list.count()}")
    
    for student in page_obj:
        print(f"Student {student.student_id}: is_active={student.is_active}")
    
    form = StudentForm()
    return render(request, 'student_list.html', {
        'page_obj': page_obj,
        'form': form,
        'status_filter': status_filter,
    })

@login_required
def view_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    student.save()
    sessions = ExtraClassSession.objects.filter(student=student).select_related('extra_class')
    sessions_with_fees = []
    for session in sessions:
        total_fee = session.extra_class.price * session.session_count
        sessions_with_fees.append({
            'session': session,
            'total_fee': total_fee,
        })
    extra_classes = student.extra_classes.all()
    dynamic_fields = []
    if request.method == 'POST':
        if 'single_session' in request.POST:
            single_form = ExtraClassSessionForm(request.POST, student=student)
            bulk_form = BulkExtraClassSessionForm(student=student)
            if single_form.is_valid():
                try:
                    session = single_form.save(commit=False)
                    session.student = student
                    session.save()
                    messages.success(request, "Single session logged successfully.")
                    return redirect('kindergarten:view_student', student_id=student_id)
                except Exception as e:
                    print(f"Error saving single session: {e}")
                    single_form.add_error(None, "An error occurred while saving the session.")
            else:
                print("Single session form errors:", single_form.errors)
        elif 'bulk_session' in request.POST:
            single_form = ExtraClassSessionForm(student=student)
            bulk_form = BulkExtraClassSessionForm(request.POST, student=student)
            if bulk_form.is_valid():
                try:
                    bulk_form.save()
                    messages.success(request, "Monthly sessions logged successfully.")
                    return redirect('kindergarten:view_student', student_id=student_id)
                except Exception as e:
                    print(f"Error saving bulk session: {e}")
                    bulk_form.add_error(None, "An error occurred while saving the sessions.")
            else:
                print("Bulk session form errors:", bulk_form.errors)
                for extra_class in extra_classes:
                    field_name = f"sessions_per_week_{extra_class.id}"
                    bound_field = bulk_form[field_name]
                    field_html = bound_field.as_widget()
                    errors = bound_field.errors.as_text() if bound_field.errors else ""
                    dynamic_fields.append({
                        'extra_class': extra_class,
                        'field_name': field_name,
                        'field_html': field_html,
                        'errors': errors,
                    })
    else:
        single_form = ExtraClassSessionForm(student=student)
        bulk_form = BulkExtraClassSessionForm(student=student)
        for extra_class in extra_classes:
            field_name = f"sessions_per_week_{extra_class.id}"
            bound_field = bulk_form[field_name]
            field_html = bound_field.as_widget()
            dynamic_fields.append({
                'extra_class': extra_class,
                'field_name': field_name,
                'field_html': field_html,
                'errors': "",
            })
    context = {
        'student': student,
        'sessions_with_fees': sessions_with_fees,
        'single_form': single_form,
        'bulk_form': bulk_form,
        'bulk_form_errors': bulk_form.errors if request.method == 'POST' and 'bulk_session' in request.POST else None,
        'dynamic_fields': dynamic_fields,
    }
    return render(request, 'view_student.html', context)

@login_required
def edit_extra_class_session(request, student_id, session_id):
    student = get_object_or_404(Student, student_id=student_id)
    session = get_object_or_404(ExtraClassSession, id=session_id, student=student)
    if request.method == 'POST':
        form = ExtraClassSessionForm(request.POST, instance=session, student=student)
        if form.is_valid():
            try:
                form.save()
                return redirect('kindergarten:view_student', student_id=student_id)
            except Exception as e:
                form.add_error(None, f"An error occurred while saving the session: {e}")
    else:
        form = ExtraClassSessionForm(instance=session, student=student)
    return render(request, 'edit_extra_class_session.html', {'form': form, 'student': student, 'session': session})

@login_required
def delete_extra_class_session(request, student_id, session_id):
    student = get_object_or_404(Student, student_id=student_id)
    session = get_object_or_404(ExtraClassSession, id=session_id, student=student)
    if request.method == 'POST':
        try:
            session.delete()
            messages.success(request, "Extra class session deleted successfully.")
            return redirect('kindergarten:view_student', student_id=student_id)
        except Exception as e:
            messages.error(request, f"Error deleting session: {e}")
            return redirect('kindergarten:view_student', student_id=student_id)
    return render(request, 'delete_extra_class_session.html', {'student': student, 'session': session})

@login_required
def generate_student_id(request):
    group = request.GET.get('group')
    if not group:
        return JsonResponse({'student_id': '', 'error': 'Group parameter is required'}, status=400)
    prefix_map = {
        'nursery': 'NUR',
        'reception_1': 'REC1',
        'reception_2': 'REC2',
        'preschool_1': 'PRE1',
        'preschool_2': 'PRE2',
    }
    prefix = prefix_map.get(group, 'STU')
    try:
        existing_students = Student.objects.filter(group=group, student_id__startswith=prefix).order_by('-student_id')
        if existing_students.exists():
            last_id = existing_students.first().student_id
            number = int(last_id.replace(prefix, '')) + 1
        else:
            number = 1
        student_id = f"{prefix}{number:03d}"
        return JsonResponse({'student_id': student_id})
    except Exception as e:
        return JsonResponse({'student_id': '', 'error': str(e)}, status=500)

@login_required
def edit_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Student updated successfully.")
                return redirect('kindergarten:student_list')
            except Exception as e:
                form.add_error(None, f"An error occurred while saving the student: {e}")
    else:
        form = StudentForm(instance=student)
    return render(request, 'edit_student.html', {'form': form, 'student': student})

@login_required
def delete_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    if request.method == 'POST':
        try:
            student.delete()
            messages.success(request, "Student deleted successfully.")
            return redirect('kindergarten:student_list')
        except Exception as e:
            messages.error(request, f"Error deleting student: {e}")
            return redirect('kindergarten:student_list')
    return render(request, 'delete_student.html', {'student': student})

@login_required
def hibernate_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    try:
        initial_status = student.is_active
        print(f"Initial status for student {student_id}: {initial_status}")
        student.is_active = not student.is_active
        print(f"New status before save for student {student_id}: {student.is_active}")
        student.save()
        student.refresh_from_db()
        print(f"Status after save for student {student_id}: {student.is_active}")
        if student.is_active == initial_status:
            messages.error(request, f"Failed to toggle student status for {student_id}. No change occurred.")
        else:
            status = "activated" if student.is_active else "deactivated"
            messages.success(request, f"Student {status} successfully.")
    except Exception as e:
        print(f"Error updating student status for {student_id}: {e}")
        messages.error(request, f"Error updating student status: {e}")
    return redirect('kindergarten:student_list')

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Logged in successfully.")
                return redirect('kindergarten:dashboard')
        messages.error(request, "Invalid username or password.")
        return render(request, 'login.html', {'form': form})
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('login')

@login_required
def export_students_to_excel(request):
    try:
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "Student List"
        headers = [
            "Picture", "Student ID", "First Name", "Last Name", "Group", 
            "Father's Name", "Mother's Name", "Parent Contact", "Parent Email", 
            "Date of Admission", "Created At", "Fee", "Extra Classes", 
            "Has Allergy", "Allergy Details", "Date of Completion", "Status"
        ]
        worksheet.append(headers)
        students = Student.objects.all().prefetch_related('extra_classes')
        for student in students:
            student.save()
            extra_classes = ", ".join([f"{extra_class.name} ({extra_class.price} RUB)" for extra_class in student.extra_classes.all()])
            picture_url = student.picture.url if student.picture else "No Picture"
            row = [
                picture_url,
                student.student_id,
                student.first_name,
                student.last_name,
                student.get_group_display(),
                student.father_name,
                student.mother_name,
                student.parent_contact,
                student.parent_email,
                student.date_of_admission.strftime('%Y-%m-%d') if student.date_of_admission else '',
                student.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                f"{student.fee} RUB",
                extra_classes,
                "Yes" if student.has_allergy else "No",
                student.allergy_details if student.has_allergy else "",
                student.date_of_completion.strftime('%Y-%m-%d') if student.date_of_completion else '',
                "Active" if student.is_active else "Inactive"
            ]
            worksheet.append(row)
        for col in worksheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column].width = adjusted_width
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=student_list.xlsx'
        workbook.save(response)
        return response
    except Exception as e:
        messages.error(request, f"Error exporting students to Excel: {e}")
        return redirect('kindergarten:student_list')

@login_required
def extra_class_list(request):
    extra_classes = ExtraClass.objects.all().order_by('name')
    paginator = Paginator(extra_classes, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'extra_class_list.html', {'page_obj': page_obj})

@login_required
def add_extra_class(request):
    if request.method == 'POST':
        form = ExtraClassForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Extra class added successfully.")
                return redirect('kindergarten:extra_class_list')
            except Exception as e:
                form.add_error(None, f"An error occurred while adding the extra class: {e}")
    else:
        form = ExtraClassForm()
    return render(request, 'add_extra_class.html', {'form': form})

@login_required
def edit_extra_class(request, extra_class_id):
    extra_class = get_object_or_404(ExtraClass, id=extra_class_id)
    if request.method == 'POST':
        form = ExtraClassForm(request.POST, instance=extra_class)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Extra class updated successfully.")
                return redirect('kindergarten:extra_class_list')
            except Exception as e:
                form.add_error(None, f"An error occurred while updating the extra class: {e}")
    else:
        form = ExtraClassForm(instance=extra_class)
    return render(request, 'edit_extra_class.html', {'form': form, 'extra_class': extra_class})

@login_required
def delete_extra_class(request, extra_class_id):
    extra_class = get_object_or_404(ExtraClass, id=extra_class_id)
    if request.method == 'POST':
        try:
            extra_class.delete()
            messages.success(request, "Extra class deleted successfully.")
            return redirect('kindergarten:extra_class_list')
        except Exception as e:
            messages.error(request, f"Error deleting extra class: {e}")
            return redirect('kindergarten:extra_class_list')
    return render(request, 'delete_extra_class.html', {'extra_class': extra_class})

@login_required
def expense_list(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    view_type = request.GET.get('view_type', 'list')

    expenses = Expense.objects.all()

    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            expenses = expenses.filter(date__gte=start_date)
        except ValueError:
            messages.error(request, "Invalid start date format. Use YYYY-MM-DD.")
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            expenses = expenses.filter(date__lte=end_date)
        except ValueError:
            messages.error(request, "Invalid end date format. Use YYYY-MM-DD.")

    category_summary = expenses.values('category__name').annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-total_amount')

    daily_expenses = expenses.annotate(day=TruncDay('date')).values('day').annotate(
        total_amount=Sum('amount')
    ).order_by('day')

    monthly_expenses = expenses.annotate(month=TruncMonth('date')).values('month').annotate(
        total_amount=Sum('amount')
    ).order_by('month')

    quarterly_expenses = expenses.annotate(quarter=TruncQuarter('date')).values('quarter').annotate(
        total_amount=Sum('amount')
    ).order_by('quarter')

    yearly_expenses = expenses.annotate(year=TruncYear('date')).values('year').annotate(
        total_amount=Sum('amount')
    ).order_by('year')

    category_chart_data = {
        'labels': [item['category__name'] for item in category_summary],
        'data': [float(item['total_amount']) for item in category_summary],
    }

    daily_chart_data = {
        'labels': [item['day'].strftime('%Y-%m-%d') for item in daily_expenses],
        'data': [float(item['total_amount']) for item in daily_expenses],
    }
    monthly_chart_data = {
        'labels': [item['month'].strftime('%Y-%m') for item in monthly_expenses],
        'data': [float(item['total_amount']) for item in monthly_expenses],
    }
    quarterly_chart_data = {
        'labels': [item['quarter'].strftime('%Y-Q') for item in quarterly_expenses],
        'data': [float(item['total_amount']) for item in quarterly_expenses],
    }
    yearly_chart_data = {
        'labels': [item['year'].strftime('%Y') for item in yearly_expenses],
        'data': [float(item['total_amount']) for item in yearly_expenses],
    }

    paginator = Paginator(expenses.order_by('-date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'expenses/expense_list.html', {
        'page_obj': page_obj,
        'category_summary': category_summary,
        'daily_expenses': daily_expenses,
        'monthly_expenses': monthly_expenses,
        'quarterly_expenses': quarterly_expenses,
        'yearly_expenses': yearly_expenses,
        'category_chart_data': category_chart_data,
        'daily_chart_data': daily_chart_data,
        'monthly_chart_data': monthly_chart_data,
        'quarterly_chart_data': quarterly_chart_data,
        'yearly_chart_data': yearly_chart_data,
        'start_date': start_date,
        'end_date': end_date,
        'view_type': view_type,
    })

@login_required
def add_expense(request):
    categories_exist = ExpenseCategory.objects.exists()
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Expense added successfully.")
                return redirect('kindergarten:expense_list')
            except Exception as e:
                form.add_error(None, f"An error occurred while adding the expense: {e}")
    else:
        form = ExpenseForm()
    return render(request, 'expenses/add_expense.html', {
        'form': form,
        'categories_exist': categories_exist,
    })

@login_required
def edit_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Expense updated successfully.")
                return redirect('kindergarten:expense_list')
            except Exception as e:
                form.add_error(None, f"An error occurred while updating the expense: {e}")
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'expenses/edit_expense.html', {'form': form, 'expense': expense})

@login_required
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    if request.method == 'POST':
        try:
            expense.delete()
            messages.success(request, "Expense deleted successfully.")
            return redirect('kindergarten:expense_list')
        except Exception as e:
            messages.error(request, f"Error deleting expense: {e}")
            return redirect('kindergarten:expense_list')
    return render(request, 'expenses/delete_expense.html', {'expense': expense})

@login_required
def payment_list(request):
    query = request.GET.get('q', '')
    payments = Payment.objects.all()
    if query:
        payments = payments.filter(
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(payment_id__icontains=query)
        )
    payments = payments.order_by('-date')
    paginator = Paginator(payments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    students = Student.objects.all()
    return render(request, 'payment/payment_list.html', {'page_obj': page_obj, 'students': students})

@login_required
def add_payment(request):
    if request.method == 'POST':
        student_id = request.POST.get('student')
        date = request.POST.get('date')
        amount = request.POST.get('amount')
        status = request.POST.get('status')
        receipt = request.FILES.get('receipt')

        try:
            student = get_object_or_404(Student, id=student_id)
            student.save()

            # Generate payment_id in the format PAYYYYYMMDDNNN
            payment_date = datetime.strptime(date, '%Y-%m-%d').date()
            date_str = payment_date.strftime('%Y%m%d')
            last_payment = Payment.objects.filter(
                date=payment_date,
                payment_id__startswith=f"PAY{date_str}"
            ).order_by('-payment_id').first()

            if last_payment:
                last_seq = int(last_payment.payment_id[-3:])
                new_seq = last_seq + 1
            else:
                new_seq = 1

            payment_id = f"PAY{date_str}{new_seq:03d}"

            payment = Payment(
                payment_id=payment_id,
                student=student,
                date=date,
                amount=amount,
                status=status,
                receipt=receipt
            )

            payment_date = datetime.strptime(date, '%Y-%m-%d').date()
            if payment_date.day <= 25:
                due_date = payment_date.replace(day=25)
            else:
                next_month = (payment_date.replace(day=1) + timedelta(days=32)).replace(day=1)
                due_date = next_month.replace(day=25)
            payment.due_date = due_date

            payment.save()
            messages.success(request, f"Payment added successfully with ID {payment_id}.")
            return redirect('kindergarten:payment_list')
        except Exception as e:
            messages.error(request, f"Error adding payment: {e}")
            students = Student.objects.all()
            return render(request, 'payment/add_payment.html', {'students': students})

    students = Student.objects.all()
    return render(request, 'payment/add_payment.html', {'students': students})

@login_required
def edit_payment(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id)
    if request.method == 'POST':
        try:
            payment.student = get_object_or_404(Student, id=request.POST.get('student'))
            payment.student.save()
            payment.date = request.POST.get('date')
            payment.amount = request.POST.get('amount')
            payment.status = request.POST.get('status')
            if request.FILES.get('receipt'):
                payment.receipt = request.FILES.get('receipt')
            payment_date = datetime.strptime(payment.date, '%Y-%m-%d').date()
            if payment_date.day <= 25:
                due_date = payment_date.replace(day=25)
            else:
                next_month = (payment_date.replace(day=1) + timedelta(days=32)).replace(day=1)
                due_date = next_month.replace(day=25)
            payment.due_date = due_date
            payment.save()
            messages.success(request, "Payment updated successfully.")
            return redirect('kindergarten:payment_list')
        except Exception as e:
            messages.error(request, f"Error updating payment: {e}")
            students = Student.objects.all()
            return render(request, 'payment/edit_payment.html', {'payment': payment, 'students': students})
    students = Student.objects.all()
    return render(request, 'payment/edit_payment.html', {'payment': payment, 'students': students})

@login_required
def delete_payment(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id)
    if request.method == 'POST':
        try:
            payment.delete()
            messages.success(request, "Payment deleted successfully.")
            return redirect('kindergarten:payment_list')
        except Exception as e:
            messages.error(request, f"Error deleting payment: {e}")
            return redirect('kindergarten:payment_list')
    return render(request, 'payment/delete_payment.html', {'payment': payment})

@login_required
def employee_list(request):
    employees = Employee.objects.all().order_by('-date_joined')
    
    employee_id = request.GET.get('employee_id', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    payment_history = EmployeePayment.objects.all()
    selected_employee = None
    
    if employee_id:
        payment_history = payment_history.filter(employee__employee_id=employee_id)
        selected_employee = Employee.objects.filter(employee_id=employee_id).first()
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            payment_history = payment_history.filter(date__gte=start_date)
        except ValueError:
            messages.error(request, "Invalid start date format. Use YYYY-MM-DD.")
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            payment_history = payment_history.filter(date__lte=end_date)
        except ValueError:
            messages.error(request, "Invalid end date format. Use YYYY-MM-DD.")
    
    payment_history = payment_history.order_by('-date')
    
    paginator = Paginator(employees, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'employees/list.html', {
        'page_obj': page_obj,
        'payment_history': payment_history,
        'selected_employee': selected_employee,
        'start_date': start_date,
        'end_date': end_date,
        'employee_id': employee_id,
    })

@login_required
def add_employee(request):
    if request.method == 'POST':
        last_employee = Employee.objects.order_by('-id').first()
        if last_employee:
            last_id = int(last_employee.employee_id.replace('EMP', ''))
            new_id = f"EMP{last_id + 1:03d}"
        else:
            new_id = "EMP001"

        employee = Employee(
            employee_id=new_id,
            employee_type=request.POST.get('employee_type'),
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            date_joined=request.POST.get('date_joined'),
            contact_number=request.POST.get('contact_number'),
            email=request.POST.get('email'),
            salary=request.POST.get('salary'),
            bonus=request.POST.get('bonus', 0.00),
        )

        if 'photo' in request.FILES:
            employee.photo = request.FILES['photo']
        if 'id_document' in request.FILES:
            employee.id_document = request.FILES['id_document']
        if 'passport' in request.FILES:
            employee.passport = request.FILES['passport']

        employee.save()

        document_titles = request.POST.getlist('document_title')
        document_files = request.FILES.getlist('document_file')
        for title, file in zip(document_titles, document_files):
            if title and file:
                Document.objects.create(employee=employee, title=title, file=file)

        messages.success(request, "Employee added successfully.")
        return redirect('kindergarten:employee_list')

    return render(request, 'employees/add.html')

@login_required
def edit_employee(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    if request.method == 'POST':
        employee.employee_type = request.POST.get('employee_type')
        employee.first_name = request.POST.get('first_name')
        employee.last_name = request.POST.get('last_name')
        employee.date_joined = request.POST.get('date_joined')
        employee.contact_number = request.POST.get('contact_number')
        employee.email = request.POST.get('email')
        employee.salary = request.POST.get('salary')
        employee.bonus = request.POST.get('bonus', 0.00)

        if 'photo' in request.FILES:
            employee.photo = request.FILES['photo']
        if 'id_document' in request.FILES:
            employee.id_document = request.FILES['id_document']
        if 'passport' in request.FILES:
            employee.passport = request.FILES['passport']

        employee.save()

        document_titles = request.POST.getlist('document_title')
        document_files = request.FILES.getlist('document_file')
        for title, file in zip(document_titles, document_files):
            if title and file:
                Document.objects.create(employee=employee, title=title, file=file)

        messages.success(request, "Employee updated successfully.")
        return redirect('kindergarten:employee_list')

    return render(request, 'employees/edit.html', {'employee': employee})

@login_required
def delete_employee(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, "Employee deleted successfully.")
        return redirect('kindergarten:employee_list')
    return render(request, 'employees/delete.html', {'employee': employee})

@login_required
def activate_employee(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    if request.method == 'POST':
        employee.is_active = True
        employee.save()
        messages.success(request, f"Employee {employee.first_name} {employee.last_name} has been activated.")
        return redirect('kindergarten:employee_list')
    return render(request, 'employees/activate.html', {'employee': employee})

@login_required
def deactivate_employee(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    if request.method == 'POST':
        employee.is_active = False
        employee.save()
        messages.success(request, f"Employee {employee.first_name} {employee.last_name} has been deactivated.")
        return redirect('kindergarten:employee_list')
    return render(request, 'employees/deactivate.html', {'employee': employee})

@login_required
def add_employee_payment(request):
    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        salary_amount = request.POST.get('salary_amount')
        bonus_amount = request.POST.get('bonus_amount', '0')
        date = request.POST.get('date')
        status = request.POST.get('status', 'pending')

        try:
            employee = get_object_or_404(Employee, id=employee_id)
            
            salaries_category, created = ExpenseCategory.objects.get_or_create(name='Salaries')

            if float(salary_amount) > 0:
                salary_payment = EmployeePayment(
                    employee=employee,
                    payment_type='salary',
                    amount=salary_amount,
                    date=date,
                    status=status,
                    created_at=timezone.now()
                )
                salary_payment.save()

                salary_expense = Expense(
                    category=salaries_category,
                    description=f"Salary payment for {employee.first_name} {employee.last_name} ({employee.employee_id})",
                    amount=salary_amount,
                    date=date
                )
                salary_expense.save()

            if float(bonus_amount) > 0:
                bonus_payment = EmployeePayment(
                    employee=employee,
                    payment_type='bonus',
                    amount=bonus_amount,
                    date=date,
                    status=status,
                    created_at=timezone.now()
                )
                bonus_payment.save()

                bonus_expense = Expense(
                    category=salaries_category,
                    description=f"Bonus payment for {employee.first_name} {employee.last_name} ({employee.employee_id})",
                    amount=bonus_amount,
                    date=date
                )
                bonus_expense.save()

            messages.success(request, "Payment(s) recorded successfully.")
            return redirect('kindergarten:employee_list')
        except Exception as e:
            messages.error(request, f"Error recording payment: {e}")
            employees = Employee.objects.all()
            return render(request, 'employees/add_payment.html', {'employees': employees})

    employees = Employee.objects.all()
    return render(request, 'employees/add_payment.html', {'employees': employees})

@login_required
def print_employee_payment_history(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    payment_history = EmployeePayment.objects.filter(employee=employee)
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            payment_history = payment_history.filter(date__gte=start_date)
        except ValueError:
            messages.error(request, "Invalid start date format. Use YYYY-MM-DD.")
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            payment_history = payment_history.filter(date__lte=end_date)
        except ValueError:
            messages.error(request, "Invalid end date format. Use YYYY-MM-DD.")
    
    payment_history = payment_history.order_by('-date')
    
    return render(request, 'employees/print_payment_history.html', {
        'employee': employee,
        'payment_history': payment_history,
        'start_date': start_date,
        'end_date': end_date,
    })

@login_required
def view_employee(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    return render(request, 'employees/view_employee.html', {'employee': employee})