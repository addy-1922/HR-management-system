from django.contrib import admin

from .models import Attendance, Department, Employee, LeaveRequest


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'employee_count', 'created_at']
    search_fields = ['name']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'department', 'designation', 'employment_status', 'joining_date']
    list_filter = ['department', 'employment_status', 'gender']
    search_fields = ['employee_id', 'full_name', 'email']
    autocomplete_fields = ['department']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status', 'applied_date']
    list_filter = ['status', 'leave_type']
    search_fields = ['employee__full_name', 'reason']
    autocomplete_fields = ['employee']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status']
    list_filter = ['status', 'date']
    search_fields = ['employee__full_name']
    autocomplete_fields = ['employee']
