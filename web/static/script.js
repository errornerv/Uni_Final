const socket = io();

const scriptOutputs = {};
let globalStop = false;
let isScriptRunning = false;

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
    console.log(`Running script: ${scriptId}`);
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
            }
        },
        error: function(xhr, status, error) {
            hideLoading();
            $('#stop-button-text').text('Stop All Scripts');
            globalStop = false;
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
                }
                hideLoading();
            },
            error: function(xhr, status, error) {
                hideLoading();
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
                }
                hideLoading();
            },
            error: function(xhr, status, error) {
                stopScript(scriptId, true);
                hideLoading();
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