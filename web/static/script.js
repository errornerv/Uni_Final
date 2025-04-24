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

// Update charts every 5 seconds
setInterval(fetchTrafficData, 5000);
fetchTrafficData();

// Trigger fetchTrafficData when filters change
$('#node-filter, #type-filter, #time-filter').on('change', function() {
    fetchTrafficData();
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
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            $('#form-message').html('<span class="bg-red-100 text-red-error px-3 py-1 rounded">Failed to add order: ' + status + ', ' + error + '</span>');
            customLog('ERROR', 'Failed to add new order: ' + status + ', ' + error);
        }
    });
});

// تابع برای باز و بسته کردن فرم
function toggleAddOrderForm() {
    console.log("toggleAddOrderForm called"); // برای دیباگ
    const addOrderSection = $('#add-order-section');
    console.log("addOrderSection:", addOrderSection); // برای دیباگ
    addOrderSection.toggleClass('show');
    console.log("show class after toggle:", addOrderSection.hasClass('show')); // برای دیباگ
    if (addOrderSection.hasClass('show')) {
        addOrderSection.removeClass('opacity-0 max-h-0 overflow-hidden');
        addOrderSection.addClass('opacity-100 max-h-[1000px] overflow-visible');
    } else {
        addOrderSection.removeClass('opacity-100 max-h-[1000px] overflow-visible');
        addOrderSection.addClass('opacity-0 max-h-0 overflow-hidden');
    }
}

// تابع برای گرفتن و آپدیت داده‌های گزارش
function fetchReportData() {
    const nodeFilter = $('#report-node-filter').val();
    const typeFilter = $('#report-type-filter').val();
    const timeFilter = $('#report-time-filter').val();
    const healthFilter = $('#report-health-filter').val();
    const reportType = window.location.pathname.split('/').pop(); // گرفتن report_type از URL

    $.get('/report/' + reportType, {
        node_id: nodeFilter,
        traffic_type: typeFilter,
        time_range: timeFilter,
        network_health: healthFilter
    }, function(data) {
        // داده‌ها رو از HTML رندرشده استخراج می‌کنیم
        const parser = new DOMParser();
        const doc = parser.parseFromString(data, 'text/html');
        const newTableBody = doc.querySelector('#report-table-body').innerHTML;

        // آپدیت جدول با داده‌های جدید
        $('#report-table-body').html(newTableBody);
        customLog('INFO', 'Report data updated successfully');
    }).fail(function(jqXHR, textStatus, errorThrown) {
        customLog('ERROR', 'Failed to fetch report data: ' + textStatus + ', ' + errorThrown);
        $('#report-table-body').html('<tr><td colspan="100">Error loading data. Please try again.</td></tr>');
    });
}

function showLoading() {
    if (isScriptRunning) {
        $('#loading').show();
    }
}

function hideLoading() {
    $('#loading').hide();
    isScriptRunning = false;
}

