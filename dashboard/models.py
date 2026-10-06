from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    college = models.ForeignKey("portal.CollegeProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="student_accounts")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    semester_label = models.CharField(max_length=100, default="Current Semester")
    semester_range = models.CharField(max_length=100, default="May - Aug 2025")
    department = models.CharField(max_length=120, blank=True)
    total_learning_hours = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Course(models.Model):
    name = models.CharField(max_length=120)
    icon_class = models.CharField(max_length=60, default="fa-book")

    def __str__(self):
        return self.name


class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    avg_score = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    highest_score = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    modules_completed = models.PositiveIntegerField(default=0)
    modules_total = models.PositiveIntegerField(default=1)
    is_completed = models.BooleanField(default=False)

    @property
    def performance_label(self):
        if self.avg_score >= 85:
            return "Excellent"
        if self.avg_score >= 70:
            return "Good"
        if self.avg_score >= 50:
            return "Average"
        return "Needs Improvement"

    @property
    def progress_percent(self):
        if self.modules_total == 0:
            return 0
        return round((self.modules_completed / self.modules_total) * 100)

    def __str__(self):
        return f"{self.student} - {self.course}"


class AttendanceRecord(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="attendance_records")
    month_label = models.CharField(max_length=20)
    order = models.PositiveIntegerField(default=0)
    total_classes = models.PositiveIntegerField(default=0)
    present = models.PositiveIntegerField(default=0)
    absent = models.PositiveIntegerField(default=0)
    late = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    @property
    def percentage(self):
        if self.total_classes == 0:
            return 0
        return round((self.present / self.total_classes) * 100)


class Assessment(models.Model):
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("pending", "Pending"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="assessments")
    name = models.CharField(max_length=150)
    subject = models.CharField(max_length=120)
    score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")

    class Meta:
        ordering = ["-date"]

    @property
    def performance_label(self):
        if self.score is None:
            return "-"
        if self.score >= 90:
            return "Excellent"
        if self.score >= 75:
            return "Good"
        if self.score >= 50:
            return "Average"
        return "Needs Improvement"


class Strength(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="strengths")
    title = models.CharField(max_length=120)

    def __str__(self):
        return self.title


class AreaToImprove(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="improvement_areas")
    title = models.CharField(max_length=120)

    def __str__(self):
        return self.title


class ActivityLog(models.Model):
    ICON_CHOICES = [
        ("submit", "Submitted"),
        ("complete", "Completed"),
        ("attend", "Attended"),
        ("download", "Downloaded"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="activities")
    description = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=20, choices=ICON_CHOICES, default="submit")
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ["-timestamp"]


class Assignment(models.Model):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("in_progress", "In Progress"),
        ("not_started", "Not Started"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=150)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started")
    submitted_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["due_date"]


class Certificate(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="certificates")
    title = models.CharField(max_length=150)
    issuer = models.CharField(max_length=120, default="Transit Nexus")
    issued_date = models.DateField()
    credential_id = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-issued_date"]


class Message(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="messages")
    sender_name = models.CharField(max_length=120)
    sender_role = models.CharField(max_length=60, default="Instructor")
    subject = models.CharField(max_length=150)
    body = models.TextField()
    timestamp = models.DateTimeField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]


class CalendarEvent(models.Model):
    EVENT_TYPES = [
        ("class", "Live Class"),
        ("exam", "Exam"),
        ("assignment", "Assignment Due"),
        ("workshop", "Workshop"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="events")
    title = models.CharField(max_length=150)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default="class")
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    instructor = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["date", "start_time"]


class Payment(models.Model):
    STATUS_CHOICES = [
        ("paid", "Paid"),
        ("due", "Due"),
        ("overdue", "Overdue"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="payments")
    description = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="due")

    class Meta:
        ordering = ["-due_date"]


class Skill(models.Model):
    CATEGORY_CHOICES = [
        ("technical", "Technical"),
        ("aptitude", "Aptitude"),
        ("soft", "Soft Skill"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=120)
    proficiency_percent = models.PositiveIntegerField(default=0)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="technical")

    class Meta:
        ordering = ["-proficiency_percent"]
