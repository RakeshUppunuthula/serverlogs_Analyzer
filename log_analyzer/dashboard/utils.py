import re
import pandas as pd
import os
from urllib.parse import parse_qs, urlparse
from django.conf import settings
from django.db import transaction
from .models import LogEntry, QueryParameter
import concurrent.futures
import multiprocessing

# Precompile the regex pattern for better performance
LOG_PATTERN = re.compile(r'([\d\.x]+) - - \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)"')

def parse_log_line(line):
    """Parse a single log line into structured data - optimized version"""
    match = LOG_PATTERN.match(line)
    if not match:
        return None, None
    
    ip, timestamp, request, status, size, referrer, user_agent = match.groups()
    
    # Parse request more efficiently
    req_parts = request.split(' ', 2)  # Split only by first 2 spaces
    method = req_parts[0] if len(req_parts) > 0 else ""
    url = req_parts[1] if len(req_parts) > 1 else ""
    protocol = req_parts[2] if len(req_parts) > 2 else ""
    
    # Parse URL
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    # Extract query parameters
    query_params = parse_qs(parsed_url.query)
    query_dict = {k: v[0] for k, v in query_params.items()}
    
    # Base log info
    log_info = {
        'ip_address': ip,
        'timestamp': timestamp,
        'method': method,
        'path': path,
        'protocol': protocol,
        'status_code': int(status),
        'response_size': int(size),
        'referrer': referrer if referrer != "-" else "",
        'user_agent': user_agent
    }
    
    return log_info, query_dict

def _process_log_batch(batch_data):
    """Process a batch of log entries and return structured data"""
    results = []
    for line in batch_data:
        if not line.strip():
            continue
        log_data, query_params = parse_log_line(line)
        if log_data:
            results.append((log_data, query_params))
    return results

def process_log_file(log_file):
    """Process a log file and store entries in the database - optimized with bulk operations"""
    # Read the file content
    with open(log_file.file.path, 'r') as file:
        content = file.readlines()
    
    # Skip empty lines
    content = [line.strip() for line in content if line.strip()]
    
    # Number of CPU cores for parallel processing
    num_cores = max(1, multiprocessing.cpu_count() - 1)  # Leave one core free
    
    # Calculate batch size for multiprocessing
    batch_size = max(1, len(content) // num_cores)
    batches = [content[i:i+batch_size] for i in range(0, len(content), batch_size)]
    
    # Process batches in parallel
    all_entries = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        results = executor.map(_process_log_batch, batches)
        for batch_result in results:
            all_entries.extend(batch_result)
    
    # Prepare bulk create lists
    log_entries = []
    query_parameters = []
    
    # Create log entries
    with transaction.atomic():
        for index, (log_data, query_params) in enumerate(all_entries):
            # Create log entry
            log_entry = LogEntry(
                log_file=log_file,
                **log_data
            )
            log_entries.append(log_entry)
        
        # Bulk create log entries
        created_entries = LogEntry.objects.bulk_create(log_entries, batch_size=1000)
        
        # Create query parameters for each log entry
        for entry, (_, query_params) in zip(created_entries, all_entries):
            for name, value in query_params.items():
                query_parameter = QueryParameter(
                    log_entry=entry,
                    name=name,
                    value=value
                )
                query_parameters.append(query_parameter)
        
        # Bulk create query parameters
        QueryParameter.objects.bulk_create(query_parameters, batch_size=1000)
    
    return len(log_entries)


def export_to_excel(log_file):
    """Export log entries to Excel format - optimized version"""
    # Use raw SQL for better performance
    from django.db import connection
    
    # Prepare Excel file path
    filename = f"{os.path.splitext(os.path.basename(log_file.file.name))[0]}_processed.xlsx"
    excel_path = os.path.join('media', 'excel', filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(excel_path), exist_ok=True)
    
    # Get log entries directly as dataframe using SQL
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                ip_address, timestamp, method, path, protocol, 
                status_code, response_size, referrer, user_agent, id
            FROM dashboard_logentry
            WHERE log_file_id = %s
        """, [log_file.id])
        columns = [col[0] for col in cursor.description]
        log_data = cursor.fetchall()
    
    log_df = pd.DataFrame(log_data, columns=columns)
    
    # Get query parameters efficiently
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT qp.log_entry_id, qp.name, qp.value
            FROM dashboard_queryparameter qp
            JOIN dashboard_logentry le ON qp.log_entry_id = le.id
            WHERE le.log_file_id = %s
        """, [log_file.id])
        param_data = cursor.fetchall()
    
    param_columns = ['Log_Entry_ID', 'Parameter', 'Value']
    param_df = pd.DataFrame(param_data, columns=param_columns)
    
    # Create pivot table of parameters efficiently
    if not param_df.empty:
        # Optimize pivot by only processing unique parameters
        unique_params = param_df['Parameter'].unique()
        
        # Create a dictionary for the pivot
        pivot_dict = {}
        
        for entry_id in log_df['id'].unique():
            pivot_dict[entry_id] = {'Log_Entry_ID': entry_id}
            
        # Fill the dictionary with parameter values
        for _, row in param_df.iterrows():
            entry_id = row['Log_Entry_ID']
            if entry_id in pivot_dict:
                pivot_dict[entry_id][row['Parameter']] = row['Value']
        
        # Convert dictionary to dataframe
        pivot_df = pd.DataFrame(list(pivot_dict.values()))
        
        # Merge with log data
        final_df = pd.merge(log_df, pivot_df, left_on='id', right_on='Log_Entry_ID', how='left')
        # Remove ID columns
        final_df = final_df.drop(['id', 'Log_Entry_ID'], axis=1, errors='ignore')
    else:
        final_df = log_df.drop('id', axis=1, errors='ignore')
    
    # Get status summaries efficiently
    status_summary = log_df['status_code'].value_counts().reset_index()
    status_summary.columns = ['Status Code', 'Count']
    
    # Get method summaries efficiently
    method_summary = log_df['method'].value_counts().reset_index()
    method_summary.columns = ['Method', 'Count']
    
    # Write to Excel with optimized settings
    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, sheet_name='Log Data', index=False)
        status_summary.to_excel(writer, sheet_name='Summary', index=False)
        method_summary.to_excel(writer, sheet_name='Summary', startrow=len(status_summary) + 3, index=False)
        
        # Add basic formatting
        workbook = writer.book
        worksheet = writer.sheets['Log Data']
        
        # Add auto-filter
        worksheet.autofilter(0, 0, 0, len(final_df.columns) - 1)
        
        # Freeze the header row
        worksheet.freeze_panes(1, 0)
    
    # Update log file model
    relative_path = os.path.join('excel', filename)
    log_file.excel_file = relative_path
    log_file.processed = True
    log_file.save(update_fields=['excel_file', 'processed'])
    
    return excel_path