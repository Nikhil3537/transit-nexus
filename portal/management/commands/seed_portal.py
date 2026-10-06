from datetime import date, timedelta, time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from portal.models import (
    AdminProfile, PartnerCollege, SupportTicket, AdminProject, SyllabusUpdate,
    TopProgram, AdminScheduleItem,
    CollegeProfile, Department, CollegeTrendPoint, CollegeQuickReport,
    TrainerProfile, Batch, TrainerAssessment, PendingTask, TrainerTrendPoint,
    CompanyProfile, Candidate, CompanyInterview,
    AdminStudentRecord, AdminAttendanceSummary, AdminInvoice, Announcement,
    CollegeStudent, CollegeAssessment, CollegeProgram, PlacementRecord,
    Faculty, SyllabusCoverage, CollegeNotification,
    BatchAttendanceEntry, TrainerAssignment, TrainerStudent, QuestionBankItem,
    TrainerCalendarEvent,
    JobDrive, Offer,
)


def _make_user(username, first, last, password):
    user, created = User.objects.get_or_create(
        username=username, defaults={"first_name": first, "last_name": last, "email": f"{username}@example.com"}
    )
    if created:
        user.set_password(password)
        user.save()
    return user, created


class Command(BaseCommand):
    help = "Seed demo data for the Admin, College, Trainer, and Company dashboards."

    def handle(self, *args, **options):
        today = date.today()

        # ---------------- ADMIN ----------------
        admin_user, created = _make_user("Transit_admin", "Admin", "User", "admin123")
        if created:
            admin_user.is_staff = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created user 'Transit_admin' / password 'admin123'"))

        admin_profile, _ = AdminProfile.objects.get_or_create(user=admin_user)
        admin_profile.active_trainings = 76
        admin_profile.assessments_conducted = 162
        admin_profile.colleges_onboarded_this_month = 5
        admin_profile.students_enrolled_this_month = 1245
        admin_profile.assessments_taken_this_month = 62
        admin_profile.placements_this_month = 87
        admin_profile.save()

        PartnerCollege.objects.all().delete()
        SupportTicket.objects.all().delete()
        AdminProject.objects.all().delete()
        SyllabusUpdate.objects.all().delete()
        TopProgram.objects.all().delete()
        AdminScheduleItem.objects.all().delete()
        AdminStudentRecord.objects.all().delete()
        AdminAttendanceSummary.objects.all().delete()
        AdminInvoice.objects.all().delete()
        Announcement.objects.all().delete()

        college_rows = [
            ("ABC Engineering College", 2350, 8, 345000, "active"),
            ("XYZ Institute of Technology", 1890, 6, 220500, "active"),
            ("PQR Degree College", 1250, 5, 175000, "payment_due"),
            ("LMN University", 3450, 10, 480000, "active"),
            ("RST College of Engineering", 2100, 7, 270230, "active"),
            ("UVW Institute", 1503, 4, 154500, "payment_due"),
            ("GHI College", 2000, 6, 199000, "active"),
            ("JKL Polytechnic", 1000, 3, 75000, "active"),
        ]
        for name, students, programs, pending, status in college_rows:
            PartnerCollege.objects.create(
                name=name, students_count=students, active_programs=programs,
                pending_payment=pending, status=status,
            )

        ticket_rows = [
            ("TKT-1256", "PQR Degree College", "Assessment login issue", "High", "Open"),
            ("TKT-1255", "XYZ Institute", "Payment receipt not generated", "Medium", "In Progress"),
            ("TKT-1254", "ABC Engineering", "Unable to upload student data", "High", "Open"),
            ("TKT-1253", "LMN University", "Interview schedule conflict", "Low", "Resolved"),
            ("TKT-1252", "UVW Institute", "Syllabus content update request", "Medium", "In Progress"),
        ]
        for code, college, issue, priority, status in ticket_rows:
            SupportTicket.objects.create(ticket_code=code, college_name=college, issue=issue, priority=priority, status=status)

        project_rows = [
            ("Aptitude Training Program", "ABC Engineering College", 500000, 325000, "In Progress"),
            ("Python Development Program", "XYZ Institute of Technology", 400000, 280000, "In Progress"),
            ("Soft Skills Enhancement", "PQR Degree College", 250000, 190000, "In Progress"),
            ("Full Stack Development", "LMN University", 600000, 435000, "In Progress"),
            ("Data Science Program", "RST College of Engineering", 450000, 260000, "On Hold"),
        ]
        for name, college, budget, spent, status in project_rows:
            AdminProject.objects.create(name=name, college_name=college, budget=budget, spent=spent, status=status)

        syllabus_rows = [
            ("Aptitude Training", "Quantitative Aptitude", "ABC Engineering College", today - timedelta(days=5), "Admin"),
            ("Python Programming", "Python Basics to Advanced", "XYZ Institute of Technology", today - timedelta(days=6), "Trainer"),
            ("Web Development", "HTML, CSS, JS", "PQR Degree College", today - timedelta(days=7), "Admin"),
        ]
        for program, course, college, dt, by in syllabus_rows:
            SyllabusUpdate.objects.create(program=program, course=course, college_name=college, updated_date=dt, updated_by=by)

        program_rows = [
            ("Aptitude Training", 2850), ("Python Programming", 2420), ("Web Development", 1980),
            ("Soft Skills Training", 1750), ("DBMS Training", 1543),
        ]
        for name, count in program_rows:
            TopProgram.objects.create(name=name, students_count=count)

        schedule_rows = [
            ("assessment", "Python Programming Test", "ABC Engineering College", today + timedelta(days=1)),
            ("assessment", "Aptitude Assessment", "XYZ Institute of Technology", today + timedelta(days=2)),
            ("assessment", "Web Development Test", "PQR Degree College", today + timedelta(days=3)),
            ("assessment", "DBMS Assessment", "LMN University", today + timedelta(days=4)),
            ("interview", "Technical Interview Drive", "ABC Engineering College", today + timedelta(days=1)),
            ("interview", "HR Interview Round", "XYZ Institute of Technology", today + timedelta(days=3)),
            ("interview", "Final Placement Interviews", "LMN University", today + timedelta(days=6)),
            ("interview", "Aptitude + HR Round", "RST College of Engineering", today + timedelta(days=8)),
        ]
        for kind, title, college, dt in schedule_rows:
            AdminScheduleItem.objects.create(kind=kind, title=title, college_name=college, date=dt)

        student_rows = [
            ("Ananya Sharma", "ABC Engineering College", "CSE", 89.5, "Active"),
            ("Rohan Kumar", "ABC Engineering College", "ISE", 85.0, "Active"),
            ("Neha Patel", "XYZ Institute of Technology", "CSE", 87.2, "Active"),
            ("Karthik R", "XYZ Institute of Technology", "ECE", 78.4, "Active"),
            ("Vivek Singh", "LMN University", "ME", 74.1, "Active"),
            ("Divya Menon", "PQR Degree College", "CSE", 68.9, "Active"),
        ]
        for name, college, dept, perf, status in student_rows:
            AdminStudentRecord.objects.create(name=name, college_name=college, department=dept, performance_pct=perf, status=status)

        attendance_summary_rows = [
            ("ABC Engineering College", 92.1, 2163, 187),
            ("XYZ Institute of Technology", 90.4, 1709, 181),
            ("LMN University", 88.6, 3057, 393),
            ("PQR Degree College", 84.2, 1052, 198),
        ]
        for college, pct, present, absent in attendance_summary_rows:
            AdminAttendanceSummary.objects.create(college_name=college, attendance_pct=pct, present_count=present, absent_count=absent)

        invoice_rows = [
            ("INV-2026-041", "ABC Engineering College", 345000, today - timedelta(days=10), "paid"),
            ("INV-2026-042", "XYZ Institute of Technology", 220500, today - timedelta(days=5), "due"),
            ("INV-2026-043", "PQR Degree College", 175000, today - timedelta(days=40), "overdue"),
            ("INV-2026-044", "LMN University", 480000, today - timedelta(days=8), "paid"),
        ]
        for no, college, amount, dt, status in invoice_rows:
            AdminInvoice.objects.create(invoice_no=no, college_name=college, amount=amount, issued_date=dt, status=status)

        announcement_rows = [
            ("Platform Maintenance Notice", "Scheduled maintenance this weekend from 11 PM to 2 AM.", "All Colleges", today - timedelta(days=2)),
            ("New Assessment Templates Released", "Updated aptitude assessment templates are now available.", "Trainers", today - timedelta(days=6)),
            ("Placement Season Kickoff", "Placement drives for this semester begin next month.", "All Colleges", today - timedelta(days=9)),
        ]
        for title, body, audience, dt in announcement_rows:
            Announcement.objects.create(title=title, body=body, audience=audience, posted_date=dt)

        # ---------------- COLLEGE ----------------
        college_user, created = _make_user("college_admin", "Priya", "Nair", "college123")
        if created:
            self.stdout.write(self.style.SUCCESS("Created user 'college_admin' / password 'college123'"))

        college_profile, _ = CollegeProfile.objects.get_or_create(user=college_user)
        college_profile.college_name = "ABC Engineering College"
        college_profile.location = "Bengaluru, Karnataka"
        college_profile.academic_year = "2024 - 2025"
        college_profile.semester_label = "Even Semester"
        college_profile.placement_eligible = 1245
        college_profile.save()

        college_profile.departments.all().delete()
        college_profile.trend_points.all().delete()
        college_profile.quick_reports.all().delete()
        college_profile.students.all().delete()
        college_profile.assessments.all().delete()
        college_profile.programs.all().delete()
        college_profile.placements.all().delete()
        college_profile.faculty.all().delete()
        college_profile.syllabus_coverage.all().delete()
        college_profile.notifications.all().delete()

        dept_rows = [
            ("CSE", "Computer Science", 512, 85.6, 92.1, 15, 1082),
            ("ISE", "Information Science", 398, 81.3, 90.4, 13, 872),
            ("ECE", "Electronics & Comm.", 356, 78.9, 89.2, 12, 764),
            ("ME", "Mechanical Engineering", 298, 74.6, 87.1, 11, 612),
            ("EEE", "Electrical & Electronics", 276, 72.4, 85.3, 10, 588),
            ("AI&DS", "Artificial Intelligence", 252, 88.7, 93.6, 14, 894),
            ("CE", "Civil Engineering", 150, 69.2, 82.4, 9, 504),
            ("BS", "Basic Sciences", 106, 71.5, 84.8, 8, 466),
        ]
        for code, name, students, perf, att, assess, hrs in dept_rows:
            Department.objects.create(
                college=college_profile, code=code, name=name, total_students=students,
                avg_performance=perf, attendance_pct=att, assessments_taken=assess, training_hours=hrs,
            )

        trend_rows = [("Jan", 1, 72.1), ("Feb", 2, 73.4), ("Mar", 3, 74.8), ("Apr", 4, 76.2), ("May", 5, 78.6)]
        for label, order, pct in trend_rows:
            CollegeTrendPoint.objects.create(college=college_profile, month_label=label, order=order, avg_percentage=pct)

        for title in ["Department Wise Performance Report", "Student Performance Report",
                      "Assessment Analysis Report", "Attendance Summary Report", "Training Programs Report"]:
            CollegeQuickReport.objects.create(college=college_profile, title=title)

        college_student_rows = [
            ("Ananya Sharma", "CSE", 89.5, 92.0), ("Rohan Kumar", "ISE", 85.0, 90.4),
            ("Neha Patel", "CSE", 87.2, 91.1), ("Karthik R", "ECE", 78.4, 89.2),
            ("Vivek Singh", "ME", 74.1, 87.1),
        ]
        for name, dept, score, att in college_student_rows:
            CollegeStudent.objects.create(college=college_profile, name=name, department=dept, avg_score=score, attendance_pct=att)

        college_assessment_rows = [
            ("Python Quiz 4", "CSE", today - timedelta(days=5), 92.0, "completed"),
            ("Web Dev Test 3", "ISE", today - timedelta(days=7), 78.0, "completed"),
            ("DSA Mock Test", "CSE", today - timedelta(days=9), 65.0, "completed"),
            ("Aptitude Assessment", "AI&DS", today + timedelta(days=3), None, "scheduled"),
        ]
        for name, dept, dt, score, status in college_assessment_rows:
            CollegeAssessment.objects.create(college=college_profile, name=name, department=dept, date=dt, avg_score=score, status=status)

        college_program_rows = [
            ("Aptitude Training", 2850, "active"), ("Python Programming", 2420, "active"),
            ("Web Development", 1980, "active"), ("Soft Skills Training", 1750, "completed"),
        ]
        for name, count, status in college_program_rows:
            CollegeProgram.objects.create(college=college_profile, name=name, students_count=count, status=status)

        placement_rows = [
            ("TechSolutions Pvt. Ltd.", 18, 8.5, today - timedelta(days=15)),
            ("InfoWave Systems", 12, 7.2, today - timedelta(days=30)),
            ("NextGen Analytics", 9, 9.0, today - timedelta(days=45)),
        ]
        for company, placed, package, dt in placement_rows:
            PlacementRecord.objects.create(college=college_profile, company_name=company, students_placed=placed, package_lpa=package, drive_date=dt)

        faculty_rows = [
            ("Prof. Ramesh Kumar", "CSE", 4.8, 120), ("Ms. Divya Iyer", "ISE", 4.6, 96),
            ("Dr. Neha Kapoor", "AI&DS", 4.9, 110), ("Prof. Suresh Babu", "ECE", 4.3, 88),
        ]
        for name, dept, rating, classes in faculty_rows:
            Faculty.objects.create(college=college_profile, name=name, department=dept, rating=rating, classes_taken=classes)

        coverage_rows = [
            ("Data Structures", "CSE", 92), ("Operating Systems", "CSE", 78),
            ("Digital Electronics", "ECE", 85), ("Thermodynamics", "ME", 70),
        ]
        for subject, dept, pct in coverage_rows:
            SyllabusCoverage.objects.create(college=college_profile, subject=subject, department=dept, coverage_pct=pct)

        notification_rows = [
            ("New assessment template uploaded for CSE department.", today - timedelta(days=1)),
            ("Placement drive scheduled with TechSolutions Pvt. Ltd.", today - timedelta(days=3)),
            ("Faculty performance review due end of month.", today - timedelta(days=5)),
        ]
        for msg, dt in notification_rows:
            CollegeNotification.objects.create(college=college_profile, message=msg, posted_date=dt)

        # ---------------- TRAINER ----------------
        trainer_user, created = _make_user("trainer_srinath", "Srinath", "Rao", "trainer123")
        if created:
            self.stdout.write(self.style.SUCCESS("Created user 'trainer_srinath' / password 'trainer123'"))

        trainer_profile, _ = TrainerProfile.objects.get_or_create(user=trainer_user)
        trainer_profile.assessments_created = 24
        trainer_profile.assignments_uploaded = 18
        trainer_profile.save()

        trainer_profile.batches.all().delete()
        trainer_profile.assessments.all().delete()
        trainer_profile.pending_tasks.all().delete()
        trainer_profile.trend_points.all().delete()
        trainer_profile.assignments.all().delete()
        trainer_profile.students.all().delete()
        trainer_profile.question_bank.all().delete()
        trainer_profile.calendar_events.all().delete()

        batch_rows = [
            ("Python Programming (CSE)", 65, 62, 3),
            ("Aptitude Training (MBA)", 58, 56, 2),
            ("Soft Skills (BBA)", 32, 30, 2),
            ("Web Development (ISE)", 60, 46, 14),
        ]
        batches = {}
        for name, total, present, absent in batch_rows:
            b = Batch.objects.create(trainer=trainer_profile, name=name, total_students=total, present_count=present, absent_count=absent)
            batches[name] = b

        trend_rows_t = [("Jan", 1, 70), ("Feb", 2, 75), ("Mar", 3, 79), ("Apr", 4, 85), ("May", 5, 90)]
        for label, order, pct in trend_rows_t:
            TrainerTrendPoint.objects.create(trainer=trainer_profile, month_label=label, order=order, avg_percentage=pct)

        assessment_rows = [
            ("Python Quiz 4", 85, today - timedelta(days=5)),
            ("Aptitude Test 3", 78, today - timedelta(days=7)),
            ("Communication Test 1", 82, today - timedelta(days=9)),
        ]
        for name, score, dt in assessment_rows:
            TrainerAssessment.objects.create(trainer=trainer_profile, name=name, avg_score=score, date=dt)

        task_rows = [("Grade Python Assignment", 12), ("Create Aptitude Test", 1), ("Check Soft Skills Video", 5)]
        for desc, qty in task_rows:
            PendingTask.objects.create(trainer=trainer_profile, description=desc, quantity=qty)

        for batch_name, b in batches.items():
            for i in range(3):
                BatchAttendanceEntry.objects.create(
                    batch=b, date=today - timedelta(days=(i + 1) * 3),
                    present=b.present_count - i * 2, absent=b.absent_count + i,
                )

        assignment_rows = [
            ("Python Loops & Functions", "Python Programming (CSE)", today + timedelta(days=4), 40, 65),
            ("Aptitude Practice Set 5", "Aptitude Training (MBA)", today + timedelta(days=2), 50, 58),
            ("Mock Interview Prep", "Soft Skills (BBA)", today - timedelta(days=1), 30, 32),
        ]
        for title, batch_name, due, subs, total in assignment_rows:
            TrainerAssignment.objects.create(trainer=trainer_profile, title=title, batch_name=batch_name,
                                              due_date=due, submissions_count=subs, total_students=total)

        trainer_student_rows = [
            ("Ananya Sharma", "Python Programming (CSE)", 92.0), ("Rohan Kumar", "Web Development (ISE)", 78.0),
            ("Neha Patel", "Python Programming (CSE)", 88.0), ("Karthik R", "Aptitude Training (MBA)", 74.0),
        ]
        for name, batch_name, score in trainer_student_rows:
            TrainerStudent.objects.create(trainer=trainer_profile, name=name, batch_name=batch_name, score_pct=score)

        question_bank_rows = [
            ("Python", "OOP Concepts", 45, "medium"), ("Aptitude", "Quantitative Reasoning", 60, "easy"),
            ("Web Development", "JavaScript Fundamentals", 38, "medium"), ("Soft Skills", "Group Discussion Topics", 20, "hard"),
        ]
        for subject, topic, count, diff in question_bank_rows:
            QuestionBankItem.objects.create(trainer=trainer_profile, subject=subject, topic=topic, questions_count=count, difficulty=diff)

        calendar_rows = [
            ("Python - Live Session", "Python Programming (CSE)", today + timedelta(days=1)),
            ("Aptitude Mock Test", "Aptitude Training (MBA)", today + timedelta(days=3)),
            ("Soft Skills Workshop", "Soft Skills (BBA)", today + timedelta(days=5)),
        ]
        for title, batch_name, dt in calendar_rows:
            TrainerCalendarEvent.objects.create(trainer=trainer_profile, title=title, batch_name=batch_name, date=dt)

        # ---------------- COMPANY ----------------
        company_user, created = _make_user("company_hr", "TechSolutions", "HR", "company123")
        if created:
            self.stdout.write(self.style.SUCCESS("Created user 'company_hr' / password 'company123'"))

        company_profile, _ = CompanyProfile.objects.get_or_create(user=company_user)
        company_profile.company_name = "TechSolutions Pvt. Ltd."
        company_profile.total_drives = 8
        company_profile.hired = 18
        company_profile.save()

        company_profile.candidates.all().delete()
        company_profile.interviews.all().delete()
        company_profile.job_drives.all().delete()
        company_profile.offers.all().delete()

        candidate_rows = [
            ("Ananya Sharma", "CSE", 86, 90, 92, "shortlisted"),
            ("Rohan Kumar", "ISE", 80, 88, 85, "shortlisted"),
            ("Neha Patel", "CSE", 80, 84, 87, "shortlisted"),
            ("Karthik R", "ECE", 75, 82, 83, "under_review"),
            ("Vivek Singh", "ME", 78, 80, 79, "under_review"),
        ]
        for name, dept, apt, tech, comm, shortlist in candidate_rows:
            Candidate.objects.create(company=company_profile, name=name, department=dept,
                                      aptitude_score=apt, technical_score=tech, communication_score=comm,
                                      shortlist_status=shortlist)

        interview_rows = [
            ("Ananya Sharma", "Technical Interview", today + timedelta(days=1), time(10, 0), "scheduled"),
            ("Rohan Kumar", "HR Interview", today + timedelta(days=1), time(11, 30), "scheduled"),
            ("Neha Patel", "Technical Interview", today + timedelta(days=2), time(14, 0), "scheduled"),
            ("Karthik R", "Final Round", today - timedelta(days=2), time(10, 0), "completed"),
            ("Vivek Singh", "HR Interview", today - timedelta(days=3), time(15, 0), "completed"),
        ]
        for name, itype, dt, tm, status in interview_rows:
            CompanyInterview.objects.create(company=company_profile, candidate_name=name, interview_type=itype,
                                             date=dt, time=tm, status=status)

        drive_rows = [
            ("Campus Placement Drive - ABC Engineering", "Bengaluru", today + timedelta(days=5), 15, "upcoming"),
            ("Technical Hiring Drive - XYZ Institute", "Bengaluru", today - timedelta(days=10), 10, "completed"),
            ("Walk-in Drive - LMN University", "Chennai", today + timedelta(days=1), 8, "ongoing"),
        ]
        for title, loc, dt, positions, status in drive_rows:
            JobDrive.objects.create(company=company_profile, title=title, location=loc, date=dt, positions=positions, status=status)

        offer_rows = [
            ("Karthik R", "Software Engineer", 8.5, "accepted", today - timedelta(days=5)),
            ("Vivek Singh", "Systems Analyst", 7.2, "offered", today - timedelta(days=2)),
            ("Divya Menon", "QA Engineer", 6.5, "declined", today - timedelta(days=8)),
        ]
        for name, position, package, status, dt in offer_rows:
            Offer.objects.create(company=company_profile, candidate_name=name, position=position,
                                  package_lpa=package, status=status, offer_date=dt)

        self.stdout.write(self.style.SUCCESS("Portal seed data created successfully."))
        self.stdout.write("Login accounts:")
        self.stdout.write("  Admin    -> Transit_admin / admin123")
        self.stdout.write("  College  -> college_admin / college123")
        self.stdout.write("  Trainer  -> trainer_srinath / trainer123")
        self.stdout.write("  Company  -> company_hr / company123")
