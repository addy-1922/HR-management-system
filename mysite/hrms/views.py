from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count as models_Count
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AttendanceForm, DepartmentForm, EmployeeForm, LeaveRequestForm, RegisterForm
from .models import Attendance, Department, Employee, LeaveRequest


def is_staff_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


staff_required = user_passes_test(is_staff_user, login_url='login')


# ---------------------------------------------------------------------------
# Authentication (login/logout handled by django.contrib.auth views in urls.py)
# ---------------------------------------------------------------------------

def register(request):
    """Public self-signup that creates a normal (non-staff) account."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome, {user.username}! Your account was created.')
        return redirect('dashboard')

    return render(request, 'registration/register.html', {'form': form})

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    today = timezone.localdate()

    context = {
        'total_employees': Employee.objects.count(),
        'total_departments': Department.objects.count(),
        'present_today': Attendance.objects.filter(date=today, status=Attendance.Status.PRESENT).count(),
        'absent_today': Attendance.objects.filter(date=today, status=Attendance.Status.ABSENT).count(),
        'pending_leaves': LeaveRequest.objects.filter(status=LeaveRequest.Status.PENDING).count(),
        'department_breakdown': Department.objects.annotate(
            total=models_Count('employees')
        ).order_by('-total')[:5],
        'recent_employees': Employee.objects.order_by('-created_at')[:5],
        'recent_leaves': LeaveRequest.objects.all()[:5],
        'today_attendance': Attendance.objects.filter(date=today)[:5],
        'is_staff': request.user.is_staff,
    }
    return render(request, 'hrms/dashboard.html', context)


# ---------------------------------------------------------------------------
# Employee CRUD
# ---------------------------------------------------------------------------

@staff_required
def employee_list(request):
    queryset = Employee.objects.select_related('department').all()
    search = request.GET.get('q', '').strip()
    department = request.GET.get('department', '')
    status = request.GET.get('status', '')

    if search:
        queryset = queryset.filter(
            Q(full_name__icontains=search)
            | Q(employee_id__icontains=search)
            | Q(email__icontains=search)
            | Q(designation__icontains=search)
        )
    if department:
        queryset = queryset.filter(department_id=department)
    if status:
        queryset = queryset.filter(employment_status=status)

    paginator = Paginator(queryset, 10)
    page = paginator.get_page(request.GET.get('page'))
    querystring = request.GET.copy()
    querystring.pop('page', None)

    context = {
        'employees': page,
        'departments': Department.objects.all(),
        'search': search,
        'filter_department': department,
        'filter_status': status,
        'employee_statuses': Employee.EmploymentStatus.values,
        'page_obj': page,
        'querystring': querystring,
    }
    return render(request, 'hrms/employee_list.html', context)


@staff_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee.objects.select_related('department'), pk=pk)
    context = {
        'employee': employee,
        'recent_leaves': employee.leave_requests.all()[:5],
        'recent_attendance': employee.attendance_records.all()[:5],
    }
    return render(request, 'hrms/employee_detail.html', context)


@staff_required
def employee_create(request):
    form = EmployeeForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        employee = form.save()
        messages.success(request, f'Employee "{employee.full_name}" was added successfully.')
        return redirect('employee_detail', pk=employee.pk)
    return render(request, 'hrms/employee_form.html', {'form': form, 'title': 'Add Employee'})


@staff_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    form = EmployeeForm(request.POST or None, request.FILES or None, instance=employee)
    if request.method == 'POST' and form.is_valid():
        employee = form.save()
        messages.success(request, f'Employee "{employee.full_name}" was updated successfully.')
        return redirect('employee_detail', pk=employee.pk)
    return render(request, 'hrms/employee_form.html', {'form': form, 'title': 'Edit Employee', 'employee': employee})


@staff_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        name = employee.full_name
        employee.delete()
        messages.success(request, f'Employee "{name}" was deleted.')
        return redirect('employee_list')
    return render(request, 'hrms/employee_confirm_delete.html', {
        'object': employee,
        'title': 'Delete Employee',
        'cancel_url': reverse('employee_detail', args=[employee.pk]),
    })


# ---------------------------------------------------------------------------
# Department CRUD
# ---------------------------------------------------------------------------

@staff_required
def department_list(request):
    departments = Department.objects.annotate(total=models_Count('employees'))
    context = {'departments': departments}
    return render(request, 'hrms/department_list.html', context)


@staff_required
def department_create(request):
    form = DepartmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        department = form.save()
        messages.success(request, f'Department "{department.name}" was created.')
        return redirect('department_list')
    return render(request, 'hrms/department_form.html', {'form': form, 'title': 'Add Department'})


@staff_required
def department_update(request, pk):
    department = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=department)
    if request.method == 'POST' and form.is_valid():
        department = form.save()
        messages.success(request, f'Department "{department.name}" was updated.')
        return redirect('department_list')
    return render(request, 'hrms/department_form.html', {'form': form, 'title': 'Edit Department', 'department': department})


@staff_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        name = department.name
        department.delete()
        messages.success(request, f'Department "{name}" was deleted.')
        return redirect('department_list')
    return render(request, 'hrms/department_confirm_delete.html', {
        'object': department,
        'title': 'Delete Department',
        'cancel_url': reverse('department_list'),
    })


# ---------------------------------------------------------------------------
# Leave Management
# ---------------------------------------------------------------------------

@login_required
def leave_list(request):
    queryset = LeaveRequest.objects.select_related('employee').all()
    status = request.GET.get('status', '')
    if status:
        queryset = queryset.filter(status=status)

    paginator = Paginator(queryset, 10)
    page = paginator.get_page(request.GET.get('page'))
    querystring = request.GET.copy()
    querystring.pop('page', None)

    context = {
        'leaves': page,
        'filter_status': status,
        'leave_statuses': LeaveRequest.Status.values,
        'page_obj': page,
        'querystring': querystring,
        'is_staff': request.user.is_staff,
    }
    return render(request, 'hrms/leave_list.html', context)


@login_required
def leave_create(request):
    form = LeaveRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        leave = form.save()
        messages.success(request, 'Leave request submitted successfully.')
        return redirect('leave_list')
    return render(request, 'hrms/leave_form.html', {'form': form, 'title': 'Request Leave'})


@staff_required
def leave_update(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    form = LeaveRequestForm(request.POST or None, instance=leave)
    if request.method == 'POST' and form.is_valid():
        leave = form.save()
        messages.success(request, 'Leave request was updated.')
        return redirect('leave_list')
    return render(request, 'hrms/leave_form.html', {'form': form, 'title': 'Edit Leave Request', 'leave': leave})


@staff_required
@require_POST
def leave_approve(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if leave.status == LeaveRequest.Status.PENDING:
        leave.status = LeaveRequest.Status.APPROVED
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        leave.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        messages.success(request, f'Leave for {leave.employee.full_name} was approved.')
    return redirect('leave_list')


@staff_required
@require_POST
def leave_reject(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if leave.status == LeaveRequest.Status.PENDING:
        leave.status = LeaveRequest.Status.REJECTED
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        leave.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        messages.warning(request, f'Leave for {leave.employee.full_name} was rejected.')
    return redirect('leave_list')


@staff_required
def leave_delete(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if request.method == 'POST':
        leave.delete()
        messages.success(request, 'Leave request was deleted.')
        return redirect('leave_list')
    return render(request, 'hrms/leave_confirm_delete.html', {
        'object': leave,
        'title': 'Delete Leave Request',
        'cancel_url': reverse('leave_list'),
    })


# ---------------------------------------------------------------------------
# Attendance CRUD
# ---------------------------------------------------------------------------

@staff_required
def attendance_list(request):
    queryset = Attendance.objects.select_related('employee').all()
    date = request.GET.get('date', '')
    status = request.GET.get('status', '')
    if date:
        queryset = queryset.filter(date=date)
    if status:
        queryset = queryset.filter(status=status)

    paginator = Paginator(queryset, 10)
    page = paginator.get_page(request.GET.get('page'))
    querystring = request.GET.copy()
    querystring.pop('page', None)

    context = {
        'attendance': page,
        'filter_date': date,
        'filter_status': status,
        'attendance_statuses': Attendance.Status.values,
        'page_obj': page,
        'querystring': querystring,
    }
    return render(request, 'hrms/attendance_list.html', context)


@staff_required
def attendance_create(request):
    form = AttendanceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        record = form.save()
        messages.success(request, f'Attendance for {record.employee.full_name} was recorded.')
        return redirect('attendance_list')
    return render(request, 'hrms/attendance_form.html', {'form': form, 'title': 'Record Attendance'})


@staff_required
def attendance_update(request, pk):
    record = get_object_or_404(Attendance, pk=pk)
    form = AttendanceForm(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        record = form.save()
        messages.success(request, 'Attendance record was updated.')
        return redirect('attendance_list')
    return render(request, 'hrms/attendance_form.html', {'form': form, 'title': 'Edit Attendance', 'record': record})


@staff_required
def attendance_delete(request, pk):
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Attendance record was deleted.')
        return redirect('attendance_list')
    return render(request, 'hrms/attendance_confirm_delete.html', {
        'object': record,
        'title': 'Delete Attendance Record',
        'cancel_url': reverse('attendance_list'),
    })
