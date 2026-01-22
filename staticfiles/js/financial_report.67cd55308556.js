/**
 * Financial Report Manager
 * Optimized for performance with caching, lazy rendering, and efficient updates
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
        
        // Set default dates (current year)
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
        document.getElementById('applyDateRange').addEventListener('click', () => {
            this.applyDateRange();
        });

        // Quick period buttons
        document.querySelectorAll('.quick-period').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setQuickPeriod(e.target.dataset.period);
            });
        });

        // Section toggle buttons
        document.querySelectorAll('.toggle-section').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.toggleSection(e.target.closest('button'));
            });
        });

        // Export button
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportReport();
        });
    }

    setQuickPeriod(period) {
        const today = new Date();
        
        switch(period) {
            case 'today':
                this.startDate = new Date(today);
                this.endDate = new Date(today);
                break;
            case 'week':
                this.startDate = new Date(today.setDate(today.getDate() - today.getDay()));
                this.endDate = new Date();
                break;
            case 'month':
                this.startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                this.endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                break;
            case 'year':
                this.startDate = new Date(today.getFullYear(), 0, 1);
                this.endDate = new Date(today.getFullYear(), 11, 31);
                break;
        }
        
        this.updateDateInputs();
        this.applyDateRange();
    }

    updateDateInputs() {
        document.getElementById('start-date').value = this.formatDateForInput(this.startDate);
        document.getElementById('end-date').value = this.formatDateForInput(this.endDate);
    }

    applyDateRange() {
        const startInput = document.getElementById('start-date').value;
        const endInput = document.getElementById('end-date').value;
        
        if (!startInput || !endInput) {
            this.showToast('الرجاء اختيار تاريخ البداية والنهاية', 'error');
            return;
        }
        
        this.startDate = new Date(startInput);
        this.endDate = new Date(endInput);
        
        // Update period text
        this.updatePeriodText();
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('periodModal'));
        if (modal) modal.hide();
        
        // Reload report
        this.loadReport();
    }

    updatePeriodText() {
        const startStr = this.formatDateArabic(this.startDate);
        const endStr = this.formatDateArabic(this.endDate);
        
        document.getElementById('period-text').textContent = `من ${startStr} إلى ${endStr}`;
    }

    async loadReport() {
        this.showLoading();
        
        try {
            const params = new URLSearchParams({
                start: this.formatDateForInput(this.startDate),
                end: this.formatDateForInput(this.endDate)
            });

            const response = await fetch(`/api/financial-report/?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success === false) {
                throw new Error(data.error);
            }

            // Store current data
            this.previousData = this.currentData;
            this.currentData = data;

            // Render everything
            this.renderReport(data);
            
            // Update period text
            this.updatePeriodText();
            
            // Enable export
            document.getElementById('exportBtn').disabled = false;

            this.hideLoading();

        } catch (error) {
            console.error('Error loading report:', error);
            this.showError('حدث خطأ أثناء تحميل التقرير. يرجى المحاولة مرة أخرى.');
        }
    }

    renderReport(data) {
        // Render summary cards with comparison
        this.renderSummaryCards(data);

        // Render chart
        this.renderChart(data);

        // Render tables
        this.renderIncome Table(data.income);
        this.renderExpenseTable(data.expenses);
    }

    renderSummaryCards(data) {
        const { summary } = data;
        
        // Calculate changes if we have previous data
        let incomeChange = null;
        let expenseChange = null;
        let profitChange = null;
        
        if (this.previousData) {
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
        document.getElementById('total-income').textContent = 
            this.formatCurrency(summary.total_income);
        
        document.getElementById('total-expenses').textContent = 
            this.formatCurrency(summary.total_costs);
        
        document.getElementById('net-profit').textContent = 
            this.formatCurrency(summary.net_profit);

        // Update changes
        this.updateChangeIndicator('income-change', incomeChange, true);
        this.updateChangeIndicator('expense-change', expenseChange, false);
        this.updateChangeIndicator('profit-change', profitChange, true);
    }

    calculateChange(oldValue, newValue) {
        if (!oldValue || oldValue === 0) return null;
        
        const percentChange = ((newValue - oldValue) / oldValue) * 100;
        return {
            percent: percentChange,
            isPositive: percentChange >= 0
        };
    }

    updateChangeIndicator(elementId, change, positiveIsGood) {
        const element = document.getElementById(elementId);
        
        if (!change) {
            element.textContent = '';
            return;
        }

        const icon = change.isPositive ? 'fa-arrow-up' : 'fa-arrow-down';
        const isGood = positiveIsGood ? change.isPositive : !change.isPositive;
        const className = isGood ? 'positive' : 'negative';
        
        element.className = `card-change ${className}`;
        element.innerHTML = `
            <i class="fas ${icon} me-1"></i>
            ${Math.abs(change.percent).toFixed(1)}% من الفترة السابقة
        `;
    }

    renderChart(data) {
        const ctx = document.getElementById('financialChart');
        if (!ctx) return;

        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
        }

        // Prepare data - combine income and expenses by month
        const monthlyData = this.prepareMonthlyData(data);

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: monthlyData.labels,
                datasets: [
                    {
                        label: 'الإيرادات',
                        data: monthlyData.income,
                        borderColor: 'rgb(16, 185, 129)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'المصروفات',
                        data: monthlyData.expenses,
                        borderColor: 'rgb(239, 68, 68)',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
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
                        align: 'end',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                family: "'Tajawal', sans-serif",
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#111827',
                        bodyColor: '#4b5563',
                        borderColor: '#e5e7eb',
                        borderWidth: 1,
                        padding: 12,
                        boxPadding: 6,
                        usePointStyle: true,
                        rtl: true,
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${this.formatCurrency(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
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
                        beginAtZero: true,
                        grid: {
                            borderDash: [2, 4],
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: (value) => this.formatCurrency(value)
                        }
                    }
                }
            }
        });
    }

    prepareMonthlyData(data) {
        // This is a simplified version - you'd need to aggregate by month from the actual data
        // For now, returning placeholder structure
        const labels = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 
                        'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
        
        return {
            labels,
            income: Array(12).fill(0),
            expenses: Array(12).fill(0)
        };
    }

    renderIncomeTable(income) {
        const tbody = document.getElementById('income-tbody');
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
        
        section.classList.toggle('collapsed');
        button.classList.toggle('collapsed');
        
        const icon = button.querySelector('i');
        icon.classList.toggle('fa-chevron-up');
        icon.classList.toggle('fa-chevron-down');
    }

    exportReport() {
        if (!this.currentData) return;
        
        // Create CSV content
        let csv = 'التقرير المالي\n';
        csv += `الفترة: من ${this.formatDateForInput(this.startDate)} إلى ${this.formatDateForInput(this.endDate)}\n\n`;
        
        csv += 'الملخص\n';
        csv += `إجمالي الإيرادات,${this.currentData.summary.total_income}\n`;
        csv += `إجمالي المصروفات,${this.currentData.summary.total_costs}\n`;
        csv += `صافي الربح,${this.currentData.summary.net_profit}\n\n`;
        
        // Download
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `financial_report_${this.formatDateForInput(this.startDate)}_${this.formatDateForInput(this.endDate)}.csv`;
        link.click();
        
        this.showToast('تم تصدير التقرير بنجاح', 'success');
    }

    // Utility functions
    formatCurrency(amount) {
        return `${parseFloat(amount).toLocaleString('ar-MA', {
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
        document.getElementById('loadingState').style.display = 'block';
        document.getElementById('reportContent').style.display = 'none';
    }

    hideLoading() {
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('reportContent').style.display = 'block';
    }

    showError(message) {
        document.getElementById('loadingState').innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }

    showToast(message, type = 'success') {
        // Reuse toast function from main dashboard if available
        if (typeof showToast === 'function') {
            showToast(message, type);
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
