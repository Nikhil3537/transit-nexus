from django.db import models
from django.contrib.auth.models import User
from dashboard.models import StudentProfile


# =========================================================
# ADMIN DASHBOARD (Super Admin — platform-wide view)
# =========================================================

class AdminProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    active_trainings = models.PositiveIntegerField(default=0)
    assessments_conducted = models.PositiveIntegerField(default=0)
    open_issues = models.PositiveIntegerField(default=0)
    colleges_onboarded_this_month = models.PositiveIntegerField(default=0)
    students_enrolled_this_month = models.PositiveIntegerField(default=0)
    assessments_taken_this_month = models.PositiveIntegerField(default=0)
    placements_this_month = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Admin: {self.user.get_full_name() or self.user.username}"


class PartnerCollege(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("payment_due", "Payment Due")]

    name = models.CharField(max_length=150)
    students_count = models.PositiveIntegerField(default=0)
    active_programs = models.PositiveIntegerField(default=0)
    pending_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        ordering = ["-students_count"]
        verbose_name = "College finance summary"
        verbose_name_plural = "College finance summaries"

    def __str__(self):
        return self.name


class SupportTicket(models.Model):
    PRIORITY_CHOICES = [("High", "High"), ("Medium", "Medium"), ("Low", "Low")]
    STATUS_CHOICES = [("Open", "Open"), ("In Progress", "In Progress"), ("Resolved", "Resolved")]

    ticket_code = models.CharField(max_length=20)
    college_name = models.CharField(max_length=150)
    issue = models.CharField(max_length=200)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="Medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Open")

    class Meta:
        ordering = ["-id"]


class AdminProject(models.Model):
    STATUS_CHOICES = [("In Progress", "In Progress"), ("On Hold", "On Hold"), ("Completed", "Completed")]

    name = models.CharField(max_length=150)
    college_name = models.CharField(max_length=150)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="In Progress")

    @property
    def remaining(self):
        return self.budget - self.spent


class SyllabusUpdate(models.Model):
    program = models.CharField(max_length=150)
    course = models.CharField(max_length=150)
    college_name = models.CharField(max_length=150)
    updated_date = models.DateField()
    updated_by = models.CharField(max_length=120)

    class Meta:
        ordering = ["-updated_date"]


class TopProgram(models.Model):
    name = models.CharField(max_length=150)
    students_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-students_count"]


class AdminScheduleItem(models.Model):
    KIND_CHOICES = [("assessment", "Assessment"), ("interview", "Interview")]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    title = models.CharField(max_length=150)
    college_name = models.CharField(max_length=150)
    date = models.DateField()

    class Meta:
        ordering = ["date"]


# =========================================================
# COLLEGE DASHBOARD
# =========================================================

class CollegeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="college_profile")
    college_name = models.CharField(max_length=150, default="ABC Engineering College")
    location = models.CharField(max_length=150, default="Bengaluru, Karnataka")
    academic_year = models.CharField(max_length=20, default="2024 - 2025")
    semester_label = models.CharField(max_length=40, default="Even Semester")
    placement_eligible = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.college_name


class Department(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="departments")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=150)
    total_students = models.PositiveIntegerField(default=0)
    avg_performance = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    attendance_pct = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    assessments_taken = models.PositiveIntegerField(default=0)
    training_hours = models.PositiveIntegerField(default=0)
    attendance_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["-total_students"]

    @property
    def performance_label(self):
        if self.avg_performance >= 85:
            return "Excellent"
        if self.avg_performance >= 70:
            return "Good"
        if self.avg_performance >= 50:
            return "Average"
        return "Needs Improvement"


class CollegeTrendPoint(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="trend_points")
    month_label = models.CharField(max_length=20)
    order = models.PositiveIntegerField(default=0)
    avg_percentage = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        ordering = ["order"]


class CollegeQuickReport(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="quick_reports")
    title = models.CharField(max_length=150)


# =========================================================
# TRAINER DASHBOARD
# =========================================================

class TrainerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="trainer_profile")
    college = models.ForeignKey(CollegeProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="trainers")
    domain = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    assessments_created = models.PositiveIntegerField(default=0)
    assignments_uploaded = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Trainer: {self.user.get_full_name() or self.user.username}"


