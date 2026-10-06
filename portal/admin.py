from django.contrib import admin
from .models import (
    AdminProfile, PartnerCollege, SupportTicket, AdminProject, SyllabusUpdate,
    TopProgram, AdminScheduleItem,
    CollegeProfile, Department, CollegeTrendPoint, CollegeQuickReport,
    TrainerProfile, Batch, TrainerAssessment, PendingTask, TrainerTrendPoint,
    CompanyProfile, Candidate, CompanyInterview,
    AdminStudentRecord, AdminAttendanceSummary, AdminInvoice, Announcement,
    CollegeStudent, CollegeAssessment, CollegeProgram, PlacementRecord,
    Faculty, SyllabusCoverage, CollegeNotification,
    BatchAttendanceEntry, TrainerAssignment, TrainerStudent, QuestionBankItem,
    TrainerCalendarEvent, OnlineTest, OnlineTestQuestion, OnlineTestAttempt, OnlineTestAnswer,
    JobDrive, Offer,
)

for model in [
    AdminProfile, PartnerCollege, SupportTicket, AdminProject, SyllabusUpdate,
    TopProgram, AdminScheduleItem,
    CollegeProfile, Department, CollegeTrendPoint, CollegeQuickReport,
    TrainerProfile, Batch, TrainerAssessment, PendingTask, TrainerTrendPoint,
    CompanyProfile, Candidate, CompanyInterview,
    AdminStudentRecord, AdminAttendanceSummary, AdminInvoice, Announcement,
    CollegeStudent, CollegeAssessment, CollegeProgram, PlacementRecord,
    Faculty, SyllabusCoverage, CollegeNotification,
    BatchAttendanceEntry, TrainerAssignment, TrainerStudent, QuestionBankItem,
    TrainerCalendarEvent, OnlineTest, OnlineTestQuestion, OnlineTestAttempt, OnlineTestAnswer,
    JobDrive, Offer,
]:
    admin.site.register(model)
