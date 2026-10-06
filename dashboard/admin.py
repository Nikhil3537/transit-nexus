from django.contrib import admin
from .models import (
    StudentProfile,
    Course,
    Enrollment,
    AttendanceRecord,
    Assessment,
    Strength,
    AreaToImprove,
    ActivityLog,
    Assignment,
    Certificate,
    Message,
    CalendarEvent,
    Payment,
    Skill,
)

admin.site.register(StudentProfile)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(AttendanceRecord)
admin.site.register(Assessment)
admin.site.register(Strength)
admin.site.register(AreaToImprove)
admin.site.register(ActivityLog)
admin.site.register(Assignment)
admin.site.register(Certificate)
admin.site.register(Message)
admin.site.register(CalendarEvent)
admin.site.register(Payment)
admin.site.register(Skill)
