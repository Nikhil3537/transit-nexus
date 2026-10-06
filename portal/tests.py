from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta

from dashboard.models import Certificate, StudentProfile
from .models import (
    AdminInvoice, AdminProfile, AdminStudentRecord, CollegeAssessment, CollegeProfile, CollegeProgram,
    CollegeQuickReport, CollegeStudent, CompanyProfile, Department, Faculty, PartnerCollege,
    OnlineTest, OnlineTestAnswer, OnlineTestAttempt, OnlineTestQuestion,
    PlacementRecord, SyllabusCoverage, TrainerAvailability, TrainerProfile,
)

COLLEGE_UPLOAD_PAGE_TEST_NAMES = {
    "students": "college_students",
    "programs": "college_programs",
    "assessments": "college_assessments",
    "attendance": "college_attendance",
    "payments": "college_payments",
    "placements": "college_placements",
    "syllabus": "college_syllabus",
    "faculty": "college_faculty",
    "reports": "college_reports",
}


class BulkImportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="import-admin", password="test-pass", is_staff=True)
        self.client.force_login(self.admin)

    def upload(self, role, content):
        file = SimpleUploadedFile("records.csv", content.encode("utf-8"), content_type="text/csv")
        return self.client.post(reverse("bulk_import"), {"role": role, "file": file})

    def test_imports_each_account_type_as_pending(self):
        college_user = User.objects.create_user(username="bulk-college-admin", password="test-pass")
        CollegeProfile.objects.create(user=college_user, college_name="North College")
        cases = [
            ("students", "username,password,first_name,last_name,email,college_name,department\nstudent-1,pass,Sam,Student,sam@example.com,North College,CSE\n"),
            ("colleges", "username,password,first_name,last_name,email,college_name,location\ncollege-1,pass,Casey,College,casey@example.com,North College,Delhi\n"),
            ("trainers", "username,password,first_name,last_name,email\ntrainer-1,pass,Taylor,Trainer,taylor@example.com\n"),
            ("companies", "username,password,first_name,last_name,email,company_name\ncompany-1,pass,Alex,Company,alex@example.com,Example Ltd\n"),
        ]
        for role, content in cases:
            with self.subTest(role=role):
                response = self.upload(role, content)
                self.assertRedirects(response, reverse("bulk_import"))
                username = {"students": "student-1", "colleges": "college-1", "trainers": "trainer-1", "companies": "company-1"}[role]
                user = User.objects.get(username=username)
                self.assertFalse(user.is_active)
        self.assertTrue(StudentProfile.objects.filter(
            user__username="student-1", college__college_name="North College", department="CSE",
        ).exists())
        self.assertTrue(AdminStudentRecord.objects.filter(name="Sam Student", college_name="North College").exists())
        self.assertTrue(CollegeProfile.objects.filter(user__username="college-1", location="Delhi").exists())
        self.assertTrue(PartnerCollege.objects.filter(name="North College").exists())
        self.assertTrue(TrainerProfile.objects.filter(user__username="trainer-1").exists())
        self.assertTrue(CompanyProfile.objects.filter(user__username="company-1", company_name="Example Ltd").exists())

    def test_invalid_file_does_not_partially_import(self):
        college_user = User.objects.create_user(username="bulk-invalid-college-admin", password="test-pass")
        CollegeProfile.objects.create(user=college_user, college_name="North College")
        User.objects.create_user(username="already-used", password="test-pass")
        content = (
            "username,password,first_name,last_name,email,college_name,department\n"
            "new-student,pass,New,Student,new@example.com,North College,CSE\n"
            "already-used,pass,Existing,Student,existing@example.com,North College,CSE\n"
        )
        response = self.upload("students", content)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertFalse(User.objects.filter(username="new-student").exists())

    def test_admin_can_approve_all_imported_accounts_at_once(self):
        pending_one = User.objects.create_user(username="pending-one", password="test-pass", is_active=False)
        pending_two = User.objects.create_user(username="pending-two", password="test-pass", is_active=False)
        response = self.client.post(reverse("admin_users"), {"action": "approve_pending"})
        self.assertRedirects(response, reverse("admin_users"))
        pending_one.refresh_from_db()
        pending_two.refresh_from_db()
        self.assertTrue(pending_one.is_active)
        self.assertTrue(pending_two.is_active)

    def test_admin_can_create_student_with_assigned_department(self):
        college_user = User.objects.create_user(username="dept-college-admin", password="test-pass")
        CollegeProfile.objects.create(user=college_user, college_name="North College")

        response = self.client.post(reverse("admin_users"), {
            "action": "create",
            "role": "student",
            "username": "dept-student",
            "password": "test-pass-123",
            "first_name": "Asha",
            "last_name": "Student",
            "email": "asha@example.com",
            "college_name": "North College",
            "department": "CSE",
        })

        self.assertRedirects(response, reverse("admin_users"))
        user = User.objects.get(username="dept-student")
        self.assertTrue(StudentProfile.objects.filter(
            user=user,
            college__college_name="North College",
            department="CSE",
        ).exists())
        self.assertTrue(AdminStudentRecord.objects.filter(
            name="Asha Student",
            college_name="North College",
            department="CSE",
        ).exists())