class TrainerAvailability(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="availability")
    date = models.DateField()
    is_available = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["date"]
        unique_together = [("trainer", "date")]

    def __str__(self):
        status = "Available" if self.is_available else "Not available"
        return f"{self.trainer} — {self.date} ({status})"


class Batch(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="batches")
    name = models.CharField(max_length=150)
    total_students = models.PositiveIntegerField(default=0)
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)

    @property
    def attendance_pct(self):
        total = self.present_count + self.absent_count
        if total == 0:
            return 0
        return round((self.present_count / total) * 100)


class TrainerAssessment(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="assessments")
    name = models.CharField(max_length=150)
    avg_score = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    date = models.DateField()

    class Meta:
        ordering = ["-date"]


class OnlineTest(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="online_tests")
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="online_tests", null=True, blank=True)
    title = models.CharField(max_length=160)
    instructions = models.TextField(blank=True)
    external_url = models.URLField(blank=True, default="")
    external_link_email_sent = models.BooleanField(default=False)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-opens_at"]

    def __str__(self):
        return self.title


class OnlineTestQuestion(models.Model):
    TYPE_CHOICES = [
        ("single", "Multiple choice"),
        ("multiple", "Select all that apply"),
        ("true_false", "True or false"),
        ("fill_blank", "Fill in the blank"),
        ("matching", "Matching / ordering"),
        ("numeric", "Numeric"),
        ("short", "Short answer"),
        ("essay", "Written response"),
        ("file", "File upload"),
    ]

    test = models.ForeignKey(OnlineTest, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    options = models.JSONField(default=list, blank=True)
    correct_answers = models.JSONField(default=list, blank=True)
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class OnlineTestAttempt(models.Model):
    STATUS_CHOICES = [("in_progress", "In progress"), ("submitted", "Submitted")]

    test = models.ForeignKey(OnlineTest, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="online_test_attempts")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="in_progress")
    score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    possible_points = models.PositiveIntegerField(default=0)
    pending_manual_review = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["test", "student"], name="unique_online_test_attempt")]
        ordering = ["-started_at"]


class OnlineTestAnswer(models.Model):
    attempt = models.ForeignKey(OnlineTestAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(OnlineTestQuestion, on_delete=models.CASCADE, related_name="answers")
    response = models.JSONField(default=list, blank=True)
    uploaded_file = models.FileField(upload_to="test_answers/%Y/%m/", null=True, blank=True)
    points_awarded = models.PositiveIntegerField(default=0)
    reviewed = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="unique_answer_per_test_question")]


class PendingTask(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="pending_tasks")
    description = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)


class TrainerTrendPoint(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="trend_points")
    month_label = models.CharField(max_length=20)
    order = models.PositiveIntegerField(default=0)
    avg_percentage = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        ordering = ["order"]


# =========================================================
# COMPANY DASHBOARD
# =========================================================

class CompanyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company_profile")
    company_name = models.CharField(max_length=150, default="TechSolutions Pvt. Ltd.")
    total_drives = models.PositiveIntegerField(default=0)
    hired = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.company_name


class Candidate(models.Model):
    SHORTLIST_STATUS = [("shortlisted", "Shortlisted"), ("under_review", "Under Review"), ("not_selected", "Not Selected")]

    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name="candidates")
    name = models.CharField(max_length=120)
    department = models.CharField(max_length=20)
    aptitude_score = models.PositiveIntegerField(default=0)
    technical_score = models.PositiveIntegerField(default=0)
    communication_score = models.PositiveIntegerField(default=0)
    shortlist_status = models.CharField(max_length=20, choices=SHORTLIST_STATUS, default="under_review")

    @property
    def overall_score(self):
        return round((self.aptitude_score + self.technical_score + self.communication_score) / 3)

    class Meta:
        ordering = ["-id"]


class CompanyInterview(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name="interviews")
    candidate_name = models.CharField(max_length=120)
    interview_type = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")

    class Meta:
        ordering = ["date", "time"]


# =========================================================
# ADMIN — extra sub-page models
# =========================================================

class AdminStudentRecord(models.Model):
    """Lightweight cross-college student record for the Admin > Students Management page."""
    name = models.CharField(max_length=120)
    college_name = models.CharField(max_length=150)
    department = models.CharField(max_length=150)
    performance_pct = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    status = models.CharField(max_length=20, default="Active")

    class Meta:
        ordering = ["-id"]


