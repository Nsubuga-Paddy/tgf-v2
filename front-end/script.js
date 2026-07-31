document.addEventListener('DOMContentLoaded', function() {
    // Initialize sidebar functionality
    initializeSidebar();
    
    // Check which page we're on and initialize appropriate data
    if (document.getElementById('savingsHistoryTable')) {
        // We're on member dashboard
        updateMemberDashboard();
    } else {
        // We're on main dashboard
        updateDashboardData();
    }
});

// Sidebar functionality - shared between both pages
function initializeSidebar() {
    const sidebarToggler = document.querySelector('.sidebar-toggler');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);
    
    function toggleSidebar() {
        if (window.innerWidth < 992) {
            sidebar.classList.toggle('show');
            overlay.classList.toggle('show');
        }
    }
    
    sidebarToggler.addEventListener('click', toggleSidebar);
    overlay.addEventListener('click', toggleSidebar);
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 992) {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
        }
    });
    
    // Handle navigation clicks
    const navLinks = sidebar.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 992) {
                toggleSidebar();
            }
            // Remove active class from all links
            navLinks.forEach(l => l.classList.remove('active'));
            // Add active class to clicked link
            this.classList.add('active');
        });
    });
}

// Main Dashboard Functions
function updateDashboardData() {
    // Sample data - replace with actual data from backend
    const dashboardData = {
        totalSaved: 50000000,
        totalInvested: 25000000,
        uninvested: 25000000,
        interestGained: calculateInvestmentReturns(25000000, 6)
    };

    // Update overview cards
    document.getElementById('totalGroupSavings').textContent = 
        formatCurrency(dashboardData.totalSaved);
    document.getElementById('totalInvested').textContent = 
        formatCurrency(dashboardData.totalInvested);
    document.getElementById('uninvestedAmount').textContent = 
        formatCurrency(dashboardData.uninvested);
    document.getElementById('interestGained').textContent = 
        formatCurrency(dashboardData.interestGained);

    // Update tables with sample data
    updateInvestmentPools();
    updateWeeklySavings();
    updateMembersOverview();
}

