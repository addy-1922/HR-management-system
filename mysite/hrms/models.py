from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


class Department(models.Model):
    """A department that groups employees together."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def employee_count(self):
        return self.employees.count()


class Employee(models.Model):
    """An employee of the organisation."""

    class Gender(models.TextChoices):
        MALE = 'Male', 'Male'
        FEMALE = 'Female', 'Female'
        OTHER = 'Other', 'Other'

    class EmploymentStatus(models.TextChoices):
        ACTIVE = 'Active', 'Active'
        ON_LEAVE = 'On Leave', 'On Leave'
        RESIGNED = 'Resigned', 'Resigned'
        TERMINATED = 'Terminated', 'Terminated'

    employee_id = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique employee identifier, e.g. EMP-001",
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^[0-9+\-\s()]+$', 'Enter a valid phone number.')],
        blank=True,
    )
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.OTHER)
    address = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )
    designation = models.CharField(max_length=100)
    joining_date = models.DateField(default=timezone.localdate)
    salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    employment_status = models.CharField(
        max_length=12,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
    )
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['employee_id']

    def __str__(self):
        return self.full_name

    def clean(self):
        super().clean()
        if self.joining_date and self.date_of_birth and self.joining_date < self.date_of_birth:
            raise ValidationError('Joining date cannot be before the date of birth.')


class LeaveRequest(models.Model):
    """A leave request submitted by an employee."""

    class LeaveType(models.TextChoices):
        SICK = 'Sick Leave', 'Sick Leave'
        CASUAL = 'Casual Leave', 'Casual Leave'
        ANNUAL = 'Annual Leave', 'Annual Leave'
        MATERNITY = 'Maternity Leave', 'Maternity Leave'
        PATERNITY = 'Paternity Leave', 'Paternity Leave'
        UNPAID = 'Unpaid Leave', 'Unpaid Leave'

    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        APPROVED = 'Approved', 'Approved'
        REJECTED = 'Rejected', 'Rejected'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    applied_date = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leave_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-applied_date']

    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type}"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('Start date cannot be after the end date.')

    @property
    def total_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0


class Attendance(models.Model):
    """Daily attendance record for an employee."""

    class Status(models.TextChoices):
        PRESENT = 'Present', 'Present'
        ABSENT = 'Absent', 'Absent'
        HALF_DAY = 'Half Day', 'Half Day'
        LEAVE = 'Leave', 'Leave'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)

    class Meta:
        ordering = ['-date', 'employee__full_name']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'date'], name='unique_attendance_per_day'),
        ]

    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.status})"

    def clean(self):
        super().clean()
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValidationError('Check-out time must be after check-in time.')
        if self.status in (self.Status.ABSENT, self.Status.LEAVE) and (self.check_in or self.check_out):
            raise ValidationError('Check-in/check-out should be empty for Absent or Leave records.')
