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
        outputDiv.className = 'script-panel';
        outputDiv.id = `panel-${scriptId}`;
        outputDiv.innerHTML = `
            <h4 onclick="toggleOutput('${scriptId}')">Script: ${scriptId} <i class="fas fa-chevron-down" id="toggle-output-${scriptId}"></i></h4>
            <pre id="output-${scriptId}" class="script-output bg-light p-3 border rounded" style="display: block;"></pre>
            <div id="link-${scriptId}" class="mt-2"></div>
            <div class="script-toolbar mt-2">
                <button onclick="stopScript('${scriptId}', true)"><i class="fas fa-stop"></i> Stop</button>
                <button onclick="clearScriptOutput('${scriptId}')"><i class="fas fa-trash-alt"></i> Clear</button>
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
        $(`#link-${data.script_id}`).html(`<a href="${data.report_link}" class="btn btn-info">View Report</a>`);
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
}

function toggleTheme() {
    $('body').toggleClass('dark-theme');
    const icon = $('.theme-toggle i');
    icon.toggleClass('fa-moon fa-sun');
}

// Initialize on Page Load
document.addEventListener('DOMContentLoaded', () => {
    fetchTrafficData();
});