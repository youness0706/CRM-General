/**
 * Financial Report Manager
 * Fixed chart behavior:
 * - Always plots month-by-month (no yearly aggregation that “spreads” totals)
 * - Ensures numeric arrays (no strings/decimals causing weird plotting)
 * - Prevents Y-axis collapse with grace + suggestedMin/Max
 * - Better mobile sizing + clearer lines
 */

class FinancialReportManager {
    constructor() {
        this.startDate = null;
        this.endDate = null;
        this.chart = null;
        this.currentData = null;
        this.previousData = null; // For comparison
        this.init();
    }

    async init() {
        console.log('Initializing Financial Report...');

        // Default dates (current year)
        const today = new Date();
        this.startDate = new Date(today.getFullYear(), 0, 1);
        this.endDate = new Date(today.getFullYear(), 11, 31);

        // Initialize UI
        this.setupEventListeners();
        this.updateDateInputs();

        // Load report
        await this.loadReport();
    }

    setupEventListeners() {
        // Apply date range button
        const applyBtn = document.getElementById('applyDateRange');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => this.applyDateRange());
        }

        // Quick period buttons
        document.querySelectorAll('.quick-period').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const period = e.target?.dataset?.period;
                if (period) this.setQuickPeriod(period);
            });
        });

        // Section toggle buttons
        document.querySelectorAll('.toggle-section').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const button = e.target.closest('button');
                if (button) this.toggleSection(button);
            });
        });

        // Export button
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportReport());
        }
    }

    setQuickPeriod(period) {
        const today = new Date();

        switch (period) {
            case 'today':
                this.startDate = new Date(today);
                this.endDate = new Date(today);
                break;
            case 'week': {
                const d = new Date();
                const day = d.getDay(); // 0..6
                const diff = d.getDate() - day; // start of week (Sunday)
                this.startDate = new Date(d.getFullYear(), d.getMonth(), diff);
                this.endDate = new Date();
                break;
            }
            case 'month':
                this.startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                this.endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                break;
            case 'year':
            default:
                this.startDate = new Date(today.getFullYear(), 0, 1);
                this.endDate = new Date(today.getFullYear(), 11, 31);
                break;
        }

        this.updateDateInputs();
        this.applyDateRange();
    }

    updateDateInputs() {
        const startEl = document.getElementById('start-date');
        const endEl = document.getElementById('end-date');

        if (startEl) startEl.value = this.formatDateForInput(this.startDate);
        if (endEl) endEl.value = this.formatDateForInput(this.endDate);
    }

    applyDateRange() {
        const startInput = document.getElementById('start-date')?.value;
        const endInput = document.getElementById('end-date')?.value;

        if (!startInput || !endInput) {
            this.showToast('الرجاء اختيار تاريخ البداية والنهاية', 'error');
            return;
        }

        this.startDate = new Date(startInput);
        this.endDate = new Date(endInput);

        // Update period text
        this.updatePeriodText();

        // Close modal
        const modalEl = document.getElementById('periodModal');
        if (modalEl && window.bootstrap?.Modal) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }

        // Reload report
        this.loadReport();
    }

    updatePeriodText() {
        const startStr = this.formatDateArabic(this.startDate);
        const endStr = this.formatDateArabic(this.endDate);

        const periodText = document.getElementById('period-text');
        if (periodText) periodText.textContent = `من ${startStr} إلى ${endStr}`;
    }

    async loadReport() {
        this.showLoading();

        try {
            const params = new URLSearchParams({
                start: this.formatDateForInput(this.startDate),
                end: this.formatDateForInput(this.endDate)
            });

            console.log('Loading report with params:', params.toString());

            const response = await fetch(`/api/financial-report/?${params}`);
            console.log('Response status:', response.status);

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            console.log('Report data received:', data);

            if (data?.success === false) {
                throw new Error(data.error || 'فشل تحميل التقرير');
            }

            // Store current data
            this.previousData = this.currentData;
            this.currentData = data;

            // Render everything
            this.renderReport(data);

            // Update period text
            this.updatePeriodText();

            // Enable export
            const exportBtn = document.getElementById('exportBtn');
            if (exportBtn) exportBtn.disabled = false;

            this.hideLoading();
        } catch (error) {
            console.error('Error loading report:', error);
            this.showError(`حدث خطأ أثناء تحميل التقرير: ${error.message}`);
        }
    }

    renderReport(data) {
        this.renderSummaryCards(data);
        this.renderChart();
        this.renderIncomeTable(data.income);
        this.renderExpenseTable(data.expenses);
    }

    renderSummaryCards(data) {
        const { summary } = data;

        // Calculate changes if we have previous data
        let incomeChange = null;
        let expenseChange = null;
        let profitChange = null;

        if (this.previousData?.summary) {
            incomeChange = this.calculateChange(
                this.previousData.summary.total_income,
                summary.total_income
            );
            expenseChange = this.calculateChange(
                this.previousData.summary.total_costs,
                summary.total_costs
            );
            profitChange = this.calculateChange(
                this.previousData.summary.net_profit,
                summary.net_profit
            );
        }

        // Update values
        const incomeEl = document.getElementById('total-income');
        const expEl = document.getElementById('total-expenses');
        const profitEl = document.getElementById('net-profit');

        if (incomeEl) incomeEl.textContent = this.formatCurrency(summary.total_income);
        if (expEl) expEl.textContent = this.formatCurrency(summary.total_costs);
        if (profitEl) profitEl.textContent = this.formatCurrency(summary.net_profit);

        // Update changes
        this.updateChangeIndicator('income-change', incomeChange, true);
        this.updateChangeIndicator('expense-change', expenseChange, false);
        this.updateChangeIndicator('profit-change', profitChange, true);
    }

    calculateChange(oldValue, newValue) {
        const oldNum = Number(oldValue);
        const newNum = Number(newValue);

        if (!oldNum || oldNum === 0 || !isFinite(oldNum) || !isFinite(newNum)) return null;

        const percentChange = ((newNum - oldNum) / oldNum) * 100;
        return {
            percent: percentChange,
            isPositive: percentChange >= 0
        };
    }

    updateChangeIndicator(elementId, change, positiveIsGood) {
        const element = document.getElementById(elementId);
        if (!element) return;

        if (!change) {
            element.textContent = '';
            element.className = '';
            return;
        }

        const icon = change.isPositive ? 'fa-arrow-up' : 'fa-arrow-down';
        const isGood = positiveIsGood ? change.isPositive : !change.isPositive;
        const className = isGood ? 'positive' : 'negative';

        element.innerHTML = `
            <i class="fas ${icon}"></i>
            ${Math.abs(change.percent).toFixed(1)}%
        `;
        element.className = `change-badge ${className}`;
    }

    async renderChart() {
        const canvas = document.getElementById('financialChart');
        if (!canvas) {
            console.error('Chart canvas not found');
            return;
        }

        // Improve mobile rendering: enforce reasonable height for the container
        if (canvas.parentElement) {
            canvas.parentElement.style.minHeight = '280px';
        }

        const ctx = canvas.getContext('2d');

        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }

        try {
            const monthlyData = await this.fetchMonthlyData();

                if (!monthlyData || monthlyData.length === 0) {
                    console.error('No monthly data received');
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.fillStyle = '#666';
                    ctx.font = '14px Cairo';
                    ctx.textAlign = 'center';
                    ctx.fillText('لا توجد بيانات لعرضها', canvas.width / 2, canvas.height / 2);
                    return;
                }

                // Decide granularity
    const useDaily = this.isSingleCalendarMonth();

    let labels, income, expenses;

    // If single month => daily breakdown
    if (useDaily) {
        const dailyData = await this.fetchDailyData();

        if (!dailyData || dailyData.length === 0) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#666';
            ctx.font = '14px Cairo';
            ctx.textAlign = 'center';
            ctx.fillText('لا توجد بيانات يومية لعرضها', canvas.width / 2, canvas.height / 2);
            return;
        }

        const prepared = this.prepareDailyData(dailyData);
        labels = prepared.labels;
        income = prepared.income;
        expenses = prepared.expenses;

    } else {
        const monthlyData = await this.fetchMonthlyData();

        if (!monthlyData || monthlyData.length === 0) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#666';
            ctx.font = '14px Cairo';
            ctx.textAlign = 'center';
            ctx.fillText('لا توجد بيانات لعرضها', canvas.width / 2, canvas.height / 2);
            return;
        }

        const prepared = this.prepareMonthlyData(monthlyData);
        labels = prepared.labels;
        income = prepared.income;
        expenses = prepared.expenses;
    }


            if (!labels.length) {
                console.error('No labels generated');
                return;
            }

            // Compute scale bounds to avoid “flat” collapse
            const allValues = [...income, ...expenses].map(v => Number(v) || 0);
            const minVal = Math.min(...allValues);
            const maxVal = Math.max(...allValues);

            // If everything is equal, still give the axis some range
            const pad = (maxVal - minVal) === 0 ? (maxVal === 0 ? 10 : maxVal * 0.1) : (maxVal - minVal) * 0.1;
            const suggestedMin = Math.max(0, minVal - pad);
            const suggestedMax = maxVal + pad;

            this.chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels,
                    datasets: [
                        {
                            label: 'الإيرادات',
                            data: income,
                            borderColor: 'rgb(16, 185, 129)',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            borderWidth: 2,
                            tension: 0, // IMPORTANT: no smoothing to avoid “distribution” perception
                            fill: true,
                            pointRadius: 3,
                            pointHoverRadius: 5
                        },
                        {
                            label: 'المصروفات',
                            data: expenses,
                            borderColor: 'rgb(239, 68, 68)',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            borderWidth: 2,
                            tension: 0, // IMPORTANT
                            fill: true,
                            pointRadius: 3,
                            pointHoverRadius: 5
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: window.innerWidth < 640 ? 'bottom' : 'top',
                            align: window.innerWidth < 640 ? 'center' : 'end',
                            rtl: false,
                            labels: {
                                usePointStyle: true,
                                padding: window.innerWidth < 640 ? 10 : 15,
                                font: { 
                                    size: window.innerWidth < 640 ? 10 : 12, 
                                    family: 'Cairo' 
                                },
                                boxWidth: window.innerWidth < 640 ? 8 : 12,
                                boxHeight: window.innerWidth < 640 ? 8 : 12
                            }
                        },
                        tooltip: {
                            rtl: false,
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            padding: window.innerWidth < 640 ? 8 : 12,
                            titleFont: { 
                                size: window.innerWidth < 640 ? 12 : 14, 
                                family: 'Cairo' 
                            },
                            bodyFont: { 
                                size: window.innerWidth < 640 ? 11 : 13, 
                                family: 'Cairo' 
                            },
                            callbacks: {
                                label: (context) =>
                                    `${context.dataset.label}: ${this.formatCurrency(context.parsed.y)}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            type: 'category',
                            position: 'bottom',
                            grid: { display: false },
                            ticks: {
                                font: { 
                                    family: 'Cairo', 
                                    size: window.innerWidth < 640 ? 9 : 11 
                                },
                                maxRotation: window.innerWidth < 640 ? 45 : 0,
                                minRotation: window.innerWidth < 640 ? 45 : 0,
                                autoSkip: true,
                                maxTicksLimit: window.innerWidth < 640 ? 6 : (useDaily ? 10 : 12),
                                padding: 5
                            }
                        },
                        y: {
                            type: 'linear',
                            position: 'left',
                            beginAtZero: false, // IMPORTANT: avoid collapsing to 0 on small ranges
                            grace: '10%',
                            suggestedMin,
                            suggestedMax,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)',
                                drawBorder: false
                            },
                            ticks: {
                                callback: (value) => {
                                    // Shorter format for mobile
                                    if (window.innerWidth < 640) {
                                        const num = Number(value) || 0;
                                        if (num >= 1000) {
                                            return `${(num / 1000).toFixed(0)}k`;
                                        }
                                        return num.toFixed(0);
                                    }
                                    return this.formatCurrency(value);
                                },
                                font: { 
                                    family: 'Cairo', 
                                    size: window.innerWidth < 640 ? 9 : 11 
                                },
                                maxTicksLimit: window.innerWidth < 640 ? 5 : 8
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Error rendering chart:', error);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#dc2626';
            ctx.font = '14px Cairo';
            ctx.textAlign = 'center';
            ctx.fillText('خطأ في عرض الرسم البياني', canvas.width / 2, canvas.height / 2);
        }
    }

    async fetchMonthlyData() {
        try {
            const params = new URLSearchParams({
                start: this.formatDateForInput(this.startDate),
                end: this.formatDateForInput(this.endDate)
            });

            const response = await fetch(`/api/monthly-breakdown/?${params}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (data?.success === false) throw new Error(data.error || 'فشل تحميل البيانات الشهرية');

            return data.monthly_data;
        } catch (error) {
            console.error('Error fetching monthly data:', error);
            return null;
        }
    }

    // IMPORTANT: Always month-by-month, never group into years
    prepareMonthlyData(monthlyData) {
        const labels = [];
        const income = [];
        const expenses = [];

        if (!monthlyData || !Array.isArray(monthlyData)) {
            console.error('Invalid monthly data format');
            return { labels: [], income: [], expenses: [] };
        }

        const multiYear =
            monthlyData.length > 1 &&
            monthlyData[0].year !== monthlyData[monthlyData.length - 1].year;

        // Check if mobile
        const isMobile = window.innerWidth < 640;
        
        // Short month names for mobile
        const shortMonths = {
            'يناير': 'ينا',
            'فبراير': 'فبر',
            'مارس': 'مار',
            'أبريل': 'أبر',
            'مايو': 'ماي',
            'يونيو': 'يون',
            'يوليو': 'يول',
            'أغسطس': 'أغس',
            'سبتمبر': 'سبت',
            'أكتوبر': 'أكت',
            'نوفمبر': 'نوف',
            'ديسمبر': 'ديس'
        };

        monthlyData.forEach(m => {
            let label;
            if (multiYear) {
                // Multi-year: show month + year
                const monthName = isMobile && shortMonths[m.month] ? shortMonths[m.month] : m.month;
                label = `${monthName} ${m.year}`;
            } else {
                // Single year: just month (short on mobile)
                label = isMobile && shortMonths[m.month] ? shortMonths[m.month] : m.month;
            }
            
            labels.push(label);
            income.push(Number(m.income) || 0);
            expenses.push(Number(m.expenses) || 0);
        });

        return { labels, income, expenses };
    }

    isSingleCalendarMonth() {
        const s = this.startDate;
        const e = this.endDate;
        if (!s || !e) return false;

        const sameMonth = s.getFullYear() === e.getFullYear() && s.getMonth() === e.getMonth();
        if (!sameMonth) return false;

        const firstDay = new Date(s.getFullYear(), s.getMonth(), 1);
        const lastDay = new Date(s.getFullYear(), s.getMonth() + 1, 0);

        // must cover full month (1..last day)
        return s.getDate() === 1 && e.getDate() === lastDay.getDate();
    }

    async fetchDailyData() {
        const params = new URLSearchParams({
            start: this.formatDateForInput(this.startDate),
            end: this.formatDateForInput(this.endDate)
        });

        const response = await fetch(`/api/daily-breakdown/?${params}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (data?.success === false) throw new Error(data.error || 'فشل تحميل البيانات اليومية');

        return data.daily_data;
    }

    prepareDailyData(dailyData) {
        const labels = [];
        const income = [];
        const expenses = [];
        const net = [];

        dailyData.forEach(d => {
            labels.push(String(d.day)); // "1", "2", ...
            income.push(Number(d.income) || 0);
            expenses.push(Number(d.expenses) || 0);
            net.push(Number(d.net) || 0);
        });

        return { labels, income, expenses, net };
    }

    
    renderIncomeTable(income) {
        const tbody = document.getElementById('income-tbody');
        if (!tbody) return;

        let html = '';

        // Payments row
        const totalPayers = Object.values(income.payments.by_category).reduce((a, b) => a + b, 0);
        html += `
            <tr>
                <td>
                    <strong>اشتراكات الأعضاء</strong>
                    <div class="small text-muted">
                        الكبار: ${income.payments.by_category.big} • 
                        الشبان: ${income.payments.by_category.med} • 
                        الصغار: ${income.payments.by_category.small} • 
                        النساء: ${income.payments.by_category.women}
                    </div>
                </td>
                <td class="text-end">${totalPayers}</td>
                <td class="text-end"><strong>${this.formatCurrency(income.payments.total)}</strong></td>
            </tr>
        `;

        // Articles row
        html += `
            <tr>
                <td><strong>الأنشطة والدورات</strong></td>
                <td class="text-end">${income.articles.count}</td>
                <td class="text-end"><strong>${this.formatCurrency(income.articles.total)}</strong></td>
            </tr>
        `;

        // Added payments
        income.added_payments.items.forEach(payment => {
            html += `
                <tr>
                    <td>
                        <strong>${payment.title}</strong>
                        ${payment.description ? `<div class="small text-muted">${payment.description}</div>` : ''}
                    </td>
                    <td class="text-end">-</td>
                    <td class="text-end"><strong>${this.formatCurrency(payment.amount)}</strong></td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    renderExpenseTable(expenses) {
        const tbody = document.getElementById('expenses-tbody');
        if (!tbody) return;

        let html = '';

        // Rent
        html += `
            <tr>
                <td><strong>الإيجار</strong></td>
                <td class="text-end">${expenses.rent.months} شهر</td>
                <td class="text-end"><strong>${this.formatCurrency(expenses.rent.total)}</strong></td>
            </tr>
        `;

        // Staff
        expenses.staff.members.forEach(member => {
            html += `
                <tr>
                    <td>
                        <strong>${member.name}</strong>
                        <div class="small text-muted">راتب</div>
                    </td>
                    <td class="text-end">${member.months} شهر</td>
                    <td class="text-end"><strong>${this.formatCurrency(member.total)}</strong></td>
                </tr>
            `;
        });

        // Articles costs
        html += `
            <tr>
                <td><strong>تكاليف الأنشطة</strong></td>
                <td class="text-end">${expenses.articles.count}</td>
                <td class="text-end"><strong>${this.formatCurrency(expenses.articles.total)}</strong></td>
            </tr>
        `;

        // Other costs
        expenses.costs.items.forEach(cost => {
            html += `
                <tr>
                    <td>
                        <strong>${cost.title}</strong>
                        ${cost.description ? `<div class="small text-muted">${cost.description}</div>` : ''}
                    </td>
                    <td class="text-end">-</td>
                    <td class="text-end"><strong>${this.formatCurrency(cost.amount)}</strong></td>
                </tr>
            `;
        });

        tbody.innerHTML = html;
    }

    toggleSection(button) {
        const targetId = button.dataset.target;
        const section = document.getElementById(targetId);

        if (!section) return;

        section.classList.toggle('collapsed');
        button.classList.toggle('collapsed');

        const icon = button.querySelector('i');
        if (icon) {
            icon.classList.toggle('fa-chevron-up');
            icon.classList.toggle('fa-chevron-down');
        }
    }

    exportReport() {
        if (!this.currentData) return;

        let csv = 'التقرير المالي\n';
        csv += `الفترة: من ${this.formatDateForInput(this.startDate)} إلى ${this.formatDateForInput(this.endDate)}\n\n`;

        csv += 'الملخص\n';
        csv += `إجمالي الإيرادات,${this.currentData.summary.total_income}\n`;
        csv += `إجمالي المصروفات,${this.currentData.summary.total_costs}\n`;
        csv += `صافي الربح,${this.currentData.summary.net_profit}\n\n`;

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `financial_report_${this.formatDateForInput(this.startDate)}_${this.formatDateForInput(this.endDate)}.csv`;
        link.click();

        this.showToast('تم تصدير التقرير بنجاح', 'success');
    }

    // Utility
    formatCurrency(amount) {
        const num = Number(amount) || 0;
        return `${num.toLocaleString('ar-MA', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })} د.م`;
    }

    formatDateForInput(date) {
        return date.toISOString().split('T')[0];
    }

    formatDateArabic(date) {
        return date.toLocaleDateString('ar-MA', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    showLoading() {
        const loading = document.getElementById('loadingState');
        const content = document.getElementById('reportContent');
        if (loading) loading.style.display = 'block';
        if (content) content.style.display = 'none';
    }

    hideLoading() {
        const loading = document.getElementById('loadingState');
        const content = document.getElementById('reportContent');
        if (loading) loading.style.display = 'none';
        if (content) content.style.display = 'block';
    }

    showError(message) {
        const loading = document.getElementById('loadingState');
        if (!loading) return;

        loading.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }

    showToast(message, type = 'success') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            alert(message);
        }
    }
}

// Initialize
let financialReport;
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing financial report...');
    financialReport = new FinancialReportManager();
});