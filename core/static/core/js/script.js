// Basic JavaScript for 52WSC Dashboard

document.addEventListener('DOMContentLoaded', function() {
    // Mobile sidebar toggle
    const sidebarToggler = document.querySelector('.sidebar-toggler');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggler && sidebar) {
        sidebarToggler.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768) {
            if (!sidebar.contains(e.target) && !sidebarToggler.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        }
    });
    
    // Update dashboard data if available
    if (typeof window.dashboardData !== 'undefined') {
        updateDashboardDisplay();
    }
});

function updateDashboardDisplay() {
    const data = window.dashboardData;
    
    // Update overview cards
    if (data.totalGroupSavings !== undefined) {
        const totalSavingsElement = document.getElementById('totalGroupSavings');
        if (totalSavingsElement) {
            totalSavingsElement.textContent = `UGX ${data.totalGroupSavings.toLocaleString()}`;
        }
    }
    
    if (data.totalInvested !== undefined) {
        const totalInvestedElement = document.getElementById('totalInvested');
        if (totalInvestedElement) {
            totalInvestedElement.textContent = `UGX ${data.totalInvested.toLocaleString()}`;
        }
    }
    
    if (data.uninvested !== undefined) {
        const uninvestedElement = document.getElementById('uninvestedAmount');
        if (uninvestedElement) {
            uninvestedElement.textContent = `UGX ${data.uninvested.toLocaleString()}`;
        }
    }
    
    if (data.interestGained !== undefined) {
        const interestElement = document.getElementById('interestGained');
        if (interestElement) {
            interestElement.textContent = `UGX ${data.interestGained.toLocaleString()}`;
        }
    }
}

// Utility function for number formatting
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'UGX',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// Add loading states to buttons
function addLoadingState(button) {
    const originalText = button.textContent;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
    return originalText;
}

function removeLoadingState(button, originalText) {
    button.disabled = false;
    button.textContent = originalText;
} 