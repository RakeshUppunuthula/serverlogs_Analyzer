import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_page

from .models import LogFile, LogEntry, QueryParameter
from .forms import LogFileUploadForm, LogFilterForm
from .utils import process_log_file, export_to_excel
import json
import time
from threading import Thread
from django.core.cache import cache


def home(request):
    """Home view with upload form and list of uploaded files"""
    form = LogFileUploadForm()
    # Select related fields to reduce queries
    log_files = LogFile.objects.all().order_by('-uploaded_at')
    
    return render(request, 'dashboard/upload.html', {
        'form': form,
        'log_files': log_files
    })


def upload_log_file(request):
    """Handle log file upload and processing"""
    if request.method != 'POST':
        return redirect('home')
        
    form = LogFileUploadForm(request.POST, request.FILES)
    if form.is_valid():
        # Save the uploaded file
        log_file = form.save()
        
        try:
            # Use a background thread for processing to avoid timeout
            def process_in_background():
                try:
                    # Process the log file
                    line_count = process_log_file(log_file)
                    
                    # Export to Excel
                    excel_path = export_to_excel(log_file)
                    
                    # Store a message in cache to show on next page load
                    cache.set(f'log_file_{log_file.id}_message', 
                             f"Successfully processed {line_count} log entries. Excel file has been created.",
                             timeout=60)
                except Exception as e:
                    # If processing fails, store error message
                    cache.set(f'log_file_{log_file.id}_error', 
                             f"Error processing log file: {str(e)}",
                             timeout=60)
            
            # Start processing in background
            thread = Thread(target=process_in_background)
            thread.daemon = True
            thread.start()
            
            messages.info(request, "Log file processing has started. This may take a few moments.")
            return redirect('dashboard', log_file_id=log_file.id)
        
        except Exception as e:
            # If immediate error occurs, delete the file and show error
            log_file.delete()
            messages.error(request, f"Error processing log file: {str(e)}")
            return redirect('home')
    else:
        for error in form.errors.values():
            messages.error(request, error)

    return redirect('home')


def get_chart_data(log_file_id, filters=None):
    """Get chart data for dashboard visualization"""
    if filters is None:
        filters = {}
    
    # Use cache key based on filters and log_file_id
    cache_key = f'chart_data_{log_file_id}_{hash(frozenset(filters.items() if filters else []))}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    log_entries = LogEntry.objects.filter(log_file_id=log_file_id, **filters)
    
    # Use Django aggregations for efficient database operations
    status_counts = log_entries.values('status_code').annotate(
        count=Count('status_code')
    ).order_by('status_code')
    
    method_counts = log_entries.values('method').annotate(
        count=Count('method')
    ).order_by('method')
    
    # Prepare chart data for JavaScript
    status_chart_data = {
        'labels': [str(item['status_code']) for item in status_counts],
        'data': [item['count'] for item in status_counts],
    }
    
    method_chart_data = {
        'labels': [item['method'] for item in method_counts],
        'data': [item['count'] for item in method_counts],
    }
    
    # Store in cache for 5 minutes
    chart_data = (status_chart_data, method_chart_data)
    cache.set(cache_key, chart_data, 300)  # 300 seconds = 5 minutes
    
    return chart_data


