from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.urls import reverse
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from .constants import LOGBOOK_TYPES, LOGBOOK_PROPERTIES
from .models import Logbook, Log, LogImage, Comment
from .forms import SignUpForm

import markdown
from datetime import datetime, timedelta
from weasyprint import HTML

# --- Helpers for Access Control ---


def get_visible_logbook(logbook_id, user):
    """
    Helper function to get a logbook only if the user has permission.
    Replaces the old 'property_type' logic with 'access_level' & 'allowed_groups'.
    """
    # 1. 유저가 속한 그룹들 가져오기
    user_groups = user.groups.all()

    # 2. 권한 조건 정의 (Owner OR Public OR Shared Group Member)
    qs = Logbook.objects.filter(
        Q(id=logbook_id) & (              # ID가 일치하고
            Q(owner=user) |               # 주인이거나
            Q(access_level='public') |    # 전체 공개이거나
            (Q(access_level='shared') & Q(allowed_groups__in=user_groups))  # 그룹 공유된 경우
        )
    ).distinct()  # 그룹 중복 제거

    # 3. 결과 반환 (없으면 404 에러)
    return get_object_or_404(qs)


def has_write_permission(logbook, user):
    """
    Check if the user has permission to create or update logs.
    Rule: Owner has full access, SHARED allows any logged-in user to write.
    """
    if logbook.owner == user:
        return True
    if logbook.property_type == 'SHARED':
        return True
    return False

# --- Logbook Management Views ---


@login_required
def logbook_dashboard(request):  # Check if function name matches your urls.py
    """
    Dashboard view showing:
    1. My Logbooks (Owner)
    2. Shared & Public Logbooks (Public OR Shared with User's Groups)
    """
    # 1. Logbooks created by the current user
    my_logbooks = Logbook.objects.filter(owner=request.user)

    # 2. Shared & Public Logbooks
    # [FIX] Logic updated to use 'access_level' instead of 'property_type'

    # Get IDs of groups the current user belongs to
    user_groups = request.user.groups.all()

    shared_logbooks = Logbook.objects.filter(
        Q(access_level='public') |
        (Q(access_level='shared') & Q(allowed_groups__in=user_groups))
    ).distinct().exclude(owner=request.user)

    return render(request, 'elog/logbook_list.html', {
        'my_logbooks': my_logbooks,
        'shared_logbooks': shared_logbooks,
    })


@login_required
def logbook_create(request):
    """
    Handle the creation of a new logbook.
    """
    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description')
        book_type = request.POST.get('book_type')
        prop_type = request.POST.get('property_type')

        Logbook.objects.create(
            name=name,
            description=description,
            owner=request.user,
            book_type=book_type,
            property_type=prop_type
        )
        return redirect('elog:logbook_dashboard')

    context = {
        'types': LOGBOOK_TYPES,
        'properties': LOGBOOK_PROPERTIES,
    }
    return render(request, 'elog/logbook_create_form.html', context)

# --- Log Operations (CRUD) ---


