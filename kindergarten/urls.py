from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'kindergarten'

urlpatterns = [
    path('', views.user_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admit-student/', views.admit_student, name='admit_student'),
    path('students/', views.student_list, name='student_list'),
    path('view-student/<str:student_id>/', views.view_student, name='view_student'),
    path('edit-student/<str:student_id>/', views.edit_student, name='edit_student'),
    path('delete-student/<str:student_id>/', views.delete_student, name='delete_student'),
    path('hibernate-student/<str:student_id>/', views.hibernate_student, name='hibernate_student'),
    path('generate-student-id/', views.generate_student_id, name='generate_student_id'),
    path('view-student/<str:student_id>/edit-session/<int:session_id>/', views.edit_extra_class_session, name='edit_extra_class_session'),
    path('view-student/<str:student_id>/delete-session/<int:session_id>/', views.delete_extra_class_session, name='delete_extra_class_session'),
    path('export-students/', views.export_students_to_excel, name='export_students_to_excel'),
    path('extra-classes/', views.extra_class_list, name='extra_class_list'),
    path('add-extra-class/', views.add_extra_class, name='add_extra_class'),
    path('edit-extra-class/<int:extra_class_id>/', views.edit_extra_class, name='edit_extra_class'),
    path('delete-extra-class/<int:extra_class_id>/', views.delete_extra_class, name='delete_extra_class'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('add-expense/', views.add_expense, name='add_expense'),
    path('edit-expense/<int:expense_id>/', views.edit_expense, name='edit_expense'),
    path('delete-expense/<int:expense_id>/', views.delete_expense, name='delete_expense'),
    path('payments/', views.payment_list, name='payment_list'),
    path('add-payment/', views.add_payment, name='add_payment'),
    path('edit-payment/<str:payment_id>/', views.edit_payment, name='edit_payment'),
    path('delete-payment/<str:payment_id>/', views.delete_payment, name='delete_payment'),
    path('employees/', views.employee_list, name='employee_list'),
    path('add-employee/', views.add_employee, name='add_employee'),
    path('edit-employee/<str:employee_id>/', views.edit_employee, name='edit_employee'),
    path('delete-employee/<str:employee_id>/', views.delete_employee, name='delete_employee'),
    path('activate-employee/<str:employee_id>/', views.activate_employee, name='activate_employee'),
    path('deactivate-employee/<str:employee_id>/', views.deactivate_employee, name='deactivate_employee'),
    path('add-employee-payment/', views.add_employee_payment, name='add_employee_payment'),
    path('view-employee/<str:employee_id>/', views.view_employee, name='view_employee'),    
    path('print-employee-payment-history/<str:employee_id>/', views.print_employee_payment_history, name='print_employee_payment_history'),
    path('logout/', views.user_logout, name='logout'),
    path('attendance/record/', views.record_attendance, name='record_attendance'),
    path('attendance/history/', views.attendance_history, name='attendance_history'),
]