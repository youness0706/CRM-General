/**
 * Dashboard Dynamic Data Loader
 * Handles all AJAX requests and client-side rendering
 * No page reloads - instant UI updates
 */

class DashboardManager {
    constructor() {
        this.charts = {
            income: null,
            unpaid: null
        };
        this.selectedTrainers = new Set();
        this.init();
    }

    async init() {
        // Set Chart.js defaults
        Chart.defaults.font.family = "'Tajawal', 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif";
        Chart.defaults.font.size = 14;

        // Load all data in parallel for maximum speed
        await this.loadAllData();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Hide loading indicator
        document.getElementById('loadingIndicator').style.display = 'none';
    }

    async loadAllData() {
        try {
            // Parallel requests for maximum speed
            const [chartData, paymentStatus, paidToday] = await Promise.all([
                this.fetchJSON('/api/chart-data/'),
                this.fetchJSON('/api/payment-status/'),
                this.fetchJSON('/api/paid-today/')
            ]);

            // Render all components
            this.renderCharts(chartData);
            this.renderPaymentStatus(paymentStatus.payment_status);
            this.renderPaidToday(paidToday.paid_today);
            
            // Show charts section
            document.getElementById('chartsSection').style.display = 'flex';
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showError('فشل تحميل البيانات. يرجى تحديث الصفحة.');
        }
    }

    async fetchJSON(url) {
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }

