from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),

    # Admin
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-colleges/", views.admin_colleges, name="admin_colleges"),
    path("admin-colleges/<int:college_id>/", views.admin_college_detail, name="admin_college_detail"),
    path("admin-trainers/", views.admin_trainers, name="admin_trainers"),
    path("admin-students/", views.admin_students, name="admin_students"),
    path("admin-programs/", views.admin_programs, name="admin_programs"),
    path("admin-assessments/", views.admin_assessments, name="admin_assessments"),
    path("admin-interviews/", views.admin_interviews, name="admin_interviews"),
    path("admin-projects/", views.admin_projects, name="admin_projects"),
    path("admin-syllabus/", views.admin_syllabus, name="admin_syllabus"),
    path("admin-schedules/", views.admin_schedules, name="admin_schedules"),
    path("admin-attendance/", views.admin_attendance, name="admin_attendance"),
    path("admin-payments/", views.admin_payments, name="admin_payments"),
    path("admin-reports/", views.admin_reports, name="admin_reports"),
    path("admin-support/", views.admin_support, name="admin_support"),
    path("admin-users/", views.admin_users, name="admin_users"),
    path("admin-bulk-import/", views.bulk_import, name="bulk_import"),
    path("admin-communications/", views.admin_communications, name="admin_communications"),
    path("admin-settings/", views.admin_settings, name="admin_settings"),

    # College
    path("college-dashboard/", views.college_dashboard, name="college_dashboard"),
    path("college/departments/", views.college_departments, name="college_departments"),
    path("college/students/", views.college_students, name="college_students"),
    path("college/assessments/", views.college_assessments, name="college_assessments"),
    path("college/attendance/", views.college_attendance, name="college_attendance"),
    path("college/programs/", views.college_programs, name="college_programs"),
    path("college/payments/", views.college_payments, name="college_payments"),
    path("college/upload/<slug:dataset>/", views.college_csv_upload, name="college_csv_upload"),
    path("college/placements/", views.college_placements, name="college_placements"),
    path("college/reports/", views.college_reports, name="college_reports"),
    path("college/faculty/", views.college_faculty, name="college_faculty"),
    path("college/syllabus/", views.college_syllabus, name="college_syllabus"),
    path("college/notifications/", views.college_notifications, name="college_notifications"),
    path("college/settings/", views.college_settings, name="college_settings"),

    # Trainer
    path("trainer-dashboard/", views.trainer_dashboard, name="trainer_dashboard"),
    path("trainer/batches/", views.trainer_batches, name="trainer_batches"),
    path("trainer/attendance/", views.trainer_attendance, name="trainer_attendance"),
    path("trainer/assessments/", views.trainer_assessments, name="trainer_assessments"),
    path("trainer/assessments/<int:test_id>/results/", views.trainer_test_results, name="trainer_test_results"),
    path("trainer/assessments/<int:test_id>/answers/<int:answer_id>/review/", views.trainer_review_test_answer, name="trainer_review_test_answer"),
    path("trainer/assignments/", views.trainer_assignments, name="trainer_assignments"),
    path("trainer/students/", views.trainer_students, name="trainer_students"),
    path("trainer/question-bank/", views.trainer_question_bank, name="trainer_question_bank"),
    path("trainer/reports/", views.trainer_reports, name="trainer_reports"),
    path("trainer/calendar/", views.trainer_calendar, name="trainer_calendar"),
    path("trainer/settings/", views.trainer_settings, name="trainer_settings"),

    # Company
    path("company-dashboard/", views.company_dashboard, name="company_dashboard"),
    path("company/search/", views.company_search, name="company_search"),
    path("company/shortlisted/", views.company_shortlisted, name="company_shortlisted"),
    path("company/interviews/", views.company_interviews, name="company_interviews"),
    path("company/drives/", views.company_drives, name="company_drives"),
    path("company/offers/", views.company_offers, name="company_offers"),
    path("company/reports/", views.company_reports, name="company_reports"),
    path("company/profile/", views.company_profile_view, name="company_profile"),
    path("company/settings/", views.company_settings, name="company_settings"),
]
