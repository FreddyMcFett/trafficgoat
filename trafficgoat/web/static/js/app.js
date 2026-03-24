/* TrafficGoat Web UI - Main JavaScript */

(function() {
    'use strict';

    // Socket.IO connection
    const socket = io();

    // Export for other pages
    window.trafficGoat = { socket: socket };

    // ---- Utility Functions ----

    function formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
    }

    function formatNumber(n) {
        return n.toLocaleString();
    }

    // ---- Status Badge ----

    function updateStatusBadge(running) {
        const badge = document.getElementById('engine-status');
        if (!badge) return;
        if (running) {
            badge.textContent = 'Running';
            badge.className = 'badge bg-success badge-pulse';
        } else {
            badge.textContent = 'Idle';
            badge.className = 'badge bg-secondary';
        }
    }

    // ---- Dashboard Stats ----

    function updateStats(data) {
        updateStatusBadge(data.running);

        const packets = document.getElementById('stat-packets');
        const pps = document.getElementById('stat-pps');
        const bytes = document.getElementById('stat-bytes');
        const errors = document.getElementById('stat-errors');
        const elapsed = document.getElementById('stat-elapsed');

        if (packets) packets.textContent = formatNumber(data.total_packets);
        if (pps) pps.innerHTML = formatNumber(Math.round(data.total_pps)) + ' <small class="fs-6">pps</small>';
        if (bytes) bytes.textContent = formatBytes(data.total_bytes);
        if (errors) errors.textContent = formatNumber(data.total_errors);
        if (elapsed) elapsed.textContent = data.elapsed.toFixed(1) + 's';

        // Update generator table
        updateGeneratorTable(data.generators || {});

        // Update button states
        updateButtons(data.running);
    }

    function updateGeneratorTable(generators) {
        const tbody = document.getElementById('generator-table');
        if (!tbody) return;

        const entries = Object.entries(generators);
        if (entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No active generators. Configure and start a test above.</td></tr>';
            return;
        }

        tbody.innerHTML = entries.map(function(entry) {
            const name = entry[0];
            const s = entry[1];
            return '<tr>' +
                '<td><i class="bi bi-broadcast text-success"></i> ' + name + '</td>' +
                '<td class="text-end">' + formatNumber(s.packets_sent) + '</td>' +
                '<td class="text-end">' + s.pps.toFixed(1) + ' pps</td>' +
                '<td class="text-end">' + formatBytes(s.bytes_sent) + '</td>' +
                '<td class="text-end">' + (s.errors > 0 ? '<span class="text-danger">' + s.errors + '</span>' : '0') + '</td>' +
                '</tr>';
        }).join('');
    }

    function updateButtons(running) {
        const startBtn = document.getElementById('btn-start');
        const stopBtn = document.getElementById('btn-stop');
        if (startBtn) startBtn.disabled = running;
        if (stopBtn) stopBtn.disabled = !running;
    }

    // ---- Socket.IO Events ----

    socket.on('stats_update', updateStats);

    socket.on('log_message', function(data) {
        const miniLog = document.getElementById('mini-log');
        if (!miniLog) return;

        if (miniLog.querySelector('.text-muted:first-child')) {
            miniLog.innerHTML = '';
        }

        const line = document.createElement('div');
        line.className = 'log-line px-1';
        line.textContent = data.message;

        if (data.message.includes('Error') || data.message.includes('error')) {
            line.classList.add('text-danger');
        } else if (data.message.includes('Starting') || data.message.includes('started')) {
            line.classList.add('text-success');
        } else if (data.message.includes('Stopped') || data.message.includes('stopping')) {
            line.classList.add('text-warning');
        }

        miniLog.appendChild(line);
        while (miniLog.children.length > 100) {
            miniLog.removeChild(miniLog.firstChild);
        }
        miniLog.scrollTop = miniLog.scrollHeight;
    });

    socket.on('connect', function() {
        console.log('TrafficGoat: Connected to server');
    });

    socket.on('disconnect', function() {
        updateStatusBadge(false);
    });

    // ---- Quick Start Form ----

    document.addEventListener('DOMContentLoaded', function() {
        // Mode selector - show/hide protocol dropdown
        const modeSelect = document.getElementById('mode');
        const protoGroup = document.getElementById('protocol-group');
        if (modeSelect && protoGroup) {
            modeSelect.addEventListener('change', function() {
                protoGroup.style.display = this.value === 'protocol' ? 'block' : 'none';
            });

            // Restore mode from localStorage (from modes page)
            const savedMode = localStorage.getItem('mode');
            if (savedMode) {
                modeSelect.value = savedMode;
                localStorage.removeItem('mode');
                if (savedMode === 'protocol') {
                    protoGroup.style.display = 'block';
                }
            }
        }

        // Start button
        const startForm = document.getElementById('quick-start-form');
        if (startForm) {
            startForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const payload = {
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

                fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(function(err) {
                    alert('Request failed: ' + err.message);
                });
            });
        }

        // Stop button
        const stopBtn = document.getElementById('btn-stop');
        if (stopBtn) {
            stopBtn.addEventListener('click', function() {
                fetch('/api/stop', { method: 'POST' })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        console.log('Stopped:', data);
                    });
            });
        }

        // Initial status fetch
        fetch('/api/status')
            .then(function(r) { return r.json(); })
            .then(updateStats)
            .catch(function() {});
    });

})();
