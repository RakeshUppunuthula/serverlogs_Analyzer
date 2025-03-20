/**
 * Optimized JavaScript for Log Analyzer Dashboard
 */

// Use DOMContentLoaded for faster page loading
document.addEventListener('DOMContentLoaded', function() {
    // Use a single object to manage all dashboard functionality
    const Dashboard = {
        charts: {},
        
        init: function() {
            this.initTooltips();
            this.handleFileInput();
            this.setupAutoCloseAlerts();
            this.enhanceQueryParamFilter();
            this.handleFilterCollapseState();
            this.setupTableHoverEffect();
            this.setupChartAnimations();
            this.setupFilterForm();
            this.initCharts();
        },
        
        initTooltips: function() {
            // Initialize tooltips with a single call
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
        },
        
        handleFileInput: function() {
            const fileInput = document.querySelector('input[type="file"]');
            if (fileInput) {
                fileInput.addEventListener('change', function(e) {
                    const fileName = e.target.files[0]?.name || 'No file selected';
                    
                    // Add a small text below input showing selected filename
                    let fileNameDisplay = document.getElementById('file-name-display');
                    if (!fileNameDisplay) {
                        fileNameDisplay = document.createElement('div');
                        fileNameDisplay.id = 'file-name-display';
                        fileNameDisplay.className = 'form-text mt-1';
                        this.parentNode.appendChild(fileNameDisplay);
                    }
                    
                    fileNameDisplay.textContent = fileName;
                });
            }
        },
        
        setupAutoCloseAlerts: function() {
            // Auto close alerts after 5 seconds
            document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
                setTimeout(() => {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }, 5000);
            });
        },
        
        enhanceQueryParamFilter: function() {
            const paramSelect = document.getElementById('id_query_param');
            const valueInput = document.getElementById('id_query_value');
            
            if (paramSelect && valueInput) {
                // Disable value input when no parameter is selected
                paramSelect.addEventListener('change', function() {
                    valueInput.disabled = (this.value === '');
                    if (this.value === '') valueInput.value = '';
                });
                
                // Initial state
                valueInput.disabled = (paramSelect.value === '');
            }
        },
        
        handleFilterCollapseState: function() {
            const filterCollapse = document.getElementById('filterCollapse');
            if (filterCollapse) {
                const collapseButton = document.querySelector('[data-bs-target="#filterCollapse"]');
                const collapseIcon = collapseButton?.querySelector('i');
                
                if (collapseButton && collapseIcon) {
                    // Update icon when collapse state changes
                    filterCollapse.addEventListener('shown.bs.collapse', function() {
                        collapseIcon.classList.replace('fa-chevron-down', 'fa-chevron-up');
                        localStorage.setItem('filterCollapsed', 'false');
                    });
                    
                    filterCollapse.addEventListener('hidden.bs.collapse', function() {
                        collapseIcon.classList.replace('fa-chevron-up', 'fa-chevron-down');
                        localStorage.setItem('filterCollapsed', 'true');
                    });
                    
                    // Set initial state based on localStorage
                    const isCollapsed = localStorage.getItem('filterCollapsed');
                    if (isCollapsed === 'false') {
                        new bootstrap.Collapse(filterCollapse, { toggle: false }).show();
                        collapseIcon.classList.replace('fa-chevron-down', 'fa-chevron-up');
                    }
                }
            }
        },
        
        setupTableHoverEffect: function() {
            // Table row hover effect
            document.querySelectorAll('.log-entry').forEach(row => {
                row.style.cursor = 'pointer';
                
                row.addEventListener('click', this.handleLogEntryClick);
            });
        },
        
        handleLogEntryClick: function() {
            const entryId = this.getAttribute('data-entry-id');
            
            // Show loading spinner
            const modal = new bootstrap.Modal(document.getElementById('entryDetailModal'));
            const modalBody = document.getElementById('entryDetailModal').querySelector('.modal-body');
            modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading details...</p></div>';
            
            // Show modal first for better UX
            modal.show();
            
            // Fetch entry details with caching
            const cacheKey = `log-entry-${entryId}`;
            const cachedData = sessionStorage.getItem(cacheKey);
            
            if (cachedData) {
                // Use cached data if available
                Dashboard.populateModalWithData(JSON.parse(cachedData));
            } else {
                // Otherwise fetch from server
                fetch(`/log-entry/${entryId}/`)
                    .then(response => response.json())
                    .then(data => {
                        // Cache the response
                        sessionStorage.setItem(cacheKey, JSON.stringify(data));
                        Dashboard.populateModalWithData(data);
                    })
                    .catch(error => {
                        console.error('Error fetching log entry details:', error);
                        modalBody.innerHTML = '<div class="alert alert-danger">Failed to load log entry details.</div>';
                    });
            }
        },
        
        populateModalWithData: function(data) {
            // Fill modal with data
            document.getElementById('modal-ip').textContent = data.ip_address;
            document.getElementById('modal-timestamp').textContent = data.timestamp;
            
            const methodEl = document.getElementById('modal-method');
            methodEl.textContent = data.method;
            methodEl.className = `badge ${Dashboard.getMethodClass(data.method)}`;
            
            document.getElementById('modal-path').textContent = data.path;
            
            const statusEl = document.getElementById('modal-status');
            statusEl.textContent = data.status_code;
            statusEl.className = `badge ${Dashboard.getStatusClass(data.status_code)}`;
            
            document.getElementById('modal-size').textContent = `${data.response_size} bytes`;
            document.getElementById('modal-user-agent').textContent = data.user_agent;
            document.getElementById('modal-referrer').textContent = data.referrer || '(none)';
            
            // Parameters
            const paramsContainer = document.getElementById('modal-parameters');
            if (data.parameters && data.parameters.length > 0) {
                const table = document.createElement('table');
                table.className = 'table table-sm';
                
                // Create table header
                const thead = document.createElement('thead');
                thead.innerHTML = '<tr><th>Name</th><th>Value</th></tr>';
                table.appendChild(thead);
                
                // Create table body with DocumentFragment for better performance
                const tbody = document.createElement('tbody');
                const fragment = document.createDocumentFragment();
                
                data.parameters.forEach(param => {
                    const row = document.createElement('tr');
                    
                    const nameCell = document.createElement('td');
                    nameCell.textContent = param.name;
                    
                    const valueCell = document.createElement('td');
                    valueCell.textContent = param.value;
                    
                    row.appendChild(nameCell);
                    row.appendChild(valueCell);
                    fragment.appendChild(row);
                });
                
                tbody.appendChild(fragment);
                table.appendChild(tbody);
                
                // Clear and append
                paramsContainer.innerHTML = '';
                
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                wrapper.appendChild(table);
                paramsContainer.appendChild(wrapper);
            } else {
                paramsContainer.innerHTML = '<div class="text-center py-3 text-muted"><i>No query parameters</i></div>';
            }
        },
        
        setupChartAnimations: function() {
            // Add animation for charts
            const charts = document.querySelectorAll('canvas');
            charts.forEach(chart => {
                chart.style.opacity = '0';
                chart.style.transform = 'translateY(20px)';
                chart.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                
                // Trigger animation after a small delay
                setTimeout(() => {
                    chart.style.opacity = '1';
                    chart.style.transform = 'translateY(0)';
                }, 300);
            });
        },
        
        setupFilterForm: function() {
            // Optimize filter form to use AJAX for faster filtering
            const filterForm = document.querySelector('form[action*="dashboard"]');
            if (filterForm) {
                filterForm.addEventListener('submit', function(e) {
                    // Only use AJAX if not changing pages
                    if (window.location.pathname.includes('/dashboard/')) {
                        e.preventDefault();
                        
                        // Show loading indicator
                        const tableContainer = document.querySelector('.table-responsive');
                        if (tableContainer) {
                            tableContainer.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Filtering logs...</p></div>';
                        }
                        
                        // Get form data
                        const formData = new FormData(this);
                        
                        // Add AJAX flag
                        const url = new URL(this.action);
                        url.searchParams.append('ajax', '1');
                        
                        // Add form data to URL
                        for (const pair of formData.entries()) {
                            url.searchParams.append(pair[0], pair[1]);
                        }
                        
                        // Fetch filtered results
                        fetch(url.toString(), {
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                        })
                            .then(response => response.json())
                            .then(data => {
                                // Update table content
                                tableContainer.innerHTML = data.html;
                                
                                // Update chart data
                                if (Dashboard.charts.statusChart) {
                                    Dashboard.updateStatusChart(data.status_chart_data);
                                }
                                
                                if (Dashboard.charts.methodChart) {
                                    Dashboard.updateMethodChart(data.method_chart_data);
                                }
                                
                                // Update total count
                                const totalCountBadge = document.querySelector('.card-header .badge');
                                if (totalCountBadge) {
                                    totalCountBadge.textContent = `${data.total_entries} entries found`;
                                }
                                
                                // Reattach event listeners
                                Dashboard.setupTableHoverEffect();
                                
                                // Update URL without reloading
                                window.history.pushState({}, '', url.toString().replace('&ajax=1', ''));
                            })
                            .catch(error => {
                                console.error('Error filtering logs:', error);
                                tableContainer.innerHTML = '<div class="alert alert-danger">Failed to filter logs. Please try again.</div>';
                            });
                    }
                });
            }
        },
        
        initCharts: function() {
            // Initialize charts if present on the page
            const statusCtx = document.getElementById('statusChart')?.getContext('2d');
            const methodCtx = document.getElementById('methodChart')?.getContext('2d');
            
            if (statusCtx && window.statusChartData) {
                const data = JSON.parse(window.statusChartData || '{"labels":[],"data":[]}');
                Dashboard.charts.statusChart = Dashboard.createStatusChart(statusCtx, data);
            }
            
            if (methodCtx && window.methodChartData) {
                const data = JSON.parse(window.methodChartData || '{"labels":[],"data":[]}');
                Dashboard.charts.methodChart = Dashboard.createMethodChart(methodCtx, data);
            }
        },
        
        createStatusChart: function(ctx, data) {
            return new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Count',
                        data: data.data,
                        backgroundColor: data.labels.map(label => Dashboard.getStatusColor(parseInt(label), 0.7)),
                        borderColor: data.labels.map(label => Dashboard.getStatusColor(parseInt(label), 1)),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                title: function(tooltipItems) {
                                    const code = parseInt(tooltipItems[0].label);
                                    return `Status ${code}: ${Dashboard.getStatusText(code)}`;
                                }
                            }
                        }
                    }
                }
            });
        },
        
        createMethodChart: function(ctx, data) {
            return new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.data,
                        backgroundColor: [
                            'rgba(40, 167, 69, 0.7)',   // GET - green
                            'rgba(13, 110, 253, 0.7)',  // POST - blue
                            'rgba(255, 193, 7, 0.7)',   // PUT - yellow
                            'rgba(220, 53, 69, 0.7)',   // DELETE - red
                            'rgba(108, 117, 125, 0.7)'  // Others - gray
                        ],
                        borderColor: [
                            'rgb(40, 167, 69)',
                            'rgb(13, 110, 253)',
                            'rgb(255, 193, 7)',
                            'rgb(220, 53, 69)',
                            'rgb(108, 117, 125)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right'
                        }
                    }
                }
            });
        },
        
        updateStatusChart: function(data) {
            const chart = Dashboard.charts.statusChart;
            if (chart) {
                chart.data.labels = data.labels;
                chart.data.datasets[0].data = data.data;
                chart.data.datasets[0].backgroundColor = data.labels.map(label => 
                    Dashboard.getStatusColor(parseInt(label), 0.7)
                );
                chart.data.datasets[0].borderColor = data.labels.map(label => 
                    Dashboard.getStatusColor(parseInt(label), 1)
                );
                chart.update();
            }
        },
        
        updateMethodChart: function(data) {
            const chart = Dashboard.charts.methodChart;
            if (chart) {
                chart.data.labels = data.labels;
                chart.data.datasets[0].data = data.data;
                chart.update();
            }
        },
        
        // Helper functions
        getMethodClass: function(method) {
            const methodClasses = {
                'GET': 'bg-success',
                'POST': 'bg-primary',
                'PUT': 'bg-warning',
                'DELETE': 'bg-danger'
            };
            return methodClasses[method] || 'bg-secondary';
        },
        
        getStatusClass: function(code) {
            if (code < 300) return 'bg-success';
            if (code < 400) return 'bg-info';
            if (code < 500) return 'bg-warning';
            return 'bg-danger';
        },
        
        getStatusColor: function(code, alpha=1) {
            if (code < 300) return `rgba(40, 167, 69, ${alpha})`;
            if (code < 400) return `rgba(23, 162, 184, ${alpha})`;
            if (code < 500) return `rgba(255, 193, 7, ${alpha})`;
            return `rgba(220, 53, 69, ${alpha})`;
        },
        
        getStatusText: function(code) {
            const statusTexts = {
                200: 'OK',
                201: 'Created',
                204: 'No Content',
                301: 'Moved Permanently',
                302: 'Found',
                304: 'Not Modified',
                400: 'Bad Request',
                401: 'Unauthorized',
                403: 'Forbidden',
                404: 'Not Found',
                500: 'Internal Server Error',
                502: 'Bad Gateway',
                503: 'Service Unavailable'
            };
            return statusTexts[code] || 'Unknown';
        }
    };
    
    // Initialize dashboard
    Dashboard.init();
});