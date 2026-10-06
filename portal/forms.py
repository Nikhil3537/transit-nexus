from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    AdminInvoice, CollegeAssessment, CollegeProfile, CollegeProgram, CollegeQuickReport, CollegeStudent,
    Department, Faculty, OnlineTest, PlacementRecord, SyllabusCoverage,
)


ACADEMIC_PROGRAMME_CHOICES = [
    ("Engineering & Technology", [
        ("Artificial Intelligence and Data Science", "Artificial Intelligence and Data Science"),
        ("Computer Science and Engineering", "Computer Science and Engineering"),
        ("Information Science and Engineering", "Information Science and Engineering"),
        ("Electronics and Communication Engineering", "Electronics and Communication Engineering"),
        ("Electrical and Electronics Engineering", "Electrical and Electronics Engineering"),
        ("Mechanical Engineering", "Mechanical Engineering"),
        ("Civil Engineering", "Civil Engineering"),
        ("Artificial Intelligence and Machine Learning", "Artificial Intelligence and Machine Learning"),
        ("Robotics and Artificial Intelligence", "Robotics and Artificial Intelligence"),
        ("Aeronautical Engineering", "Aeronautical Engineering"),
        ("Aerospace Engineering", "Aerospace Engineering"),
        ("Automobile Engineering", "Automobile Engineering"),
        ("Biotechnology", "Biotechnology"),
        ("Chemical Engineering", "Chemical Engineering"),
        ("Industrial Engineering", "Industrial Engineering"),
        ("Biomedical Engineering", "Biomedical Engineering"),
        ("Mining Engineering", "Mining Engineering"),
        ("Food Technology", "Food Technology"),
        ("Agricultural Engineering", "Agricultural Engineering"),
        ("Other Engineering", "Other Engineering"),
    ]),
    ("Architecture & Design", [
        ("Bachelor of Architecture (B.Arch)", "Bachelor of Architecture (B.Arch)"),
        ("Bachelor of Design (B.Des)", "Bachelor of Design (B.Des)"),
        ("Interior Design", "Interior Design"),
        ("Fashion Design", "Fashion Design"),
        ("Product Design", "Product Design"),
        ("Communication Design", "Communication Design"),
        ("Other Design", "Other Design"),
    ]),
    ("Medical & Health Sciences", [
        ("Bachelor of Nursing (B.Sc Nursing)", "Bachelor of Nursing (B.Sc Nursing)"),
        ("General Nursing and Midwifery (GNM)", "General Nursing and Midwifery (GNM)"),
        ("Bachelor of Physiotherapy (BPT)", "Bachelor of Physiotherapy (BPT)"),
        ("Bachelor of Pharmacy (B.Pharm)", "Bachelor of Pharmacy (B.Pharm)"),
        ("Doctor of Pharmacy (Pharm.D)", "Doctor of Pharmacy (Pharm.D)"),
        ("Allied Health Sciences", "Allied Health Sciences"),
        ("Medical Laboratory Technology", "Medical Laboratory Technology"),
        ("Radiology and Medical Imaging", "Radiology and Medical Imaging"),
        ("Other Health Sciences", "Other Health Sciences"),
    ]),
    ("Computer & IT", [
        ("Bachelor of Computer Applications (BCA)", "Bachelor of Computer Applications (BCA)"),
        ("Information Technology", "Information Technology"),
        ("Data Science", "Data Science"),
        ("Cyber Security", "Cyber Security"),
        ("Computer Applications", "Computer Applications"),
    ]),
    ("Management & Commerce", [
        ("Bachelor of Business Administration (BBA)", "Bachelor of Business Administration (BBA)"),
        ("Master of Business Administration (MBA)", "Master of Business Administration (MBA)"),
        ("Bachelor of Commerce (B.Com)", "Bachelor of Commerce (B.Com)"),
        ("Bachelor of Management Studies (BMS)", "Bachelor of Management Studies (BMS)"),
        ("Bachelor of Business Management (BBM)", "Bachelor of Business Management (BBM)"),
        ("Bachelor of Hotel Management (BHM)", "Bachelor of Hotel Management (BHM)"),
    ]),
    ("Science", [
        ("Bachelor of Science (B.Sc)", "Bachelor of Science (B.Sc)"),
        ("Microbiology", "Microbiology"),
        ("Biochemistry", "Biochemistry"),
        ("Physics", "Physics"),
        ("Chemistry", "Chemistry"),
        ("Mathematics", "Mathematics"),
        ("Statistics", "Statistics"),
        ("Environmental Science", "Environmental Science"),
    ]),
    ("Arts & Humanities", [
        ("Bachelor of Arts (BA)", "Bachelor of Arts (BA)"),
        ("English", "English"),
        ("Economics", "Economics"),
        ("Psychology", "Psychology"),
        ("Journalism and Mass Communication", "Journalism and Mass Communication"),
        ("Social Work", "Social Work"),
        ("Political Science", "Political Science"),
        ("Sociology", "Sociology"),
    ]),
    ("Law", [
        ("Bachelor of Laws (LL.B)", "Bachelor of Laws (LL.B)"),
        ("BA LL.B", "BA LL.B"),
        ("BBA LL.B", "BBA LL.B"),
        ("B.Com LL.B", "B.Com LL.B"),
    ]),
    ("Education", [
        ("Bachelor of Education (B.Ed)", "Bachelor of Education (B.Ed)"),
        ("Bachelor of Elementary Education (B.El.Ed)", "Bachelor of Elementary Education (B.El.Ed)"),
    ]),
    ("Agriculture", [
        ("Bachelor of Science in Agriculture (B.Sc Agriculture)", "Bachelor of Science in Agriculture (B.Sc Agriculture)"),
        ("Horticulture", "Horticulture"),
        ("Forestry", "Forestry"),
        ("Dairy Technology", "Dairy Technology"),
    ]),
    ("Other Programmes", [
        ("Bachelor of Social Work (BSW)", "Bachelor of Social Work (BSW)"),
        ("Bachelor of Library and Information Science (B.Lib.I.Sc)", "Bachelor of Library and Information Science (B.Lib.I.Sc)"),
        ("Bachelor of Travel and Tourism", "Bachelor of Travel and Tourism"),
        ("Other Undergraduate Programme", "Other Undergraduate Programme"),
        ("__custom__", "Other / Custom department"),
    ]),
]


