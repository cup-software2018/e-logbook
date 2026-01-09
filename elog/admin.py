from django.contrib import admin
from .models import Logbook, Log, LogImage, Comment


class LogInline(admin.TabularInline):
    """
    Allows viewing and editing Logs directly inside the Logbook detail page.
    """
    model = Log
    extra = 0  # Do not show empty placeholder rows by default
    fields = ('user', 'content', 'created_at')
    readonly_fields = ('created_at',)
    show_change_link = True  # Provides a link to the full Log edit page


@admin.register(Logbook)
class LogbookAdmin(admin.ModelAdmin):
    # [FIX] Updated list_display to match current model fields
    # Removed 'book_type' and 'property_type'
    list_display = ('name', 'owner', 'access_level',
                    'created_at', 'updated_at')

    # [FIX] Updated filters
    list_filter = ('access_level', 'created_at')

    search_fields = ('name', 'description', 'owner__username')

    # [Recommended] Adds a nice UI for selecting multiple groups
    filter_horizontal = ('allowed_groups',)


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('id', 'logbook', 'user', 'created_at')
    list_filter = ('logbook', 'created_at', 'user')
    search_fields = ('content',)
    date_hierarchy = 'created_at'