class AdminAttendanceSummary(models.Model):
    college_name = models.CharField(max_length=150)
    attendance_pct = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    present_count = models.PositiveIntegerField(default=0)
    absent_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-attendance_pct"]


class AdminInvoice(models.Model):
    STATUS_CHOICES = [("paid", "Paid"), ("due", "Due"), ("overdue", "Overdue")]

    invoice_no = models.CharField(max_length=30)
    college_name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    issued_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="due")

    class Meta:
        ordering = ["-issued_date"]


class Announcement(models.Model):
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=300)
    audience = models.CharField(max_length=60, default="All Colleges")
    posted_date = models.DateField()

    class Meta:
        ordering = ["-posted_date"]


# =========================================================
# COLLEGE — extra sub-page models
# =========================================================

class CollegeStudent(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="students")
    name = models.CharField(max_length=120)
    department = models.CharField(max_length=20)
    avg_score = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    attendance_pct = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        ordering = ["-avg_score"]


class CollegeAssessment(models.Model):
    STATUS_CHOICES = [("completed", "Completed"), ("scheduled", "Scheduled")]

    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="assessments")
    name = models.CharField(max_length=150)
    department = models.CharField(max_length=20)
    date = models.DateField()
    avg_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")

    class Meta:
        ordering = ["-date"]


class CollegeProgram(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("completed", "Completed")]

    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=150)
    students_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")


class PlacementRecord(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="placements")
    company_name = models.CharField(max_length=150)
    students_placed = models.PositiveIntegerField(default=0)
    package_lpa = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    drive_date = models.DateField()

    class Meta:
        ordering = ["-drive_date"]


class Faculty(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="faculty")
    name = models.CharField(max_length=120)
    department = models.CharField(max_length=20)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    classes_taken = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-rating"]


class SyllabusCoverage(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="syllabus_coverage")
    subject = models.CharField(max_length=150)
    department = models.CharField(max_length=20)
    coverage_pct = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-coverage_pct"]


class CollegeNotification(models.Model):
    college = models.ForeignKey(CollegeProfile, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=250)
    posted_date = models.DateField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-posted_date"]


# =========================================================
# TRAINER — extra sub-page models
# =========================================================

class BatchAttendanceEntry(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="attendance_entries")
    date = models.DateField()
    present = models.PositiveIntegerField(default=0)
    absent = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date"]


class TrainerAssignment(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=150)
    batch_name = models.CharField(max_length=150)
    due_date = models.DateField()
    submissions_count = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["due_date"]


class TrainerStudent(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="students")
    name = models.CharField(max_length=120)
    batch_name = models.CharField(max_length=150)
    score_pct = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        ordering = ["-score_pct"]


class QuestionBankItem(models.Model):
    DIFFICULTY_CHOICES = [("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")]

    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="question_bank")
    subject = models.CharField(max_length=120)
    topic = models.CharField(max_length=150)
    questions_count = models.PositiveIntegerField(default=0)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="medium")


class TrainerCalendarEvent(models.Model):
    trainer = models.ForeignKey(TrainerProfile, on_delete=models.CASCADE, related_name="calendar_events")
    title = models.CharField(max_length=150)
    batch_name = models.CharField(max_length=150)
    date = models.DateField()

    class Meta:
        ordering = ["date"]


# =========================================================
# COMPANY — extra sub-page models
# =========================================================

class JobDrive(models.Model):
    STATUS_CHOICES = [("upcoming", "Upcoming"), ("ongoing", "Ongoing"), ("completed", "Completed")]

    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name="job_drives")
    title = models.CharField(max_length=150)
    location = models.CharField(max_length=120)
    date = models.DateField()
    positions = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="upcoming")

    class Meta:
        ordering = ["date"]


class Offer(models.Model):
    STATUS_CHOICES = [("offered", "Offered"), ("accepted", "Accepted"), ("declined", "Declined")]

    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name="offers")
    candidate_name = models.CharField(max_length=120)
    position = models.CharField(max_length=120)
    package_lpa = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="offered")
    offer_date = models.DateField()

    class Meta:
        ordering = ["-offer_date"]
