/**
 * Enhanced Dashboard Manager
 * Optimized for performance with intelligent caching, progressive loading, and smooth UX
 */

class DashboardManager {
    constructor() {
        this.charts = {
            income: null,
            unpaid: null
        };
        this.selectedTrainers = new Set();
        this.currentPeriod = 'today';
        this.cache = new Map();
        this.init();
    }

    async init() {
        // Configure Chart.js defaults
        this.configureCharts();
        
        // Load initial data
        await this.loadDashboardData();
        
        // Setup event listeners
        this.setupEventListeners();
    }

    configureCharts() {
        Chart.defaults.font.family = "'Tajawal', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
        Chart.defaults.font.size = 13;
        Chart.defaults.color = '#858796';
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 16;
    }

    async loadDashboardData() {
        try {
            // Progressive data loading for better perceived performance
            // Load KPIs first (most important)
            const kpiPromise = this.loadKPIs();
            
            // Then load charts and lists in parallel
            const [kpiData, chartData, paymentStatus, paidToday] = await Promise.all([
                kpiPromise,
                this.fetchWithCache('/api/chart-data/'),
                this.fetchWithCache('/api/payment-status/'),
                this.fetchWithCache('/api/paid-today/')
            ]);

            // Render in priority order
            this.renderKPIs(kpiData);
            this.renderCharts(chartData);
            this.renderPaymentStatus(paymentStatus.payment_status);
            this.renderPaidToday(paidToday.paid_today);
            
        } catch (error) {
            console.error('Dashboard loading error:', error);
            this.showError('فشل تحميل بعض البيانات. يرجى تحديث الصفحة.');
        }
    }

    async fetchWithCache(url, ttl = 300000) {
        // Check cache first (5 min TTL)
        const cached = this.cache.get(url);
        if (cached && Date.now() - cached.timestamp < ttl) {
            return cached.data;
        }

        const response = await fetch(url, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        
        // Cache the response
        this.cache.set(url, {
            data,
            timestamp: Date.now()
        });

        return data;
    }

    async loadKPIs() {
        // Simulate KPI calculation (replace with actual API call)
        // This should come from your Django backend
        return {
            income: {
                value: 'جاري التحميل...',
                change: null,
                trend: null
            },
            active: {
                value: 'جاري التحميل...',
                change: null,
                trend: null
            },
            unpaid: {
                value: 'جاري التحميل...',
                change: null,
                trend: null
            },
            expiring: {
                value: 'جاري التحميل...',
                change: null,
                trend: null
            }
        };
    }

    renderKPIs(data) {
        const kpiContainer = document.getElementById('kpiCards');
        
        const kpis = [
            {
                key: 'income',
                title: 'إجمالي الدخل',
                icon: 'fas fa-dollar-sign',
                color: 'success',
                format: (val) => `${val} د.م`
            },
            {
                key: 'active',
                title: 'المتدربون النشطون',
                icon: 'fas fa-users',
                color: 'primary',
                format: (val) => val
            },
            {
                key: 'unpaid',
                title: 'غير مدفوع',
                icon: 'fas fa-exclamation-triangle',
                color: 'danger',
                format: (val) => val
            },
            {
                key: 'expiring',
                title: 'اشتراكات منتهية قريباً',
                icon: 'fas fa-clock',
                color: 'warning',
                format: (val) => val
            }
        ];

        kpiContainer.innerHTML = kpis.map(kpi => {
            const kpiData = data[kpi.key];
            const changeClass = kpiData.trend === 'up' ? 'positive' : 
                               kpiData.trend === 'down' ? 'negative' : '';
            const changeIcon = kpiData.trend === 'up' ? 'fa-arrow-up' : 
                              kpiData.trend === 'down' ? 'fa-arrow-down' : '';

            return `
                <div class="col-12 col-sm-6 col-xl-3 fade-in" data-kpi="${kpi.key}">
                    <div class="card border-0 shadow-sm kpi-card ${kpi.key}">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-3">
                                <div>
                                    <p class="text-muted mb-0 small text-uppercase">${kpi.title}</p>
                                </div>
                                <div class="kpi-icon bg-${kpi.color} bg-opacity-10">
                                    <i class="${kpi.icon} text-${kpi.color}"></i>
                                </div>
                            </div>
                            <h2 class="kpi-value mb-1">${kpi.format(kpiData.value)}</h2>
                            ${kpiData.change ? `
                                <p class="kpi-change mb-0 ${changeClass}">
                                    <i class="fas ${changeIcon} me-1"></i>
                                    ${kpiData.change}
                                </p>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
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

        // Destroy existing chart
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
                    borderRadius: 6,
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
                        align: 'end'
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
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${context.parsed.y.toLocaleString()} د.م`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                family: "'Tajawal', sans-serif"
                            }
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
                            callback: (value) => value.toLocaleString()
                        }
                    }
                }
            }
        });
    }

    renderPaymentStatus(paymentStatus) {
        const container = document.getElementById('paymentStatusContainer');
        
        // Prepare data for unpaid chart
        const chartData = Object.entries(paymentStatus).map(([key, status]) => ({
            label: status.label,
            count: status.total_unpaid_trainers,
            trainers: status.unpaid_trainers
        }));

        // Render unpaid chart
        this.renderUnpaidChart(chartData);

        // Render payment status cards
        container.innerHTML = Object.entries(paymentStatus)
            .map(([category, status]) => this.createPaymentStatusCard(category, status))
            .join('');
    }

    createPaymentStatusCard(category, status) {
        const hasUnpaid = status.unpaid_trainers.length > 0;
        const showCount = Math.min(5, status.unpaid_trainers.length);
        const hasMore = status.unpaid_trainers.length > 5;

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
                        ${hasUnpaid ? `
                            <div class="trainer-list" data-category="${category}">
                                ${status.unpaid_trainers.slice(0, showCount).map(trainer => 
                                    this.createTrainerItem(trainer, category)
                                ).join('')}
                            </div>
                            ${hasMore ? `
                                <button class="show-more-btn" onclick="dashboard.toggleShowAll('${category}')">
                                    <i class="fas fa-chevron-down me-1"></i>
                                    عرض المزيد (${status.unpaid_trainers.length - showCount})
                                </button>
                            ` : ''}
                        ` : `
                            <div class="empty-state">
                                <div class="empty-state-icon">
                                    <i class="fas fa-check-circle text-success"></i>
                                </div>
                                <p class="empty-state-text">الجميع مسدد ✓</p>
                            </div>
                        `}
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
                       data-category="${category}"
                       onclick="event.preventDefault(); event.stopPropagation(); this.checked = !this.checked; dashboard.handleCheckboxChange(this);">
                <div class="trainer-avatar bg-danger bg-opacity-10 text-danger">
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
                <span class="badge bg-danger">متأخر</span>
            </a>
        `;
    }

    renderUnpaidChart(data) {
        const ctx = document.getElementById('unpaidTrainersChart');
        if (!ctx) return;

        const colors = [
            'rgba(78, 115, 223, 0.8)',
            'rgba(54, 185, 204, 0.8)',
            'rgba(28, 200, 138, 0.8)',
            'rgba(246, 194, 62, 0.8)'
        ];

        if (this.charts.unpaid) {
            this.charts.unpaid.destroy();
        }

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
                        position: 'bottom'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#5a5c69',
                        bodyColor: '#858796',
                        borderColor: '#e3e6f0',
                        borderWidth: 1,
                        padding: 12,
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
                    <div class="trainer-avatar bg-success bg-opacity-10 text-success">
                        ${initials}
                    </div>
                    <div class="trainer-info">
                        <h6 class="trainer-name">${payment.trainer_name}</h6>
                        <p class="trainer-meta">${this.formatDate(payment.payment_date)}</p>
                    </div>
                    <div class="d-flex gap-2">
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
                this.loadDashboardData();
            });
        });

