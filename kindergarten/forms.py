from django import forms
from .models import Student, ExtraClass, Expense, ExpenseCategory, ExtraClassSession
from datetime import datetime, timedelta
from django.utils import timezone

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'group', 'first_name', 'last_name', 'father_name', 'mother_name',
            'parent_contact', 'parent_email', 'picture', 'extra_classes', 'date_of_admission',
            'fee', 'has_allergy', 'allergy_details', 'date_of_completion'
        ]  # Excluded student_id
        widgets = {
            'group': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'picture': forms.FileInput(attrs={'class': 'form-control'}),
            'extra_classes': forms.CheckboxSelectMultiple(),
            'date_of_admission': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': 'required'}),
            'fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': 'required'}),
            'has_allergy': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allergy_details': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_completion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        has_allergy = cleaned_data.get('has_allergy')
        allergy_details = cleaned_data.get('allergy_details')

        if has_allergy and not allergy_details:
            self.add_error('allergy_details', "Please specify the allergy details.")
        elif not has_allergy and allergy_details:
            self.add_error('allergy_details', "Allergy details should only be provided if the student has an allergy.")

        return cleaned_data

class ExtraClassForm(forms.ModelForm):
    class Meta:
        model = ExtraClass
        fields = ['name', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': 'required'}),
        }

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'description', 'amount', 'date']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control', 'required': 'required'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': 'required'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': 'required'}),
        }

class ExtraClassSessionForm(forms.ModelForm):
    class Meta:
        model = ExtraClassSession
        fields = ['extra_class', 'session_date', 'session_count']
        widgets = {
            'extra_class': forms.Select(attrs={'class': 'form-control', 'required': 'required'}),
            'session_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': 'required'}),
            'session_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'required': 'required'}),
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student:
            self.fields['extra_class'].queryset = student.extra_classes.all()

class BulkExtraClassSessionForm(forms.Form):
    month = forms.IntegerField(min_value=1, max_value=12, required=True, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Month (1-12)'}))
    year = forms.IntegerField(min_value=2020, required=True, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Year (e.g., 2025)'}))
    
    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        if student:
            for extra_class in student.extra_classes.all():
                self.fields[f'sessions_per_week_{extra_class.id}'] = forms.IntegerField(
                    min_value=0,
                    max_value=7,
                    required=False,
                    initial=0,
                    label=f"Sessions per week for {extra_class.name}",
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )
    
    def save(self):
        month = self.cleaned_data['month']
        year = self.cleaned_data['year']
        
        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)

        for extra_class in self.student.extra_classes.all():
            sessions_per_week = self.cleaned_data.get(f'sessions_per_week_{extra_class.id}', 0)
            if sessions_per_week > 0:
                total_days = (last_day - first_day).days + 1
                total_weeks = total_days // 7
                remaining_days = total_days % 7
                
                current_date = first_day
                while current_date <= last_day:
                    if current_date.weekday() == 0:
                        ExtraClassSession.objects.update_or_create(
                            student=self.student,
                            extra_class=extra_class,
                            session_date=current_date,
                            defaults={'session_count': sessions_per_week}
                        )
                    current_date += timedelta(days=1)