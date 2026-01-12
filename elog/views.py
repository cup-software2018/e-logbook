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
from .forms import SignUpForm, LogbookForm

import markdown
from datetime import datetime, timedelta
from weasyprint import HTML

# --- Helpers for Access Control ---


def get_visible_logbook(logbook_id, user):
    """
    Helper function to get a logbook only if the user has permission.
    Replaces the old 'property_type' logic with 'access_level' & 'allowed_groups'.
    """
    # 1. Get user groups
    user_groups = user.groups.all()

    # 2. Define permission conditions (Owner OR Public OR Shared Group Member)
    qs = Logbook.objects.filter(
        Q(id=logbook_id) & (
            Q(owner=user) |
            Q(access_level='public') |
            (Q(access_level='shared') & Q(allowed_groups__in=user_groups))
        )
    ).distinct()

    # 3. Return object or 404
    return get_object_or_404(qs)


def has_write_permission(logbook, user):
    """
    Check if the user has permission to create or update logs.
    """
    if logbook.owner == user:
        return True
    # Assuming 'access_level' replaced property_type logic, but keeping legacy check if needed
    if getattr(logbook, 'access_level', '') == 'shared' or getattr(logbook, 'property_type', '') == 'SHARED':
        return True
    return False

# --- Logbook Management Views ---