        // Bulk actions
        document.getElementById('deactivateSelected')?.addEventListener('click', () => {
            this.bulkDeactivate();
        });

        document.getElementById('clearSelection')?.addEventListener('click', () => {
            this.clearSelection();
        });

        // Delegate checkbox events
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('select-all-category')) {
                this.handleSelectAll(e.target);
            }
        });
    }

    handleCheckboxChange(checkbox) {
        if (checkbox.checked) {
            this.selectedTrainers.add(checkbox.value);
        } else {
            this.selectedTrainers.delete(checkbox.value);
        }

        // Update select-all state
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
        
        if (this.selectedTrainers.size > 0) {
            bar.classList.add('show');
        } else {
            bar.classList.remove('show');
        }
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
                this.showToast(data.message, 'success');
                this.clearSelection();
                
                // Clear cache and reload
                this.cache.clear();
                setTimeout(() => this.loadDashboardData(), 1000);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Bulk deactivate error:', error);
            this.showToast('حدث خطأ أثناء إلغاء التفعيل', 'error');
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-user-slash me-1"></i> إلغاء التفعيل';
        }
    }

    toggleShowAll(category) {
        const list = document.querySelector(`.trainer-list[data-category="${category}"]`);
        const button = event.target;
        
        if (list.classList.contains('show-all')) {
            list.classList.remove('show-all');
            button.innerHTML = '<i class="fas fa-chevron-down me-1"></i> عرض المزيد';
        } else {
            list.classList.add('show-all');
            button.innerHTML = '<i class="fas fa-chevron-up me-1"></i> عرض أقل';
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

    showToast(message, type = 'success') {
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
            alert(message);
        }
    }

    showError(message) {
        console.error(message);
        this.showToast(message, 'error');
    }
}

// Initialize
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new DashboardManager();
});