// static/js/high_alert.js
$(function(){
    // ======================
    // Generated Timestamp
    // ======================
    (function fillGeneratedOn(){
        const now = new Date();
        const dateOpts = { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'Asia/Kolkata' };
        const timeOpts = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' };
        
        document.querySelector('#generatedOn .gen-date').textContent = now.toLocaleDateString('en-GB', dateOpts);
        document.querySelector('#generatedOn .gen-time').textContent = now.toLocaleTimeString('en-GB', timeOpts);
    })();

    // ======================
    // Sidebar Toggle (jQuery)
    // ======================
    $('#toggle-btn').on('click', function() {
        $('#sidebar').toggleClass('collapsed');
        $('#main-content').toggleClass('expanded');
        updateModalPosition();
        localStorage.setItem('sidebarCollapsed', $('#sidebar').hasClass('collapsed'));
    });

    // ======================
    // District Filter Setup
    // ======================
    let selectedDistricts = [];
    
    function loadDistricts() {
        $.ajax({
            url: "/get-districts/",
            method: "GET",
            success: function(response) {
                const optionsContainer = $('.dropdown-options');
                optionsContainer.find('.option-item:not(.all-districts)').remove();
                
                response.districts.forEach((district, index) => {
                    optionsContainer.append(`
                        <div class="option-item" data-value="${district}">
                            <input type="checkbox" id="district-${index}" 
                                   class="district-checkbox" value="${district}">
                            <label for="district-${index}">${district}</label>
                        </div>
                    `);
                });
            }
        });
    }

    function initDistrictDropdown() {
        $('.dropdown-trigger').on('click', function(e) {
            e.preventDefault();
            $('.dropdown-content').toggle();
            $('.search-input').focus();
        });

        $(document).on('click', function(e) {
            if (!$(e.target).closest('.dropdown-container').length) {
                $('.dropdown-content').hide();
            }
        });

        $('.search-input').on('input', function() {
            const searchTerm = $(this).val().toLowerCase();
            $('.option-item:not(.all-districts)').each(function() {
                $(this).toggle($(this).text().toLowerCase().includes(searchTerm));
            });
        });

        // District Selection Handling
        $(document).on('change', '.district-checkbox', function() {
            const isAllChecked = $('#selectAll').is(':checked');
            const districts = $('.district-checkbox:checked:not(#selectAll)').map(function() {
                return $(this).val();
            }).get();

            if($(this).is('#selectAll')) {
                $('.district-checkbox:not(#selectAll)').prop('checked', isAllChecked);
                $('#districtDropdown').val(isAllChecked ? [] : ['all']);
            } else {
                $('#selectAll').prop('checked', false);
            }

            selectedDistricts = districts;
            $('#districtDropdown').val(districts);
            triggerFilterUpdate();
        });
    }

    // ======================
    // Table Handling
    // ======================
    const table = $('#highAlertTable');
    const tbody = table.find('tbody');
    const paginationControls = $('.pagination-controls');

    function loadTableData(page=1) {
        $.ajax({
            url: '/high-alert/',
            data: {
                page: page,
                district: selectedDistricts.join(','),
                page_size: 50
            },
            success: function(response) {
                renderTable(response.data);
                renderPagination(response.pagination);
            }
        });
    }

    function renderTable(data) {
        tbody.empty();
        data.forEach(row => {
            tbody.append(`
                <tr>
                    <td>${row.serial_no}</td>
                    <td>${row.claim_id}</td>
                    <td>${row.patient_name}</td>
                    <td>${row.hospital_id}</td>
                    <td>${row.hospital_name}</td>
                    <td>${row.district}</td>
                    <td>${row.preauth_initiated_date}</td>
                    <td>${row.preauth_initiated_time}</td>
                    ${renderCheckmarkCells(row)}
                </tr>
            `);
        });
    }

    function renderCheckmarkCells(row) {
        return [
            'watchlist_hospital', 'high_value_claims', 'hospital_bed_cases',
            'family_id_cases', 'geographic_anomalies', 'ophthalmology_cases'
        ].map(field => `<td class="checkmark">${row[field]}</td>`).join('');
    }

    function renderPagination(pagination) {
        paginationControls.empty();
        let controls = [];
        
        if (pagination.has_previous) {
            controls.push(`<button class="page-btn" data-page="${pagination.current_page - 1}">Previous</button>`);
        }
        
        controls.push(`<span>Page ${pagination.current_page} of ${pagination.total_pages}</span>`);
        
        if (pagination.has_next) {
            controls.push(`<button class="page-btn" data-page="${pagination.current_page + 1}">Next</button>`);
        }
        
        paginationControls.html(controls.join(' '));
    }

    // ======================
    // Chart Handling
    // ======================
    let districtChart, ageChart, genderChart;
    
    function initCharts() {
        // District Bar Chart
        districtChart = new Chart(document.getElementById('districtChart').getContext('2d'), {
            type: 'bar',
            data: { labels: [], datasets: [{
                label: 'Cases',
                backgroundColor: '#26547D',
                borderColor: '#1a3a5a',
                data: []
            }]},
            options: chartBarOptions()
        });

        // Age Doughnut Chart
        ageChart = new Chart(document.getElementById('ageChart').getContext('2d'), {
            type: 'doughnut',
            data: { labels: [], datasets: [{
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF'],
                data: []
            }]},
            options: chartDoughnutOptions('Age Distribution')
        });

        // Gender Doughnut Chart
        genderChart = new Chart(document.getElementById('genderChart').getContext('2d'), {
            type: 'doughnut',
            data: { labels: [], datasets: [{
                backgroundColor: ['#36A2EB', '#FF6384', '#4BC0C0', '#C9CBCF'],
                data: []
            }]},
            options: chartDoughnutOptions('Gender Distribution')
        });
    }

    function chartBarOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, grid: { display: false } },
                x: { ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } }
            },
            plugins: {
                legend: { display: false },
                datalabels: {
                    anchor: 'end',
                    align: 'top',
                    color: '#26547D',
                    formatter: value => value > 0 ? value : ''
                }
            }
        };
    }

    function chartDoughnutOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: { position: 'bottom' },
                title: { display: true, text: title, font: { size: 16 } },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const percent = ((ctx.parsed / total) * 100).toFixed(1);
                            return `${ctx.label}: ${ctx.parsed} (${percent}%)`;
                        }
                    }
                }
            }
        };
    }

    // ======================
    // Data Loading
    // ======================
    function loadAllVisualizations() {
        loadTableData();
        loadChartData();
        loadDemographics();
    }

    function loadChartData() {
        $.ajax({
            url: window.HIGH_ALERT_URLS.districts,
            data: { district: selectedDistricts.join(',') },
            success: data => {
                districtChart.data.labels = data.labels;
                districtChart.data.datasets[0].data = data.counts;
                districtChart.update();
            }
        });
    }

    function loadDemographics() {
        ['age', 'gender'].forEach(type => {
            $.ajax({
                url: window.HIGH_ALERT_URLS.demographics.replace('type', type),
                data: { district: selectedDistricts.join(',') },
                success: data => {
                    const chart = type === 'age' ? ageChart : genderChart;
                    chart.data.labels = data.labels;
                    chart.data.datasets[0].data = data.data;
                    chart.update();
                }
            });
        });
    }

    // ======================
    // Event Handling
    // ======================
    function triggerFilterUpdate() {
        loadAllVisualizations();
    }

    $(document).on('click', '.page-btn', function() {
        loadTableData($(this).data('page'));
    });

    // ======================
    // Initialization
    // ======================
    function initializeDashboard() {
        loadDistricts();
        initDistrictDropdown();
        initCharts();
        loadAllVisualizations();
    }

    initializeDashboard();
});