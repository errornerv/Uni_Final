const socket = io();
const scriptOutputs = {};
let isScriptRunning = false;
const LOG_LEVEL = 'ERROR'; // Options: 'DEBUG', 'INFO', 'ERROR'
let isFetchingTraffic = false;
let isFetchingPredictions = false;

// Custom logging function
function customLog(level, message) {
    if (LOG_LEVEL === 'DEBUG' || (LOG_LEVEL === 'INFO' && level !== 'DEBUG') || (level === 'ERROR')) {
        console.log(`[${level}] ${message}`);
    }
}

// Initialize charts only if their canvas elements exist
let trafficChart, healthChart, latencyChart, typeChart, predictionChart;

if (document.getElementById('trafficChart')) {
    const trafficCtx = document.getElementById('trafficChart').getContext('2d');
    trafficChart = new Chart(trafficCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Traffic Volume (MB/s)',
                data: [],
                borderColor: '#4BC0C0',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            scales: {
                x: { title: { display: true, text: 'Time' } },
                y: { title: { display: true, text: 'Traffic (MB/s)' }, beginAtZero: true }
            },
            plugins: {
                legend: { display: true }
            }
        }
    });
}

if (document.getElementById('healthChart')) {
    const healthCtx = document.getElementById('healthChart').getContext('2d');
    healthChart = new Chart(healthCtx, {
        type: 'bar',
        data: {
            labels: ['Good', 'Fair', 'Moderate', 'Poor', 'Bad'],
            datasets: [{
                label: 'Network Health',
                data: [0, 0, 0, 0, 0],
                backgroundColor: ['#28a745', '#28a745', '#ffc107', '#dc3545', '#dc3545']
            }]
        },
        options: {
            scales: {
                x: { title: { display: true, text: 'Health Status' } },
                y: { 
                    title: { display: true, text: 'Count' }, 
                    beginAtZero: true,
                    min: 0,
                    max: 8,
                    ticks: {
                        stepSize: 2,
                        callback: function(value) {
                            const labels = { 0: 'Good', 2: 'Fair', 4: 'Moderate', 6: 'Poor', 8: 'Bad' };
                            return labels[value] || value;
                        }
                    }
                }
            },
            plugins: {
                legend: { display: true }
            }
        }
    });
}

if (document.getElementById('latencyChart')) {
    const latencyCtx = document.getElementById('latencyChart').getContext('2d');
    latencyChart = new Chart(latencyCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Latency (ms)',
                data: [],
                borderColor: '#36A2EB',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            scales: {
                x: { title: { display: true, text: 'Time' } },
                y: { title: { display: true, text: 'Latency (ms)' }, beginAtZero: true }
            },
            plugins: {
                legend: { display: true }
            }
        }
    });
}

if (document.getElementById('typeChart')) {
    const typeCtx = document.getElementById('typeChart').getContext('2d');
    typeChart = new Chart(typeCtx, {
        type: 'bar',
        data: {
            labels: ['data', 'video', 'audio'],
            datasets: [{
                label: 'Traffic',
                data: [0, 0, 0],
                backgroundColor: '#FFCE56',
                borderColor: '#FFCE56',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                x: { title: { display: true, text: 'Type' } },
                y: { 
                    title: { display: true, text: 'Count' }, 
                    beginAtZero: true,
                    min: 0,
                    max: 10
                }
            },
            plugins: {
                legend: { display: true }
            }
        }
    });
}

if (document.getElementById('predictionChart')) {
    const predictionCtx = document.getElementById('predictionChart').getContext('2d');
    predictionChart = new Chart(predictionCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Actual Congestion',
                    data: [],
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                    borderColor: '#36A2EB',
                    borderWidth: 1
                },
                {
                    label: 'Predicted Congestion',
                    data: [],
                    backgroundColor: 'rgba(255, 99, 132, 0.6)',
                    borderColor: '#FF6384',
                    borderWidth: 1
                }
            ]
        },
        options: {
            scales: {
                x: { title: { display: true, text: 'Node' } },
                y: { 
                    title: { display: true, text: 'Congestion Level' }, 
                    beginAtZero: true,
                    max: 2,
                    ticks: {
                        stepSize: 1,
                        callback: function(value) {
                            const labels = { 0: 'Low', 1: 'Medium', 2: 'High' };
                            return labels[value] || value;
                        }
                    }
                }
            },
            plugins: {
                legend: { display: true }
            }
        }
    });
}

