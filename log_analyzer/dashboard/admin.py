from django.contrib import admin
from .models import LogFile, LogEntry, QueryParameter

class QueryParameterInline(admin.TabularInline):
    model = QueryParameter
    extra = 0

class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'timestamp', 'method', 'path', 'status_code', 'response_size')
    list_filter = ('method', 'status_code')
    search_fields = ('ip_address', 'path', 'user_agent')
    inlines = [QueryParameterInline]

class LogEntryInline(admin.TabularInline):
    model = LogEntry
    extra = 0
    fields = ('ip_address', 'timestamp', 'method', 'path', 'status_code')
    show_change_link = True
    can_delete = False
    max_num = 10
    verbose_name_plural = "Recent Log Entries (10 max)"

class LogFileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'uploaded_at', 'processed', 'entry_count')
    list_filter = ('processed', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
    inlines = [LogEntryInline]
    
    def entry_count(self, obj):
        return obj.entries.count()
    entry_count.short_description = 'Entries'

admin.site.register(LogFile, LogFileAdmin)
admin.site.register(LogEntry, LogEntryAdmin)