class StudentCollegeFlowTests(TestCase):
    def test_student_can_self_register_with_valid_college_and_department(self):
        CollegeProfile.objects.create(user=User.objects.create_user(username="north-college-register-admin", password="test-pass"), college_name="North College")

        response = self.client.post(reverse("student_register"), {
            "username": "new-student-self",
            "password": "student-pass-123",
            "first_name": "New",
            "last_name": "Student",
            "email": "newstudent@example.com",
            "college_name": "North College",
            "department": "Engineering",
        })

        self.assertRedirects(response, reverse("login"))
        user = User.objects.get(username="new-student-self")
        self.assertFalse(user.is_active)
        self.assertTrue(StudentProfile.objects.filter(
            user=user,
            college__college_name="North College",
            department="Engineering",
        ).exists())

    def test_student_can_self_register_with_only_allowed_department_categories(self):
        CollegeProfile.objects.create(
            user=User.objects.create_user(username="north-college-departments-admin", password="test-pass"),
            college_name="North College",
        )

        for index, (department, canonical_name) in enumerate([
            ("Engineering", "Engineering"),
            ("Arts and Commerce", "Arts & Commerce"),
            ("Pharmacy", "Pharmacy"),
            ("Allied Health Science", "Allied Health Science"),
            ("Architecture and Design", "Architecture & Design"),
            ("Nursing", "Nursing"),
            ("Management", "Management"),
        ], start=1):
            with self.subTest(department=department):
                username = f"dept-{index}-{department.lower().replace(' ', '-').replace('&', 'and')[:20]}"
                response = self.client.post(reverse("student_register"), {
                    "username": username,
                    "password": "student-pass-123",
                    "first_name": "Dept",
                    "last_name": "Student",
                    "email": f"{username}@example.com",
                    "college_name": "North College",
                    "department": department,
                })
                self.assertRedirects(response, reverse("login"))
                user = User.objects.get(username=username)
                self.assertTrue(StudentProfile.objects.filter(
                    user=user,
                    college__college_name="North College",
                    department=canonical_name,
                ).exists())

    def test_student_login_redirects_to_assigned_college_list(self):
        college_user = User.objects.create_user(username="college-admin-flow", password="test-pass")
        college = CollegeProfile.objects.create(user=college_user, college_name="North College")
        student_user = User.objects.create_user(username="student-login-flow", password="test-pass")
        StudentProfile.objects.create(user=student_user, college=college)

        response = self.client.post(reverse("login"), {
            "username": "student-login-flow",
            "password": "test-pass",
        })

        self.assertRedirects(response, reverse("student_colleges"))

        self.client.force_login(student_user)
        page = self.client.get(reverse("student_colleges"))
        self.assertContains(page, "North College")

    def test_admin_rejects_invalid_student_college_department_pairing(self):
        admin_user = User.objects.create_user(username="admin-invalid-pair", password="test-pass", is_staff=True, is_superuser=True)
        AdminProfile.objects.create(user=admin_user)
        college_user = User.objects.create_user(username="college-admin-invalid", password="test-pass")
        CollegeProfile.objects.create(user=college_user, college_name="North College")
        self.client.force_login(admin_user)

        response = self.client.post(reverse("admin_users"), {
            "action": "create",
            "role": "student",
            "username": "invalid-pair-student",
            "password": "test-pass-123",
            "first_name": "Bad",
            "last_name": "Student",
            "email": "bad@example.com",
            "college_name": "North College",
            "department": "Not A Real Department",
        })

        self.assertRedirects(response, reverse("admin_users"))
        self.assertFalse(User.objects.filter(username="invalid-pair-student").exists())

    def test_admin_users_can_filter_students_by_college(self):
        admin_user = User.objects.create_user(username="admin-filter-students", password="test-pass", is_staff=True, is_superuser=True)
        AdminProfile.objects.create(user=admin_user)
        north = CollegeProfile.objects.create(user=User.objects.create_user(username="north-college-admin", password="test-pass"), college_name="North College")
        south = CollegeProfile.objects.create(user=User.objects.create_user(username="south-college-admin", password="test-pass"), college_name="South College")

        north_student = User.objects.create_user(username="north-student", password="test-pass")
        south_student = User.objects.create_user(username="south-student", password="test-pass")
        StudentProfile.objects.create(user=north_student, college=north, department="CSE")
        StudentProfile.objects.create(user=south_student, college=south, department="ECE")

        self.client.force_login(admin_user)
        response = self.client.get(reverse("admin_users"), {"college_filter": "North College"})

        self.assertContains(response, "north-student")
        self.assertNotContains(response, "south-student")

    def test_admin_users_tab_filters_by_account_type(self):
        admin_user = User.objects.create_user(username="admin-role-tab", password="test-pass", is_staff=True, is_superuser=True)
        AdminProfile.objects.create(user=admin_user)
        self.client.force_login(admin_user)

        college_admin_user = User.objects.create_user(username="college-tab-admin", password="test-pass")
        CollegeProfile.objects.create(user=college_admin_user, college_name="Tab College")

        trainer_user = User.objects.create_user(username="trainer-tab-user", password="test-pass")
        TrainerProfile.objects.create(user=trainer_user, college=CollegeProfile.objects.create(user=User.objects.create_user(username="other-tab-college-admin", password="test-pass"), college_name="Other Tab College"))

        company_user = User.objects.create_user(username="company-tab-user", password="test-pass")
        CompanyProfile.objects.create(user=company_user, company_name="Tab Company")

        student_user = User.objects.create_user(username="student-tab-user", password="test-pass")
        StudentProfile.objects.create(user=student_user, college=CollegeProfile.objects.create(user=User.objects.create_user(username="student-tab-college-admin", password="test-pass"), college_name="Student Tab College"), department="CSE")

        response = self.client.get(reverse("admin_users"), {"role_tab": "student"})
        self.assertContains(response, "student-tab-user")
        self.assertNotContains(response, "college-tab-admin")
        self.assertNotContains(response, "trainer-tab-user")
        self.assertNotContains(response, "company-tab-user")


class CollegeProgramManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="college-admin", password="test-pass")
        self.college = CollegeProfile.objects.create(user=self.user, college_name="North College")
        self.client.force_login(self.user)

    def test_create_program_from_college_page(self):
        response = self.client.post(reverse("college_programs"), {
            "name": "Data Analytics",
            "students_count": "42",
            "status": "active",
        })
        self.assertRedirects(response, reverse("college_programs"))
        program = CollegeProgram.objects.get(college=self.college, name="Data Analytics")
        self.assertEqual(program.students_count, 42)
        self.assertEqual(program.status, "active")

    def test_edit_program_from_college_page(self):
        program = CollegeProgram.objects.create(college=self.college, name="Old Name", students_count=10)
        response = self.client.post(reverse("college_programs"), {
            "program_id": str(program.pk),
            "name": "Updated Name",
            "students_count": "25",
            "status": "completed",
        })
        self.assertRedirects(response, reverse("college_programs"))
        program.refresh_from_db()
        self.assertEqual(program.name, "Updated Name")
        self.assertEqual(program.students_count, 25)
        self.assertEqual(program.status, "completed")

    def test_cannot_edit_another_colleges_program(self):
        other_user = User.objects.create_user(username="other-college", password="test-pass")
        other_college = CollegeProfile.objects.create(user=other_user, college_name="Other College")
        program = CollegeProgram.objects.create(college=other_college, name="Private Program")
        response = self.client.post(reverse("college_programs"), {
            "program_id": str(program.pk),
            "name": "Tampered Name",
            "students_count": "1",
            "status": "active",
        })
        self.assertEqual(response.status_code, 200)
        program.refresh_from_db()
        self.assertEqual(program.name, "Private Program")


class CollegePageRecordManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="college-record-admin", password="test-pass")
        self.college = CollegeProfile.objects.create(user=self.user, college_name="North College")
        self.client.force_login(self.user)

    def test_each_record_type_has_its_own_page_and_student_list_is_scoped(self):
        other_user = User.objects.create_user(username="separate-college", password="test-pass")
        other_college = CollegeProfile.objects.create(user=other_user, college_name="Other College")
        CollegeStudent.objects.create(college=other_college, name="Other College Student", department="ECE")
        for route in ["college_students", "college_assessments", "college_faculty", "college_placements"]:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Add")
                if route == "college_students":
                    self.assertNotContains(response, "Other College Student")

    def test_college_account_cannot_view_other_college_students(self):
        other_user = User.objects.create_user(username="private-college", password="test-pass")
        other_college = CollegeProfile.objects.create(user=other_user, college_name="Private College")
        CollegeStudent.objects.create(college=other_college, name="Private Student", department="ECE")
        response = self.client.get(reverse("college_students"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Private Student")

    def test_college_dashboard_reflects_students_and_assessments(self):
        student_user = User.objects.create_user(username="dashboard-student", password="test-pass")
        StudentProfile.objects.create(user=student_user, college=self.college)
        CollegeAssessment.objects.create(
            college=self.college, name="Dashboard Assessment", department="CSE", date="2026-10-01",
        )
        response = self.client.get(reverse("college_dashboard"))
        self.assertEqual(response.context["total_students"], 1)
        self.assertEqual(response.context["total_assessments"], 1)

    def test_college_admin_can_update_location_academic_year_and_semester(self):
        response = self.client.post(reverse("college_settings"), {
            "college_name": "North College",
            "location": "Bangalore",
            "academic_year": "2026 - 2027",
            "semester_label": "Odd Semester",
        })
        self.assertRedirects(response, reverse("college_settings"))
        self.college.refresh_from_db()
        self.assertEqual(self.college.location, "Bangalore")
        self.assertEqual(self.college.academic_year, "2026 - 2027")
        self.assertEqual(self.college.semester_label, "Odd Semester")

    def test_college_page_lists_student_accounts_assigned_to_that_college(self):
        student_user = User.objects.create_user(username="college-student", password="test-pass", first_name="Asha", last_name="Student", email="asha@example.com")
        StudentProfile.objects.create(user=student_user, college=self.college)
        other_user = User.objects.create_user(username="other-college-student", password="test-pass", first_name="Nina", last_name="Student", email="nina@example.com")
        StudentProfile.objects.create(user=other_user, college=CollegeProfile.objects.create(user=User.objects.create_user(username="other-college-student-owner", password="test-pass"), college_name="Other College"))
        response = self.client.get(reverse("college_students"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Asha Student")
        self.assertNotContains(response, "Nina Student")

    def test_college_students_can_be_filtered_by_department(self):
        first_user = User.objects.create_user(username="cse-student", password="test-pass", first_name="CSE")
        second_user = User.objects.create_user(username="ece-student", password="test-pass", first_name="ECE")
        StudentProfile.objects.create(user=first_user, college=self.college, department="CSE")
        StudentProfile.objects.create(user=second_user, college=self.college, department="ECE")
        response = self.client.get(reverse("college_students"), {"department": "CSE"})
        self.assertContains(response, "CSE")
        self.assertContains(response, "cse-student")
        self.assertNotContains(response, "ece-student")

    def test_college_student_department_filter_uses_matching_admin_record(self):
        student_user = User.objects.create_user(
            username="department-assigned-student", password="test-pass", first_name="Asha", last_name="Student",
        )
        StudentProfile.objects.create(user=student_user, college=self.college)
        AdminStudentRecord.objects.create(
            name="Asha Student", college_name=self.college.college_name, department="CSE",
        )

        response = self.client.get(reverse("college_students"), {"department": "CSE"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Computer Science and Engineering")
        self.assertContains(response, "department-assigned-student")
        self.assertNotContains(response, "Unassigned (1)")

    def test_college_department_overview_uses_student_departments_when_summary_rows_are_missing(self):
        first_user = User.objects.create_user(username="dept-overview-one", password="test-pass", first_name="Dept")
        second_user = User.objects.create_user(username="dept-overview-two", password="test-pass", first_name="Overview")
        StudentProfile.objects.create(user=first_user, college=self.college, department="CSE")
        StudentProfile.objects.create(user=second_user, college=self.college, department="ECE")

        response = self.client.get(reverse("college_departments"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Computer Science and Engineering")
        self.assertContains(response, "Electronics and Communication Engineering")
        self.assertNotContains(response, "No departments added yet.")

    def test_college_department_overview_refreshes_counts_from_student_assignments(self):
        Department.objects.create(
            college=self.college, code="CSE", name="Computer Science and Engineering", total_students=25,
        )
        student_user = User.objects.create_user(username="updated-dept-student", password="test-pass")
        StudentProfile.objects.create(user=student_user, college=self.college, department="CSE")

        response = self.client.get(reverse("college_departments"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["departments"][0].total_students, 1)

    def test_college_department_overview_uses_admin_department_records_without_double_counting_accounts(self):
        student_user = User.objects.create_user(
            username="admin-record-student", password="test-pass", first_name="Asha", last_name="Student",
        )
        StudentProfile.objects.create(user=student_user, college=self.college)
        AdminStudentRecord.objects.create(
            name="Asha Student", college_name=self.college.college_name,
            department="CSE", performance_pct=82,
        )
        AdminStudentRecord.objects.create(
            name="Orphan Record", college_name=self.college.college_name, department="ECE",
        )

        response = self.client.get(reverse("college_departments"))

        self.assertEqual(response.status_code, 200)
        departments = response.context["departments"]
        self.assertEqual(len(departments), 1)
        self.assertEqual(departments[0].name, "Computer Science and Engineering")
        self.assertEqual(departments[0].total_students, 1)

    def test_college_admin_can_create_student_account_for_own_college(self):
        response = self.client.post(reverse("college_students"), {
            "action": "create_account",
            "username": "new-college-student",
            "password": "student-pass-123",
            "first_name": "New",
            "last_name": "Student",
            "email": "new.student@example.com",
            "department": "Computer Science",
        })
        self.assertRedirects(response, reverse("college_students"))
        student_user = User.objects.get(username="new-college-student")
        self.assertTrue(StudentProfile.objects.filter(user=student_user, college=self.college).exists())
        self.assertTrue(AdminStudentRecord.objects.filter(
            college_name=self.college.college_name, name="New Student", department="Computer Science",
        ).exists())

    def test_college_admin_cannot_reuse_existing_student_username(self):
        User.objects.create_user(username="existing-student", password="test-pass")
        response = self.client.post(reverse("college_students"), {
            "action": "create_account", "username": "existing-student",
            "password": "student-pass-123", "first_name": "Duplicate", "department": "CSE",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "That username is already in use.")

    def test_create_records_from_their_individual_pages(self):
        cases = [
            ("college_students", {"name": "Riya Student", "department": "CSE", "avg_score": "85.5", "attendance_pct": "92.0"}),
            ("college_assessments", {"name": "Midterm", "department": "CSE", "date": "2026-10-15", "avg_score": "78.5", "status": "scheduled"}),
            ("college_faculty", {"name": "Asha Trainer", "department": "CSE", "rating": "4.5", "classes_taken": "18"}),
            ("college_placements", {"company_name": "Example Ltd", "students_placed": "12", "package_lpa": "8.5", "drive_date": "2026-10-20"}),
        ]
        for route, data in cases:
            with self.subTest(route=route):
                response = self.client.post(reverse(route), data)
                self.assertRedirects(response, reverse(route))
        self.assertTrue(CollegeStudent.objects.filter(college=self.college, name="Riya Student").exists())
        self.assertTrue(CollegeAssessment.objects.filter(college=self.college, name="Midterm").exists())
        self.assertTrue(Faculty.objects.filter(college=self.college, name="Asha Trainer").exists())
        self.assertTrue(PlacementRecord.objects.filter(college=self.college, company_name="Example Ltd").exists())

    def test_create_attendance_invoice_and_report_from_college_pages(self):
        attendance_response = self.client.post(reverse("college_attendance"), {
            "code": "CSE", "name": "Computer Science", "total_students": "40",
            "attendance_pct": "92", "avg_performance": "80", "assessments_taken": "3",
            "training_hours": "12",
        })
        self.assertRedirects(attendance_response, reverse("college_attendance"))
        self.assertTrue(Department.objects.filter(college=self.college, code="CSE").exists())

        invoice_response = self.client.post(reverse("college_payments"), {
            "invoice_no": "INV-COLLEGE-1", "amount": "1500", "issued_date": "2026-10-01", "status": "due",
        })
        self.assertRedirects(invoice_response, reverse("college_payments"))
        self.assertTrue(AdminInvoice.objects.filter(college_name=self.college.college_name, invoice_no="INV-COLLEGE-1").exists())

        report_response = self.client.post(reverse("college_reports"), {"title": "Attendance Summary"})
        self.assertRedirects(report_response, reverse("college_reports"))
        self.assertTrue(CollegeQuickReport.objects.filter(college=self.college, title="Attendance Summary").exists())

    def test_update_and_delete_actions_are_scoped_to_current_college(self):
        other_user = User.objects.create_user(username="other-college-record-admin", password="test-pass")
        other_college = CollegeProfile.objects.create(user=other_user, college_name="Other College")
        student = CollegeStudent.objects.create(college=other_college, name="Protected Student", department="ECE")
        response = self.client.post(reverse("college_students"), {
            "record_id": str(student.pk), "name": "Modified Student", "department": "CSE",
            "avg_score": "90", "attendance_pct": "100",
        })
        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        self.assertEqual(student.name, "Protected Student")
        response = self.client.post(reverse("college_students"), {
            "record_id": str(student.pk), "action": "delete",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CollegeStudent.objects.filter(pk=student.pk).exists())


class CollegeSyllabusCoverageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="syllabus-admin", password="test-pass")
        self.college = CollegeProfile.objects.create(user=self.user, college_name="North College")
        self.client.force_login(self.user)

    def test_create_and_update_subject_coverage(self):
        response = self.client.post(reverse("college_syllabus"), {
            "subject": "Mathematics", "department": "CSE", "coverage_pct": "75",
        })
        self.assertRedirects(response, reverse("college_syllabus"))
        subject = SyllabusCoverage.objects.get(college=self.college, subject="Mathematics")
        self.assertEqual(subject.coverage_pct, 75)

        response = self.client.post(reverse("college_syllabus"), {
            "record_id": str(subject.pk), "subject": "Mathematics", "department": "CSE", "coverage_pct": "90",
        })
        self.assertRedirects(response, reverse("college_syllabus"))
        subject.refresh_from_db()
        self.assertEqual(subject.coverage_pct, 90)

    def test_coverage_must_be_between_zero_and_one_hundred(self):
        response = self.client.post(reverse("college_syllabus"), {
            "subject": "Mathematics", "department": "CSE", "coverage_pct": "120",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SyllabusCoverage.objects.filter(college=self.college).exists())

    def test_faculty_page_shows_coverage_and_hides_other_college_data(self):
        SyllabusCoverage.objects.create(
            college=self.college, subject="Mathematics", department="CSE", coverage_pct=75,
        )
        other_user = User.objects.create_user(username="other-syllabus-admin", password="test-pass")
        other_college = CollegeProfile.objects.create(user=other_user, college_name="Other College")
        SyllabusCoverage.objects.create(
            college=other_college, subject="Private Subject", department="ECE", coverage_pct=30,
        )
        response = self.client.get(reverse("college_faculty"))
        self.assertContains(response, "Mathematics")
        self.assertContains(response, "75%")
        self.assertNotContains(response, "Private Subject")


class PlatformCollegeWorkspaceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="platform-admin", password="test-pass", is_staff=True)
        self.client.force_login(self.admin)
        self.college_user = User.objects.create_user(username="workspace-college", password="test-pass")
        self.college = CollegeProfile.objects.create(
            user=self.college_user, college_name="North College", location="Bengaluru",
        )

    def test_platform_dashboard_and_college_index_use_college_accounts(self):
        dashboard = self.client.get(reverse("admin_dashboard"))
        self.assertContains(dashboard, "Platform Operations Dashboard")
        self.assertContains(dashboard, "Transit Training and Recruitment Partner")
        listing = self.client.get(reverse("admin_colleges"))
        self.assertContains(listing, "North College")
        self.assertContains(listing, reverse("admin_college_detail", args=[self.college.pk]))
        self.assertNotContains(listing, "Partner Colleges")

    def test_college_index_counts_uploaded_student_accounts(self):
        student_user = User.objects.create_user(username="index-student", password="test-pass")
        StudentProfile.objects.create(user=student_user, college=self.college)
        listing = self.client.get(reverse("admin_colleges"))
        college_row = next(item for item in listing.context["colleges"] if item["profile"] == self.college)
        self.assertEqual(college_row["students_count"], 1)
        self.assertContains(listing, "1")

    def test_platform_payment_total_keeps_unlinked_finance_summaries(self):
        PartnerCollege.objects.create(name="North College", pending_payment=125)
        PartnerCollege.objects.create(name="Legacy College", pending_payment=375)
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.context["total_pending_payment"], 500)
        self.assertEqual(response.context["total_colleges"], 1)
        self.assertEqual(PartnerCollege._meta.verbose_name_plural, "College finance summaries")

    def test_admin_dashboard_lists_college_trainers_with_availability(self):
        trainer_user = User.objects.create_user(username="admin-trainer", password="test-pass", first_name="Priya", last_name="Rao", email="priya@example.com")
        trainer = TrainerProfile.objects.create(user=trainer_user, college=self.college)
        TrainerAvailability.objects.create(trainer=trainer, date=timezone.localdate(), is_available=False, note="Workshop day")
        response = self.client.get(reverse("admin_dashboard"))
        self.assertContains(response, "College Trainer Availability")
        self.assertContains(response, "Priya Rao")
        self.assertContains(response, "North College")
        self.assertContains(response, "Not available")
        self.assertContains(response, "Workshop day")

    def test_platform_admin_role_takes_precedence_over_misassigned_college_profile(self):
        placeholder = CollegeProfile.objects.create(user=self.admin, college_name="Platform Placeholder")
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("admin_dashboard"))
        listing = self.client.get(reverse("admin_colleges"))
        self.assertContains(listing, "North College")
        self.assertNotContains(listing, "Platform Placeholder")
        self.assertEqual(self.client.get(reverse("admin_college_detail", args=[placeholder.pk])).status_code, 404)

    def test_college_credentials_cannot_access_platform_admin_routes(self):
        self.client.force_login(self.college_user)
        for route in ["admin_dashboard", "admin_colleges", "admin_users", "admin_payments"]:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 403)
        self.assertEqual(self.client.get(reverse("college_dashboard")).status_code, 200)

    def test_platform_credentials_cannot_access_college_only_routes(self):
        CollegeProfile.objects.create(user=self.admin, college_name="Platform Placeholder")
        for route in ["college_dashboard", "college_students", "college_programs", "college_settings"]:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 403)
        self.assertFalse(CollegeStudent.objects.filter(college__user=self.admin).exists())

    def test_platform_admin_can_create_college_account_with_institution_details(self):
        response = self.client.post(reverse("admin_users"), {
            "action": "create", "role": "college", "username": "new-college-login",
            "password": "temporary-pass-123", "first_name": "College", "last_name": "Admin",
            "college_name": "East College", "college_location": "Mysuru",
        })
        self.assertRedirects(response, reverse("admin_users"))
        created_college = CollegeProfile.objects.get(user__username="new-college-login")
        self.assertEqual(created_college.college_name, "East College")
        self.assertEqual(created_college.location, "Mysuru")
        self.assertTrue(PartnerCollege.objects.filter(name="East College").exists())

    def test_platform_admin_must_name_college_when_creating_college_credentials(self):
        response = self.client.post(reverse("admin_users"), {
            "action": "create", "role": "college", "username": "unnamed-college-login",
            "password": "temporary-pass-123",
        })
        self.assertRedirects(response, reverse("admin_users"))
        self.assertFalse(User.objects.filter(username="unnamed-college-login").exists())

    def test_workspace_groups_only_selected_colleges_records(self):
        CollegeStudent.objects.create(college=self.college, name="North Student", department="CSE")
        CollegeProgram.objects.create(college=self.college, name="North Program")
        CollegeAssessment.objects.create(
            college=self.college, name="North Assessment", department="CSE", date="2026-10-15",
        )
        Department.objects.create(college=self.college, code="CSE", name="Computer Science", attendance_pct=91)
        AdminInvoice.objects.create(
            invoice_no="NORTH-001", college_name="North College", amount=1000, issued_date="2026-09-01",
        )
        CollegeQuickReport.objects.create(college=self.college, title="North Report")

        other_user = User.objects.create_user(username="other-workspace-college", password="test-pass")
        other_college = CollegeProfile.objects.create(user=other_user, college_name="South College")
        CollegeStudent.objects.create(college=other_college, name="South Student", department="ECE")

        response = self.client.get(reverse("admin_college_detail", args=[self.college.pk]))
        self.assertEqual(response.status_code, 200)
        for visible_record in ["North Student", "North Program", "North Assessment", "NORTH-001", "North Report"]:
            self.assertContains(response, visible_record)
        self.assertNotContains(response, "South Student")

    def test_college_page_lists_uploaded_student_accounts(self):
        student_user = User.objects.create_user(
            username="uploaded-student", first_name="Uploaded", last_name="Student",
        )
        StudentProfile.objects.create(user=student_user, college=self.college)
        AdminStudentRecord.objects.create(
            name="Uploaded Student", college_name=self.college.college_name,
            department="Computer Science and Engineering", status="Pending",
        )
        response = self.client.get(reverse("admin_college_detail", args=[self.college.pk]))
        self.assertContains(response, "Uploaded Student")
        self.assertContains(response, "Computer Science and Engineering")
        self.assertContains(response, "Account")
        self.assertEqual(response.context["total_students"], 1)


class CollegeCSVUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="csv-college", password="test-pass")
        self.college = CollegeProfile.objects.create(user=self.user, college_name="CSV College")
        self.client.force_login(self.user)

    def upload(self, dataset, csv_text):
        file = SimpleUploadedFile("records.csv", csv_text.encode("utf-8"), content_type="text/csv")
        return self.client.post(reverse("college_csv_upload", args=[dataset]), {"file": file})

    def test_each_college_data_page_shows_its_csv_uploader(self):
        for dataset, route in COLLEGE_UPLOAD_PAGE_TEST_NAMES.items():
            with self.subTest(dataset=dataset):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Download template")
                self.assertContains(response, reverse("college_csv_upload", args=[dataset]))

    def test_templates_and_uploads_exist_for_each_college_data_type(self):
        cases = {
            "students": ("name,department,avg_score,attendance_pct\nMina,CSE,85,90\n", CollegeStudent, "name", "Mina"),
            "programs": ("name,students_count,status\nPython,35,active\n", CollegeProgram, "name", "Python"),
            "assessments": ("name,department,date,avg_score,status\nQuiz,CSE,2026-10-20,80,completed\n", CollegeAssessment, "name", "Quiz"),
            "attendance": ("code,name,total_students,attendance_pct\nCSE,Computer Science,40,92\n", Department, "code", "CSE"),
            "payments": ("invoice_no,amount,issued_date,status\nINV-1,1500,2026-09-01,due\n", AdminInvoice, "invoice_no", "INV-1"),
            "placements": ("company_name,students_placed,package_lpa,drive_date\nExample Ltd,4,8.5,2026-10-25\n", PlacementRecord, "company_name", "Example Ltd"),
            "syllabus": ("subject,department,coverage_pct\nDatabases,CSE,70\n", SyllabusCoverage, "subject", "Databases"),
            "faculty": ("name,department,rating,classes_taken\nAsha,CSE,4.5,10\n", Faculty, "name", "Asha"),
            "reports": ("title\nAttendance Summary\n", CollegeQuickReport, "title", "Attendance Summary"),
        }
        for dataset, (csv_text, model, field, value) in cases.items():
            with self.subTest(dataset=dataset):
                template = self.client.get(reverse("college_csv_upload", args=[dataset]), {"template": "1"})
                self.assertEqual(template.status_code, 200)
                self.assertEqual(template["Content-Type"].split(";")[0], "text/csv")
                response = self.upload(dataset, csv_text)
                self.assertRedirects(response, reverse(COLLEGE_UPLOAD_PAGE_TEST_NAMES[dataset]))
                if model is AdminInvoice:
                    record = model.objects.get(invoice_no=value)
                    self.assertEqual(record.college_name, self.college.college_name)
                else:
                    record = model.objects.get(college=self.college, **{field: value})
                    self.assertEqual(record.college_id, self.college.pk)

    def test_invalid_csv_does_not_import_any_rows(self):
        response = self.upload(
            "assessments",
            "name,department,date,avg_score,status\nValid,CSE,2026-10-20,80,completed\nBad,CSE,not-a-date,70,completed\n",
        )
        self.assertRedirects(response, reverse("college_assessments"))
        self.assertFalse(CollegeAssessment.objects.filter(college=self.college).exists())

    def test_college_csv_upload_cannot_set_another_colleges_owner(self):
        other_user = User.objects.create_user(username="other-csv-college", password="test-pass")
        other_college = CollegeProfile.objects.create(user=other_user, college_name="Other CSV College")
        response = self.upload("students", "name,department\nOwned Here,CSE\n")
        self.assertRedirects(response, reverse("college_students"))
        self.assertTrue(CollegeStudent.objects.filter(college=self.college, name="Owned Here").exists())
        self.assertFalse(CollegeStudent.objects.filter(college=other_college).exists())

    def test_other_college_cannot_use_csv_upload_for_this_college(self):
        admin = User.objects.create_user(username="csv-platform", password="test-pass", is_staff=True)
        self.client.force_login(admin)
        response = self.upload("students", "name,department\nNot Allowed,CSE\n")
        self.assertEqual(response.status_code, 403)


class OnlineTestWorkflowTests(TestCase):
    def setUp(self):
        self.trainer_user = User.objects.create_user(username="test-trainer", password="test-pass")
        self.trainer = TrainerProfile.objects.create(user=self.trainer_user)
        self.college_user = User.objects.create_user(username="test-college-admin", password="test-pass")
        self.college = CollegeProfile.objects.create(user=self.college_user, college_name="Test College")
        self.student_user = User.objects.create_user(username="test-student", password="test-pass")
        self.student = StudentProfile.objects.create(user=self.student_user, college=self.college)

    def create_test(self, closes_in=120):
        now = timezone.localtime()
        online_test = OnlineTest.objects.create(
            trainer=self.trainer,
            college=self.college,
            title="Python Fundamentals",
            instructions="Answer all questions.",
            opens_at=now - timedelta(minutes=2),
            closes_at=now + timedelta(minutes=closes_in),
            duration_minutes=30,
        )
        question = OnlineTestQuestion.objects.create(
            test=online_test, prompt="2 + 2?", question_type="single",
            options=["3", "4"], correct_answers=["4"], points=5, order=0,
        )
        return online_test, question

    def test_trainer_creates_scheduled_test_and_objective_question(self):
        self.client.force_login(self.trainer_user)
        now = timezone.localtime()
        response = self.client.post(reverse("trainer_assessments"), {
            "college": str(self.college.pk),
            "title": "Algebra Test", "instructions": "Show your work.",
            "opens_at": (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M"),
            "closes_at": (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": "25",
            "question_prompt": ["Solve 2 + 2", "", ""],
            "question_type": ["single", "single", "single"],
            "question_options": ["3\n4", "", ""],
            "question_answers": ["4", "", ""],
            "question_points": ["2", "1", "1"],
        })
        online_test = OnlineTest.objects.get(trainer=self.trainer, title="Algebra Test")
        self.assertRedirects(response, reverse("trainer_test_results", args=[online_test.pk]))
        self.assertEqual(online_test.questions.count(), 1)
        self.assertEqual(online_test.questions.get().correct_answers, ["4"])

    def test_trainer_can_schedule_external_testmoz_assessment_without_local_questions(self):
        self.client.force_login(self.trainer_user)
        now = timezone.localtime()
        response = self.client.post(reverse("trainer_assessments"), {
            "college": str(self.college.pk),
            "title": "Testmoz Assessment",
            "instructions": "Complete this assessment on Testmoz.",
            "external_url": "https://testmoz.com/123456",
            "opens_at": (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M"),
            "closes_at": (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": "30",
        })
        online_test = OnlineTest.objects.get(trainer=self.trainer, title="Testmoz Assessment")
        self.assertRedirects(response, reverse("trainer_test_results", args=[online_test.pk]))
        self.assertEqual(online_test.external_url, "https://testmoz.com/123456")
        self.assertEqual(online_test.questions.count(), 0)

    def test_students_only_see_tests_assigned_to_their_college(self):
        target_test, _ = self.create_test()
        other_user = User.objects.create_user(username="other-test-college-admin", password="test-pass")
        other_college = CollegeProfile.objects.create(user=other_user, college_name="Other Test College")
        other_test = OnlineTest.objects.create(
            trainer=self.trainer, college=other_college, title="Other College Test",
            opens_at=timezone.now() - timedelta(minutes=1), closes_at=timezone.now() + timedelta(hours=1),
        )
        self.client.force_login(self.student_user)
        listing = self.client.get(reverse("scheduled_tests"))
        self.assertContains(listing, target_test.title)
        self.assertNotContains(listing, other_test.title)
        self.assertEqual(self.client.get(reverse("take_online_test", args=[other_test.pk])).status_code, 404)

    def test_external_testmoz_assessments_display_for_students(self):
        external_test = OnlineTest.objects.create(
            trainer=self.trainer,
            college=self.college,
            title="External Testmoz Quiz",
            instructions="Take this assessment on Testmoz.",
            opens_at=timezone.now() - timedelta(minutes=5),
            closes_at=timezone.now() + timedelta(days=1),
            duration_minutes=30,
            external_url="https://testmoz.com/123456",
        )
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("scheduled_tests"))
        self.assertContains(response, "External Testmoz Quiz")
        self.assertContains(response, "Open Testmoz assessment")
        self.assertContains(response, "https://testmoz.com/123456")

    def test_student_can_download_only_their_own_certificate(self):
        certificate = Certificate.objects.create(
            student=self.student,
            title="Python Foundations",
            issuer="Transit Nexus",
            issued_date=date(2026, 9, 30),
            credential_id="TN-123",
        )
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("download_certificate", args=[certificate.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Python Foundations", response.content.decode())
        self.assertIn("attachment; filename=\"certificate-", response["Content-Disposition"])

    def test_trainer_directory_shows_date_specific_availability(self):
        target_date = date(2026, 10, 15)
        trainer_user = User.objects.create_user(username="availability-trainer", password="test-pass")
        trainer = TrainerProfile.objects.create(user=trainer_user, college=self.college)
        TrainerAvailability.objects.create(trainer=trainer, date=target_date, is_available=False, note="Booked for workshop")
        self.client.force_login(self.student_user)
        response = self.client.get(reverse("trainers"), {"date": target_date.isoformat()})
        self.assertContains(response, "Not available")
        self.assertContains(response, "Booked for workshop")

    def test_trainer_can_manage_availability_for_specific_dates(self):
        target_date = date(2026, 10, 20)
        self.client.force_login(self.trainer_user)
        response = self.client.post(reverse("trainer_settings"), {
            "action": "availability",
            "availability_date": target_date.isoformat(),
            "is_available": "false",
            "availability_note": "Workshop day",
        })
        self.assertRedirects(response, reverse("trainer_settings"))
        availability = TrainerAvailability.objects.get(trainer=self.trainer, date=target_date)
        self.assertFalse(availability.is_available)
        self.assertEqual(availability.note, "Workshop day")

    def test_student_attempt_scores_and_result_stays_hidden_until_close(self):
        online_test, question = self.create_test()
        self.client.force_login(self.student_user)
        start = self.client.get(reverse("take_online_test", args=[online_test.pk]))
        self.assertEqual(start.status_code, 200)
        attempt = OnlineTestAttempt.objects.get(test=online_test, student=self.student)
        response = self.client.post(reverse("take_online_test", args=[online_test.pk]), {
            f"answer_{question.pk}": "4",
        })
        self.assertRedirects(response, reverse("take_online_test", args=[online_test.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 5)
        self.assertEqual(attempt.status, "submitted")
        before_release = self.client.get(reverse("take_online_test", args=[online_test.pk]))
        self.assertContains(before_release, "result will be released after")
        self.assertNotContains(before_release, "Result: 5")
        online_test.closes_at = timezone.now() - timedelta(seconds=1)
        online_test.save(update_fields=["closes_at"])
        after_release = self.client.get(reverse("take_online_test", args=[online_test.pk]))
        self.assertContains(after_release, "Result: 5.00 / 5")

    def test_server_rejects_answers_submitted_after_deadline(self):
        online_test, question = self.create_test()
        online_test.duration_minutes = 1
        online_test.save(update_fields=["duration_minutes"])
        self.client.force_login(self.student_user)
        self.client.get(reverse("take_online_test", args=[online_test.pk]))
        attempt = OnlineTestAttempt.objects.get(test=online_test, student=self.student)
        attempt.started_at = timezone.now() - timedelta(minutes=3)
        attempt.save(update_fields=["started_at"])
        response = self.client.post(reverse("take_online_test", args=[online_test.pk]), {
            f"answer_{question.pk}": "4",
        })
        self.assertRedirects(response, reverse("take_online_test", args=[online_test.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, "submitted")
        self.assertEqual(attempt.score, 0)
        answer = OnlineTestAnswer.objects.get(attempt=attempt, question=question)
        self.assertEqual(answer.response, [])

    def test_essay_result_waits_for_trainer_review_after_close(self):
        online_test, _ = self.create_test(closes_in=-1)
        essay = OnlineTestQuestion.objects.create(
            test=online_test, prompt="Explain your approach", question_type="essay",
            points=10, order=1,
        )
        attempt = OnlineTestAttempt.objects.create(
            test=online_test, student=self.student, status="submitted",
            submitted_at=timezone.now(), score=0, possible_points=15, pending_manual_review=1,
        )
        answer = OnlineTestAnswer.objects.create(
            attempt=attempt, question=essay, response=["I explained it."],
        )
        self.client.force_login(self.trainer_user)
        results = self.client.get(reverse("trainer_test_results", args=[online_test.pk]))
        self.assertContains(results, "I explained it.")
        review = self.client.post(
            reverse("trainer_review_test_answer", args=[online_test.pk, answer.pk]),
            {"points_awarded": "8"},
        )
        self.assertRedirects(review, reverse("trainer_test_results", args=[online_test.pk]))
        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 8)
        self.assertEqual(attempt.pending_manual_review, 0)

    def test_students_cannot_create_tests_and_trainers_cannot_take_them_as_students(self):
        online_test, _ = self.create_test()
        self.client.force_login(self.student_user)
        self.assertEqual(self.client.get(reverse("trainer_assessments")).status_code, 403)
        self.client.force_login(self.trainer_user)
        self.assertEqual(self.client.get(reverse("scheduled_tests")).status_code, 403)
        self.assertEqual(self.client.get(reverse("take_online_test", args=[online_test.pk])).status_code, 403)
