from django.db import models
import os
from django.db.models import Count

class LogFile(models.Model):
    """Model to store uploaded log files"""
    file = models.FileField(upload_to='logs/')
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)  # Add index for better performance
    processed = models.BooleanField(default=False, db_index=True)  # Add index for filtering
    excel_file = models.FileField(upload_to='excel/', null=True, blank=True)
    
    def __str__(self):
        return os.path.basename(self.file.name)
    
    def delete(self, *args, **kwargs):
        # Delete the files when the model is deleted
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        if self.excel_file:
            if os.path.isfile(self.excel_file.path):
                os.remove(self.excel_file.path)
        super().delete(*args, **kwargs)
    
    class Meta:
        indexes = [
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['processed']),
        ]
        ordering = ['-uploaded_at']  # Add default ordering

    def entry_count(self):
        """Efficiently count entries using annotation"""
        count = getattr(self, '_entry_count', None)
        if count is None:
            count = self.entries.count()
            setattr(self, '_entry_count', count)
        return count


class LogEntry(models.Model):
    """Model to store individual log entries"""
    log_file = models.ForeignKey(LogFile, on_delete=models.CASCADE, related_name='entries')
    ip_address = models.CharField(max_length=50, db_index=True)  # Add index for better filtering
    timestamp = models.CharField(max_length=100, db_index=True)  # Add index for better filtering
    method = models.CharField(max_length=10, db_index=True)  # Add index for better filtering
    path = models.CharField(max_length=255, db_index=True)  # Add index for better filtering
    protocol = models.CharField(max_length=20)
    status_code = models.IntegerField(db_index=True)  # Add index for better filtering
    response_size = models.IntegerField()
    referrer = models.CharField(max_length=255, blank=True)
    user_agent = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.ip_address} - {self.timestamp} - {self.status_code}"
    
    class Meta:
        indexes = [
            models.Index(fields=['log_file', 'status_code']),
            models.Index(fields=['log_file', 'method']),
            models.Index(fields=['log_file', 'timestamp']),
        ]
        # Add composite indexes for common query patterns


class QueryParameter(models.Model):
    """Model to store query parameters for each log entry"""
    log_entry = models.ForeignKey(LogEntry, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=100, db_index=True)  # Add index for better filtering
    value = models.TextField()
    
    def __str__(self):
        return f"{self.name}: {self.value[:50]}"
    
    class Meta:
        indexes = [
            models.Index(fields=['log_entry', 'name']),
            models.Index(fields=['name', 'value']),
        ]
        # Add composite indexes for common query patterns