def dashboard(request, log_file_id):
    """Main dashboard view for analyzing log data"""
    log_file = get_object_or_404(LogFile, id=log_file_id)
    filter_form = LogFilterForm(request.GET)
    
    # Check for background processing messages
    processing_message = cache.get(f'log_file_{log_file_id}_message')
    if processing_message:
        messages.success(request, processing_message)
        cache.delete(f'log_file_{log_file_id}_message')
    
    processing_error = cache.get(f'log_file_{log_file_id}_error')
    if processing_error:
        messages.error(request, processing_error)
        cache.delete(f'log_file_{log_file_id}_error')
    
    # Build filters with optimization
    filters = {}
    if request.GET:
        if 'ip_address' in request.GET and request.GET['ip_address']:
            filters['ip_address__icontains'] = request.GET['ip_address']
        
        if 'method' in request.GET and request.GET['method']:
            filters['method'] = request.GET['method']
        
        if 'status_code' in request.GET and request.GET['status_code']:
            filters['status_code'] = request.GET['status_code']
        
        if 'path' in request.GET and request.GET['path']:
            filters['path__icontains'] = request.GET['path']
        
        # Date range filter optimization
        if 'start_date' in request.GET and request.GET['start_date']:
            filters['timestamp__contains'] = request.GET['start_date']
        
        if 'end_date' in request.GET and request.GET['end_date']:
            filters['timestamp__contains'] = request.GET['end_date']
        
        # Query parameter filter with optimization
        if 'query_param' in request.GET and request.GET['query_param']:
            param_name = request.GET['query_param']
            if 'query_value' in request.GET and request.GET['query_value']:
                param_value = request.GET['query_value']
                # Use a subquery for better performance
                filter_params = QueryParameter.objects.filter(
                    name=param_name,
                    value__icontains=param_value,
                    log_entry__log_file=log_file
                ).values_list('log_entry_id', flat=True)
            else:
                filter_params = QueryParameter.objects.filter(
                    name=param_name,
                    log_entry__log_file=log_file
                ).values_list('log_entry_id', flat=True)
            
            filters['id__in'] = filter_params
    
    # Apply filters with optimized query
    log_entries = LogEntry.objects.filter(log_file=log_file, **filters)
    total_entries = log_entries.count()
    
    # Paginate results with optimization
    paginator = Paginator(log_entries.order_by('-timestamp'), 25)  # Show 25 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get chart data
    status_chart_data, method_chart_data = get_chart_data(log_file_id, filters)
    
    # Get parameter names for filtering with optimization
    param_names = QueryParameter.objects.filter(
        log_entry__log_file=log_file
    ).values_list('name', flat=True).distinct()
    
    # Check if this is AJAX request (partial page load)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return only the table data for AJAX requests (for dynamic filtering)
        html = render(request, 'dashboard/partials/log_entries_table.html', {
            'page_obj': page_obj,
            'total_entries': total_entries,
            'filtered': bool(filters)
        }).content.decode('utf-8')
        
        return JsonResponse({
            'html': html,
            'status_chart_data': status_chart_data,
            'method_chart_data': method_chart_data,
            'total_entries': total_entries
        })
    
    context = {
        'log_file': log_file,
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_entries': total_entries,
        'status_chart_data': json.dumps(status_chart_data),
        'method_chart_data': json.dumps(method_chart_data),
        'param_names': param_names,
        'filtered': bool(filters)
    }
    
    return render(request, 'dashboard/dashboard.html', context)


def log_entry_detail(request, entry_id):
    """AJAX view to get detailed information about a log entry"""
    # Try to get from cache first
    cache_key = f'log_entry_detail_{entry_id}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return JsonResponse(cached_data)
        
    # Use select_related and prefetch_related for optimization
    log_entry = get_object_or_404(
        LogEntry.objects.prefetch_related('parameters'),
        id=entry_id
    )
    parameters = log_entry.parameters.all()
    
    # Prepare data for response
    entry_data = {
        'ip_address': log_entry.ip_address,
        'timestamp': log_entry.timestamp,
        'method': log_entry.method,
        'path': log_entry.path,
        'protocol': log_entry.protocol,
        'status_code': log_entry.status_code,
        'response_size': log_entry.response_size,
        'referrer': log_entry.referrer,
        'user_agent': log_entry.user_agent,
        'parameters': [
            {'name': param.name, 'value': param.value}
            for param in parameters
        ]
    }
    
    # Cache the result for 60 seconds
    cache.set(cache_key, entry_data, 60)
    
    return JsonResponse(entry_data)


@require_POST
def delete_log_file(request, log_file_id):
    """Delete a log file and all its entries"""
    log_file = get_object_or_404(LogFile, id=log_file_id)
    file_name = os.path.basename(log_file.file.name)
    
    # Use transaction to ensure data consistency
    from django.db import transaction
    with transaction.atomic():
        log_file.delete()
        
    messages.success(request, f"Log file '{file_name}' has been deleted.")
    return redirect('home')


def download_excel(request, log_file_id):
    """Download the processed Excel file"""
    log_file = get_object_or_404(LogFile, id=log_file_id)
    
    if not log_file.excel_file:
        messages.error(request, "Excel file not found. Please process the log file first.")
        return redirect('dashboard', log_file_id=log_file.id)
    
    file_path = log_file.excel_file.path
    if os.path.exists(file_path):
        # Stream file response more efficiently
        with open(file_path, 'rb') as excel:
            response = HttpResponse(
                excel.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    else:
        messages.error(request, "Excel file not found on the server.")
        return redirect('dashboard', log_file_id=log_file.id)