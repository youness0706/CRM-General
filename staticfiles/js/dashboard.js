/**
 * Fixed Dashboard Manager
 * Works with existing API structure
 */

class DashboardManager {
    constructor() {
        this.charts = {
            income: null,
            unpaid: null
        };
        this.selectedTrainers = new Set();
        this.currentPeriod = 'today';
        this.init();
    }

    async init() {
        console.log('Initializing dashboard...');
        
        // Configure Chart.js
        this.configureCharts();
        
        // Show loading skeletons
        this.showKPISkeletons();
        
        // Load data
        await this.loadAllData();
        
        // Setup event listeners
        this.setupEventListeners();
    }

    configureCharts() {
        Chart.defaults.font.family = "'Tajawal', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
        Chart.defaults.font.size = 13;
        Chart.defaults.color = '#858796';
    }

    showKPISkeletons() {
        const container = document.getElementById('kpiCards');
        const skeletons = Array(4).fill(0).map(() => `
            <div class="col-12 col-sm-6 col-xl-3">
                <div class="skeleton-card">
                    <div class="skeleton skeleton-line"></div>
                    <div class="skeleton skeleton-line large"></div>
                    <div class="skeleton skeleton-line small"></div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = skeletons;
    }

    async loadAllData() {
        try {
            console.log('Loading dashboard data...');
            
            // Load all data in parallel
            const [chartData, paymentStatus, paidToday] = await Promise.all([
                this.fetchJSON('/api/chart-data/'),
                this.fetchJSON('/api/payment-status/'),
                this.fetchJSON('/api/paid-today/')
            ]);

            console.log('Data loaded:', { chartData, paymentStatus, paidToday });

            // Calculate KPIs from the data we have
            this.renderKPIsFromData(paymentStatus, paidToday);
            
            // Render components
            this.renderCharts(chartData);
            this.renderPaymentStatus(paymentStatus.payment_status);
            this.renderPaidToday(paidToday.paid_today);
            
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
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }

    renderKPIsFromData(paymentStatus, paidToday) {
        const container = document.getElementById('kpiCards');
        
        // Calculate totals from payment status
        let totalUnpaid = 0;
        Object.values(paymentStatus.payment_status).forEach(status => {
            totalUnpaid += status.total_unpaid_trainers;
        });
        
        // Calculate income from paid today
        const todayIncome = paidToday.paid_today.reduce((sum, payment) => {
            return sum + parseFloat(payment.payment_amount);
        }, 0);
        
        const kpis = [
            {
                key: 'income',
                title: 'إجمالي الدخل (اليوم)',
                icon: 'fas fa-dollar-sign',
                value: `${todayIncome.toFixed(2)} د.م`,
                color: 'income'
            },
            {
                key: 'paid',
                title: 'دفعوا اليوم',
                icon: 'fas fa-check-circle',
                value: paidToday.paid_today.length,
                color: 'active'
            },
            {
                key: 'unpaid',
                title: 'غير مدفوع',
                icon: 'fas fa-exclamation-triangle',
                value: totalUnpaid,
                color: 'unpaid'
            },
            {
                key: 'categories',
                title: 'فئات المدفوعات',
                icon: 'fas fa-list',
                value: Object.keys(paymentStatus.payment_status).length,
                color: 'expiring'
            }
        ];

        container.innerHTML = kpis.map((kpi, index) => `
            <div class="col-12 col-sm-6 col-xl-3 fade-in" style="animation-delay: ${index * 0.1}s">
                <div class="kpi-card ${kpi.color}">
                    <div class="kpi-content">
                        <div class="kpi-text">
                            <p class="kpi-label">${kpi.title}</p>
                            <h2 class="kpi-value">${kpi.value}</h2>
                        </div>
                        <div class="kpi-icon ${kpi.color}">
                            <i class="${kpi.icon}"></i>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    renderCharts(data) {
        this.renderIncomeChart(data);
    }

    renderIncomeChart(data) {
        const ctx = document.getElementById('incomeByCategoryChart');
        if (!ctx) return;

        const colors = {
            month: { bg: 'rgba(78, 115, 223, 0.8)', border: 'rgb(78, 115, 223)' },
            subscription: { bg: 'rgba(54, 185, 204, 0.8)', border: 'rgb(54, 185, 204)' },
            assurance: { bg: 'rgba(28, 200, 138, 0.8)', border: 'rgb(28, 200, 138)' },
            jawaz: { bg: 'rgba(246, 194, 62, 0.8)', border: 'rgb(246, 194, 62)' }
        };

        const labels = {
            month: 'شهرية',
            subscription: 'انخراط',
            assurance: 'التأمين',
            jawaz: 'جواز'
        };

        if (this.charts.income) {
            this.charts.income.destroy();
        }

        this.charts.income = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.chart_labels,
                datasets: Object.keys(colors).map(key => ({
                    label: labels[key],
                    data: data.chart_data[key] || [],
                    backgroundColor: colors[key].bg,
                    borderColor: colors[key].border,
                    borderWidth: 0,
                    borderRadius: 8,
                    borderSkipped: false,
                }))
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
                        align: 'end',
                        labels: {
                            usePointStyle: true,
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#5a5c69',
                        bodyColor: '#858796',
                        borderColor: '#e3e6f0',
                        borderWidth: 1,
                        padding: 12,
                        boxPadding: 6,
                        usePointStyle: true,
                        rtl: true,
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${context.parsed.y.toLocaleString('ar-MA')} د.م`;
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
                        beginAtZero: true,
                        grid: {
                            borderDash: [2, 4],
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: (value) => value.toLocaleString('ar-MA')
                        }
                    }
                }
            }
        });
    }

    renderPaymentStatus(paymentStatus) {
        const container = document.getElementById('paymentStatusContainer');
        
        // Prepare chart data
        const chartData = Object.entries(paymentStatus).map(([key, status]) => ({
            label: status.label,
            count: status.total_unpaid_trainers
        }));

        // Render unpaid chart
        this.renderUnpaidChart(chartData);

        // Render cards
        container.innerHTML = Object.entries(paymentStatus)
            .map(([category, status]) => this.createPaymentCard(category, status))
            .join('');
    }

    createPaymentCard(category, status) {
        const hasUnpaid = status.unpaid_trainers.length > 0;

        return `
            <div class="col-lg-4 fade-in">
                <div class="card border-0 shadow-sm payment-status-card">
                    <div class="card-header bg-white border-0 py-3">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="mb-0 fw-semibold">${status.label}</h6>
                            ${hasUnpaid ? `
                                <div class="form-check">
                                    <input class="form-check-input select-all-category" 
                                           type="checkbox" 
                                           id="selectAll${category}" 
                                           data-category="${category}">
                                    <label class="form-check-label small" for="selectAll${category}">
                                        تحديد الكل
                                    </label>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    <div class="card-body p-0">
                        ${hasUnpaid ? 
                            status.unpaid_trainers.map(trainer => 
                                this.createTrainerItem(trainer, category)
                            ).join('') :
                            `<div class="empty-state">
                                <div class="empty-state-icon">
                                    <i class="fas fa-check-circle text-success"></i>
                                </div>
                                <p class="empty-state-text">الجميع مسدد ✓</p>
                            </div>`
                        }
                    </div>
                </div>
            </div>
        `;
    }

    createTrainerItem(trainer, category) {
        const initials = trainer.trainer_name.split(' ')
            .map(n => n[0])
            .slice(0, 2)
            .join('');

        return `
            <a href="/profile/${trainer.trainer_id}/" class="trainer-item">
                <input class="form-check-input trainer-checkbox" 
                       type="checkbox" 
                       value="${trainer.trainer_id}" 
                       id="trainer${trainer.trainer_id}"
                       data-category="${category}">
                <div class="trainer-avatar" style="background: linear-gradient(135deg, #e74a3b 0%, #c0392b 100%);">
                    ${initials}
                </div>
                <div class="trainer-info">
                    <h6 class="trainer-name">${trainer.trainer_name}</h6>
                    <p class="trainer-meta">
                        ${trainer.last_payment_date 
                            ? `آخر دفع: ${this.formatDate(trainer.last_payment_date)}`
                            : '<span class="text-danger">لم يدفع أبدًا</span>'
                        }
                    </p>
                </div>
                <span class="badge bg-danger rounded-pill">متأخر</span>
            </a>
        `;
    }

    renderUnpaidChart(data) {
        const ctx = document.getElementById('unpaidTrainersChart');
        if (!ctx) return;

        const hasData = data.some(d => d.count > 0);

        if (!hasData) {
            ctx.parentElement.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <i class="fas fa-check-circle text-success"></i>
                    </div>
                    <p class="empty-state-text">لا يوجد متدربون غير مدفوعين!</p>
                </div>
            `;
            return;
        }

        const colors = [
            'rgba(78, 115, 223, 0.8)',
            'rgba(54, 185, 204, 0.8)',
            'rgba(28, 200, 138, 0.8)',
            'rgba(246, 194, 62, 0.8)'
        ];

        if (this.charts.unpaid) {
            this.charts.unpaid.destroy();
        }

        this.charts.unpaid = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: colors,
                    borderWidth: 0,
                    cutout: '70%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#5a5c69',
                        bodyColor: '#858796',
                        borderColor: '#e3e6f0',
                        borderWidth: 1,
                        padding: 12,
                        rtl: true,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${context.label}: ${context.parsed} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    renderPaidToday(paidToday) {
        const container = document.getElementById('paidTodayContainer');
        const countBadge = document.getElementById('paidTodayCount');
        
        countBadge.textContent = paidToday.length;

        if (paidToday.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <i class="fas fa-calendar-day"></i>
                    </div>
                    <p class="empty-state-text">لم يدفع أحد اليوم</p>
                </div>
            `;
            return;
        }

        container.innerHTML = paidToday.map(payment => {
            const initials = payment.trainer_name.split(' ')
                .map(n => n[0])
                .slice(0, 2)
                .join('');

            return `
                <div class="trainer-item">
                    <div class="trainer-avatar" style="background: linear-gradient(135deg, #1cc88a 0%, #17a673 100%);">
                        ${initials}
                    </div>
                    <div class="trainer-info">
                        <h6 class="trainer-name">${payment.trainer_name}</h6>
                        <p class="trainer-meta">${this.formatDate(payment.payment_date)}</p>
                    </div>
                    <div class="d-flex gap-2 flex-wrap">
                        <span class="badge bg-primary">${payment.payment_category}</span>
                        <span class="badge bg-success">${payment.payment_amount} د.م</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    setupEventListeners() {
        // Period filter
        document.querySelectorAll('input[name="period"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentPeriod = e.target.value;
                console.log('Period changed to:', this.currentPeriod);
                // Note: You can add logic here to filter data by period if your API supports it
            });
        });

        // Bulk actions
        const deactivateBtn = document.getElementById('deactivateSelected');
        if (deactivateBtn) {
            deactivateBtn.addEventListener('click', () => this.bulkDeactivate());
        }

        const clearBtn = document.getElementById('clearSelection');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearSelection());
        }

        // Delegate checkbox events
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('select-all-category')) {
                this.handleSelectAll(e.target);
            } else if (e.target.classList.contains('trainer-checkbox')) {
                this.handleCheckboxChange(e.target);
            }
        });
    }

    handleCheckboxChange(checkbox) {
        if (checkbox.checked) {
            this.selectedTrainers.add(checkbox.value);
        } else {
            this.selectedTrainers.delete(checkbox.value);
        }

        const category = checkbox.dataset.category;
        this.updateSelectAllState(category);
        this.updateBulkActionsBar();
    }

    handleSelectAll(checkbox) {
        const category = checkbox.dataset.category;
        const categoryCheckboxes = document.querySelectorAll(
            `.trainer-checkbox[data-category="${category}"]`
        );

        categoryCheckboxes.forEach(cb => {
            cb.checked = checkbox.checked;
            if (checkbox.checked) {
                this.selectedTrainers.add(cb.value);
            } else {
                this.selectedTrainers.delete(cb.value);
            }
        });

        this.updateBulkActionsBar();
    }

    updateSelectAllState(category) {
        const selectAll = document.querySelector(`.select-all-category[data-category="${category}"]`);
        if (!selectAll) return;

        const checkboxes = document.querySelectorAll(`.trainer-checkbox[data-category="${category}"]`);
        const checked = document.querySelectorAll(`.trainer-checkbox[data-category="${category}"]:checked`);

        if (checked.length === 0) {
            selectAll.checked = false;
            selectAll.indeterminate = false;
        } else if (checked.length === checkboxes.length) {
            selectAll.checked = true;
            selectAll.indeterminate = false;
        } else {
            selectAll.checked = false;
            selectAll.indeterminate = true;
        }
    }

    updateBulkActionsBar() {
        const bar = document.getElementById('bulkActionsBar');
        const count = document.getElementById('selectedCount');
        
        count.textContent = this.selectedTrainers.size;
        bar.style.display = this.selectedTrainers.size > 0 ? 'block' : 'none';
    }

    clearSelection() {
        this.selectedTrainers.clear();
        
        document.querySelectorAll('.trainer-checkbox').forEach(cb => {
            cb.checked = false;
        });
        
        document.querySelectorAll('.select-all-category').forEach(cb => {
            cb.checked = false;
            cb.indeterminate = false;
        });
        
        this.updateBulkActionsBar();
    }

    async bulkDeactivate() {
        if (this.selectedTrainers.size === 0) return;

        if (!confirm(`هل أنت متأكد من إلغاء تفعيل ${this.selectedTrainers.size} متدرب؟`)) {
            return;
        }

        const button = document.getElementById('deactivateSelected');
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>جاري الحفظ...';

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
                if (window.showToast) {
                    window.showToast(data.message, 'success');
                } else {
                    alert(data.message);
                }
                
                this.clearSelection();
                setTimeout(() => this.loadAllData(), 1000);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Bulk deactivate error:', error);
            if (window.showToast) {
                window.showToast('حدث خطأ أثناء إلغاء التفعيل', 'error');
            } else {
                alert('حدث خطأ أثناء إلغاء التفعيل');
            }
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-user-slash me-1"></i> إلغاء التفعيل';
        }
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('ar-MA', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        
        if (document.cookie) {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        
        if (!cookieValue) {
            cookieValue = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        }
        
        return cookieValue;
    }

    showError(message) {
        console.error(message);
        const kpiContainer = document.getElementById('kpiCards');
        kpiContainer.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            </div>
        `;
    }
}

// Initialize
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');
    dashboard = new DashboardManager();
});