@login_required
def logbook_dashboard(request):
    """
    Dashboard view showing My Logbooks and Shared/Public Logbooks.
    """
    my_logbooks = Logbook.objects.filter(owner=request.user)
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
    Handle the creation of a new logbook using LogbookForm.
    """
    if request.method == "POST":
        form = LogbookForm(request.POST)
        if form.is_valid():
            # Create object but don't save to DB yet
            logbook = form.save(commit=False)
            # Assign the current user as owner
            logbook.owner = request.user
            # Save to DB
            logbook.save()
            # Save Many-to-Many data (Allowed Groups)
            form.save_m2m()
            return redirect('elog:logbook_dashboard')
    else:
        form = LogbookForm()

    return render(request, 'elog/logbook_create_form.html', {'form': form})

# --- Log Operations (CRUD) ---


@login_required
def log_list(request, logbook_id):
    """
    List logs for a specific logbook with:
    1. Search functionality.
    2. SMART Date Navigation (skips empty days).
    3. Calendar Markers (sends list of dates with logs).
    """
    # 1. Get Logbook (Check permissions)
    logbook = get_visible_logbook(logbook_id, request.user)

    # 2. Get parameters
    date_str = request.GET.get('date')
    search_query = request.GET.get('search', '').strip()

    # 3. Base QuerySet (Optimized with prefetch)
    logs_qs = Log.objects.filter(logbook=logbook).prefetch_related(
        'user', 'images', 'comments__user'
    )

    # [NEW] Get a list of ALL dates that have logs (for Flatpickr calendar dots)
    # Returns a list like: ['2023-10-01', '2023-10-05', ...]
    log_dates_qs = logs_qs.values_list(
        'created_at__date', flat=True).distinct()
    log_dates = [d.strftime('%Y-%m-%d') for d in log_dates_qs if d]

    # 4. Logic Branch: Search vs Date Navigation
    if search_query:
        # --- Search Mode ---
        # Show all matching logs, newest first
        logs = logs_qs.filter(
            Q(content__icontains=search_query) |
            Q(user__username__icontains=search_query)
        ).order_by('-created_at')

        target_date = None
        prev_date_str = None
        next_date_str = None

    else:
        # --- Date Navigation Mode ---

        # Determine Target Date
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            # Default: Go to the date of the most recent log (or today if empty)
            latest_log = logs_qs.order_by('-created_at').first()
            target_date = latest_log.created_at.date() if latest_log else timezone.now().date()

        # Filter logs for the specific date (Chronological order)
        logs = logs_qs.filter(
            created_at__date=target_date).order_by('created_at')

        # [SMART NAVIGATION] Find actual previous/next dates with data

        # Find the latest log BEFORE the target date
        prev_log = logs_qs.filter(
            created_at__date__lt=target_date).order_by('-created_at').first()
        prev_date_str = prev_log.created_at.date().strftime(
            '%Y-%m-%d') if prev_log else None

        # Find the earliest log AFTER the target date
        next_log = logs_qs.filter(
            created_at__date__gt=target_date).order_by('created_at').first()
        next_date_str = next_log.created_at.date().strftime(
            '%Y-%m-%d') if next_log else None

    # 5. Markdown Processing (Convert content to HTML)
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'nl2br'])
    for log in logs:
        log.content_html = md.convert(log.content)

    # 6. Context Preparation
    context = {
        'logbook': logbook,
        'logs': logs,

        # Date Info
        'current_date': target_date,
        'today_date': timezone.now().date(),
        'log_dates': log_dates,       # For Calendar Dots
        'prev_date': prev_date_str,   # For Smart Nav Button (<)
        'next_date': next_date_str,   # For Smart Nav Button (>)

        # Other Info
        'search_query': search_query,
        'can_write': has_write_permission(logbook, request.user),
    }

    return render(request, 'elog/log_list.html', context)


@login_required
def log_create(request, logbook_id):
    """
    Create a new log entry.
    """
    logbook = get_visible_logbook(logbook_id, request.user)

    if not has_write_permission(logbook, request.user):
        return HttpResponseForbidden("You do not have permission to write in this logbook.")

    if request.method == "POST":
        content = request.POST.get('content')
        images = request.FILES.getlist('images')

        log = Log.objects.create(
            logbook=logbook,
            content=content,
            user=request.user,
        )

        for img in images:
            LogImage.objects.create(log=log, image=img, width=400)

        # [MODIFIED] Added anchor (#log-ID) to the redirect URL
        # This ensures the page scrolls to the newly created log.
        redirect_url = f"{reverse('elog:log_list', args=[logbook.id])}?date={log.created_at.date()}#log-{log.id}"
        return redirect(redirect_url)

    return render(request, 'elog/log_form.html', {'logbook': logbook})


@login_required
def log_edit(request, logbook_id, log_id):
    """
    Edit a log entry.
    """
    logbook = get_visible_logbook(logbook_id, request.user)
    log_entry = get_object_or_404(Log, id=log_id, logbook=logbook)

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

        # [MODIFIED] Added anchor (#log-ID) to redirect URL
        # Scrolls back to the specific log entry after editing.
        redirect_url = f"{reverse('elog:log_list', args=[logbook.id])}?date={log_date}#log-{log_entry.id}"
        return redirect(redirect_url)

    return render(request, 'elog/log_edit_form.html', {'log': log_entry, 'logbook': logbook})


@login_required
def log_delete(request, logbook_id, log_id):
    logbook = get_visible_logbook(logbook_id, request.user)
    log = get_object_or_404(Log, id=log_id, logbook=logbook)

    if log.user != request.user and logbook.owner != request.user:
        return HttpResponseForbidden("Permission denied.")

    if request.method == 'POST':
        log_date = log.created_at.strftime('%Y-%m-%d')
        log.delete()
        # [NOTE] No anchor here because the log is gone.
        return redirect(f"{reverse('elog:log_list', args=[logbook.id])}?date={log_date}")

    return redirect('elog:log_list', logbook_id=logbook.id)


@login_required
def log_comment(request, logbook_id, log_id):
    """
    Post a comment.
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
            )

        log_date = log_entry.created_at.date().strftime('%Y-%m-%d')

        # [MODIFIED] Added anchor (#log-ID) to redirect URL
        # Keeps focus on the log entry where the comment was added.
        redirect_url = f"{reverse('elog:log_list', args=[logbook.id])}?date={log_date}#log-{log_entry.id}"
        return redirect(redirect_url)

    return render(request, 'elog/log_comment_form.html', {'log': log_entry, 'logbook': logbook})


@login_required
def export_logs_pdf(request, logbook_id):
    # ... (No changes needed here for this task) ...
    # (Keeping your existing export code structure for brevity)
    date_str = request.GET.get('date')
    if date_str:
        current_date = parse_date(date_str)
    else:
        current_date = timezone.now().date()

    logbook = get_object_or_404(Logbook, id=logbook_id)
    logs = Log.objects.filter(
        logbook=logbook, created_at__date=current_date).order_by('created_at')

    for log in logs:
        log.content_html = markdown.markdown(
            log.content, extensions=['fenced_code', 'tables', 'nl2br']
        )

    context = {
        'logbook': logbook,
        'logs': logs,
        'target_date': current_date,
        'request': request,
    }

    html_string = render_to_string('elog/log_pdf.html', context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Log_{current_date}.pdf"'
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(response)
    return response


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('elog:logbook_dashboard')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})