@login_required
def log_list(request, logbook_id):
    """
    List logs for a specific logbook with search and date navigation.
    """
    logbook = get_visible_logbook(logbook_id, request.user)

    date_str = request.GET.get('date')
    search_query = request.GET.get('search', '').strip()

    # Base QuerySet with optimizations
    logs_qs = Log.objects.filter(logbook=logbook).prefetch_related(
        'user', 'images', 'comments__user'
    )

    if search_query:
        # Search Mode: Show all matching logs, newest first
        logs = logs_qs.filter(
            Q(content__icontains=search_query) |
            Q(user__username__icontains=search_query)
        ).order_by('-created_at')
        target_date = None
    else:
        # Date Navigation Mode
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            # Default: Show date of the most recent log
            latest_log = logs_qs.order_by('-created_at').first()
            target_date = latest_log.created_at.date() if latest_log else timezone.now().date()

        # Filter by target date, oldest first (Chronological)
        logs = logs_qs.filter(
            created_at__date=target_date).order_by('created_at')

    # Markdown Processing
    md = markdown.Markdown(extensions=['tables', 'fenced_code'])
    for log in logs:
        log.content_html = md.convert(log.content)

    # Date Navigation Links
    today_date = timezone.now().date()
    base_date = target_date if target_date else today_date
    prev_date = (base_date - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (base_date + timedelta(days=1)).strftime('%Y-%m-%d')

    context = {
        'logbook': logbook,
        'logs': logs,
        'current_date': target_date,
        'today_date': today_date,
        'prev_date': prev_date,
        'next_date': next_date,
        'search_query': search_query,
        'can_write': has_write_permission(logbook, request.user),
    }
    return render(request, 'elog/log_list.html', context)


@login_required
def log_create(request, logbook_id):
    """
    Create a new log entry. Write access: Owner or Shared property.
    """
    logbook = get_visible_logbook(logbook_id, request.user)

    if not has_write_permission(logbook, request.user):
        return HttpResponseForbidden("You do not have permission to write in this logbook.")

    if request.method == "POST":
        content = request.POST.get('content')
        # Ensure form has enctype="multipart/form-data"
        images = request.FILES.getlist('images')

        log = Log.objects.create(
            logbook=logbook,
            content=content,
            user=request.user,
            # created_at is handled by model default
        )

        for img in images:
            LogImage.objects.create(log=log, image=img, width=400)

        # Redirect to the date of the created log
        return redirect(f"{reverse('elog:log_list', args=[logbook.id])}?date={log.created_at.date()}")

    return render(request, 'elog/log_form.html', {'logbook': logbook})


@login_required
def log_edit(request, logbook_id, log_id):
    """
    Edit a log entry. Permission: Author or Logbook Owner.
    """
    logbook = get_visible_logbook(logbook_id, request.user)
    log_entry = get_object_or_404(Log, id=log_id, logbook=logbook)

    # Permission Check
    if log_entry.user != request.user and logbook.owner != request.user:
        return HttpResponseForbidden("Permission denied.")

    if request.method == "POST":
        log_entry.content = request.POST.get('content')
        log_entry.save()

        # Update Image Widths
        for img in log_entry.images.all():
            width_val = request.POST.get(f'width_{img.id}')
            if width_val:
                try:
                    img.width = int(width_val)
                    img.save()
                except ValueError:
                    pass

        # Delete Selected Images
        delete_ids = request.POST.getlist('delete_images')
        if delete_ids:
            LogImage.objects.filter(id__in=delete_ids, log=log_entry).delete()

        # Add New Images
        new_files = request.FILES.getlist('images')
        for f in new_files:
            LogImage.objects.create(log=log_entry, image=f, width=400)

        log_date = log_entry.created_at.date().strftime('%Y-%m-%d')
        return redirect(f"{reverse('elog:log_list', args=[logbook.id])}?date={log_date}")

    return render(request, 'elog/log_edit_form.html', {'log': log_entry, 'logbook': logbook})


@login_required
def log_delete(request, logbook_id, log_id):
    """
    Delete a log entry. Permission: Author or Logbook Owner.
    """
    logbook = get_visible_logbook(logbook_id, request.user)
    log = get_object_or_404(Log, id=log_id, logbook=logbook)

    # Permission Check
    if log.user != request.user and logbook.owner != request.user:
        return HttpResponseForbidden("Permission denied.")

    if request.method == 'POST':
        log_date = log.created_at.strftime('%Y-%m-%d')
        log.delete()
        return redirect(f"{reverse('elog:log_list', args=[logbook.id])}?date={log_date}")

    return redirect('elog:log_list', logbook_id=logbook.id)

# --- Interaction & Export ---


@login_required
def log_comment(request, logbook_id, log_id):
    """
    Post a comment to a log entry.
    """
    logbook = get_visible_logbook(logbook_id, request.user)
    log_entry = get_object_or_404(Log, id=log_id, logbook=logbook)

    if request.method == "POST":
        content = request.POST.get('content')
        if content:
            Comment.objects.create(
                log=log_entry,
                content=content,
                user=request.user,
                # created_at handled by auto_now_add
            )

        log_date = log_entry.created_at.date().strftime('%Y-%m-%d')
        return redirect(f"{reverse('elog:log_list', args=[logbook.id])}?date={log_date}")

    return render(request, 'elog/log_comment_form.html', {'log': log_entry, 'logbook': logbook})


@login_required
def export_logs_pdf(request, logbook_id):
    """
    Generates a PDF of logs for a specific date, converting Markdown to HTML.
    """
    # 1. Get the target date
    date_str = request.GET.get('date')
    if date_str:
        current_date = parse_date(date_str)
    else:
        current_date = timezone.now().date()

    # 2. Retrieve Logbook and Log data
    logbook = get_object_or_404(Logbook, id=logbook_id)
    logs = Log.objects.filter(
        logbook=logbook,
        created_at__date=current_date
    ).order_by('created_at')

    # [FIX] 3. Convert Markdown content to HTML manually for each log
    # This step is crucial because the template expects 'log.content_html'
    for log in logs:
        log.content_html = markdown.markdown(
            log.content,
            extensions=['fenced_code', 'tables', 'nl2br']  # Common extensions
        )

    # 4. Prepare context data for the template
    context = {
        'logbook': logbook,
        'logs': logs,
        'target_date': current_date,
        'request': request,
    }

    # 5. Render HTML content
    html_string = render_to_string('elog/log_pdf.html', context)

    # 6. Generate PDF using WeasyPrint
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Log_{current_date}.pdf"'

    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)

    return response


def signup(request):
    """
    Handles new user registration with extended fields.
    """
    if request.method == 'POST':
        # Use Custom Form
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('elog:logbook_dashboard')
    else:
        # Use Custom Form
        form = SignUpForm()

    return render(request, 'registration/signup.html', {'form': form})


@login_required
def logbook_list(request):
    """
    Dashboard view showing:
    1. My Logbooks (Owner)
    2. Shared & Public Logbooks (Public OR Shared with User's Groups)
    """
    # 1. Logbooks created by the current user
    my_logbooks = Logbook.objects.filter(owner=request.user)

    # 2. Shared & Public Logbooks
    # Logic:
    #   (Access Level is Public)
    #   OR
    #   (Access Level is Shared AND The logbook's allowed groups intersect with User's groups)

    # Get IDs of groups the current user belongs to
    user_groups = request.user.groups.all()

    shared_logbooks = Logbook.objects.filter(
        Q(access_level='public') |
        (Q(access_level='shared') & Q(allowed_groups__in=user_groups))
    ).distinct().exclude(owner=request.user)

    return render(request, 'elog/logbook_list.html', {
        'my_logbooks': my_logbooks,
        'shared_logbooks': shared_logbooks,
    })

# Helper function to check permissions


def check_logbook_access(user, logbook):
    """
    Returns True if user has access to the logbook, False otherwise.

    Permission Rules:
    1. Owner -> Always Allow
    2. Public -> Always Allow
    3. Shared -> Allow if user belongs to one of the allowed_groups
    """
    # 1. Check Owner or Public status
    if logbook.owner == user or logbook.access_level == 'public':
        return True

    # 2. Check Group Membership for Shared logbooks
    if logbook.access_level == 'shared':
        # Check if any of the user's groups are in the logbook's allowed_groups
        if user.groups.filter(id__in=logbook.allowed_groups.all()).exists():
            return True

    return False
