/* TrafficGoat Web UI - FortiOS Style Dashboard */

(function() {
    'use strict';

    // Socket.IO connection
    var socket = io();
    window.trafficGoat = { socket: socket };

    // ---- State ----
    var lastStats = null;
    var pollInterval = null;
    var isConnected = false;
    var trafficChart = null;
    var protocolChart = null;
    var chartData = { labels: [], pps: [], bytes: [] };
    var maxChartPoints = 120;
    var startTime = null;

    // ---- Utility Functions ----

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        var units = ['B', 'KB', 'MB', 'GB', 'TB'];
        var i = Math.floor(Math.log(bytes) / Math.log(1024));
        if (i >= units.length) i = units.length - 1;
        return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
    }

    function formatNumber(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return n.toLocaleString();
    }

    function formatPps(n) {
        if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
        return Math.round(n).toString();
    }

    function formatDuration(seconds) {
        if (!seconds || seconds <= 0) return '0s';
        var h = Math.floor(seconds / 3600);
        var m = Math.floor((seconds % 3600) / 60);
        var s = Math.floor(seconds % 60);
        if (h > 0) return h + 'h ' + m + 'm ' + s + 's';
        if (m > 0) return m + 'm ' + s + 's';
        return s + 's';
    }

    function formatTime(timestamp) {
        if (!timestamp) return '-';
        var d = new Date(timestamp * 1000);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function formatDateTime(timestamp) {
        if (!timestamp) return '-';
        var d = new Date(timestamp * 1000);
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' +
               d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // ---- Header Status ----

    function updateHeaderStatus(running) {
        var statusEl = document.getElementById('header-engine-status');
        if (!statusEl) return;
        var dot = statusEl.querySelector('.status-dot');
        var text = statusEl.querySelector('.status-text');
        if (running) {
            dot.className = 'status-dot running';
            text.textContent = 'Running';
        } else {
            dot.className = 'status-dot idle';
            text.textContent = 'Idle';
        }
    }

    // ---- Uptime Clock ----

    function updateUptime() {
        var el = document.getElementById('header-uptime');
        if (!el) return;
        var now = new Date();
        el.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    setInterval(updateUptime, 1000);
    updateUptime();

    // ---- Charts ----

    function initTrafficChart() {
        var canvas = document.getElementById('traffic-chart');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        trafficChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Packets/sec',
                    data: [],
                    borderColor: '#4b8bf5',
                    backgroundColor: 'rgba(75, 139, 245, 0.08)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHitRadius: 10,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#222838',
                        titleColor: '#c8cdd5',
                        bodyColor: '#e8ecf1',
                        borderColor: '#2d3548',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false,
                        callbacks: {
                            label: function(ctx) {
                                return formatNumber(Math.round(ctx.parsed.y)) + ' pps';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.04)',
                            drawBorder: false,
                        },
                        ticks: {
                            color: '#7a8494',
                            font: { size: 10 },
                            maxTicksLimit: 10,
                        }
                    },
                    y: {
                        display: true,
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.04)',
                            drawBorder: false,
                        },
                        ticks: {
                            color: '#7a8494',
                            font: { size: 10 },
                            callback: function(value) {
                                return formatPps(value);
                            }
                        }
                    }
                }
            }
        });
    }

    function initProtocolChart() {
        var canvas = document.getElementById('protocol-chart');
        if (!canvas) return;

        var ctx = canvas.getContext('2d');
        protocolChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['No Data'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['rgba(122, 132, 148, 0.2)'],
                    borderColor: ['rgba(122, 132, 148, 0.3)'],
                    borderWidth: 1,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                animation: { duration: 300 },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#7a8494',
                            font: { size: 10 },
                            padding: 12,
                            usePointStyle: true,
                            pointStyleWidth: 8,
                        }
                    },
                    tooltip: {
                        backgroundColor: '#222838',
                        titleColor: '#c8cdd5',
                        bodyColor: '#e8ecf1',
                        borderColor: '#2d3548',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(ctx) {
                                return ctx.label + ': ' + formatNumber(ctx.parsed) + ' pkts';
                            }
                        }
                    }
                }
            }
        });
    }

    function updateTrafficChart(pps, elapsed) {
        if (!trafficChart) return;

        var label = formatDuration(elapsed);
        chartData.labels.push(label);
        chartData.pps.push(pps);

        if (chartData.labels.length > maxChartPoints) {
            chartData.labels.shift();
            chartData.pps.shift();
        }

        trafficChart.data.labels = chartData.labels;
        trafficChart.data.datasets[0].data = chartData.pps;
        trafficChart.update('none');
    }

    function updateProtocolChart(generators) {
        if (!protocolChart) return;

        var entries = Object.entries(generators || {});
        var totalEl = document.getElementById('protocol-total');

        if (entries.length === 0) {
            protocolChart.data.labels = ['No Data'];
            protocolChart.data.datasets[0].data = [1];
            protocolChart.data.datasets[0].backgroundColor = ['rgba(122, 132, 148, 0.2)'];
            protocolChart.data.datasets[0].borderColor = ['rgba(122, 132, 148, 0.3)'];
            if (totalEl) {
                totalEl.querySelector('.chart-center-number').textContent = '0';
            }
            protocolChart.update();
            return;
        }

        // Group by protocol type
        var groups = {};
        var colors = {
            'tcp': '#4b8bf5',
            'udp': '#34c759',
            'icmp': '#ffb830',
            'http': '#f5503b',
            'dns': '#3bbdf5',
            'bulk': '#a855f7',
            'raw': '#ec4899',
            'ntp': '#14b8a6',
            'default': '#6b7280',
        };

        entries.forEach(function(entry) {
            var name = entry[0].toLowerCase();
            var packets = entry[1].packets_sent || 0;
            var type = 'default';
            for (var key in colors) {
                if (key !== 'default' && name.includes(key)) {
                    type = key;
                    break;
                }
            }
            if (!groups[type]) groups[type] = 0;
            groups[type] += packets;
        });

        var labels = [];
        var data = [];
        var bgColors = [];
        var borderColors = [];

        Object.keys(groups).sort(function(a, b) { return groups[b] - groups[a]; }).forEach(function(type) {
            labels.push(type.toUpperCase());
            data.push(groups[type]);
            var color = colors[type] || colors['default'];
            bgColors.push(color + '33');
            borderColors.push(color);
        });

        protocolChart.data.labels = labels;
        protocolChart.data.datasets[0].data = data;
        protocolChart.data.datasets[0].backgroundColor = bgColors;
        protocolChart.data.datasets[0].borderColor = borderColors;
        protocolChart.update();

        if (totalEl) {
            totalEl.querySelector('.chart-center-number').textContent = entries.length;
        }
    }

    // ---- Dashboard Stats ----

    function updateStats(data) {
        lastStats = data;
        updateHeaderStatus(data.running);

        var packets = document.getElementById('stat-packets');
        var pps = document.getElementById('stat-pps');
        var bytes = document.getElementById('stat-bytes');
        var errors = document.getElementById('stat-errors');
        var elapsed = document.getElementById('stat-elapsed');

        if (packets) packets.textContent = formatNumber(data.total_packets);
        if (pps) pps.innerHTML = formatPps(data.total_pps) + ' <small>pps</small>';
        if (bytes) bytes.textContent = formatBytes(data.total_bytes);
        if (errors) errors.textContent = formatNumber(data.total_errors);
        if (elapsed) elapsed.textContent = formatDuration(data.elapsed) + ' elapsed';

        updateGeneratorTable(data.generators || {});
        updateButtons(data.running);
        managePoll(data.running);

        // Update charts
        if (data.running) {
            updateTrafficChart(data.total_pps, data.elapsed);
        }
        updateProtocolChart(data.generators);

        // Update generator count badge
        var countBadge = document.getElementById('generator-count-badge');
        if (countBadge) {
            var count = Object.keys(data.generators || {}).length;
            countBadge.textContent = count + ' active';
            if (count > 0) {
                countBadge.style.background = 'rgba(75, 139, 245, 0.15)';
                countBadge.style.color = '#4b8bf5';
            } else {
                countBadge.style.background = '';
                countBadge.style.color = '';
            }
        }

        // Reset chart when stopped
        if (!data.running && chartData.pps.length > 0 && data.total_pps === 0) {
            chartData = { labels: [], pps: [], bytes: [] };
            if (trafficChart) {
                trafficChart.data.labels = [];
                trafficChart.data.datasets[0].data = [];
                trafficChart.update('none');
            }
        }
    }

    function updateGeneratorTable(generators) {
        var tbody = document.getElementById('generator-table');
        if (!tbody) return;

        var entries = Object.entries(generators);
        if (entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4"><i class="bi bi-inbox"></i> No active generators</td></tr>';
            return;
        }

        tbody.innerHTML = entries.map(function(entry) {
            var name = entry[0];
            var s = entry[1];
            var hasErrors = s.errors > 0;
            return '<tr>' +
                '<td><span class="gen-status gen-status-active"><span class="gen-status-dot"></span></span> ' + name + '</td>' +
                '<td class="text-end">' + formatNumber(s.packets_sent) + '</td>' +
                '<td class="text-end">' + formatPps(s.pps) + '</td>' +
                '<td class="text-end">' + formatBytes(s.bytes_sent) + '</td>' +
                '<td class="text-end">' + (hasErrors ? '<span style="color:var(--forti-danger)">' + s.errors + '</span>' : '0') + '</td>' +
                '<td class="text-end"><span class="forti-badge forti-badge-success">Active</span></td>' +
                '</tr>';
        }).join('');
    }

    function updateButtons(running) {
        var startBtn = document.getElementById('btn-start');
        var stopBtnTargeted = document.getElementById('btn-stop-targeted');
        var autoStartBtn = document.getElementById('btn-auto-start');
        var stopBtnAuto = document.getElementById('btn-stop-auto');
        // Old stop button (if exists)
        var stopBtn = document.getElementById('btn-stop');

        if (startBtn) startBtn.disabled = running;
        if (autoStartBtn) autoStartBtn.disabled = running;
        if (stopBtnTargeted) stopBtnTargeted.disabled = !running;
        if (stopBtnAuto) stopBtnAuto.disabled = !running;
        if (stopBtn) stopBtn.disabled = !running;
    }

    // ---- Session History ----

    function loadHistory() {
        fetch('/api/history?n=20')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var tbody = document.getElementById('history-table');
                if (!tbody) return;

                var sessions = data.sessions || [];
                if (sessions.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4"><i class="bi bi-inbox"></i> No previous sessions</td></tr>';
                    return;
                }

                tbody.innerHTML = sessions.map(function(s) {
                    var duration = s.end_time ? (s.end_time - s.start_time) : 0;
                    var statusBadge = s.status === 'running'
                        ? '<span class="forti-badge forti-badge-primary">Running</span>'
                        : '<span class="forti-badge forti-badge-success">Completed</span>';
                    var modeLabel = s.mode;
                    if (s.load_level) modeLabel += ' (' + s.load_level + ')';
                    if (s.dry_run) modeLabel += ' [dry]';

                    return '<tr>' +
                        '<td>' + s.id + '</td>' +
                        '<td>' + formatDateTime(s.start_time) + '</td>' +
                        '<td><span class="session-mode">' + modeLabel + '</span></td>' +
                        '<td>' + (s.target || '-') + '</td>' +
                        '<td>' + formatDuration(duration) + '</td>' +
                        '<td class="text-end">' + formatNumber(s.total_packets) + '</td>' +
                        '<td class="text-end">' + formatBytes(s.total_bytes) + '</td>' +
                        '<td class="text-end">' + (s.total_errors > 0 ? '<span style="color:var(--forti-danger)">' + s.total_errors + '</span>' : '0') + '</td>' +
                        '<td>' + statusBadge + '</td>' +
                        '</tr>';
                }).join('');
            })
            .catch(function() {});
    }
    // Export for inline onclick
    window.loadHistory = loadHistory;

    // ---- Polling Fallback ----

    function managePoll(running) {
        if (running && !pollInterval) {
            pollInterval = setInterval(function() {
                fetch('/api/status')
                    .then(function(r) { return r.json(); })
                    .then(function(data) { updateStats(data); })
                    .catch(function() {});
            }, 1000);
        } else if (!running && pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
            // Refresh history when engine stops
            loadHistory();
        }
    }

    // ---- Socket.IO Events ----

    socket.on('stats_update', updateStats);

    socket.on('log_message', function(data) {
        var miniLog = document.getElementById('mini-log');
        if (!miniLog) return;

        if (miniLog.querySelector('.text-muted')) {
            miniLog.innerHTML = '';
        }

        var line = document.createElement('div');
        line.className = 'forti-log-line';
        line.textContent = data.message;

        if (data.message.includes('Error') || data.message.includes('error')) {
            line.classList.add('log-error');
        } else if (data.message.includes('Starting') || data.message.includes('started')) {
            line.classList.add('log-success');
        } else if (data.message.includes('Stopped') || data.message.includes('stopping')) {
            line.classList.add('log-warning');
        }

        miniLog.appendChild(line);
        while (miniLog.children.length > 100) {
            miniLog.removeChild(miniLog.firstChild);
        }
        miniLog.scrollTop = miniLog.scrollHeight;
    });

    socket.on('connect', function() {
        isConnected = true;
    });

    socket.on('disconnect', function() {
        isConnected = false;
        updateHeaderStatus(false);
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    });

    // ---- Sidebar Toggle ----

    function setupSidebar() {
        var toggle = document.getElementById('sidebar-toggle');
        var sidebar = document.getElementById('sidebar');
        if (!toggle || !sidebar) return;

        toggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            document.body.classList.toggle('sidebar-collapsed');
        });
    }

    // ---- DOMContentLoaded ----

    document.addEventListener('DOMContentLoaded', function() {
        setupSidebar();
        initTrafficChart();
        initProtocolChart();
        loadHistory();

        // --- Auto mode: start button ---
        var autoStartBtn = document.getElementById('btn-auto-start');
        if (autoStartBtn) {
            autoStartBtn.addEventListener('click', function() {
                var loadLevel = 'medium';
                var checked = document.querySelector('input[name="load-level"]:checked');
                if (checked) loadLevel = checked.value;

                var duration = parseInt(document.getElementById('auto-duration').value) || 120;
                var dryRun = document.getElementById('auto-dry-run').checked;

                var payload = {
                    mode: 'auto',
                    load: loadLevel,
                    duration: duration,
                    dry_run: dryRun
                };

                // Reset chart data for new session
                chartData = { labels: [], pps: [], bytes: [] };

                fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) alert('Error: ' + data.error);
                })
                .catch(function(err) {
                    alert('Request failed: ' + err.message);
                });
            });
        }

        // --- Targeted mode: mode selector ---
        var modeSelect = document.getElementById('mode');
        var protoGroup = document.getElementById('protocol-group');
        if (modeSelect && protoGroup) {
            modeSelect.addEventListener('change', function() {
                protoGroup.style.display = this.value === 'protocol' ? 'block' : 'none';
            });

            var savedMode = localStorage.getItem('mode');
            if (savedMode) {
                modeSelect.value = savedMode;
                localStorage.removeItem('mode');
                if (savedMode === 'protocol') {
                    protoGroup.style.display = 'block';
                }
            }
        }

        // --- Targeted mode: start button ---
        var startForm = document.getElementById('quick-start-form');
        if (startForm) {
            startForm.addEventListener('submit', function(e) {
                e.preventDefault();
                var payload = {
                    target: document.getElementById('target').value,
                    ports: document.getElementById('ports').value,
                    mode: document.getElementById('mode').value,
                    duration: parseInt(document.getElementById('duration').value),
                    rate: parseInt(document.getElementById('rate').value),
                    dry_run: document.getElementById('dry-run').checked,
                };
                if (payload.mode === 'protocol') {
                    payload.protocol = document.getElementById('protocol').value;
                }

                chartData = { labels: [], pps: [], bytes: [] };

                fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) alert('Error: ' + data.error);
                })
                .catch(function(err) {
                    alert('Request failed: ' + err.message);
                });
            });
        }

        // --- Stop buttons ---
        ['btn-stop', 'btn-stop-auto', 'btn-stop-targeted'].forEach(function(id) {
            var btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', function() {
                    fetch('/api/stop', { method: 'POST' })
                        .then(function(r) { return r.json(); })
                        .then(function() {
                            updateButtons(false);
                            updateHeaderStatus(false);
                        });
                });
            }
        });

        // --- Initial status fetch ---
        fetch('/api/status')
            .then(function(r) { return r.json(); })
            .then(updateStats)
            .catch(function() {});
    });

})();