class CollegeStudentForm(forms.ModelForm):
    avg_score = forms.DecimalField(required=False, min_value=0, max_value=100)
    attendance_pct = forms.DecimalField(required=False, min_value=0, max_value=100)

    class Meta:
        model = CollegeStudent
        fields = ["name", "department", "avg_score", "attendance_pct"]
        widgets = {
            "avg_score": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.1"}),
            "attendance_pct": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.1"}),
        }


class CollegeStudentAccountForm(forms.Form):
    username = forms.CharField(max_length=150, label="Username")
    password = forms.CharField(min_length=8, widget=forms.PasswordInput, label="Temporary password")
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, required=False, label="Last name")
    email = forms.EmailField(required=False)
    department = forms.CharField(max_length=120)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("That username is already in use.")
        return username


class CollegeAssessmentForm(forms.ModelForm):
    class Meta:
        model = CollegeAssessment
        fields = ["name", "department", "date", "avg_score", "status"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "avg_score": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.1"}),
        }


class FacultyForm(forms.ModelForm):
    rating = forms.DecimalField(required=False, min_value=0, max_value=5)
    classes_taken = forms.IntegerField(required=False, min_value=0)

    class Meta:
        model = Faculty
        fields = ["name", "department", "rating", "classes_taken"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": "0", "max": "10", "step": "0.1"}),
            "classes_taken": forms.NumberInput(attrs={"min": "0"}),
        }


