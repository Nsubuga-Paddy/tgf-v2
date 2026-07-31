document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTables
    const fixedSavingsTable = $('#fixedSavingsTable').DataTable({
        responsive: true,
        pageLength: 10,
        order: [[4, 'asc']], // Sort by maturity date by default
        language: {
            search: "Search deposits:",
            lengthMenu: "Show _MENU_ deposits per page",
            info: "Showing _START_ to _END_ of _TOTAL_ deposits",
            infoEmpty: "No deposits found",
            infoFiltered: "(filtered from _MAX_ total deposits)"
        },
        columnDefs: [
            { orderable: false, targets: -1 } // Disable sorting on actions column
        ]
    });

    // Initialize Maturity Timeline Chart
    const maturityChart = new Chart(
        document.getElementById('maturityTimeline'),
        {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Upcoming Maturities',
                    data: [2, 1, 0, 3, 1, 2],
                    borderColor: '#ff6b00',
                    backgroundColor: 'rgba(255, 107, 0, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.raw} deposits maturing`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        }
    );

    // Handle row expansion
    $('.deposit-row').on('click', function() {
        const row = $(this);
        const detailsRow = row.next('.deposit-details');
        
        // Toggle details visibility
        detailsRow.toggleClass('d-none');
        
        // Update expand/collapse icon
        const icon = row.find('.expand-icon');
        icon.toggleClass('fa-chevron-down fa-chevron-up');
        
        // Update aria-expanded attribute
        const isExpanded = !detailsRow.hasClass('d-none');
        row.attr('aria-expanded', isExpanded);
    });

    // Handle action buttons
    $('.action-btn').on('click', function(e) {
        e.stopPropagation(); // Prevent row expansion when clicking action buttons
        
        const action = $(this).data('action');
        const accountNumber = $(this).data('account');
        
        switch(action) {
            case 'download':
                downloadStatement(accountNumber);
                break;
            case 'renew':
                showRenewalModal(accountNumber);
                break;
            case 'view':
                // Handled by row click
                break;
        }
    });

    // Download Statement Function
    function downloadStatement(accountNumber) {
        // Simulate API call
        console.log(`Downloading statement for account ${accountNumber}`);
        // Add actual download logic here
    }

    // Show Renewal Modal
    function showRenewalModal(accountNumber) {
        // Simulate API call to get account details
        console.log(`Showing renewal modal for account ${accountNumber}`);
        // Add actual modal logic here
    }

    // Break Deposit Calculator
    $('#breakDepositForm').on('submit', function(e) {
        e.preventDefault();
        
        const currentBalance = parseFloat($('#currentBalance').val().replace(/[^0-9.-]+/g, ''));
        const withdrawalAmount = parseFloat($('#withdrawalAmount').val());
        const penaltyRate = 0.03; // 3%
        
        const penaltyAmount = withdrawalAmount * penaltyRate;
        const netAmount = withdrawalAmount - penaltyAmount;
        
        $('#penaltyAmount').val(`UGX ${penaltyAmount.toLocaleString()}`);
        $('#netAmount').val(`UGX ${netAmount.toLocaleString()}`);
    });

    // Handle New Fixed Deposit Button
    $('#newDepositBtn').on('click', function() {
        // Add logic to show new deposit form
        console.log('Opening new deposit form');
    });

    // Accessibility: Keyboard Navigation
    $('.deposit-row').on('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            $(this).click();
        }
    });

    // Print Functionality
    $('#printTableBtn').on('click', function() {
        window.print();
    });
}); 