// Fetch real-time data with filters
function fetchTrafficData() {
    if (isFetchingTraffic || (!trafficChart && !healthChart && !latencyChart && !typeChart)) return;
    isFetchingTraffic = true;
    
    const nodeFilter = $('#node-filter').val();
    const typeFilter = $('#type-filter').val();
    const timeFilter = $('#time-filter').val();

    $.get('/traffic_data', {
        node_id: nodeFilter,
        traffic_type: typeFilter,
        time_range: timeFilter
    }, function(data) {
        if (data.error) {
            customLog('ERROR', 'Error fetching data: ' + data.error);
            return;
        }
        customLog('INFO', 'Data fetched successfully');

        // Update Traffic Volume Chart
        if (trafficChart) {
            trafficChart.data.labels = data.timestamps || [];
            trafficChart.data.datasets[0].data = data.volumes || [];
            trafficChart.update();
        }

        // Update Network Health Chart
        if (healthChart) {
            healthChart.data.datasets[0].data = data.network_health_scores || [0, 0, 0, 0, 0];
            healthChart.update();
        }

        // Update Latency Chart
        if (latencyChart) {
            latencyChart.data.labels = data.timestamps || [];
            latencyChart.data.datasets[0].data = data.latencies || [];
            latencyChart.update();
        }

        // Update Traffic Type Chart
        if (typeChart) {
            typeChart.data.labels = data.traffic_types || ['data', 'video', 'audio'];
            typeChart.data.datasets[0].data = data.type_counts || [0, 0, 0];
            typeChart.update();
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch /traffic_data: ' + textStatus + ', ' + errorThrown);
    }).always(function() {
        isFetchingTraffic = false;
    });
}

// Fetch congestion predictions
function fetchPredictions() {
    if (isFetchingPredictions || !predictionChart) return;
    isFetchingPredictions = true;
    
    const nodeFilter = $('#node-filter').val();
    const timeFilter = $('#time-filter').val();

    $.get('/predictions', {
        node_id: nodeFilter,
        time_range: timeFilter
    }, function(data) {
        if (data.error) {
            customLog('ERROR', 'Error fetching predictions: ' + data.error);
            return;
        }
        customLog('INFO', 'Predictions fetched successfully');

        // Update Congestion Prediction Chart
        if (predictionChart) {
            predictionChart.data.labels = data.node_ids || [];
            predictionChart.data.datasets[0].data = data.actual_congestion || [];
            predictionChart.data.datasets[1].data = data.predicted_congestion || [];
            predictionChart.update();
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch /predictions: ' + textStatus + ', ' + errorThrown);
    }).always(function() {
        isFetchingPredictions = false;
    });
}

// Update charts every 5 seconds
setInterval(fetchTrafficData, 5000);
setInterval(fetchPredictions, 5000);
fetchTrafficData();
fetchPredictions();

// Trigger fetchTrafficData and fetchPredictions when filters change
$('#node-filter, #type-filter, #time-filter').on('change', function() {
    fetchTrafficData();
    fetchPredictions();
});

// Handle form submission for adding new order
if (document.getElementById('add-order-form')) {
    $('#add-order-form').on('submit', function(e) {
        e.preventDefault();
        const formData = {
            node_id: $('#order_node_id').val(),
            traffic_type: $('#order_traffic_type').val(),
            traffic_volume: $('#order_traffic_volume').val(),
            network_health: $('#order_network_health').val(),
            latency: $('#order_latency').val()
        };

        // Basic client-side validation
        if (!formData.node_id || !formData.traffic_type || !formData.traffic_volume || !formData.network_health || !formData.latency) {
            $('#form-message').html('<span class="bg-red-100 text-red-error px-3 py-1 rounded">Please fill in all fields.</span>');
            return;
        }

        if (formData.traffic_volume < 0 || formData.latency < 0) {
            $('#form-message').html('<span class="bg-red-100 text-red-error px-3 py-1 rounded">Traffic volume and latency must be positive numbers.</span>');
            return;
        }

        $('#form-message').html('<span class="bg-blue-100 text-blue-hover px-3 py-1 rounded">Adding order...</span>');
        showLoading();

        $.ajax({
            url: '/add_new_order',
            type: 'POST',
            data: formData,
            success: function(data) {
                hideLoading();
                if (data.error) {
                    $('#form-message').html('<span class="bg-red-100 text-red-error px-3 py-1 rounded">Error: ' + data.error + '</span>');
                    customLog('ERROR', 'Error adding new order: ' + data.error);
                } else {
                    $('#form-message').html('<span class="bg-green-100 text-green-success px-3 py-1 rounded">Order added successfully!</span>');
                    customLog('INFO', 'New order added successfully');
                    $('#add-order-form')[0].reset();
                    fetchTrafficData();
                    fetchPredictions();
                }
            },
            error: function(xhr, status, error) {
                hideLoading();
                $('#form-message').html('<span class="bg-red-100 text-red-error px-3 py-1 rounded">Failed to add order: ' + status + ', ' + error + '</span>');
                customLog('ERROR', 'Failed to add new order: ' + status + ', ' + error);
            }
        });
    });
}

// Function to toggle the add order form
function toggleAddOrderForm() {
    const addOrderSection = $('#add-order-section');
    addOrderSection.toggleClass('show');
    if (addOrderSection.hasClass('show')) {
        addOrderSection.removeClass('opacity-0 max-h-0 overflow-hidden');
        addOrderSection.addClass('opacity-100 max-h-[1000px] overflow-visible');
    } else {
        addOrderSection.removeClass('opacity-100 max-h-[1000px] overflow-visible');
        addOrderSection.addClass('opacity-0 max-h-0 overflow-hidden');
    }
}

// Function to fetch and update report data
function fetchReportData() {
    if (!document.getElementById('report-table-body')) return;
    
    const nodeFilter = $('#report-node-filter').val();
    const typeFilter = $('#report-type-filter').val();
    const timeFilter = $('#report-time-filter').val();
    const healthFilter = $('#report-health-filter').val();
    const reportType = window.location.pathname.split('/').pop() || 'traffic_report';

    $.get('/report/' + reportType, {
        node_id: nodeFilter,
        traffic_type: typeFilter,
        time_range: timeFilter,
        network_health: healthFilter
    }, function(data) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(data, 'text/html');
        const newTableBody = doc.querySelector('#report-table-body')?.innerHTML || '<tr><td colspan="100">No data available</td></tr>';
        $('#report-table-body').html(newTableBody);
        customLog('INFO', 'Report data updated successfully');
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch report data: ' + textStatus + ', ' + errorThrown);
        $('#report-table-body').html('<tr><td colspan="100">Error loading data. Please try again.</td></tr>');
    });
}

// Function to fetch traffic report data for Plotly charts
function fetchTrafficReportData() {
    if (!document.getElementById('trafficTrendChart') || !document.getElementById('healthTrendChart')) return;

    $.get('/traffic_report_data', function(data) {
        if (data.error) {
            customLog('ERROR', 'Error fetching traffic report data: ' + data.error);
            Plotly.newPlot('trafficTrendChart', [], { title: 'Error: ' + data.error });
            Plotly.newPlot('healthTrendChart', [], { title: 'Error: ' + data.error });
            return;
        }
        customLog('INFO', 'Traffic report data fetched successfully');

        // Plot Daily Average Traffic Trend
        const avgTrafficTrace = {
            x: data.timestamps || [],
            y: data.daily_avg_traffic || [],
            mode: 'lines+markers',
            name: 'Daily Average Traffic',
            line: { color: '#4BC0C0' }
        };

        const maxTrafficTrace = {
            x: data.timestamps || [],
            y: data.daily_max_traffic || [],
            mode: 'lines+markers',
            name: 'Daily Max Traffic',
            line: { color: '#FF6384' }
        };

        const minTrafficTrace = {
            x: data.timestamps || [],
            y: data.daily_min_traffic || [],
            mode: 'lines+markers',
            name: 'Daily Min Traffic',
            line: { color: '#36A2EB' }
        };

        const trafficLayout = {
            title: 'Daily Traffic Trends',
            xaxis: { title: 'Timestamp' },
            yaxis: { title: 'Traffic Volume (MB/s)' },
            margin: { t: 50, b: 50, l: 50, r: 50 }
        };

        Plotly.newPlot('trafficTrendChart', [avgTrafficTrace, maxTrafficTrace, minTrafficTrace], trafficLayout);

        // Plot Network Health Trend
        const healthTrace = {
            x: data.timestamps || [],
            y: data.health_trend || [],
            mode: 'lines+markers',
            name: 'Network Health',
            line: { color: '#28a745' },
            text: data.health_trend || [],
            textposition: 'auto'
        };

        const healthLayout = {
            title: 'Network Health Trend',
            xaxis: { title: 'Timestamp' },
            yaxis: { 
                title: 'Health Status',
                type: 'category',
                categoryorder: 'array',
                categoryarray: ['good', 'moderate', 'poor']
            },
            margin: { t: 50, b: 50, l: 50, r: 50 }
        };

        Plotly.newPlot('healthTrendChart', [healthTrace], healthLayout);
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch /traffic_report_data: ' + textStatus + ', ' + errorThrown);
        Plotly.newPlot('trafficTrendChart', [], { title: 'Error loading data' });
        Plotly.newPlot('healthTrendChart', [], { title: 'Error loading data' });
    });
}

// Theme toggle functionality
function toggleTheme() {
    const body = document.body;
    const themeIcon = document.querySelector('.theme-toggle i');
    body.classList.toggle('dark-mode');
    if (body.classList.contains('dark-mode')) {
        body.classList.remove('bg-gradient-to-br', 'from-light-bg', 'to-light-gray', 'text-text-dark');
        body.classList.add('bg-gradient-to-br', 'from-dark-bg', 'to-dark-gray', 'text-text-light');
        themeIcon.classList.remove('fa-moon');
        themeIcon.classList.add('fa-sun');
    } else {
        body.classList.remove('bg-gradient-to-br', 'from-dark-bg', 'to-dark-gray', 'text-text-light');
        body.classList.add('bg-gradient-to-br', 'from-light-bg', 'to-light-gray', 'text-text-dark');
        themeIcon.classList.remove('fa-sun');
        themeIcon.classList.add('fa-moon');
    }
    customLog('INFO', 'Theme toggled');
}

// Loading animation functions
function showLoading() {
    const loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'loading-overlay';
    loadingOverlay.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0, 0, 0, 0.5); display: flex; justify-content: center; 
        align-items: center; z-index: 9999;
    `;
    loadingOverlay.innerHTML = `
        <div style="border: 4px solid #f3f3f3; border-top: 4px solid #4BC0C0; 
        border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    `;
    document.body.appendChild(loadingOverlay);
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// Fetch traffic report data on page load if elements exist
$(document).ready(function() {
    fetchTrafficReportData();
});

// Update report data when filters change
$('#report-node-filter, #report-type-filter, #report-time-filter, #report-health-filter').on('change', function() {
    fetchReportData();
});

// Initial fetch for report data if on report page
if (document.getElementById('report-table-body')) {
    fetchReportData();
}