function updateInvestmentPools() {
    const poolsBody = document.getElementById('investmentPoolsBody');
    if (!poolsBody) return; // Exit if element doesn't exist

    // Sample data - replace with actual data
    const pools = [
        {
            date: '2024-01-15',
            amount: 25000000,
            memberCount: 12,
            maturityDate: '2024-09-15',
            status: 'Active'
        },
        {
            date: '2024-02-15',
            amount: 25000000,
            memberCount: 15,
            maturityDate: '2024-10-15',
            status: 'Active'
        }
    ];

    poolsBody.innerHTML = '';
    let totalInvested = 0;
    let totalInterest = 0;

    pools.forEach(pool => {
        const currentInterest = calculateCurrentInterest({
            date: pool.date,
            amount: pool.amount,
            maturityDate: pool.maturityDate
        });
        
        totalInvested += pool.amount;
        totalInterest += currentInterest;

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formatDate(pool.date)}</td>
            <td>${formatCurrency(pool.amount)}</td>
            <td>${pool.memberCount} members</td>
            <td>${formatCurrency(currentInterest)}</td>
            <td>${formatDate(pool.maturityDate)}</td>
            <td><span class="badge bg-${pool.status === 'Active' ? 'success' : 'secondary'}">${pool.status}</span></td>
        `;
        poolsBody.appendChild(row);
    });

    // Update totals if elements exist
    const totalInvestedEl = document.getElementById('totalInvestedAmount');
    const totalInterestEl = document.getElementById('totalInterestEarned');
    if (totalInvestedEl) totalInvestedEl.textContent = formatCurrency(totalInvested);
    if (totalInterestEl) totalInterestEl.textContent = formatCurrency(totalInterest);
}

function updateWeeklySavings() {
    const savingsBody = document.getElementById('weeklySavingsBody');
    if (!savingsBody) return; // Exit if element doesn't exist

    // Add your implementation here
}

function updateMembersOverview() {
    const membersBody = document.getElementById('membersTableBody');
    if (!membersBody) return; // Exit if element doesn't exist

    // Add your implementation here
}

// Member Dashboard Functions
function updateMemberDashboard() {
    // Sample member data - replace with actual data from backend
    const memberData = {
        totalSaved: 1500000,
        weeksCovered: 15,
        invested: 1000000,
        expectedReturns: calculateExpectedReturns(1000000)
    };

    // Update overview cards
    updateMemberOverviewCards(memberData);
    
    // Update tables
    updatePersonalInvestments();
    updateSavingsHistory();
}

function updateMemberOverviewCards(data) {
    // Update amounts if elements exist
    const elements = {
        personalSavings: document.getElementById('personalSavings'),
        weeksCovered: document.getElementById('weeksCovered'),
        personalInvested: document.getElementById('personalInvested'),
        expectedReturns: document.getElementById('expectedReturns'),
        savingsProgress: document.getElementById('savingsProgress'),
        weeksProgress: document.getElementById('weeksProgress')
    };

    if (elements.personalSavings) 
        elements.personalSavings.textContent = formatCurrency(data.totalSaved);
    if (elements.weeksCovered) 
        elements.weeksCovered.textContent = `${data.weeksCovered}/52`;
    if (elements.personalInvested) 
        elements.personalInvested.textContent = formatCurrency(data.invested);
    if (elements.expectedReturns) 
        elements.expectedReturns.textContent = formatCurrency(data.expectedReturns);

    // Update progress bars
    const savingsProgress = (data.totalSaved / 13780000) * 100;
    const weeksProgress = (data.weeksCovered / 52) * 100;
    
    if (elements.savingsProgress) 
        elements.savingsProgress.style.width = `${savingsProgress}%`;
    if (elements.weeksProgress) 
        elements.weeksProgress.style.width = `${weeksProgress}%`;
}

function updatePersonalInvestments() {
    const investmentsBody = document.getElementById('personalInvestmentsBody');
    if (!investmentsBody) return; // Exit if element doesn't exist

    // Add your implementation here for personal investments table
}

function updateSavingsHistory() {
    const savingsBody = document.getElementById('savingsHistoryBody');
    if (!savingsBody) return; // Exit if element doesn't exist

    // Add your implementation here for savings history table
}

// Utility Functions - shared between both dashboards
function calculateInvestmentReturns(amount, monthsElapsed) {
    const interestRate = 0.30;
    const maturityPeriod = 8; // months
    if (monthsElapsed > maturityPeriod) monthsElapsed = maturityPeriod;
    return amount * (interestRate * monthsElapsed / maturityPeriod);
}

function calculateExpectedReturns(amount) {
    return amount * 0.30;
}

function calculateCurrentInterest(investment) {
    const startDate = new Date(investment.date);
    const maturityDate = new Date(investment.maturityDate);
    const today = new Date();
    
    const totalDays = (maturityDate - startDate) / (1000 * 60 * 60 * 24);
    const elapsedDays = (today - startDate) / (1000 * 60 * 60 * 24);
    
    return investment.amount * 0.30 * (elapsedDays / totalDays);
}

function calculateDaysRemaining(maturityDate) {
    const today = new Date();
    const maturity = new Date(maturityDate);
    const diffTime = maturity - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 0;
}

function calculateWeekCoverage(amount) {
    const weeklyTarget = 10000;
    const fullWeeks = Math.floor(amount / weeklyTarget);
    const remainingAmount = amount % weeklyTarget;
    const partialWeekPercentage = (remainingAmount / weeklyTarget) * 100;
    
    return {
        fullWeeks,
        partialWeekPercentage: Math.round(partialWeekPercentage)
    };
}

function formatCurrency(amount) {
    return `UGX ${amount.toLocaleString()}`;
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-UG', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Add these functions to your existing script.js

function initializeMembersPage() {
    updateMembersStats();
    updateMembersTable();
    initializeSearch();
}

function updateMembersStats() {
    // Sample data - replace with actual data from backend
    const stats = {
        totalMembers: 25,
        totalSavings: 50000000,
        totalWeeksCovered: 375 // Sum of all members' weeks
    };

    // Calculate averages
    const averageSavings = stats.totalSavings / stats.totalMembers;
    const averageWeeks = stats.totalWeeksCovered / stats.totalMembers;

    // Update stats cards
    document.getElementById('totalMembers').textContent = stats.totalMembers;
    document.getElementById('averageSavings').textContent = formatCurrency(averageSavings);
    document.getElementById('averageWeeks').textContent = averageWeeks.toFixed(1);
}

function updateMembersTable() {
    const membersTableBody = document.getElementById('membersTableBody');
    if (!membersTableBody) return;

    // Sample data - replace with actual data from backend
    const members = [
        {
            name: "John Doe",
            savings: 2500000,
            weeksCovered: 15,
            lastContribution: "2024-03-15",
            status: "Active"
        },
        {
            name: "Jane Smith",
            savings: 1800000,
            weeksCovered: 12,
            lastContribution: "2024-03-14",
            status: "Active"
        }
        // Add more members as needed
    ];

    membersTableBody.innerHTML = '';

    members.forEach(member => {
        const progressPercentage = (member.weeksCovered / 52) * 100;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar-circle me-2">${member.name.charAt(0)}</div>
                    ${member.name}
                </div>
            </td>
            <td>${formatCurrency(member.savings)}</td>
            <td>${member.weeksCovered}/52</td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="progress flex-grow-1" style="height: 8px;">
                        <div class="progress-bar" style="width: ${progressPercentage}%"></div>
                    </div>
                    <span class="ms-2">${progressPercentage.toFixed(1)}%</span>
                </div>
            </td>
            <td>${formatDate(member.lastContribution)}</td>
            <td>
                <span class="badge bg-${member.status === 'Active' ? 'success' : 'warning'}">
                    ${member.status}
                </span>
            </td>
        `;
        membersTableBody.appendChild(row);
    });
}

function initializeSearch() {
    const searchInput = document.getElementById('searchMember');
    if (!searchInput) return;

    searchInput.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const rows = document.querySelectorAll('#membersTableBody tr');

        rows.forEach(row => {
            const memberName = row.querySelector('td').textContent.toLowerCase();
            if (memberName.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
}

function exportMembersList() {
    // Implement export functionality
    alert('Exporting members list...');
}

// Add this to your DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', function() {
    // ... existing initialization code ...
    
    // Check if we're on the members page
    if (document.getElementById('membersTable')) {
        initializeMembersPage();
    }
});