    renderCharts(data) {
        const colorPalette = {
            primary: ['rgba(78, 115, 223, 0.8)', 'rgba(54, 185, 204, 0.8)', 'rgba(28, 200, 138, 0.8)', 'rgba(246, 194, 62, 0.8)'],
            hover: ['rgba(78, 115, 223, 1)', 'rgba(54, 185, 204, 1)', 'rgba(28, 200, 138, 1)', 'rgba(246, 194, 62, 1)']
        };

        // Income by Category Chart
        const ctxCategory = document.getElementById('incomeByCategoryChart').getContext('2d');
        this.charts.income = new Chart(ctxCategory, {
            type: 'bar',
            data: {
                labels: data.chart_labels,
                datasets: [
                    {
                        label: 'شهرية',
                        data: data.chart_data.month,
                        backgroundColor: colorPalette.primary[0],
                        hoverBackgroundColor: colorPalette.hover[0],
                        borderRadius: 6,
                        borderSkipped: false
                    },
                    {
                        label: 'انخراط',
                        data: data.chart_data.subscription,
                        backgroundColor: colorPalette.primary[1],
                        hoverBackgroundColor: colorPalette.hover[1],
                        borderRadius: 6,
                        borderSkipped: false
                    },
                    {
                        label: 'التأمين',
                        data: data.chart_data.assurance,
                        backgroundColor: colorPalette.primary[2],
                        hoverBackgroundColor: colorPalette.hover[2],
                        borderRadius: 6,
                        borderSkipped: false
                    },
                    {
                        label: 'جواز',
                        data: data.chart_data.jawaz,
                        backgroundColor: colorPalette.primary[3],
                        hoverBackgroundColor: colorPalette.hover[3],
                        borderRadius: 6,
                        borderSkipped: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        titleColor: '#6e707e',
                        bodyColor: '#858796',
                        borderColor: '#e3e6f0',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y + ' DH';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        stacked: true,
                        grid: {
                            borderDash: [2],
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                }
            }
        });
    }

    renderPaymentStatus(paymentStatus) {
        const container = document.getElementById('paymentStatusContainer');
        container.innerHTML = '';

        // Calculate totals for unpaid trainers chart
        const chartLabels = [];
        const chartData = [];
        const chartColors = ['rgba(78, 115, 223, 0.8)', 'rgba(54, 185, 204, 0.8)', 'rgba(28, 200, 138, 0.8)', 'rgba(246, 194, 62, 0.8)'];

        Object.entries(paymentStatus).forEach(([category, status], index) => {
            chartLabels.push(status.label);
            chartData.push(status.total_unpaid_trainers);

            const colDiv = document.createElement('div');
            colDiv.className = 'col-md-4';
            
            const cardHTML = `
                <div class="card shadow-sm border-0 mb-4">
                    <div class="card-header bg-gradient-danger text-white py-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="m-0 font-weight-bold">${status.label} - غير مدفوعة</h6>
                            <div class="form-check">
                                <input class="form-check-input select-all-category" type="checkbox" 
                                       id="selectAll${category}" data-category="${category}"> 
                                <label class="form-check-label text-white mr-5" for="selectAll${category}">
                                    تحديد الكل
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="card-body px-4">
                        <div class="list-group list-group-flush">
                            ${this.renderUnpaidTrainers(status.unpaid_trainers, category)}
                        </div>
                    </div>
                </div>
            `;
            
            colDiv.innerHTML = cardHTML;
            container.appendChild(colDiv);
        });

        // Render unpaid trainers chart
        this.renderUnpaidChart(chartLabels, chartData, chartColors);
    }

    renderUnpaidTrainers(trainers, category) {
        if (trainers.length === 0) {
            return '<small class="text-success badge font-weight-bold m-3">الجميع مسدد</small>';
        }

        return trainers.map(trainer => `
            <a class="text-primary" href="/profile/${trainer.trainer_id}/">
                <div class="list-group-item border-0 px-0 py-3">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="d-flex align-items-center">
                            <div class="form-check me-3">
                                <input class="form-check-input trainer-checkbox" type="checkbox" 
                                       value="${trainer.trainer_id}" 
                                       id="trainer${trainer.trainer_id}"
                                       data-category="${category}">
                            </div>
                            <div class="avatar-circle bg-danger-light me-3">
                                ${trainer.trainer_name.charAt(0)}
                            </div>
                            <div>
                                <h6 class="mb-0">${trainer.trainer_name}</h6>
                                ${trainer.last_payment_date 
                                    ? `<small class="text-muted">آخر دفع: ${trainer.last_payment_date}</small>`
                                    : '<small class="text-danger">لم يدفع أبدًا</small>'
                                }
                            </div>
                        </div>
                        <span class="badge bg-danger rounded-pill">متأخر</span>
                    </div>
                </div>
            </a>
        `).join('');
    }

    renderUnpaidChart(labels, data, colors) {
        const ctxUnpaid = document.getElementById('unpaidTrainersChart').getContext('2d');
        this.charts.unpaid = new Chart(ctxUnpaid, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors,
                    hoverBackgroundColor: colors.map(c => c.replace('0.8', '1')),
                    borderWidth: 0,
                    cutout: '75%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        titleColor: '#6e707e',
                        bodyColor: '#858796',
                        borderColor: '#e3e6f0',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const value = context.parsed;
                                const percentage = ((value/total) * 100).toFixed(1);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderPaidToday(paidToday) {
        const container = document.getElementById('paidTodayContainer');
        
        if (paidToday.length === 0) {
            container.innerHTML = '<small class="text-success badge font-weight-bold m-3">لم يدفع أحد اليوم</small>';
            return;
        }

        container.innerHTML = paidToday.map(trainee => `
            <div class="list-group-item border-0 px-0 py-3">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <div class="avatar-circle bg-success me-3" style="background-color: rgba(40, 167, 69, 0.1); color: #28a745;">
                            ${trainee.trainer_name.charAt(0)}
                        </div>
                        <div>
                            <h6 class="mb-0">${trainee.trainer_name}</h6>
                            <small class="text-muted">${trainee.payment_date}</small>
                        </div>
                    </div>
                    <div>
                        <span class="badge badge-success">${trainee.payment_category}</span>
                        <span class="badge badge-primary">${trainee.payment_amount} DH</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    setupEventListeners() {
        // Delegate event listeners for dynamically loaded content
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('trainer-checkbox')) {
                this.handleTrainerCheckboxChange(e.target);
            } else if (e.target.classList.contains('select-all-category')) {
                this.handleSelectAllChange(e.target);
            }
        });

        // Bulk action buttons
        document.getElementById('deactivateSelected').addEventListener('click', () => {
            this.bulkDeactivate();
        });

        document.getElementById('clearSelection').addEventListener('click', () => {
            this.clearSelection();
        });
    }

    handleTrainerCheckboxChange(checkbox) {
        if (checkbox.checked) {
            this.selectedTrainers.add(checkbox.value);
        } else {
            this.selectedTrainers.delete(checkbox.value);
        }

        // Update select-all checkbox for this category
        const category = checkbox.dataset.category;
        const categoryCheckboxes = document.querySelectorAll(`.trainer-checkbox[data-category="${category}"]`);
        const categorySelectAll = document.querySelector(`.select-all-category[data-category="${category}"]`);
        
        const checkedCount = document.querySelectorAll(`.trainer-checkbox[data-category="${category}"]:checked`).length;
        
        if (checkedCount === categoryCheckboxes.length) {
            categorySelectAll.checked = true;
            categorySelectAll.indeterminate = false;
        } else if (checkedCount > 0) {
            categorySelectAll.checked = false;
            categorySelectAll.indeterminate = true;
        } else {
            categorySelectAll.checked = false;
            categorySelectAll.indeterminate = false;
        }

        this.updateBulkActionsBar();
    }

    handleSelectAllChange(selectAllCheckbox) {
        const category = selectAllCheckbox.dataset.category;
        const categoryCheckboxes = document.querySelectorAll(`.trainer-checkbox[data-category="${category}"]`);
        
        categoryCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
            if (selectAllCheckbox.checked) {
                this.selectedTrainers.add(checkbox.value);
            } else {
                this.selectedTrainers.delete(checkbox.value);
            }
        });

        this.updateBulkActionsBar();
    }

    updateBulkActionsBar() {
        const count = this.selectedTrainers.size;
        const bulkActionsBar = document.getElementById('bulkActionsBar');
        const selectedCountSpan = document.getElementById('selectedCount');
        
        if (count > 0) {
            bulkActionsBar.style.display = 'block';
            selectedCountSpan.textContent = count;
        } else {
            bulkActionsBar.style.display = 'none';
        }
    }

    clearSelection() {
        document.querySelectorAll('.trainer-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        document.querySelectorAll('.select-all-category').forEach(selectAll => {
            selectAll.checked = false;
            selectAll.indeterminate = false;
        });
        this.selectedTrainers.clear();
        this.updateBulkActionsBar();
    }

    async bulkDeactivate() {
        if (this.selectedTrainers.size === 0) {
            alert('يرجى تحديد متدربين أولاً');
            return;
        }

        if (!confirm(`هل أنت متأكد من إلغاء تفعيل ${this.selectedTrainers.size} متدرب؟`)) {
            return;
        }

        const button = document.getElementById('deactivateSelected');
        button.classList.add('loading-overlay');
        button.disabled = true;

        try {
            const response = await fetch('/api/bulk-deactivate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    trainer_ids: Array.from(this.selectedTrainers)
                })
            });

            const data = await response.json();

            if (data.success) {
                alert(data.message);
                
                // Remove deactivated trainers from UI
                this.selectedTrainers.forEach(trainerId => {
                    const checkbox = document.querySelector(`#trainer${trainerId}`);
                    if (checkbox) {
                        const listItem = checkbox.closest('.list-group-item');
                        if (listItem) {
                            listItem.remove();
                        }
                    }
                });

                this.selectedTrainers.clear();
                this.updateBulkActionsBar();
                
                // Reload data to update counts and charts
                setTimeout(() => {
                    this.loadAllData();
                }, 1000);
            } else {
                alert('خطأ: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('حدث خطأ أثناء إلغاء التفعيل');
        } finally {
            button.classList.remove('loading-overlay');
            button.disabled = false;
        }
    }

    getCSRFToken() {
        // Try to get CSRF token from cookie first (Django's default)
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        
        // Fallback to form field if cookie not found
        if (!cookieValue) {
            cookieValue = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        }
        
        return cookieValue;
    }

    showError(message) {
        document.getElementById('loadingIndicator').innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new DashboardManager();
});