function createScriptOutputPanel(scriptId) {
    if (!scriptOutputs[scriptId]) {
        const outputDiv = document.createElement('div');
        outputDiv.className = 'script-panel bg-gray-light rounded-lg p-4 mb-4 max-h-[300px] overflow-y-auto shadow-small';
        outputDiv.id = `panel-${scriptId}`;
        outputDiv.innerHTML = `
            <h4 onclick="toggleOutput('${scriptId}')" class="mb-3 cursor-pointer flex justify-between items-center">Script: ${scriptId} <i class="fas fa-chevron-down" id="_toggle-output-${scriptId}"></i></h4>
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
        $('header').addClass('bg-header-dark'); // استفاده از کلاس جدید
        $('.sidebar').removeClass('bg-sidebar-bg');
        $('.sidebar').addClass('bg-dark-blue');
        $('.menu-item').removeClass('bg-sidebar-menu hover:bg-sidebar-hover');
        $('.menu-item').addClass('bg-sidebar-bg hover:bg-sidebar-hover');
        $('.sub-menu a, .sub-menu p').removeClass('bg-sidebar-menu hover:bg-sidebar-hover');
        $('.sub-menu a, .sub-menu p').addClass('bg-sidebar-bg hover:bg-sidebar-hover');
        $('.output-container, .card, .chart-card').removeClass('bg-white shadow-medium');
        $('.output-container, .card, .chart-card').addClass('bg-sidebar-bg shadow-dark');
        $('.script-panel').removeClass('bg-gray-light');
        $('.script-panel').addClass('bg-gray-dark');
        $('.filter-section').removeClass('bg-white border-gray-border shadow-light');
        $('.filter-section').addClass('bg-sidebar-bg border-sidebar-hover shadow-dark');
        $('.filter-section label').removeClass('text-dark-blue');
        $('.filter-section label').addClass('text-text-light');
        $('.filter-section select').removeClass('bg-gray-50');
        $('.filter-section select').addClass('bg-gray-dark text-text-light border-sidebar-hover');
        $('.filter-section select:focus').removeClass('bg-white');
        $('.filter-section select:focus').addClass('bg-sidebar-menu');
        $('.report-page h1').removeClass('text-dark-blue');
        $('.report-page h1').addClass('text-text-light');
        $('.table th').removeClass('bg-dark-blue');
        $('.table th').addClass('bg-sidebar-bg');
        $('.table td').removeClass('bg-gray-light border-gray-border');
        $('.table td').addClass('bg-gray-dark border-sidebar-hover');
        $('.table tr:hover').removeClass('bg-gray-200');
        $('.table tr:hover').addClass('bg-sidebar-hover');
        $('#add-order-form .card').removeClass('bg-gradient-to-br from-white to-gray-light border-gray-border shadow-light');
        $('#add-order-form .card').addClass('bg-gradient-to-br from-sidebar-bg to-gray-dark border-sidebar-hover shadow-dark');
        $('#add-order-form .card h3').removeClass('text-dark-blue');
        $('#add-order-form .card h3').addClass('text-text-light');
        $('#add-order-form .form-group label').removeClass('text-text-dark');
        $('#add-order-form .form-group label').addClass('text-text-light');
        $('#add-order-form .form-group select, #add-order-form .form-group input').removeClass('bg-gray-50');
        $('#add-order-form .form-group select, #add-order-form .form-group input').addClass('bg-gray-dark text-text-light border-sidebar-hover');
        $('#add-order-form .form-group select:focus, #add-order-form .form-group input:focus').removeClass('bg-white');
        $('#add-order-form .form-group select:focus, #add-order-form .form-group input:focus').addClass('bg-sidebar-menu');
        $('.add-order-toggle').removeClass('bg-teal hover:bg-blue-hover');
        $('.add-order-toggle').addClass('bg-teal hover:bg-blue-hover');
    } else {
        $('body').removeClass('bg-gradient-to-br from-dark-blue to-sidebar-bg text-white');
        $('body').addClass('bg-gradient-to-br from-light-bg to-light-gray text-text-dark');
        $('header').removeClass('bg-header-dark'); // حذف کلاس جدید
        $('header').addClass('bg-dark-blue');
        $('.sidebar').removeClass('bg-dark-blue');
        $('.sidebar').addClass('bg-sidebar-bg');
        $('.menu-item').removeClass('bg-sidebar-bg hover:bg-sidebar-hover');
        $('.menu-item').addClass('bg-sidebar-menu hover:bg-sidebar-hover');
        $('.sub-menu a, .sub-menu p').removeClass('bg-sidebar-bg hover:bg-sidebar-hover');
        $('.sub-menu a, .sub-menu p').addClass('bg-sidebar-menu hover:bg-sidebar-hover');
        $('.output-container, .card, .chart-card').removeClass('bg-sidebar-bg shadow-dark');
        $('.output-container, .card, .chart-card').addClass('bg-white shadow-medium');
        $('.script-panel').removeClass('bg-gray-dark');
        $('.script-panel').addClass('bg-gray-light');
        $('.filter-section').removeClass('bg-sidebar-bg border-sidebar-hover shadow-dark');
        $('.filter-section').addClass('bg-white border-gray-border shadow-light');
        $('.filter-section label').removeClass('text-text-light');
        $('.filter-section label').addClass('text-dark-blue');
        $('.filter-section select').removeClass('bg-gray-dark text-text-light border-sidebar-hover');
        $('.filter-section select').addClass('bg-gray-50 text-black border-gray-border');
        $('.filter-section select:focus').removeClass('bg-sidebar-menu');
        $('.filter-section select:focus').addClass('bg-white');
        $('.report-page h1').removeClass('text-text-light');
        $('.report-page h1').addClass('text-dark-blue');
        $('.table th').removeClass('bg-sidebar-bg');
        $('.table th').addClass('bg-dark-blue');
        $('.table td').removeClass('bg-gray-dark border-sidebar-hover');
        $('.table td').addClass('bg-gray-light border-gray-border');
        $('.table tr:hover').removeClass('bg-sidebar-hover');
        $('.table tr:hover').addClass('bg-gray-200');
        $('#add-order-form .card').removeClass('bg-gradient-to-br from-sidebar-bg to-gray-dark border-sidebar-hover shadow-dark');
        $('#add-order-form .card').addClass('bg-gradient-to-br from-white to-gray-light border-gray-border shadow-light');
        $('#add-order-form .card h3').removeClass('text-text-light');
        $('#add-order-form .card h3').addClass('text-dark-blue');
        $('#add-order-form .form-group label').removeClass('text-text-light');
        $('#add-order-form .form-group label').addClass('text-text-dark');
        $('#add-order-form .form-group select, #add-order-form .form-group input').removeClass('bg-gray-dark text-text-light border-sidebar-hover');
        $('#add-order-form .form-group select, #add-order-form .form-group input').addClass('bg-gray-50 text-black border-gray-border');
        $('#add-order-form .form-group select:focus, #add-order-form .form-group input:focus').removeClass('bg-sidebar-menu');
        $('#add-order-form .form-group select:focus, #add-order-form .form-group input:focus').addClass('bg-white');
        $('.add-order-toggle').removeClass('bg-teal hover:bg-blue-hover');
        $('.add-order-toggle').addClass('bg-teal hover:bg-blue-hover');
    }
}

// Initialize on Page Load
document.addEventListener('DOMContentLoaded', () => {
    fetchTrafficData();
});