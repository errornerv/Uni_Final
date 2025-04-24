const socket = io();
const scriptOutputs = {};
let globalStop = false;
let isScriptRunning = false;
const LOG_LEVEL = 'ERROR'; // Options: 'DEBUG', 'INFO', 'ERROR'

// Custom logging function
function customLog(level, message) {
    if (LOG_LEVEL === 'DEBUG' || (LOG_LEVEL === 'INFO' && level !== 'DEBUG') || (level === 'ERROR')) {
        console.log(`[${level}] ${message}`);
    }
}

// Traffic Volume Chart
const trafficCtx = document.getElementById('trafficChart').getContext('2d');
const trafficChart = new Chart(trafficCtx, {
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

// Network Health Chart
const healthCtx = document.getElementById('healthChart').getContext('2d');
const healthChart = new Chart(healthCtx, {
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

// Latency Chart
const latencyCtx = document.getElementById('latencyChart').getContext('2d');
const latencyChart = new Chart(latencyCtx, {
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

// Traffic Type Distribution Chart
const typeCtx = document.getElementById('typeChart').getContext('2d');
const typeChart = new Chart(typeCtx, {
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

// Congestion Prediction Chart
const predictionCtx = document.getElementById('predictionChart').getContext('2d');
const predictionChart = new Chart(predictionCtx, {
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

// Fetch real-time data with filters
function fetchTrafficData() {
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
        trafficChart.data.labels = data.timestamps;
        trafficChart.data.datasets[0].data = data.volumes;
        trafficChart.update();

        // Update Network Health Chart
        healthChart.data.datasets[0].data = [
            data.network_health_scores[0] || 0, // Good
            data.network_health_scores[1] || 0, // Fair
            data.network_health_scores[2] || 0, // Moderate
            data.network_health_scores[3] || 0, // Poor
            data.network_health_scores[4] || 0  // Bad
        ];
        healthChart.update();

        // Update Latency Chart
        latencyChart.data.labels = data.timestamps;
        latencyChart.data.datasets[0].data = data.latencies;
        latencyChart.update();

        // Update Traffic Type Chart
        typeChart.data.labels = data.traffic_types;
        typeChart.data.datasets[0].data = data.type_counts;
        typeChart.update();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch /traffic_data: ' + textStatus + ', ' + errorThrown);
    });
}

// Fetch congestion predictions
function fetchPredictions() {
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
        predictionChart.data.labels = data.node_ids;
        predictionChart.data.datasets[0].data = data.actual_congestion;
        predictionChart.data.datasets[1].data = data.predicted_congestion;
        predictionChart.update();
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch /predictions: ' + textStatus + ', ' + errorThrown);
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
                // Clear the form
                $('#add-order-form')[0].reset();
                // Refresh the charts to reflect the new data
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
    const nodeFilter = $('#report-node-filter').val();
    const typeFilter = $('#report-type-filter').val();
    const timeFilter = $('#report-time-filter').val();
    const healthFilter = $('#report-health-filter').val();
    const reportType = window.location.pathname.split('/').pop(); // Extract report_type from URL

    $.get('/report/' + reportType, {
        node_id: nodeFilter,
        traffic_type: typeFilter,
        time_range: timeFilter,
        network_health: healthFilter
    }, function(data) {
        // Extract data from the rendered HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(data, 'text/html');
        const newTableBody = doc.querySelector('#report-table-body').innerHTML;

        // Update the table with new data
        $('#report-table-body').html(newTableBody);
        customLog('INFO', 'Report data updated successfully');
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch report data: ' + textStatus + ', ' + errorThrown);
        $('#report-table-body').html('<tr><td colspan="100">Error loading data. Please try again.</td></tr>');
    });
}

// Function to fetch traffic report data for Plotly charts
function fetchTrafficReportData() {
    $.get('/traffic_report_data', function(data) {
        if (data.error) {
            customLog('ERROR', 'Error fetching traffic report data: ' + data.error);
            return;
        }
        customLog('INFO', 'Traffic report data fetched successfully');

        // Plot Daily Average Traffic Trend
        const avgTrafficTrace = {
            x: data.timestamps,
            y: data.daily_avg_traffic,
            mode: 'lines+markers',
            name: 'Daily Average Traffic',
            line: { color: '#4BC0C0' }
        };

        const maxTrafficTrace = {
            x: data.timestamps,
            y: data.daily_max_traffic,
            mode: 'lines+markers',
            name: 'Daily Max Traffic',
            line: { color: '#FF6384' }
        };

        const minTrafficTrace = {
            x: data.timestamps,
            y: data.daily_min_traffic,
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
            x: data.timestamps,
            y: data.health_trend.map(h => ({ 'good': 0, 'moderate': 1, 'poor': 2 }[h] || 0)),
            mode: 'lines+markers',
            name: 'Health Trend',
            line: { color: '#FFCE56' }
        };

        const healthLayout = {
            title: 'Network Health Trend',
            xaxis: { title: 'Timestamp' },
            yaxis: { 
                title: 'Health Status', 
                tickvals: [0, 1, 2],
                ticktext: ['Good', 'Moderate', 'Poor']
            },
            margin: { t: 50, b: 50, l: 50, r: 50 }
        };

        Plotly.newPlot('healthTrendChart', [healthTrace], healthLayout);
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch /traffic_report_data: ' + textStatus + ', ' + errorThrown);
    });
}

// Call fetchTrafficReportData when on report page with charts
if (document.getElementById('trafficTrendChart') && document.getElementById('healthTrendChart')) {
    fetchTrafficReportData();
    setInterval(fetchTrafficReportData, 5000); // Update every 5 seconds
}

// Show/Hide loading spinner
function showLoading() {
    if (isScriptRunning) {
        $('#loading').show();
    }
}

function hideLoading() {
    $('#loading').hide();
    isScriptRunning = false;
}

// Create script output panel
function createScriptOutputPanel(scriptId) {
    if (!scriptOutputs[scriptId]) {
        const outputDiv = document.createElement('div');
        outputDiv.className = 'script-panel bg-gray-light rounded-lg p-4 mb-4 max-h-[300px] overflow-y-auto shadow-small';
        outputDiv.id = `panel-${scriptId}`;
        outputDiv.innerHTML = `
            <h4 onclick="toggleOutput('${scriptId}')" class="mb-3 cursor-pointer flex justify-between items-center">Script: ${scriptId} <i class="fas fa-chevron-down" id="toggle-output-${scriptId}"></i></h4>
            <pre id="output-${scriptId}" class="script-output bg-white p-4 border rounded block"></pre>
            <div id="link-${scriptId}" class="mt-2"></div>
            <div class="script-toolbar mt-2 flex gap-3 sticky bottom-0 bg-gray-light pt-3">
                <button onclick="stopScript('${scriptId}', true)" class="bg-red-error border-none px-3 py-1 rounded text-white transition-all duration-200 hover:bg-red-hover hover:scale-105"><i class="fas fa-stop"></i> Stop</button>
                <button onclick="clearScriptOutput('${scriptId}')" class="bg-red-error border-none px-3 py-1 rounded text-white transition-all duration-200 hover:bg-red-hover hover:scale-105"><i class="fas fa-trash-alt"></i> Clear</button>
            </div>
        `;
        document.getElementById('script-outputs').appendChild(outputDiv);
        scriptOutputs[scriptId] = true;
    }
}

socket.on('script_output', function(data) {
    hideLoading();
    if (globalStop) return;
    createScriptOutputPanel(data.script_id);
    const output = $(`#output-${data.script_id}`);
    output.append(data.output + '\n');
    const panel = $(`#panel-${data.script_id}`);
    panel.scrollTop(panel[0].scrollHeight);
});

socket.on('report_link', function(data) {
    createScriptOutputPanel(data.script_id);
    if (data.report_link) {
        $(`#link-${data.script_id}`).html(`<a href="${data.report_link}" class="btn btn-info px-4 py-2 rounded font-medium cursor-pointer transition-colors duration-300 bg-blue-500 text-white hover:bg-blue-600">View Report</a>`);
    } else {
        $(`#link-${data.script_id}`).html('');
    }
});

socket.on('script_status', function(data) {
    if (data.status === 'stopped_all') {
        hideLoading();
        globalStop = false;
        $('#stop-button-text').text('Stop All Scripts');
    } else if (data.status === 'running') {
        createScriptOutputPanel(data.script_id);
        $(`#output-${data.script_id}`).text('Script is running...\n');
    } else if (data.status === 'stopped') {
        hideLoading();
        createScriptOutputPanel(data.script_id);
        const output = $(`#output-${data.script_id}`);
        output.append('Script stopped.\n');
        const panel = $(`#panel-${data.script_id}`);
        panel.scrollTop(panel[0].scrollHeight);
        $(`#link-${data.script_id}`).html('');
    }
});

function runScript(scriptId) {
    customLog('INFO', `Running script: ${scriptId}`);
    isScriptRunning = true;
    showLoading();
    globalStop = false;
    createScriptOutputPanel(scriptId);
    $(`#output-${scriptId}`).text('');
    $(`#link-${scriptId}`).html('');
    $.post('/run_script', { script_id: scriptId }, function(data) {
        if (data.error) {
            hideLoading();
            $(`#output-${scriptId}`).text('Error: ' + data.error);
        }
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to run script: ' + textStatus + ', ' + errorThrown);
        hideLoading();
    });
}

function stopAllScripts() {
    $('#stop-button-text').text('Searching for spot to stop...');
    showLoading();
    globalStop = true;
    $.ajax({
        url: '/stop_all_scripts',
        type: 'POST',
        success: function(data) {
            if (data.error) {
                hideLoading();
                $('#stop-button-text').text('Stop All Scripts');
                globalStop = false;
                customLog('ERROR', 'Error stopping all scripts: ' + data.error);
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            $('#stop-button-text').text('Stop All Scripts');
            globalStop = false;
            customLog('ERROR', 'Failed to stop all scripts: ' + status + ', ' + error);
        }
    });
}

function stopScript(scriptId, force = false) {
    if (force) {
        $.ajax({
            url: '/force_stop_script',
            type: 'POST',
            data: { script_id: scriptId },
            success: function(data) {
                if (data.error) {
                    $(`#output-${scriptId}`).append('Error: ' + data.error + '\n');
                    customLog('ERROR', 'Error force stopping script: ' + data.error);
                }
                hideLoading();
            },
            error: function(xhr, status, error) {
                hideLoading();
                customLog('ERROR', 'Failed to force stop script: ' + status + ', ' + error);
            }
        });
    } else {
        $.ajax({
            url: '/stop_script',
            type: 'POST',
            data: { script_id: scriptId },
            success: function(data) {
                if (data.error) {
                    stopScript(scriptId, true);
                    customLog('ERROR', 'Error stopping script: ' + data.error);
                }
                hideLoading();
            },
            error: function(xhr, status, error) {
                stopScript(scriptId, true);
                hideLoading();
                customLog('ERROR', 'Failed to stop script: ' + status + ', ' + error);
            }
        });
    }
}

function clearTerminal() {
    Object.keys(scriptOutputs).forEach(scriptId => {
        $(`#output-${scriptId}`).text('');
        $(`#link-${scriptId}`).html('');
    });
    Object.keys(scriptOutputs).forEach(scriptId => {
        $(`#panel-${scriptId}`).remove();
        delete scriptOutputs[scriptId];
    });
}

function clearScriptOutput(scriptId) {
    $(`#output-${scriptId}`).text('');
    $(`#link-${scriptId}`).html('');
}

function toggleSubMenu(id) {
    const subMenu = $(`#${id}`);
    const icon = $(`#${id}-icon`);
    subMenu.slideToggle();
    icon.toggleClass('fa-chevron-down fa-chevron-up');
}

function toggleOutput(scriptId) {
    const output = $(`#output-${scriptId}`);
    const icon = $(`#toggle-output-${scriptId}`);
    output.slideToggle();
    icon.toggleClass('fa-chevron-down fa-chevron-up');
}

function toggleSidebar() {
    const sidebar = $('#sidebar');
    const mainContent = $('#main-content');
    sidebar.toggleClass('collapsed');
    mainContent.toggleClass('full-width');
    if (sidebar.hasClass('collapsed')) {
        sidebar.addClass('-translate-x-full');
        mainContent.removeClass('ml-[250px] w-[calc(100%-250px)]');
        mainContent.addClass('ml-0 w-full');
    } else {
        sidebar.removeClass('-translate-x-full');
        mainContent.removeClass('ml-0 w-full');
        mainContent.addClass('ml-[250px] w-[calc(100%-250px)]');
    }
}

function toggleTheme() {
    $('body').toggleClass('dark-theme');
    const icon = $('.theme-toggle i');
    icon.toggleClass('fa-moon fa-sun');
    if ($('body').hasClass('dark-theme')) {
        $('body').removeClass('bg-gradient-to-br from-light-bg to-light-gray text-text-dark');
        $('body').addClass('bg-gradient-to-br from-dark-blue to-sidebar-bg text-white');
        $('header').removeClass('bg-dark-blue');
        $('header').addClass('bg-header-dark');
        $('.sidebar').removeClass('bg-sidebar-bg');
        $('.sidebar').addClass('bg-dark-blue');
        $('.menu-item').removeClass('bg-sidebar-menu hover:bg-sidebar-hover');
        $('.menu-item').addClass('bg-sidebar-bg hover:bg-sidebar-hover-dark');
        $('.sub-menu a, .sub-menu p').removeClass('bg-sidebar-menu hover:bg-sidebar-hover');
        $('.sub-menu a, .sub-menu p').addClass('bg-sidebar-bg hover:bg-sidebar-hover-dark');
        $('.output-container, .card, .chart-card').removeClass('bg-white shadow-medium');
        $('.output-container, .card, .chart-card').addClass('bg-dark-card shadow-dark');
        $('.filter-section').removeClass('bg-white shadow-light');
        $('.filter-section').addClass('bg-dark-card shadow-dark');
        $('.script-panel').removeClass('bg-gray-light');
        $('.script-panel').addClass('bg-dark-card');
        $('.script-output').removeClass('bg-white');
        $('.script-output').addClass('bg-gray-800 text-white');
    } else {
        $('body').removeClass('bg-gradient-to-br from-dark-blue to-sidebar-bg text-white');
        $('body').addClass('bg-gradient-to-br from-light-bg to-light-gray text-text-dark');
        $('header').removeClass('bg-header-dark');
        $('header').addClass('bg-dark-blue');
        $('.sidebar').removeClass('bg-dark-blue');
        $('.sidebar').addClass('bg-sidebar-bg');
        $('.menu-item').removeClass('bg-sidebar-bg hover:bg-sidebar-hover-dark');
        $('.menu-item').addClass('bg-sidebar-menu hover:bg-sidebar-hover');
        $('.sub-menu a, .sub-menu p').removeClass('bg-sidebar-bg hover:bg-sidebar-hover-dark');
        $('.sub-menu a, .sub-menu p').addClass('bg-sidebar-menu hover:bg-sidebar-hover');
        $('.output-container, .card, .chart-card').removeClass('bg-dark-card shadow-dark');
        $('.output-container, .card, .chart-card').addClass('bg-white shadow-medium');
        $('.filter-section').removeClass('bg-dark-card shadow-dark');
        $('.filter-section').addClass('bg-white shadow-light');
        $('.script-panel').removeClass('bg-dark-card');
        $('.script-panel').addClass('bg-gray-light');
        $('.script-output').removeClass('bg-gray-800 text-white');
        $('.script-output').addClass('bg-white');
    }
}