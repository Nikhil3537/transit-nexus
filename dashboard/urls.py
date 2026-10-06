from django.urls import path
from . import views

urlpatterns = [
    path("student-colleges/", views.student_colleges_view, name="student_colleges"),
    path("student-dashboard/", views.student_dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("register/", views.student_register_view, name="student_register"),
    path("logout/", views.logout_view, name="logout"),

    path("profile/", views.profile_view, name="profile"),
    path("courses/", views.courses_view, name="courses"),
    path("live-classes/", views.live_classes_view, name="live_classes"),
    path("attendance/", views.attendance_view, name="attendance"),
    path("assessments/", views.assessments_view, name="assessments"),
    path("trainers/", views.trainer_directory_view, name="trainers"),
    path("tests/", views.scheduled_tests_view, name="scheduled_tests"),
    path("tests/<int:test_id>/", views.take_online_test_view, name="take_online_test"),
    path("tests/answers/<int:answer_id>/file/", views.download_test_answer_file, name="download_test_answer_file"),
    path("results-reports/", views.results_reports_view, name="results_reports"),
    path("assignments/", views.assignments_view, name="assignments"),
    path("certificates/", views.certificates_view, name="certificates"),
    path("certificates/<int:certificate_id>/download/", views.download_certificate_view, name="download_certificate"),
    path("learning-path/", views.learning_path_view, name="learning_path"),
    path("skill-progress/", views.skill_progress_view, name="skill_progress"),
    path("messages/", views.messages_view, name="messages_list"),
    path("calendar/", views.calendar_view, name="calendar_view"),
    path("payments/", views.payments_view, name="payments"),
]
