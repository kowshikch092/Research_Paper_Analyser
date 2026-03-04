// Global utility functions
function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
}

function getScoreColor(score) {
    if (score >= 70) return 'success';
    if (score >= 50) return 'warning';
    return 'danger';
}

function showToast(message, type = 'info') {
    // Create toast container if not exists
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    // Create toast
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Initialize and show
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
    bsToast.show();

    // Remove after hide
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Clear history function
function clearHistory() {
    if (confirm('Are you sure you want to clear all analysis history?')) {
        fetch('/clear_history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('History cleared successfully', 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            }
        })
        .catch(error => {
            showToast('Error clearing history', 'danger');
        });
    }
}

// Export to PDF function
function exportToPDF(elementId, filename) {
    const element = document.getElementById(elementId);
    if (!element) return;

    // You can implement PDF export here using libraries like html2pdf
    // For now, just trigger the download endpoint
    window.location.href = `/download/${filename}`;
}

// Chart initialization for dashboard
function initializeCharts() {
    // Check if we're on a page with charts
    const chartCanvas = document.getElementById('scoresChart');
    if (!chartCanvas) return;

    // Get data from data attributes
    const readabilityScores = JSON.parse(chartCanvas.dataset.readability || '[]');
    const noveltyScores = JSON.parse(chartCanvas.dataset.novelty || '[]');
    const labels = JSON.parse(chartCanvas.dataset.labels || '[]');

    new Chart(chartCanvas, {
        type: 'radar',
        data: {
            labels: ['Readability', 'Grammar', 'Style', 'Coherence', 'Novelty'],
            datasets: [{
                label: 'Current Paper',
                data: readabilityScores,
                backgroundColor: 'rgba(67, 97, 238, 0.2)',
                borderColor: 'rgba(67, 97, 238, 1)',
                borderWidth: 2
            }]
        },
        options: {
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    
    // Add tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});