class PlacementRecordForm(forms.ModelForm):
    students_placed = forms.IntegerField(required=False, min_value=0)
    package_lpa = forms.DecimalField(required=False, min_value=0)

    class Meta:
        model = PlacementRecord
        fields = ["company_name", "students_placed", "package_lpa", "drive_date"]
        widgets = {
            "students_placed": forms.NumberInput(attrs={"min": "0"}),
            "package_lpa": forms.NumberInput(attrs={"min": "0", "step": "0.1"}),
            "drive_date": forms.DateInput(attrs={"type": "date"}),
        }


class SyllabusCoverageForm(forms.ModelForm):
    coverage_pct = forms.IntegerField(min_value=0, max_value=100, label="Coverage percent")

    class Meta:
        model = SyllabusCoverage
        fields = ["subject", "department", "coverage_pct"]
        widgets = {
            "coverage_pct": forms.NumberInput(attrs={"min": "0", "max": "100"}),
        }


class CollegeProgramForm(forms.ModelForm):
    students_count = forms.IntegerField(required=False, min_value=0)
    status = forms.ChoiceField(choices=CollegeProgram.STATUS_CHOICES, required=False)

    class Meta:
        model = CollegeProgram
        fields = ["name", "students_count", "status"]


class DepartmentAttendanceForm(forms.ModelForm):
    name = forms.ChoiceField(choices=ACADEMIC_PROGRAMME_CHOICES, label="Academic programme or department")
    custom_department = forms.CharField(
        max_length=150,
        required=False,
        label="Custom department name",
        help_text="Fill this only when you selected Other / Custom department.",
    )
    total_students = forms.IntegerField(required=False, min_value=0)
    avg_performance = forms.DecimalField(required=False, min_value=0, max_value=100)
    assessments_taken = forms.IntegerField(required=False, min_value=0)
    training_hours = forms.IntegerField(required=False, min_value=0)

    class Meta:
        model = Department
        fields = ["code", "name", "total_students", "attendance_pct", "avg_performance", "assessments_taken", "training_hours"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("name") == "__custom__":
            custom_name = (cleaned.get("custom_department") or "").strip()
            if not custom_name:
                self.add_error("custom_department", "Enter the custom department name.")
            else:
                cleaned["name"] = custom_name
        return cleaned


class CollegeInvoiceForm(forms.ModelForm):
    status = forms.ChoiceField(choices=AdminInvoice.STATUS_CHOICES, required=False)

    class Meta:
        model = AdminInvoice
        fields = ["invoice_no", "amount", "issued_date", "status"]
        widgets = {"issued_date": forms.DateInput(attrs={"type": "date"})}


class CollegeQuickReportForm(forms.ModelForm):
    class Meta:
        model = CollegeQuickReport
        fields = ["title"]


class OnlineTestForm(forms.ModelForm):
    college = forms.ModelChoiceField(queryset=CollegeProfile.objects.none(), required=True)
    external_url = forms.URLField(required=False, help_text="Optional Testmoz URL")
    opens_at = forms.DateTimeField(input_formats=["%Y-%m-%dT%H:%M"])
    closes_at = forms.DateTimeField(input_formats=["%Y-%m-%dT%H:%M"])

    class Meta:
        model = OnlineTest
        fields = ["college", "title", "instructions", "external_url", "opens_at", "closes_at", "duration_minutes"]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 3}),
            "external_url": forms.URLInput(attrs={"placeholder": "https://testmoz.com/your-assessment"}),
            "opens_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "closes_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "duration_minutes": forms.NumberInput(attrs={"min": "1", "max": "600"}),
        }

    def clean(self):
        cleaned = super().clean()
        opens_at = cleaned.get("opens_at")
        closes_at = cleaned.get("closes_at")
        duration = cleaned.get("duration_minutes")
        if opens_at and closes_at and closes_at <= opens_at:
            self.add_error("closes_at", "The close time must be after the open time.")
        if closes_at and closes_at <= timezone.now():
            self.add_error("closes_at", "The test must close in the future.")
        if duration is not None and not 1 <= duration <= 600:
            self.add_error("duration_minutes", "Duration must be between 1 and 600 minutes.")
        return cleaned
