$(document).ready(function() {
    window.highValueCharts = {};
    let agePieChart, genderPieChart;

    function safeCanvasDataURL(id) {
        const el = document.getElementById(id);
        return el ? el.toDataURL() : '';
    }

    function safeInnerHTML(id) {
        const el = document.getElementById(id);
        return el ? el.innerHTML : '';
    }

    // ======================
    // Sidebar Toggle (jQuery)
    // ======================
    $('#toggle-btn').on('click', function() {
        $('#sidebar').toggleClass('collapsed');
        $('#main-content').toggleClass('expanded');
        updateModalPosition();
        localStorage.setItem('sidebarCollapsed', $('#sidebar').hasClass('collapsed'));
    });

    // Add this to handle modal repositioning
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        $('#sidebar').addClass('collapsed');
        $('#main-content').addClass('expanded');
        $('.modal-overlay').css('left', '0');
    } else {
        $('.modal-overlay').css('left', '250px');
    }

    function updateModalPosition() {
        if ($('#sidebar').hasClass('collapsed')) {
            $('.modal-overlay').css('left', '0');
        } else {
            $('.modal-overlay').css('left', '250px');
        }
    }

    // ======================
    // District Dropdown (jQuery)
    // ======================
    function loadDistricts() {
        $.ajax({
            url: "/get-districts/",
            method: "GET",
            success: function(response) {
                const dropdown = $('#districtDropdown');
                const optionsContainer = $('.dropdown-options');
                
                // Clear existing options except "All Districts"
                dropdown.empty().append('<option value="">All Districts</option>');
                optionsContainer.find('.option-item:not(.all-districts)').remove();
                
                // Add districts to both the hidden select and visible options
                $.each(response.districts, function(index, district) {
                    // Add to hidden select
                    dropdown.append($('<option>', { 
                        value: district, 
                        text: district 
                    }));
                    
                    // Add to visible options with checkbox
                    optionsContainer.append(`
                        <div class="option-item" data-value="${district}">
                            <input type="checkbox" id="district-${index}" 
                                   class="district-checkbox" value="${district}">
                            <label for="district-${index}">${district}</label>
                        </div>
                    `);
                });
                
                // Initialize the selected display
                $('#selectAll').prop('checked', true);
                updateSelectedDisplay();
            }
        });
    }

    // Function to update the display of selected districts
    function updateSelectedDisplay() {
        const selectedCheckboxes = $('.district-checkbox:checked:not(#selectAll)');
        const allDistrictsCheckbox = $('#selectAll');
        const hiddenSelect = $('#districtDropdown');
        const selectedValueDisplay = $('.selected-value');
        
        if (selectedCheckboxes.length === 0 || allDistrictsCheckbox.is(':checked')) {
            selectedValueDisplay.text('All Districts');
            hiddenSelect.val('');
        } else if (selectedCheckboxes.length <= 3) {
            // Show up to 3 district names
            selectedValueDisplay.text(selectedCheckboxes.map(function() {
                return $(this).val();
            }).get().join(', '));
        } else {
            // Show count if more than 3
            selectedValueDisplay.text(`${selectedCheckboxes.length} districts selected`);
        }
    }

    function initDistrictDropdown() {
        // Toggle dropdown
        $('.dropdown-trigger').on('click', function(e) {
            e.preventDefault();
            $('.dropdown-content').toggle();
            $('.search-input').focus();
        });
        
        // Close dropdown when clicking outside
        $(document).on('click', function(e) {
            if (!$(e.target).closest('.dropdown-container').length) {
                $('.dropdown-content').hide();
            }
        });
        
        // Search functionality
        $('.search-input').on('input', function() {
            const searchTerm = $(this).val().toLowerCase();
            $('.option-item:not(.all-districts)').each(function() {
                const text = $(this).text().toLowerCase();
                $(this).toggle(text.includes(searchTerm));
            });
        });
        
        // District checkbox selection - UPDATED VERSION
        $(document).on('change', '.district-checkbox:not(#selectAll)', function() {
            const district = $(this).val();
            const hiddenOption = $('#districtDropdown option[value="' + district + '"]');
            
            if ($(this).is(':checked')) {
                hiddenOption.prop('selected', true);
                $('#selectAll').prop('checked', false);
            } else {
                hiddenOption.prop('selected', false);
            }
            
            updateSelectedDisplay();
            
            // Get all selected districts
            const selectedDistricts = $('.district-checkbox:checked:not(#selectAll)').map(function() {
                return $(this).val();
            }).get();
            
            // Trigger update - empty array means "All Districts"
            updateFlaggedClaims(selectedDistricts);
            updateHighValueClaims(selectedDistricts);
            updateHospitalBedCases(selectedDistricts);
            updateGeoAnomalies(selectedDistricts);
            updateOphthalmology(selectedDistricts);
        });
        
        // "All Districts" checkbox - UPDATED VERSION
        $(document).on('change', '#selectAll', function() {
            const isChecked = $(this).is(':checked');
            
            $('.district-checkbox:not(#selectAll)').prop('checked', isChecked);
            
            if (isChecked) {
                $('#districtDropdown option').prop('selected', false);
                $('#districtDropdown option[value=""]').prop('selected', true);
            } else {
                $('#districtDropdown option').prop('selected', false);
            }
            
            updateSelectedDisplay();
            
            // Trigger update with empty array for "All Districts"
            updateFlaggedClaims(isChecked ? [] : null);
            updateHighValueClaims(isChecked ? [] : null);
            updateHospitalBedCases(isChecked ? [] : null);
            updateFamilyIdCases(isChecked ? [] : null);
            updateGeoAnomalies(isChecked ? [] : null);
            updateOphthalmology(isChecked ? [] : null);
        });
    }
    
    loadDistricts();
    initDistrictDropdown();

    function updateFlaggedClaims(districts = []) {
        // If null (All Districts unchecked), show empty state
        if (districts === null) {
            $('.flagged-claims .card-value').text('0');
            $('.flagged-claims .time-value').text('0');
            return;
        }
        
        $.ajax({
            url: '/get-flagged-claims/',
            method: 'GET',
            data: { 
                district: districts.length > 0 ? districts.join(',') : ''
            },
            beforeSend: function() {
                $('.flagged-claims .card-value').html('<i class="fas fa-spinner fa-spin"></i>');
            },
            success: function(response) {
                $('.flagged-claims .card-value').text(response.total.toLocaleString());
                $('.flagged-claims .time-metric:nth-child(1) .time-value').text(response.total.toLocaleString());
                $('.flagged-claims .time-metric:nth-child(2) .time-value').text(response.yesterday.toLocaleString());
                $('.flagged-claims .time-metric:nth-child(3) .time-value').text(response.last_30_days.toLocaleString());
            },
            error: function(xhr, status, error) {
                console.error('Error fetching flagged claims:', error);
                $('.flagged-claims .card-value').text('Error');
            }
        });
    }

    $(function(){
        $('#download-flagged').on('click', function(){
          const baseUrl  = $(this).data('download-url');
          const district = $(this).data('district') || '';
    
          let url = baseUrl;
          if (district) {
            url += '?district=' + encodeURIComponent(district);
          }
          window.location.href = url;
        });
    });

    function updateHighValueClaims(districts = []) {
        // If null (All Districts unchecked), show empty state
        if (districts === null) {
            $('.high-value .card-value').text('0');
            $('.high-value .time-value').text('0');
            return;
        }
    
        $.ajax({
            url: '/get-high-value-claims/',
            method: 'GET',
            data: { district: districts.join(',') },
            success: function(response) {
                // console.log("Full Response:", response);
                
                // 1. Update Main Card
                $('.high-value .card-value').text(response.total_count.toLocaleString());
                
                // 2. Update Surgical Section - more precise selectors
                $('.high-value .surgical .time-metric:eq(0) .time-value').text(response.surgical.count.toLocaleString());
                $('.high-value .surgical .time-metric:eq(1) .time-value').text(response.surgical.yesterday.toLocaleString());
                $('.high-value .surgical .time-metric:eq(2) .time-value').text(response.surgical.last_30_days.toLocaleString());
                
                // 3. Update Medical Section - more precise selectors
                $('.high-value .medical .time-metric:eq(0) .time-value').text(response.medical.count.toLocaleString());
                $('.high-value .medical .time-metric:eq(1) .time-value').text(response.medical.yesterday.toLocaleString());
                $('.high-value .medical .time-metric:eq(2) .time-value').text(response.medical.last_30_days.toLocaleString());
                
                // Debug verification
                // console.log("Surgical value set to:", response.surgical.count);
                // console.log("Medical value set to:", response.medical.count);
            },
            error: function(xhr, status, error) {
                console.error("Error:", error);
                $('.high-value .card-value').text('Error');
            }
        });
    }

    $(document).on('click', '.card.high-value .download-btn', function(e) {
        e.preventDefault();
        const $card     = $(this).closest('.card.high-value');
        const baseUrl   = $card.data('download-url');
        const district  = $card.data('district') || '';
      
        let url = baseUrl;
        if (district) {
          url += '?district=' + encodeURIComponent(district);
        }
        window.location.href = url;
    });

    function updateHospitalBedCases(districts = []) {
        // $('.hospital-beds .card-value').html('<i class="fas fa-spinner fa-spin"></i>');
        
        $.ajax({
            url: '/get-hospital-bed-cases/',
            method: 'GET',
            data: { district: districts.join(',') },
            success: function(response) {
                // Update main card
                $('.hospital-beds .card-value').text(response.total.toLocaleString());
                
                // Update hover content
                $('.hospital-beds .time-metric:nth-child(1) .time-value').text(response.total.toLocaleString());
                $('.hospital-beds .time-metric:nth-child(2) .time-value').text(response.yesterday.toLocaleString());
                $('.hospital-beds .time-metric:nth-child(3) .time-value').text(response.last_30_days.toLocaleString());
                
                // Update violation details (for modal or tooltip)
                if (response.violations_today && response.violations_today.length > 0) {
                    const violationsHtml = response.violations_today.map(v => `
                        <div class="violation-item">
                            <strong>${v.hospital}</strong>:
                            ${v.admissions} admissions (Capacity: ${v.bed_strength})
                        </div>
                    `).join('');
                    $('.hospital-beds .violations-container').html(violationsHtml);
                }
            },
            error: function(xhr, status, error) {
                console.error("Error fetching bed cases:", error);
                $('.hospital-beds .card-value').text('Error');
            }
        });
    }

    function updateFamilyIdCases(districts = []) {
        $('.family-id .card-value').html('<i class="fas fa-spinner fa-spin"></i>');
        
        $.ajax({
            url: '/get-family-id-cases/',
            method: 'GET',
            data: { district: districts.join(',') },
            success: function(response) {
                // Update main card
                $('.family-id .card-value').text(response.total.toLocaleString());
                
                // Update hover content
                $('.family-id .time-metric:nth-child(1) .time-value').text(response.total.toLocaleString());
                $('.family-id .time-metric:nth-child(2) .time-value').text(response.yesterday.toLocaleString());
                $('.family-id .time-metric:nth-child(3) .time-value').text(response.last_30_days.toLocaleString());
                
                // Update violation details
                if (response.violations.length > 0) {
                    const violationsHtml = response.violations.map(v => `
                        <div class="violation-item">
                            <strong>Family ${v.family_id}</strong>:
                            ${v.count} claims on ${v.date} across
                            ${v.hospitals.length} hospitals
                        </div>
                    `).join('');
                    $('.family-id .violations-container').html(violationsHtml);
                }
            }
        });
    }

    function updateGeoAnomalies(districts = []) {
        $.ajax({
            url: '/get-geo-anomalies/',
            data: { district: districts.join(',') },
            success: function(response) {
                $('.geo-anomalies .card-value').text(response.total.toLocaleString());
                $('.geo-anomalies .time-metric:nth-child(1) .time-value').text(response.total.toLocaleString());
                $('.geo-anomalies .time-metric:nth-child(2) .time-value').text(response.yesterday.toLocaleString());
                $('.geo-anomalies .time-metric:nth-child(3) .time-value').text(response.last_30_days.toLocaleString());
                // Update other elements similarly
            }
        });
    }

    function updateOphthalmology(districts = []) {
        $.ajax({
            url: '/get-ophthalmology-cases/',
            data: { district: districts.join(',') },
            success: function(response) {
                // Main card
                $('.ophthalmology .card-value').text(response.total.toLocaleString());
                
                // Sub-cards
                $('.sub-card.age .card-value').text(response.age_under_40.total);
                $('.sub-card.age .time-metric:nth-child(1) .time-value').text(response.age_under_40.total);
                $('.sub-card.age .time-metric:nth-child(2) .time-value').text(response.age_under_40.yesterday);
                $('.sub-card.age .time-metric:nth-child(3) .time-value').text(response.age_under_40.last_30_days);

                $('.sub-card.ot-cases .card-value').text(response.ot_cases.total);
                $('.sub-card.ot-cases .time-metric:nth-child(1) .time-value').text(response.ot_cases.total);
                $('.sub-card.ot-cases .time-metric:nth-child(2) .time-value').text(response.ot_cases.yesterday);
                $('.sub-card.ot-cases .time-metric:nth-child(3) .time-value').text(response.ot_cases.last_30_days);

                $('.sub-card.preauth .card-value').text(response.preauth_time.total);
                $('.sub-card.preauth .time-metric:nth-child(1) .time-value').text(response.preauth_time.total);
                $('.sub-card.preauth .time-metric:nth-child(2) .time-value').text(response.preauth_time.yesterday);
                $('.sub-card.preauth .time-metric:nth-child(3) .time-value').text(response.preauth_time.last_30_days);
            }
        });
    }

    // Initialize
    $(document).ready(function() {
        updateFlaggedClaims();
        updateHighValueClaims();
        updateHospitalBedCases();
        updateFamilyIdCases();
        updateGeoAnomalies();
        updateOphthalmology();
        
        // Update when district changes
        $(document).on('districtSelected', function(e, districts) {
            updateFlaggedClaims(districts);
            updateHighValueClaims(districts);
            updateHospitalBedCases(districts);
            updateFamilyIdCases(districts);
            updateGeoAnomalies(districts);
            updateOphthalmology(districts);
        });
    });

    // ======================
    // Enhanced Modal Controller
    // ======================
    const cardTemplates = {
        'flagged-claims': {
            title: "Flagged Claims Details",
            content: `
                <!-- Table -->
                <div class="data-table-container">
                    <div class="table-controls">
                        <button class="table-download-btn">
                            <i class="fas fa-download"></i> Export Excel
                        </button>
                        <div class="page-size-selector">
                            <span>Items per page:</span>
                            <select id="flaggedPageSizeSelect">
                                <option value="10">10</option>
                                <option value="25">25</option>
                                <option value="50" selected>50</option>
                                <option value="100">100</option>
                            </select>
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Claim ID</th>
                                <th>Patient</th>
                                <th>Hospital</th>
                                <th>District</th>
                                <th>Amount (₹)</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="flaggedClaimsData"></tbody>
                    </table>
                    <div class="table-footer">
                        <div class="pagination-info">
                            Showing <span id="flaggedStartRecord">0</span> to <span id="flaggedEndRecord">0</span> 
                            of <span id="flaggedTotalRecords">0</span> records
                        </div>
                        <div class="pagination-controls" id="flaggedPaginationControls"></div>
                    </div>
                </div>

                <!-- Bar Chart -->
                <div class="chart-container">
                    <h4>District-wise Flagged Claims Distribution</h4>
                    <canvas id="flaggedClaimsChart"></canvas>
                    <div class="chart-legend" id="flaggedClaimsLegend"></div>
                </div>

                <!-- Pie Chart -->
                <div class="dual-pie-container">
                    <!-- Age Distribution Pie -->
                    <div class="pie-card">
                        <h4>Age Group Distribution</h4>
                        <div class="chart-wrapper">
                            <canvas id="agePieChart"></canvas>
                            <div class="chart-callouts" id="ageCallouts"></div>
                        </div>
                    </div>
                    
                    <!-- Gender Distribution Pie -->
                    <div class="pie-card">
                        <h4>Gender Distribution</h4>
                        <div class="chart-wrapper">
                            <canvas id="genderPieChart"></canvas>
                            <div class="chart-callouts" id="genderCallouts"></div>
                        </div>
                    </div>
                </div>
            `,
            postRender: function(districts) {
                this.initPagination(districts);
                this.loadTableData(districts);
                this.loadChartData(districts);
                const selected = districts || [];
                const modal = document.querySelector('.modal-container');
                modal.dataset.district = selected.join(',');
                modal.dataset.cardId = 'flagged-claims';
                modal.dataset.pdfUrl  = window.PDF_URLS.flagged;
            },
            initPagination: function(districts) {
                this.currentPage = 1;
                this.pageSize = 50;
                this.totalPages = 1;
                this.districts = districts;
    
                // Event listeners
                $('#flaggedPageSizeSelect').off('change').on('change', () => {
                    this.pageSize = parseInt($('#flaggedPageSizeSelect').val());
                    this.currentPage = 1;
                    this.loadTableData(this.districts);
                });
    
                $(document).off('click', '.flagged-page-btn').on('click', '.flagged-page-btn', (e) => {
                    e.preventDefault();
                    const page = parseInt($(e.currentTarget).data('page'));
                    if (page >= 1 && page <= this.totalPages) {
                        this.currentPage = page;
                        this.loadTableData(this.districts);
                    }
                });
            },
            loadTableData: function(districts) {
                const url = `/get-flagged-claims-details/?district=${districts.join(',')}&page=${this.currentPage}&page_size=${this.pageSize}`;
    
                fetch(url, {
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                .then(response => response.json())
                .then(response => {
                    const tableBody = document.getElementById('flaggedClaimsData');
                    tableBody.innerHTML = response.data.map(item => `
                        <tr>
                            <td>${item.serial_no}</td>
                            <td>${item.claim_id}</td>
                            <td>${item.patient_name}</td>
                            <td>${item.hospital_name}</td>
                            <td>${item.district_name}</td>
                            <td>₹${item.amount.toLocaleString('en-IN')}</td>
                            <td><span class="status-badge ${item.reason === 'Suspicious hospital' ? 'danger' : 'warning'}">
                                ${item.reason}
                            </span></td>
                        </tr>
                    `).join('');
    
                    this.updatePaginationUI(response.pagination);
                })
                .catch(error => {
                    console.error('Error loading data:', error);
                    document.getElementById('flaggedClaimsData').innerHTML = `
                        <tr>
                            <td colspan="7" class="error-message">
                                Failed to load data. ${error.message}
                            </td>
                        </tr>
                    `;
                });
            },
            updatePaginationUI: function(paginationData) {
                this.totalPages = paginationData.total_pages;
    
                // Update record count info
                const start = ((this.currentPage - 1) * this.pageSize) + 1;
                const end = Math.min(start + this.pageSize - 1, paginationData.total_records);
                $('#flaggedStartRecord').text(start);
                $('#flaggedEndRecord').text(end);
                $('#flaggedTotalRecords').text(paginationData.total_records);
    
                // Generate pagination buttons
                const paginationControls = $('#flaggedPaginationControls');
                paginationControls.empty();
    
                // Previous button
                paginationControls.append(`
                    <button class="flagged-page-btn ${paginationData.has_previous ? '' : 'disabled'}" 
                            data-page="${this.currentPage - 1}">
                        &laquo; Previous
                    </button>
                `);
    
                // Page numbers
                const maxVisiblePages = 5;
                let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
                let endPage = Math.min(this.totalPages, startPage + maxVisiblePages - 1);
    
                if (endPage - startPage < maxVisiblePages - 1) {
                    startPage = Math.max(1, endPage - maxVisiblePages + 1);
                }
    
                if (startPage > 1) {
                    paginationControls.append(`
                        <button class="flagged-page-btn" data-page="1">1</button>
                        ${startPage > 2 ? '<span class="page-dots">...</span>' : ''}
                    `);
                }
    
                for (let i = startPage; i <= endPage; i++) {
                    paginationControls.append(`
                        <button class="flagged-page-btn ${i === this.currentPage ? 'active' : ''}" 
                                data-page="${i}">
                            ${i}
                        </button>
                    `);
                }
    
                if (endPage < this.totalPages) {
                    paginationControls.append(`
                        ${endPage < this.totalPages - 1 ? '<span class="page-dots">...</span>' : ''}
                        <button class="flagged-page-btn" data-page="${this.totalPages}">
                            ${this.totalPages}
                        </button>
                    `);
                }
    
                // Next button
                paginationControls.append(`
                    <button class="flagged-page-btn ${paginationData.has_next ? '' : 'disabled'}" 
                            data-page="${this.currentPage + 1}">
                        Next &raquo;
                    </button>
                `);
            },
            loadChartData: function(districts) {
                // Load bar chart data
                const chartUrl = `/get-flagged-claims-by-district/?district=${districts.join(',')}`;
                
                fetch(chartUrl)
                    .then(response => response.json())
                    .then(chartData => {
                        this.renderFlaggedClaimsChart(chartData);
                        this.loadDemographicCharts(districts);
                    })
                    .catch(error => console.error('Chart load error:', error));
            },
            
            renderFlaggedClaimsChart: function(chartData) {
                const canvas = document.getElementById('flaggedClaimsChart');
                if (!canvas) return;
                
                const ctx = canvas.getContext('2d');
                
                // Destroy existing chart
                // if (window.flaggedClaimsChart) {
                //     window.flaggedClaimsChart.destroy();
                // }
                
                window.flaggedClaimsChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: chartData.districts,
                        datasets: [{
                            label: 'Flagged Claims',
                            data: chartData.counts,
                            backgroundColor: 'rgba(54, 162, 235, 0.7)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => `${context.parsed.y} claims`
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Number of Claims' },
                                ticks: { precision: 0 }
                            },
                            x: {
                                title: { display: true, text: 'Districts' },
                                ticks: { 
                                    autoSkip: false,
                                    maxRotation: 45,
                                    minRotation: 45 
                                }
                            }
                        }
                    }
                });
            },
            
            loadDemographicCharts: function(districts) {
                // Load age distribution
                fetch(`/get-age-distribution/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderDemographicChart('agePieChart', data, 'ageCallouts'));
                
                // Load gender distribution
                fetch(`/get-gender-distribution/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderDemographicChart('genderPieChart', data, 'genderCallouts'));
            },
            
            renderDemographicChart: function(canvasId, data, calloutId) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) return;
                
                // Destroy existing chart
                // if (window[canvasId]) {
                //     window[canvasId].destroy();
                // }
                
                window[canvasId] = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.data,
                            backgroundColor: data.colors,
                            borderWidth: 0,
                            cutout: '65%'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => {
                                        const total = context.dataset.data.reduce((a, b) => a + b);
                                        const percentage = Math.round((context.raw / total) * 100);
                                        return `${context.label}: ${context.raw} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
                
                this.generateDemographicCallouts(data, calloutId);
            },
            
            generateDemographicCallouts: function(data, containerId) {
                const container = document.getElementById(containerId);
                if (!container) return;
                
                const total = data.data.reduce((a, b) => a + b, 0);
                container.innerHTML = data.labels.map((label, i) => `
                    <div class="callout-item">
                        <span class="callout-color" style="background:${data.colors[i]}"></span>
                        <strong>${label}:</strong> 
                        ${data.data[i]} (${Math.round((data.data[i]/total)*100)}%)
                    </div>
                `).join('');
            },
        
        },
        'high-value': {
            title: "High Value Claims",
            content: `
                <div class="case-type-selector">
                    <button class="case-type-btn active" data-type="all">All</button>
                    <button class="case-type-btn" data-type="surgical">Surgical</button>
                    <button class="case-type-btn" data-type="medical">Medical</button>
                </div>
                
                <!-- Table Container -->
                <div class="data-table-container">
                    <div class="table-controls">
                        <button class="table-download-btn">
                            <i class="fas fa-download"></i> Export Excel
                        </button>
                        <div class="page-size-selector">
                            <span>Items per page:</span>
                            <select id="pageSizeSelect">
                                <option value="10">10</option>
                                <option value="25">25</option>
                                <option value="50" selected>50</option>
                                <option value="100">100</option>
                            </select>
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Claim ID</th>
                                <th>Patient</th>
                                <th>Hospital</th>
                                <th>District</th>
                                <th>Amount (₹)</th>
                                <th>Type</th>
                            </tr>
                        </thead>
                        <tbody id="highValueClaimsData"></tbody>
                    </table>
                    <div class="table-footer">
                        <div class="pagination-info">
                            Showing <span id="startRecord">0</span> to <span id="endRecord">0</span> of <span id="totalRecords">0</span> records
                        </div>
                        <div class="pagination-controls" id="paginationControls"></div>
                    </div>
                </div>

                <!-- Charts Container -->
                <div class="charts-container" id="highValueCharts"></div>
            `,
            initPagination: function(districts) {
                this.currentPage = 1;
                this.pageSize = 50;
                this.totalPages = 1;
                this.districts = districts;
                
                // Event listeners
                $('#pageSizeSelect').off('change').on('change', () => {
                    this.pageSize = parseInt($('#pageSizeSelect').val());
                    this.currentPage = 1;
                    this.loadTableData(this.currentCaseType, this.districts);
                });
                
                $(document).off('click', '.page-btn').on('click', '.page-btn', (e) => {
                    e.preventDefault();
                    const page = parseInt($(e.currentTarget).data('page'));
                    if (page >= 1 && page <= this.totalPages) {
                        this.currentPage = page;
                        this.loadTableData(this.currentCaseType, this.districts);
                    }
                });
            },
            
            updatePaginationUI: function(paginationData) {
                this.totalPages = paginationData.total_pages;
                
                // Update record count info
                const start = ((this.currentPage - 1) * this.pageSize) + 1;
                const end = Math.min(start + this.pageSize - 1, paginationData.total_records);
                $('#startRecord').text(start.toLocaleString());
                $('#endRecord').text(end.toLocaleString());
                $('#totalRecords').text(paginationData.total_records.toLocaleString());
                
                // Generate pagination buttons
                const paginationControls = $('#paginationControls');
                paginationControls.empty();
                
                // Previous button
                paginationControls.append(`
                    <button class="page-btn ${paginationData.has_previous ? '' : 'disabled'}" 
                            data-page="${this.currentPage - 1}">
                        &laquo; Previous
                    </button>
                `);
                
                // Page numbers
                const maxVisiblePages = 5;
                let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
                let endPage = Math.min(this.totalPages, startPage + maxVisiblePages - 1);
                
                if (endPage - startPage < maxVisiblePages - 1) {
                    startPage = Math.max(1, endPage - maxVisiblePages + 1);
                }
                
                if (startPage > 1) {
                    paginationControls.append(`
                        <button class="page-btn" data-page="1">1</button>
                        ${startPage > 2 ? '<span class="page-dots">...</span>' : ''}
                    `);
                }
                
                for (let i = startPage; i <= endPage; i++) {
                    paginationControls.append(`
                        <button class="page-btn ${i === this.currentPage ? 'active' : ''}" 
                                data-page="${i}">
                            ${i}
                        </button>
                    `);
                }
                
                if (endPage < this.totalPages) {
                    paginationControls.append(`
                        ${endPage < this.totalPages - 1 ? '<span class="page-dots">...</span>' : ''}
                        <button class="page-btn" data-page="${this.totalPages}">
                            ${this.totalPages}
                        </button>
                    `);
                }
                
                // Next button
                paginationControls.append(`
                    <button class="page-btn ${paginationData.has_next ? '' : 'disabled'}" 
                            data-page="${this.currentPage + 1}">
                        Next &raquo;
                    </button>
                `);
            },

            postRender: function(districts) {
                this.initPagination(districts);
                const initialType = 'all';
                this.handleCaseTypeChange(initialType, districts);
                this.initCaseTypeButtons(districts);
                const selected = districts || [];
                const modal = document.querySelector('.modal-container');
                modal.dataset.district = selected.join(',');
                modal.dataset.cardId = 'high-value';
                modal.dataset.pdfUrl  = window.PDF_URLS.highValue;
            },
            handleCaseTypeChange: function(caseType, districts) {
                this.loadTableData(caseType, districts);
                this.loadCharts(caseType, districts);
            },
            loadTableData: function(caseType, districts) {
                this.currentCaseType = caseType;
                const url = `/get-high-value-claims-details/?case_type=${caseType}&district=${districts.join(',')}&page=${this.currentPage}&page_size=${this.pageSize}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(response => {
                        const tbody = document.getElementById('highValueClaimsData');
                        tbody.innerHTML = response.data.map(item => `
                            <tr>
                                <td>${item.serial_no}</td>
                                <td>${item.claim_id}</td>
                                <td>${item.patient_name}</td>
                                <td>${item.hospital_name}</td>
                                <td>${item.district_name}</td>
                                <td>₹${item.amount.toLocaleString('en-IN')}</td>
                                <td class="case-type-${item.case_type.toLowerCase()}">${item.case_type}</td>
                            </tr>
                        `).join('');
                        // document.getElementById('highValueRowCount').textContent = data.length;
                        this.updatePaginationUI(response.pagination);
                    })
                    .catch(error => console.error('Table load error:', error));
            },
            loadCharts: function(caseType, districts) {
                const container = document.getElementById('highValueCharts');
                if(caseType == 'all') {
                    container.innerHTML = `
                    <div class="chart-group">
                        <!-- Bar Charts -->
                        <div class="combined-bar-header">
                            <h2>COMBINED</h2>
                            <div class="chart-container">
                                <h4>Combined District Distribution</h4>
                                <canvas id="highValueAllChart"></canvas>
                            </div>
                        </div>
                        <div class="medical-bar-header">
                            <h2>MEDICAL</h2>
                            <div class="chart-container">
                                <h4>Medical Cases Distribution</h4>
                                <canvas id="highValueMedicalChart"></canvas>
                            </div>
                        </div>
                        <div class="surgical-bar-header">
                            <h2>SURGICAL</h2>
                            <div class="chart-container">
                                <h4>Surgical Cases Distribution</h4>
                                <canvas id="highValueSurgicalChart"></canvas>
                            </div>
                        </div>
                        
                        <!-- Pie Charts -->
                        <div class="combined-pie-header">
                            <h2>COMBINED</h2>
                            <div class="dual-pie-container">
                                <div class="pie-card">
                                    <h4>Combined Age Distribution</h4>
                                    <canvas id="highValueAllAgeChart"></canvas>
                                    <div class="chart-callouts" id="highValueAllAgeCallouts"></div>
                                </div>
                                <div class="pie-card">
                                    <h4>Combined Gender Distribution</h4>
                                    <canvas id="highValueAllGenderChart"></canvas>
                                    <div class="chart-callouts" id="highValueAllGenderCallouts"></div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="medical-pie-header">
                            <h2>MEDICAL</h2>
                            <div class="dual-pie-container">
                                <div class="pie-card">
                                    <h4>Medical Age Distribution</h4>
                                    <canvas id="highValueMedicalAgeChart"></canvas>
                                    <div class="chart-callouts" id="highValueMedicalAgeCallouts"></div>
                                </div>
                                <div class="pie-card">
                                    <h4>Medical Gender Distribution</h4>
                                    <canvas id="highValueMedicalGenderChart"></canvas>
                                    <div class="chart-callouts" id="highValueMedicalGenderCallouts"></div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="surgical-pie-header">
                            <h2>SURGICAL</h2>
                            <div class="dual-pie-container">
                                <div class="pie-card">
                                    <h4>Surgical Age Distribution</h4>
                                    <canvas id="highValueSurgicalAgeChart"></canvas>
                                    <div class="chart-callouts" id="highValueSurgicalAgeCallouts"></div>
                                </div>
                                <div class="pie-card">
                                    <h4>Surgical Gender Distribution</h4>
                                    <canvas id="highValueSurgicalGenderChart"></canvas>
                                    <div class="chart-callouts" id="highValueSurgicalGenderCallouts"></div>
                                </div>
                            </div>
                        </div>
                    </div>`; 
                } else {
                    const cap = this.capitalize(caseType);
                    container.innerHTML = 
                    `<div class="chart-group">
                        <div class="chart-container">
                            <h4>District Distribution (${cap})</h4>
                            <canvas id="highValue${cap}Chart"></canvas>
                        </div>
                        
                        <div class="dual-pie-container">
                            <div class="pie-card">
                                <h4>${this.capitalize(cap)} Age Distribution</h4>
                                <canvas id="highValue${cap}AgeChart"></canvas>
                                <div class="chart-callouts" id="highValue${cap}AgeCallouts"></div>
                            </div>
                            <div class="pie-card">
                                <h4>${this.capitalize(cap)} Gender Distribution</h4>
                                <canvas id="highValue${cap}GenderChart"></canvas>
                                <div class="chart-callouts" id="highValue${cap}GenderCallouts"></div>
                            </div>
                        </div>
                    </div>
                `;
                }
        
                if (caseType === 'all') {
                    this.loadChartData('all', districts, 'highValueAllChart');
                    this.loadChartData('medical', districts, 'highValueMedicalChart');
                    this.loadChartData('surgical', districts, 'highValueSurgicalChart');
                    
                    this.loadDemographics('all', districts, 'highValueAllAgeChart', 'highValueAllGenderChart', 
                        'highValueAllAgeCallouts', 'highValueAllGenderCallouts');
                    this.loadDemographics('medical', districts, 'highValueMedicalAgeChart', 'highValueMedicalGenderChart', 
                        'highValueMedicalAgeCallouts', 'highValueMedicalGenderCallouts');
                    this.loadDemographics('surgical', districts, 'highValueSurgicalAgeChart', 'highValueSurgicalGenderChart', 
                        'highValueSurgicalAgeCallouts', 'highValueSurgicalGenderCallouts');
                } else {
                    const cap = this.capitalize(caseType);
                    this.loadChartData(caseType, districts, `highValue${cap}Chart`);
                    this.loadDemographics(caseType, districts, 
                        `highValue${cap}AgeChart`, 
                        `highValue${cap}GenderChart`, 
                        `highValue${cap}AgeCallouts`, 
                        `highValue${cap}GenderCallouts`);
                }
            },
            loadChartData: function(caseType, districts, canvasId) {
                const url = `/get-high-value-claims-by-district/?case_type=${caseType}&district=${districts.join(',')}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => this.renderBarChart(canvasId, data, caseType))
                    .catch(error => console.error('Chart load error:', error));
            },
            renderBarChart: function(canvasId, data, caseType) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) {
                    console.error('Canvas context not found for:', canvasId);
                    return;
                }
        
                if (window.highValueCharts[canvasId]) {
                    window.highValueCharts[canvasId].destroy();
                }
                
                window.highValueCharts[canvasId] = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.districts,
                        datasets: [{
                            label: `${this.capitalize(caseType)} Claims`,
                            data: data.counts,
                            backgroundColor: caseType === 'surgical' ? '#FF6384' : '#36A2EB',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => `${context.dataset.label}: ${context.parsed.y}`
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Number of Claims' },
                                ticks: { precision: 0 }
                            },
                            x: {
                                title: { display: true, text: 'Districts' },
                                ticks: { 
                                    autoSkip: false,
                                    maxRotation: 45,
                                    minRotation: 45 
                                }
                            }
                        },
                        animation: {
                            onComplete: () => {
                                this.handleChartResize();
                            }
                        },
                    }
                });
            },
            loadDemographics: function(caseType, districts, ageCanvasId, genderCanvasId, ageCalloutId, genderCalloutId) {
                fetch(`/get-high-value-age-distribution/?case_type=${caseType}&district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderPieChart(ageCanvasId, data, ageCalloutId))
                    .catch(error => console.error('Age data error:', error));
        
                fetch(`/get-high-value-gender-distribution/?case_type=${caseType}&district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderPieChart(genderCanvasId, data, genderCalloutId))
                    .catch(error => console.error('Gender data error:', error));
            },
            renderPieChart: function(canvasId, data, calloutId) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) {
                    console.error('Canvas context not found for:', canvasId);
                    return;
                }   
        
                if (window.highValueCharts[canvasId]) {
                    window.highValueCharts[canvasId].destroy();
                }
                
                window.highValueCharts[canvasId] = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.data,
                            backgroundColor: data.colors,
                            borderWidth: 0,
                            cutout: '65%'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => {
                                        const total = context.dataset.data.reduce((a, b) => a + b);
                                        const percentage = Math.round((context.raw / total) * 100);
                                        return `${context.label}: ${context.raw} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    },
                    animation: {
                        onComplete: () => {
                            this.handleChartResize();
                        }
                    },
                });
                
                this.generateCallouts(data, calloutId);
            },
            handleChartResize: function() {
                Object.values(window.highValueCharts).forEach(chart => {
                    chart.resize();
                });
            },
            generateCallouts: function(data, containerId) {
                const container = document.getElementById(containerId);
                if (!container) return;
                const total = data.data.reduce((a, b) => a + b, 0);
                container.innerHTML = data.labels.map((label, i) => `
                    <div class="callout-item">
                        <span class="callout-color" style="background:${data.colors[i]}"></span>
                        <strong>${label}:</strong> 
                        ${data.data[i]} (${Math.round((data.data[i]/total)*100)}%)
                    </div>
                `).join('');
            },
            initCaseTypeButtons: function(districts) {
                $('.case-type-btn').off('click').on('click', e => {
                    const btn = $(e.currentTarget);
                    const caseType = btn.data('type');
                    
                    $('.case-type-btn').removeClass('active');
                    btn.addClass('active');
                    
                    this.handleCaseTypeChange(caseType, districts);
                });
            },
            capitalize: function(str) {
                return str.charAt(0).toUpperCase() + str.slice(1);
            },
            
        },
        'hospital-beds': {
            title: "Hospital Bed Violations Analysis",
            content: `
                <div class="data-table-container">
                    <div class="table-controls">
                        <button class="table-download-btn">
                            <i class="fas fa-download"></i> Export Excel
                        </button>
                        <div class="page-size-selector">
                            <span>Items per page:</span>
                            <select id="hospitalPageSizeSelect">
                                <option value="10">10</option>
                                <option value="25">25</option>
                                <option value="50" selected>50</option>
                                <option value="100">100</option>
                            </select>
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Hospital ID</th>
                                <th>Hospital Name</th>
                                <th>District</th>
                                <th>State</th>
                                <th>Bed Capacity</th>
                                <th>Admissions</th>
                                <th>Excess</th>
                                <th>Last Violation</th>
                            </tr>
                        </thead>
                        <tbody id="hospitalBedData"></tbody>
                    </table>
                    <div class="table-footer">
                        <div class="pagination-info">
                            Showing <span id="hospitalStart">0</span> to 
                            <span id="hospitalEnd">0</span> of 
                            <span id="hospitalTotal">0</span> records
                        </div>
                        <div class="pagination-controls" id="hospitalPagination"></div>
                    </div>
                </div>

                <div class="chart-container">
                    <h4>District-wise Bed Violations</h4>
                    <canvas id="hospitalDistrictChart"></canvas>
                    <div class="chart-legend" id="hospitalDistrictLegend"></div>
                </div>
            `,
            postRender: function(districts) {
                this.initPagination(districts);
                this.loadTableData(districts);
                this.loadChartData(districts);
            },
            initPagination: function(districts) {
                this.currentPage = 1;
                this.pageSize = 50;
                this.districts = districts;

                $('#hospitalPageSizeSelect').off('change').on('change', () => {
                    this.pageSize = parseInt($('#hospitalPageSizeSelect').val());
                    this.currentPage = 1;
                    this.loadTableData(districts);
                });

                $(document).off('click', '.hospital-page-btn').on('click', '.hospital-page-btn', (e) => {
                    const page = parseInt($(e.currentTarget).data('page'));
                    if (page >= 1 && page <= this.totalPages) {
                        this.currentPage = page;
                        this.loadTableData(districts);
                    }
                });
            },
            loadTableData: function(districts) {
                const url = `/get-hospital-bed-details/?district=${districts.join(',')}&page=${this.currentPage}&page_size=${this.pageSize}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(response => {
                        const tbody = document.getElementById('hospitalBedData');
                        tbody.innerHTML = response.data.map(item => `
                            <tr class="${item.excess > 0 ? 'excess-row' : ''}">
                                <td>${item.serial_no}</td>
                                <td>${item.hospital_id}</td>
                                <td>${item.hospital_name}</td>
                                <td>${item.district}</td>
                                <td>${item.state}</td>
                                <td>${item.bed_capacity}</td>
                                <td>${item.admissions}</td>
                                <td class="excess-cell">${item.excess}</td>
                                <td>${item.last_violation}</td>
                            </tr>
                        `).join('');
                        this.updatePaginationUI(response.pagination);
                    })
                    .catch(error => console.error('Table load error:', error));
            },
            loadChartData: function(districts) {
                fetch(`/hospital-violations-by-district/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderBarChart(data));
            },
            renderBarChart: function(data) {
                const ctx = document.getElementById('hospitalDistrictChart')?.getContext('2d');
                if (!ctx) return;

                if (window.hospitalDistrictChart) {
                    window.hospitalDistrictChart.destroy();
                }

                window.hospitalDistrictChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.districts,
                        datasets: [{
                            label: 'Hospital Violations',
                            data: data.counts,
                            backgroundColor: 'rgba(255, 99, 132, 0.7)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => `${context.parsed.y} hospitals in ${context.label}`
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Number of Hospitals' },
                                ticks: { precision: 0 }
                            },
                            x: {
                                title: { display: true, text: 'Districts' },
                                ticks: { 
                                    autoSkip: false,
                                    maxRotation: 45,
                                    minRotation: 45 
                                }
                            }
                        }
                    }
                });
            },
            updatePaginationUI: function(pagination) {
                $('#hospitalStart').text(((pagination.current_page - 1) * this.pageSize + 1).toLocaleString());
                $('#hospitalEnd').text(Math.min(pagination.current_page * this.pageSize, pagination.total_records).toLocaleString());
                $('#hospitalTotal').text(pagination.total_records.toLocaleString());

                const controls = $('#hospitalPagination');
                controls.empty();

                // Previous Button
                controls.append(`
                    <button class="hospital-page-btn ${pagination.has_previous ? '' : 'disabled'}" 
                            data-page="${pagination.current_page - 1}">
                        &laquo; Previous
                    </button>
                `);

                // Page Numbers
                const maxPages = 5;
                let startPage = Math.max(1, pagination.current_page - Math.floor(maxPages/2));
                let endPage = Math.min(pagination.total_pages, startPage + maxPages - 1);

                if (endPage - startPage < maxPages - 1) {
                    startPage = Math.max(1, endPage - maxPages + 1);
                }

                if (startPage > 1) {
                    controls.append(`<button class="hospital-page-btn" data-page="1">1</button>`);
                    if (startPage > 2) controls.append('<span class="page-dots">...</span>');
                }

                for (let i = startPage; i <= endPage; i++) {
                    controls.append(`
                        <button class="hospital-page-btn ${i === pagination.current_page ? 'active' : ''}" 
                                data-page="${i}">
                            ${i}
                        </button>
                    `);
                }

                if (endPage < pagination.total_pages) {
                    if (endPage < pagination.total_pages - 1) controls.append('<span class="page-dots">...</span>');
                    controls.append(`<button class="hospital-page-btn" data-page="${pagination.total_pages}">${pagination.total_pages}</button>`);
                }

                // Next Button
                controls.append(`
                    <button class="hospital-page-btn ${pagination.has_next ? '' : 'disabled'}" 
                            data-page="${pagination.current_page + 1}">
                        Next &raquo;
                    </button>
                `);
            }
        },
        'family-id': {
            title: "Family ID Cases Analysis",
            content: `
                <div class="data-table-container">
                    <div class="table-controls">
                        <button class="table-download-btn">
                            <i class="fas fa-download"></i> Export Excel
                        </button>
                        <div class="page-size-selector">
                            <span>Items per page:</span>
                            <select id="familyPageSizeSelect">
                                <option value="10">10</option>
                                <option value="25">25</option>
                                <option value="50" selected>50</option>
                                <option value="100">100</option>
                            </select>
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Family ID</th>
                                <th>Claim ID</th>
                                <th>Patient</th>
                                <th>District</th>
                                <th>Hospital</th>
                            </tr>
                        </thead>
                        <tbody id="familyCasesData"></tbody>
                    </table>
                    <div class="table-footer">
                        <div class="pagination-info">
                            Showing <span id="familyStartRecord">0</span> to 
                            <span id="familyEndRecord">0</span> of 
                            <span id="familyTotalRecords">0</span> records
                        </div>
                        <div class="pagination-controls" id="familyPaginationControls"></div>
                    </div>
                </div>

                <div class="chart-container">
                    <h4>District-wise Family Violations</h4>
                    <canvas id="familyViolationsChart"></canvas>
                    <div class="chart-legend" id="familyViolationsLegend"></div>
                </div>

                <div class="dual-pie-container">
                    <div class="pie-card">
                        <h4>Age Distribution</h4>
                        <canvas id="familyAgeChart"></canvas>
                        <div class="chart-callouts" id="familyAgeCallouts"></div>
                    </div>
                    <div class="pie-card">
                        <h4>Gender Distribution</h4>
                        <canvas id="familyGenderChart"></canvas>
                        <div class="chart-callouts" id="familyGenderCallouts"></div>
                    </div>
                </div>
            `,
            colorMap: {},
            postRender: function(districts) {
                this.initPagination(districts);
                this.loadTableData(districts);
                this.loadCharts(districts);
            },
            initPagination: function(districts) {
                this.currentPage = 1;
                this.pageSize = 50;
                this.totalPages = 1;
                this.districts = districts;

                $('#familyPageSizeSelect').off('change').on('change', () => {
                    this.pageSize = parseInt($('#familyPageSizeSelect').val());
                    this.currentPage = 1;
                    this.loadTableData(districts);
                });

                $(document).off('click', '.family-page-btn').on('click', '.family-page-btn', (e) => {
                    const page = parseInt($(e.currentTarget).data('page'));
                    if (page >= 1 && page <= this.totalPages) {
                        this.currentPage = page;
                        this.loadTableData(districts);
                    }
                });
            },
            loadTableData: function(districts) {
                const url = `/get-family-id-cases-details/?district=${districts.join(',')}&page=${this.currentPage}&page_size=${this.pageSize}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(response => {
                        const tbody = document.getElementById('familyCasesData');
                        tbody.innerHTML = response.data.map(item => {
                            const color = this.getFamilyColor(item.family_id);
                            return `
                                <tr style="background-color: ${color}">
                                    <td>${item.serial_no}</td>
                                    <td>${item.family_id}</td>
                                    <td>${item.claim_id}</td>
                                    <td>${item.patient_name}</td>
                                    <td>${item.district_name}</td>
                                    <td>${item.hospital_name}</td>
                                </tr>
                            `;
                        }).join('');
                        this.updatePaginationUI(response.pagination);
                    })
                    .catch(error => console.error('Table load error:', error));
            },
            getFamilyColor: function(familyId) {
                if (!this.colorMap[familyId]) {
                    this.colorMap[familyId] = `hsl(${Math.floor(Math.random() * 360)}, 70%, 90%)`;
                }
                return this.colorMap[familyId];
            },
            loadCharts: function(districts) {
                // Bar Chart
                fetch(`/get-family-violations-by-district/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderBarChart('familyViolationsChart', data));
                
                // Pie Charts
                fetch(`/get-family-age-distribution/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderPieChart('familyAgeChart', data, 'familyAgeCallouts'));
                
                fetch(`/get-family-gender-distribution/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderPieChart('familyGenderChart', data, 'familyGenderCallouts'));
            },
            renderBarChart: function(canvasId, data) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) return;

                if (window[canvasId]) window[canvasId].destroy();
                
                window[canvasId] = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.districts,
                        datasets: [{
                            label: 'Family Violations',
                            data: data.counts,
                            backgroundColor: 'rgba(255, 99, 132, 0.7)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => `${context.parsed.y} family violations`
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Number of Families' },
                                ticks: { precision: 0 }
                            },
                            x: {
                                title: { display: true, text: 'Districts' },
                                ticks: { 
                                    autoSkip: false,
                                    maxRotation: 45,
                                    minRotation: 45 
                                }
                            }
                        }
                    }
                });
            },
            renderPieChart: function(canvasId, data, calloutId) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) return;

                if (window[canvasId]) window[canvasId].destroy();
                
                window[canvasId] = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.data,
                            backgroundColor: data.colors,
                            borderWidth: 0,
                            cutout: '65%'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => {
                                        const total = context.dataset.data.reduce((a, b) => a + b);
                                        const percentage = Math.round((context.raw / total) * 100);
                                        return `${context.label}: ${context.raw} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
                
                this.generateCallouts(data, calloutId);
            },
            generateCallouts: function(data, containerId) {
                const container = document.getElementById(containerId);
                if (!container) return;
                
                const total = data.data.reduce((a, b) => a + b, 0);
                container.innerHTML = data.labels.map((label, i) => `
                    <div class="callout-item">
                        <span class="callout-color" style="background:${data.colors[i]}"></span>
                        <strong>${label}:</strong> 
                        ${data.data[i]} (${Math.round((data.data[i]/total)*100)}%)
                    </div>
                `).join('');
            },
            updatePaginationUI: function(paginationData) {
                this.totalPages = paginationData.total_pages;
                
                const start = ((this.currentPage - 1) * this.pageSize) + 1;
                const end = Math.min(start + this.pageSize - 1, paginationData.total_records);
                
                $('#familyStartRecord').text(start.toLocaleString());
                $('#familyEndRecord').text(end.toLocaleString());
                $('#familyTotalRecords').text(paginationData.total_records.toLocaleString());
                
                const paginationControls = $('#familyPaginationControls');
                paginationControls.empty();
                
                // Previous button
                paginationControls.append(`
                    <button class="family-page-btn ${paginationData.has_previous ? '' : 'disabled'}" 
                            data-page="${this.currentPage - 1}">
                        &laquo; Previous
                    </button>
                `);
                
                // Page numbers
                const maxVisiblePages = 5;
                let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
                let endPage = Math.min(this.totalPages, startPage + maxVisiblePages - 1);
                
                if (endPage - startPage < maxVisiblePages - 1) {
                    startPage = Math.max(1, endPage - maxVisiblePages + 1);
                }
                
                if (startPage > 1) {
                    paginationControls.append(`
                        <button class="family-page-btn" data-page="1">1</button>
                        ${startPage > 2 ? '<span class="page-dots">...</span>' : ''}
                    `);
                }
                
                for (let i = startPage; i <= endPage; i++) {
                    paginationControls.append(`
                        <button class="family-page-btn ${i === this.currentPage ? 'active' : ''}" 
                                data-page="${i}">
                            ${i}
                        </button>
                    `);
                }
                
                if (endPage < this.totalPages) {
                    paginationControls.append(`
                        ${endPage < this.totalPages - 1 ? '<span class="page-dots">...</span>' : ''}
                        <button class="family-page-btn" data-page="${this.totalPages}">
                            ${this.totalPages}
                        </button>
                    `);
                }
                
                // Next button
                paginationControls.append(`
                    <button class="family-page-btn ${paginationData.has_next ? '' : 'disabled'}" 
                            data-page="${this.currentPage + 1}">
                        Next &raquo;
                    </button>
                `);
            }
        },
        'geo-anomalies': {
            title: "Geographic Anomalies Analysis",
            content: `
                <div class="data-table-container">
                    <div class="table-controls">
                        <button class="table-download-btn">
                            <i class="fas fa-download"></i> Export Excel
                        </button>
                        <div class="page-size-selector">
                            <span>Items per page:</span>
                            <select id="geoPageSizeSelect">
                                <option value="10">10</option>
                                <option value="25">25</option>
                                <option value="50" selected>50</option>
                                <option value="100">100</option>
                            </select>
                        </div>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Claim ID</th>
                                <th>Patient</th>
                                <th>Hospital</th>
                                <th>District</th>
                                <th>Patient State</th>
                                <th>Hospital State</th>
                            </tr>
                        </thead>
                        <tbody id="geoCasesData"></tbody>
                    </table>
                    <div class="table-footer">
                        <div class="pagination-info">
                            Showing <span id="geoStartRecord">0</span> to 
                            <span id="geoEndRecord">0</span> of 
                            <span id="geoTotalRecords">0</span> records
                        </div>
                        <div class="pagination-controls" id="geoPaginationControls"></div>
                    </div>
                </div>

                <div class="chart-container">
                    <h4>State-wise Anomalies</h4>
                    <canvas id="geoViolationsChart"></canvas>
                    <div class="chart-legend" id="geoViolationsLegend"></div>
                </div>

                <div class="dual-pie-container">
                    <div class="pie-card">
                        <h4>Age Distribution</h4>
                        <canvas id="geoAgeChart"></canvas>
                        <div class="chart-callouts" id="geoAgeCallouts"></div>
                    </div>
                    <div class="pie-card">
                        <h4>Gender Distribution</h4>
                        <canvas id="geoGenderChart"></canvas>
                        <div class="chart-callouts" id="geoGenderCallouts"></div>
                    </div>
                </div>
            `,
            postRender: function(districts) {
                this.initPagination(districts);
                this.loadTableData(districts);
                this.loadCharts(districts);
            },
            initPagination: function(districts) {
                this.currentPage = 1;
                this.pageSize = 50;
                this.totalPages = 1;
                this.districts = districts;

                $('#geoPageSizeSelect').off('change').on('change', () => {
                    this.pageSize = parseInt($('#geoPageSizeSelect').val());
                    this.currentPage = 1;
                    this.loadTableData(districts);
                });

                $(document).off('click', '.geo-page-btn').on('click', '.geo-page-btn', (e) => {
                    const page = parseInt($(e.currentTarget).data('page'));
                    if (page >= 1 && page <= this.totalPages) {
                        this.currentPage = page;
                        this.loadTableData(districts);
                    }
                });
            },
            loadTableData: function(districts) {
                const url = `/get-geo-anomalies-details/?district=${districts.join(',')}&page=${this.currentPage}&page_size=${this.pageSize}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(response => {
                        const tbody = document.getElementById('geoCasesData');
                        tbody.innerHTML = response.data.map(item => `
                            <tr>
                                <td>${item.serial_no}</td>
                                <td>${item.claim_id}</td>
                                <td>${item.patient_name}</td>
                                <td>${item.hospital_name}</td>
                                <td>${item.district_name}</td>
                                <td>${item.patient_state}</td>
                                <td>${item.hospital_state}</td>
                            </tr>
                        `).join('');
                        this.updatePaginationUI(response.pagination);
                    })
                    .catch(error => console.error('Table load error:', error));
            },
            loadCharts: function(districts) {
                // Bar Chart
                fetch(`/get-geo-violations-by-state/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderBarChart('geoViolationsChart', data));
                
                // Pie Charts
                fetch(`/get-geo-demographics/age/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderPieChart('geoAgeChart', data, 'geoAgeCallouts'));
                
                fetch(`/get-geo-demographics/gender/?district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderPieChart('geoGenderChart', data, 'geoGenderCallouts'));
            },
            renderBarChart: function(canvasId, data) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) return;

                if (window[canvasId]) window[canvasId].destroy();
                
                window[canvasId] = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.states,
                        datasets: [{
                            label: 'State Anomalies',
                            data: data.counts,
                            backgroundColor: 'rgba(54, 162, 235, 0.7)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => `${context.parsed.y} state mismatches`
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Number of Cases' },
                                ticks: { precision: 0 }
                            },
                            x: {
                                title: { display: true, text: 'Patient States' },
                                ticks: { 
                                    autoSkip: false,
                                    maxRotation: 45,
                                    minRotation: 45 
                                }
                            }
                        }
                    }
                });
            },
            renderPieChart: function(canvasId, data, calloutId) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) return;

                if (window[canvasId]) window[canvasId].destroy();
                
                window[canvasId] = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.data,
                            backgroundColor: data.colors,
                            borderWidth: 0,
                            cutout: '65%'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => {
                                        const total = context.dataset.data.reduce((a, b) => a + b);
                                        const percentage = Math.round((context.raw / total) * 100);
                                        return `${context.label}: ${context.raw} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
                
                this.generateCallouts(data, calloutId);
            },
            generateCallouts: function(data, containerId) {
                const container = document.getElementById(containerId);
                if (!container) return;
                
                const total = data.data.reduce((a, b) => a + b, 0);
                container.innerHTML = data.labels.map((label, i) => `
                    <div class="callout-item">
                        <span class="callout-color" style="background:${data.colors[i]}"></span>
                        <strong>${label}:</strong> 
                        ${data.data[i]} (${total > 0 ? Math.round((data.data[i]/total)*100) : 0}%)
                    </div>
                `).join('');
            },
            updatePaginationUI: function(paginationData) {
                this.totalPages = paginationData.total_pages;
                
                const start = ((this.currentPage - 1) * this.pageSize) + 1;
                const end = Math.min(start + this.pageSize - 1, paginationData.total_records);
                
                $('#geoStartRecord').text(start.toLocaleString());
                $('#geoEndRecord').text(end.toLocaleString());
                $('#geoTotalRecords').text(paginationData.total_records.toLocaleString());
                
                const paginationControls = $('#geoPaginationControls');
                paginationControls.empty();
                
                // Previous button
                paginationControls.append(`
                    <button class="geo-page-btn ${paginationData.has_previous ? '' : 'disabled'}" 
                            data-page="${this.currentPage - 1}">
                        &laquo; Previous
                    </button>
                `);
                
                // Page numbers
                const maxVisiblePages = 5;
                let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
                let endPage = Math.min(this.totalPages, startPage + maxVisiblePages - 1);
                
                if (endPage - startPage < maxVisiblePages - 1) {
                    startPage = Math.max(1, endPage - maxVisiblePages + 1);
                }
                
                if (startPage > 1) {
                    paginationControls.append(`
                        <button class="geo-page-btn" data-page="1">1</button>
                        ${startPage > 2 ? '<span class="page-dots">...</span>' : ''}
                    `);
                }
                
                for (let i = startPage; i <= endPage; i++) {
                    paginationControls.append(`
                        <button class="geo-page-btn ${i === this.currentPage ? 'active' : ''}" 
                                data-page="${i}">
                            ${i}
                        </button>
                    `);
                }
                
                if (endPage < this.totalPages) {
                    paginationControls.append(`
                        ${endPage < this.totalPages - 1 ? '<span class="page-dots">...</span>' : ''}
                        <button class="geo-page-btn" data-page="${this.totalPages}">
                            ${this.totalPages}
                        </button>
                    `);
                }
                
                // Next button
                paginationControls.append(`
                    <button class="geo-page-btn ${paginationData.has_next ? '' : 'disabled'}" 
                            data-page="${this.currentPage + 1}">
                        Next &raquo;
                    </button>
                `);
            }
        },
        'ophthalmology': {
            title: "Ophthalmology Analysis",
            content: `
                <div class="violation-type-selector">
                    <button class="violation-type-btn active" data-type="all">All</button>
                    <button class="violation-type-btn" data-type="age">Age <40</button>
                    <button class="violation-type-btn" data-type="ot">OT Cases</button>
                    <button class="violation-type-btn" data-type="preauth">Pre-auth Time</button>
                </div>
                
                <div class="data-table-container">
                    <div class="table-controls">
                        <button class="table-download-btn">
                            <i class="fas fa-download"></i> Export Excel
                        </button>
                        <div class="page-size-selector">
                            <span>Items per page:</span>
                            <select id="ophthPageSizeSelect">
                                <option value="10">10</option>
                                <option value="25">25</option>
                                <option value="50" selected>50</option>
                                <option value="100">100</option>
                            </select>
                        </div>
                    </div>
                    <table class="data-table" id="ophthTable">
                        <thead id="ophthTableHeader"></thead>
                        <tbody id="ophthCasesData"></tbody>
                    </table>
                    <div class="table-footer">
                        <div class="pagination-info">
                            Showing <span id="ophthStartRecord">0</span> to 
                            <span id="ophthEndRecord">0</span> of 
                            <span id="ophthTotalRecords">0</span> records
                        </div>
                        <div class="pagination-controls" id="ophthPaginationControls"></div>
                    </div>
                </div>

                <div class="charts-container" id="ophthCharts"></div>
            `,
            currentViolationType: 'all',
            colorMap: {
                age: '#FFEB3B',
                ot: '#E91E63',
                preauth: '#009688',
                all: '#9C27B0'
            },
            postRender: function(districts) {
                this.initPagination(districts);
                this.initViolationTypeButtons(districts);
                this.loadTableData('all', districts);
                this.loadCharts('all', districts);
            },
            initPagination: function(districts) {
                this.currentPage = 1;
                this.pageSize = 50;
                this.totalPages = 1;
                this.districts = districts;

                $('#ophthPageSizeSelect').off('change').on('change', () => {
                    this.pageSize = parseInt($('#ophthPageSizeSelect').val());
                    this.currentPage = 1;
                    this.loadTableData(this.currentViolationType, districts);
                });

                $(document).off('click', '.ophth-page-btn').on('click', '.ophth-page-btn', (e) => {
                    const page = parseInt($(e.currentTarget).data('page'));
                    if (page >= 1 && page <= this.totalPages) {
                        this.currentPage = page;
                        this.loadTableData(this.currentViolationType, districts);
                    }
                });
            },
            updatePaginationUI: function(paginationData) {
                this.totalPages = paginationData.total_pages;
                const start = ((this.currentPage - 1) * this.pageSize) + 1;
                const end = Math.min(start + this.pageSize - 1, paginationData.total_records);
                
                $('#ophthStartRecord').text(start.toLocaleString());
                $('#ophthEndRecord').text(end.toLocaleString());
                $('#ophthTotalRecords').text(paginationData.total_records.toLocaleString());
                
                const controls = $('#ophthPaginationControls').empty();
                
                // Previous button
                controls.append(`
                    <button class="ophth-page-btn ${paginationData.has_previous ? '' : 'disabled'}" 
                            data-page="${this.currentPage - 1}">
                        &laquo; Previous
                    </button>
                `);

                // Page numbers
                const maxVisiblePages = 5;
                let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
                let endPage = Math.min(this.totalPages, startPage + maxVisiblePages - 1);
                
                if (endPage - startPage < maxVisiblePages - 1) {
                    startPage = Math.max(1, endPage - maxVisiblePages + 1);
                }
                
                if (startPage > 1) {
                    controls.append(`
                        <button class="ophth-page-btn" data-page="1">1</button>
                        ${startPage > 2 ? '<span class="page-dots">...</span>' : ''}
                    `);
                }
                
                for (let i = startPage; i <= endPage; i++) {
                    controls.append(`
                        <button class="ophth-page-btn ${i === this.currentPage ? 'active' : ''}" 
                                data-page="${i}">
                            ${i}
                        </button>
                    `);
                }
                
                if (endPage < this.totalPages) {
                    controls.append(`
                        ${endPage < this.totalPages - 1 ? '<span class="page-dots">...</span>' : ''}
                        <button class="ophth-page-btn" data-page="${this.totalPages}">
                            ${this.totalPages}
                        </button>
                    `);
                }
                
                // Next button
                controls.append(`
                    <button class="ophth-page-btn ${paginationData.has_next ? '' : 'disabled'}" 
                            data-page="${this.currentPage + 1}">
                        Next &raquo;
                    </button>
                `);
            },
            initViolationTypeButtons: function(districts) {
                $('.violation-type-btn').off('click').on('click', (e) => {
                    const btn = $(e.currentTarget);
                    const violationType = btn.data('type');
                    
                    $('.violation-type-btn').removeClass('active');
                    btn.addClass('active');
                    
                    this.currentViolationType = violationType;
                    this.currentPage = 1;
                    this.loadTableData(violationType, districts);
                    this.loadCharts(violationType, districts);
                });
            },
            loadTableData: function(violationType, districts) {
                const url = `/get-ophthalmology-details/?type=${violationType}&district=${districts.join(',')}&page=${this.currentPage}&page_size=${this.pageSize}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(response => {
                        this.updateTableHeader(violationType);
                        this.updateTableBody(response.data, violationType);
                        this.updatePaginationUI(response.pagination);
                    })
                    .catch(error => console.error('Error loading table data:', error));
            },
            updateTableHeader: function(violationType) {
                const headers = {
                    all: ['#', 'Claim ID', 'Patient', 'Hospital', 'District', 'Amount', 'Age<40', 'OT Cases', 'Pre-auth Time'],
                    age: ['#', 'Claim ID', 'Patient', 'Hospital', 'District', 'Amount', 'Age<40'],
                    ot: ['#', 'Claim ID', 'Patient', 'Hospital', 'District', 'Amount', 'OT Cases'],
                    preauth: ['#', 'Claim ID', 'Patient', 'Hospital', 'District', 'Amount', 'Pre-auth Time']
                };

                const headerHTML = headers[violationType].map(h => `<th>${h}</th>`).join('');
                $('#ophthTableHeader').html(`<tr>${headerHTML}</tr>`);
            },
            updateTableBody: function(data, violationType) {
                const rows = data.map(item => {
                    const baseCols = `
                        <td>${item.serial_no}</td>
                        <td>${item.claim_id}</td>
                        <td>${item.patient_name}</td>
                        <td>${item.hospital_name}</td>
                        <td>${item.district_name}</td>
                        <td>₹${item.amount?.toLocaleString('en-IN') || '0'}</td>
                    `;

                    let violationCols = '';
                    if (violationType === 'all') {
                        violationCols = `
                            <td class="${item.age_violation ? 'age-violation' : ''}">${item.age_violation ? 'Yes' : ''}</td>
                            <td class="${item.ot_violation ? 'ot-violation' : ''}">${item.ot_violation ? 'Yes' : ''}</td>
                            <td class="${item.preauth_violation ? 'preauth-violation' : ''}">${item.preauth_violation ? 'Yes' : ''}</td>
                        `;
                    } else {
                        const violationClass = `${violationType}-violation`;
                        violationCols = `<td class="${violationClass}">Yes</td>`;
                    }

                    return `<tr>${baseCols}${violationCols}</tr>`;
                });
                
                $('#ophthCasesData').html(rows.join(''));
            },
            loadCharts: function(violationType, districts) {
                const container = $('#ophthCharts');
                container.empty();
                
                if (violationType === 'all') {
                    container.html(`
                        <div class="chart-group">
                            <!-- Combined Bar Chart -->
                            <div class="ophthalmology-combined-bar-header">
                                <h2>COMBINED</h2>
                                <div class="chart-container">
                                    <h4>Combined Distribution</h4>
                                    <canvas id="ophthCombinedChart"></canvas>
                                </div>
                            </div>
                            
                            <!-- Individual Bar Charts -->
                            <div class="ophthalmology-age-bar-header">
                                <h2>Age Less Than 40</h2>
                                <div class="chart-container">
                                    <h4>Age &lt;40 Distribution</h4>
                                    <canvas id="ophthAgeChart"></canvas>
                                </div>
                            </div>

                            <div class="ophthalmology-ot-bar-header">
                                <h2>OT Cases</h2>
                                <div class="chart-container">
                                    <h4>OT Cases Distribution</h4>
                                    <canvas id="ophthOtChart"></canvas>
                                </div>
                            </div>

                            <div class="ophthalmology-preauth-bar-header">
                                <h2>Pre-auth Time Cases</h2>
                                <div class="chart-container">
                                    <h4>Pre-auth Time Distribution</h4>
                                    <canvas id="ophthPreauthChart"></canvas>
                                </div>
                            </div>

                            <!-- Pie Charts Container -->
                            <div class="dual-pie-container">
                                <!-- Combined Pies -->
                                <div class="pie-card">
                                    <h4>Combined Age</h4>
                                    <canvas id="ophthAllAgeChart"></canvas>
                                    <div class="chart-callouts" id="ophthAllAgeCallouts"></div>
                                </div>
                                <div class="pie-card">
                                    <h4>Combined Gender</h4>
                                    <canvas id="ophthAllGenderChart"></canvas>
                                    <div class="chart-callouts" id="ophthAllGenderCallouts"></div>
                                </div>

                                <!-- Age <40 Pies -->
                                <div class="pie-card">
                                    <h4>Age &lt;40 Age</h4>
                                    <canvas id="ophthAgeAgeChart"></canvas>
                                    <div class="chart-callouts" id="ophthAgeAgeCallouts"></div>
                                </div>
                                <div class="pie-card">
                                    <h4>Age &lt;40 Gender</h4>
                                    <canvas id="ophthAgeGenderChart"></canvas>
                                    <div class="chart-callouts" id="ophthAgeGenderCallouts"></div>
                                </div>

                                <!-- OT Cases Pies -->
                                <div class="pie-card">
                                    <h4>OT Cases Age</h4>
                                    <canvas id="ophthOtAgeChart"></canvas>
                                    <div class="chart-callouts" id="ophthOtAgeCallouts"></div>
                                </div>
                                <div class="pie-card">
                                    <h4>OT Cases Gender</h4>
                                    <canvas id="ophthOtGenderChart"></canvas>
                                    <div class="chart-callouts" id="ophthOtGenderCallouts"></div>
                                </div>

                                <!-- Pre-auth Pies -->
                                <div class="pie-card">
                                    <h4>Pre-auth Age</h4>
                                    <canvas id="ophthPreauthAgeChart"></canvas>
                                    <div class="chart-callouts" id="ophthPreauthAgeCallouts"></div>
                                </div>
                                <div class="pie-card">
                                    <h4>Pre-auth Gender</h4>
                                    <canvas id="ophthPreauthGenderChart"></canvas>
                                    <div class="chart-callouts" id="ophthPreauthGenderCallouts"></div>
                                </div>
                            </div>
                        </div>
                    `);
                    
                    ['all', 'age', 'ot', 'preauth'].forEach(type => {
                        const canvasId = type === 'all' 
                        ? 'ophthCombinedChart' 
                        : `ophth${this.capitalize(type)}Chart`;
                    this.loadBarChart(type, districts, canvasId, `ophth${this.capitalize(type)}Legend`);
                    });

                    this.loadPieCharts('all', districts); // Combined pies
                    ['age', 'ot', 'preauth'].forEach(type => {
                        this.loadPieCharts(type, districts); // Individual violation pies
                    });
                } else {
                    container.html(`
                        <div class="chart-group">
                            <div class="chart-container">
                                <h4>${this.capitalize(violationType)} Distribution</h4>
                                <canvas id="ophth${this.capitalize(violationType)}Chart"></canvas>
                                <div class="chart-legend" id="ophth${this.capitalize(violationType)}Legend"></div>
                            </div>
                            <div class="dual-pie-container">
                                <div class="pie-card">
                                    <h4>Age Distribution</h4>
                                    <canvas id="ophth${this.capitalize(violationType)}AgeChart"></canvas>
                                    <div class="chart-callouts" id="ophth${this.capitalize(violationType)}AgeCallouts"></div>
                                </div>
                                <div class="pie-card">
                                    <h4>Gender Distribution</h4>
                                    <canvas id="ophth${this.capitalize(violationType)}GenderChart"></canvas>
                                    <div class="chart-callouts" id="ophth${this.capitalize(violationType)}GenderCallouts"></div>
                                </div>
                            </div>
                        </div>
                    `);
                    
                    this.loadBarChart(violationType, districts, `ophth${this.capitalize(violationType)}Chart`, `ophth${this.capitalize(violationType)}Legend`);
                    this.loadPieCharts(violationType, districts);
                }
            },
            loadBarChart: function(violationType, districts, canvasId, legendId) {
                fetch(`/get-ophthalmology-distribution/?type=${violationType}&district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderBarChart(canvasId, legendId, data, violationType))
                    .catch(error => console.error('Error loading bar chart:', error));
            },
            loadPieCharts: function(violationType, districts) {
                fetch(`/get-ophthalmology-demographics/age/?violation_type=${violationType}&district=${districts.join(',')}`)
                    .then(response => {
                        if (!response.ok) throw new Error('Network error');
                        return response.json();
                    })
                    .then(data => this.renderPieChart(
                        `ophth${this.capitalize(violationType)}AgeChart`, 
                        `ophth${this.capitalize(violationType)}AgeCallouts`, 
                        data
                    ))
                    .catch(error => {
                        console.error('Age demo error:', error);
                        document.getElementById(`ophth${this.capitalize(violationType)}AgeChart`).innerHTML = 
                            '<div class="chart-error">Failed to load age data</div>';
                    });
                    
                fetch(`/get-ophthalmology-demographics/gender/?violation_type=${violationType}&district=${districts.join(',')}`)
                    .then(response => response.json())
                    .then(data => this.renderPieChart(
                        `ophth${this.capitalize(violationType)}GenderChart`, 
                        `ophth${this.capitalize(violationType)}GenderCallouts`, 
                        data
                    ))
                    .catch(error => {
                        console.error('Gender demo error:', error);
                        document.getElementById(`ophth${this.capitalize(violationType)}GenderChart`).innerHTML = 
                            '<div class="chart-error">Failed to load age data</div>';
                    });
            },
            renderBarChart: function(canvasId, legendId, data, violationType) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) return;

                if (window.ophthCharts?.[canvasId]) {
                    window.ophthCharts[canvasId].destroy();
                }
                
                window.ophthCharts = window.ophthCharts || {};
                window.ophthCharts[canvasId] = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.districts,
                        datasets: [{
                            label: `${this.formatLabel(violationType)} Cases`,
                            data: data.counts,
                            backgroundColor: this.colorMap[violationType],
                            borderColor: this.adjustColor(this.colorMap[violationType], -20),
                            borderWidth: 1,
                            hoverBackgroundColor: this.adjustColor(this.colorMap[violationType], 20)
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
                                    label: context => `${context.dataset.label}: ${context.parsed.y}`
                                }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { 
                                    display: true, 
                                    text: 'Number of Cases',
                                    font: { weight: 'bold' }
                                },
                                ticks: { precision: 0 }
                            },
                            x: {
                                title: { 
                                    display: true, 
                                    text: 'Districts',
                                    font: { weight: 'bold' }
                                },
                                ticks: { 
                                    autoSkip: false,
                                    maxRotation: 45,
                                    minRotation: 45 
                                }
                            }
                        },
                        animation: {
                            duration: 1000,
                            easing: 'easeOutQuart'
                        }
                    }
                });

                // Generate legend
                if (legendId) {
                    const legend = document.getElementById(legendId);
                    if (legend) {
                        legend.innerHTML = `
                            <div class="legend-item">
                                <span class="legend-color" style="background:${this.colorMap[violationType]}"></span>
                                <span>${this.formatLabel(violationType)} Cases</span>
                            </div>
                        `;
                    }
                }
            },
            renderPieChart: function(canvasId, calloutId, data) {
                const ctx = document.getElementById(canvasId)?.getContext('2d');
                if (!ctx) return;

                if (window.ophthCharts?.[canvasId]) {
                    window.ophthCharts[canvasId].destroy();
                }
                
                window.ophthCharts = window.ophthCharts || {};
                window.ophthCharts[canvasId] = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.data,
                            backgroundColor: data.colors,
                            borderWidth: 0,
                            cutout: '65%'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                callbacks: {
                                    label: context => {
                                        const total = context.dataset.data.reduce((a, b) => a + b);
                                        const percentage = Math.round((context.raw / total) * 100);
                                        return `${context.label}: ${context.raw} (${percentage}%)`;
                                    }
                                }
                            }
                        },
                        animation: {
                            animateScale: true,
                            animateRotate: true
                        }
                    }
                });
                
                this.generateCallouts(data, calloutId);
            },
            generateCallouts: function(data, containerId) {
                const container = document.getElementById(containerId);
                if (!container) return;
                
                const total = data.data.reduce((a, b) => a + b, 0);
                container.innerHTML = data.labels.map((label, i) => `
                    <div class="callout-item">
                        <span class="callout-color" style="background:${data.colors[i]}"></span>
                        <strong>${label}:</strong> 
                        ${data.data[i]} (${total > 0 ? Math.round((data.data[i]/total)*100) : 0}%)
                    </div>
                `).join('');
            },
            capitalize: function(str) {
                return str.charAt(0).toUpperCase() + str.slice(1);
            },
            formatLabel: function(type) {
                const labels = {
                    'age': 'Age <40',
                    'ot': 'OT',
                    'preauth': 'Pre-auth Time',
                    'all': 'All'
                };
                return labels[type] || type;
            },
            adjustColor: function(color, amount) {
                return '#' + color.replace(/^#/, '').replace(/../g, color => 
                    ('0' + Math.min(255, Math.max(0, parseInt(color, 16) + amount)).toString(16)).substr(-2)
                );
            }
        },
        // 'age': {
        //     title: "Age Analysis",
        //     content: `<div class="card-details">
        //                 <h4>Patient Age Distribution</h4>
        //                 <div class="age-metrics">
        //                     <div class="metric">
        //                         <span>Under 40:</span>
        //                         <span>64 cases</span>
        //                     </div>
        //                 </div>
        //               </div>`
        // },
        // 'ot-cases': {
        //     title: "OT Cases",
        //     content: `<div class="card-details">
        //                 <h4>Operation Theater Cases</h4>
        //                 <div class="ot-metrics">
        //                     <div class="metric">
        //                         <span>This Month:</span>
        //                         <span>183 cases</span>
        //                     </div>
        //                 </div>
        //               </div>`
        // }
    };

    function getCookie(name) {
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
        return cookieValue;
    }

    function renderFlaggedClaimsChart(data) {
        console.log("Chart rendering started with data:", data); // Debug
        
        const canvas = document.getElementById('flaggedClaimsChart');
        if (!canvas) {
            console.error('Canvas element not found');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        // Safely destroy previous chart
        if (window.flaggedClaimsChart instanceof Chart) {
            window.flaggedClaimsChart.destroy();
        }
        
        // Handle empty data
        if (!data || !data.districts || !data.counts || data.districts.length === 0) {
            console.warn("No valid chart data received");
            canvas.style.display = 'none';
            const legend = document.getElementById('flaggedClaimsLegend');
            if (legend) legend.innerHTML = '<p>No district data available</p>';
            return;
        }
        
        try {
            window.flaggedClaimsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.districts,
                    datasets: [{
                        label: 'Flagged Claims',
                        data: data.counts,
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.parsed.y} claims`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Number of Claims' },
                            ticks: { precision: 0 }
                        },
                        x: {
                            title: { display: true, text: 'Districts' },
                            ticks: { 
                                autoSkip: false,
                                maxRotation: 45,
                                minRotation: 45 
                            }
                        }
                    }
                }
            });
            console.log("Chart rendered successfully");
        } catch (error) {
            console.error("Chart rendering error:", error);
            canvas.style.display = 'none';
            const legend = document.getElementById('flaggedClaimsLegend');
            if (legend) legend.innerHTML = '<p>Error rendering chart</p>';
        }
    }

    function initDemographicCharts(districts) {
        // Load age distribution
        fetch(`/get-age-distribution/${districts.length ? `?district=${districts.join(',')}` : ''}`)
            .then(response => response.json())
            .then(data => renderPieChart('agePieChart', data, 'ageCallouts'));
        
        // Load gender distribution
        fetch(`/get-gender-distribution/${districts.length ? `?district=${districts.join(',')}` : ''}`)
            .then(response => response.json())
            .then(data => renderPieChart('genderPieChart', data, 'genderCallouts'));
    }
    
    function renderPieChart(canvasId, data, calloutId) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        // Destroy existing chart if it exists
        if (canvasId === 'agePieChart' && agePieChart) agePieChart.destroy();
        if (canvasId === 'genderPieChart' && genderPieChart) genderPieChart.destroy();
        
        // Create new chart
        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.data,
                    backgroundColor: data.colors,
                    borderWidth: 0,
                    cutout: '65%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b);
                                const percentage = Math.round((context.raw / total) * 100);
                                return `${context.label}: ${context.raw} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    animateScale: true,
                    animateRotate: true
                }
            }
        });
        
        // Store chart reference
        if (canvasId === 'agePieChart') agePieChart = chart;
        if (canvasId === 'genderPieChart') genderPieChart = chart;
        
        // Generate callouts
        generateCallouts(data, calloutId);
    }
    
    function generateCallouts(data, containerId) {
        const total = data.data.reduce((a, b) => a + b, 0);
        const calloutHTML = data.labels.map((label, i) => {
            const value = data.data[i];
            const percentage = Math.round((value / total) * 100);
            return `
                <div class="callout-item">
                    <span class="callout-color" style="background:${data.colors[i]}"></span>
                    <strong>${label}&nbsp:&nbsp</strong> 
                    ${value} (${percentage}%)
                </div>
            `;
        }).join('');
        
        document.getElementById(containerId).innerHTML = calloutHTML;
    }

    // fetch CSRF token…
    function getCookie(name) {
        let v = null;
        document.cookie.split(';').forEach(c => {
        const [k, val] = c.trim().split('=');
        if (k === name) v = decodeURIComponent(val);
        });
        return v;
    }

    function generatePDFReport() {
        const loader      = document.getElementById('pdfLoader');
        const progressBar = document.getElementById('pdfProgressBar');
        const progressTxt = document.getElementById('pdfProgressText');
        const downloadBtn = document.querySelector('.modal-pdf-download');
        const modal       = document.querySelector('.modal-container');
        const cardId      = modal.dataset.cardId;       // 'flagged-claims' or 'high-value'
        const downloadUrl = modal.dataset.pdfUrl;
        const district    = modal.dataset.district || '';
      
        // Show loader & disable button
        loader.classList.add('show');
        downloadBtn.disabled = true;
      
        // Simulate progress to 90%
        let prog = 0;
        progressBar.style.width = '0%';
        progressTxt.textContent  = '0%';
        const interval = setInterval(() => {
          if (prog < 90) {
            prog++;
            progressBar.style.width = `${prog}%`;
            progressTxt.textContent  = `${prog}%`;
          } else {
            clearInterval(interval);
          }
        }, 50);
      
        // Build payload
        const fd = new FormData();
        fd.append('district', district);
      
        if (cardId === 'flagged-claims') {
          ['flagged','age','gender'].forEach(key => {
            const idMap = {
              flagged: 'flaggedClaimsChart',
              age:     'agePieChart',
              gender:  'genderPieChart'
            };
            fd.append(`${key}_chart`, safeCanvasDataURL(idMap[key]));
          });
          ['age','gender'].forEach(key => {
            fd.append(`${key}_callouts`, safeInnerHTML(key + 'Callouts'));
          });
        }
        else if (cardId === 'high-value') {
          // Determine which sub-type to include
          const activeBtn = document.querySelector('.case-type-btn.active');
          const caseType  = activeBtn?.dataset.type || 'all';  // 'all','surgical','medical'
          fd.append('case_type', caseType);
      
          // Pick the right sections
          const typesToDo = caseType === 'all'
            ? ['Surgical','Medical']
            : [ caseType.charAt(0).toUpperCase() + caseType.slice(1) ];
      
          typesToDo.forEach(type => {
            const key = type.toLowerCase();
            // Charts
            ['chart','age_chart','gender_chart'].forEach(suffix => {
              const field    = `${key}_${suffix}`;
              const canvasId = `highValue${type}` + {
                chart:       'Chart',
                age_chart:   'AgeChart',
                gender_chart:'GenderChart'
              }[suffix];
              fd.append(field, safeCanvasDataURL(canvasId));
            });
            // Callouts
            ['AgeCallouts','GenderCallouts'].forEach(suffix => {
              const field = `${key}_` + suffix.toLowerCase();
              fd.append(field, safeInnerHTML(`highValue${type}${suffix}`));
            });
          });
        }
      
        // Fire the request
        fetch(downloadUrl, {
          method:  'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
          body:    fd
        })
        .then(r => r.blob())
        .then(blob => {
          clearInterval(interval);
          progressBar.style.width = '100%';
          progressTxt.textContent  = '100%';
          setTimeout(() => {
            loader.classList.remove('show');
            downloadBtn.disabled = false;
      
            // Trigger download
            const url = URL.createObjectURL(blob);
            const a   = document.createElement('a');
            a.href    = url;
            a.download = cardId === 'flagged-claims'
              ? 'flagged_claims_report.pdf'
              : 'High_Value_Claims_PDF_Report.pdf';
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
          }, 200);
        })
        .catch(err => {
          console.error(err);
          clearInterval(interval);
          loader.classList.remove('show');
          downloadBtn.disabled = false;
        });
    }      

    const ModalController = {
        init() {
          $('#modalOverlay').hide().removeClass('show');
          this.setupEventListeners();
        },
      
        setupEventListeners() {
            $(document).off('click.modal', '.card')
                        .off('click.modal', '.modal-close')
                        .off('click.modal', '.modal-overlay')
                        .off('keyup.modal')
                        .off('click.modal', '.modal-pdf-download')
                        .off('click.modal', '.modal-container .table-download-btn');

            $(document).off('.modal');
        
            // Card click → open modal
            $(document).on('click.modal', '.card', (e) => {
                if ($(e.target).is('.download-btn, .download-btn *')) return;
                const cardId    = $(e.currentTarget).attr('class').split(' ')[1];
                const districts = getSelectedDistricts();
                this.open(cardId, districts);
            });
        
            // Close
            $(document).on('click.modal', '.modal-close', (e) => {
                e.stopPropagation();
                ModalController.close();
              });

            // Overlay click handler
            $(document).on('click', '.modal-overlay', function(e) {
                if (e.target === this) ModalController.close();
            });
        
            // ESC key
            $(document).on('keyup.modal', (e) => {
            if (e.key === 'Escape' && $('#modalOverlay').is(':visible')) {
                this.close();
            }
            });
        
            // PDF download (unchanged)
            $(document).on('click.modal', '.modal-pdf-download', (e) => {
                e.preventDefault();
                generatePDFReport();
            });
        
            // **Excel download in modal**
            $(document).on('click.modal', '.modal-container .table-download-btn', (e) => {
                e.preventDefault();
                const $m        = $(e.currentTarget).closest('.modal-container');
                const baseUrl   = $m.data('excel-url');
                const district  = $m.data('district') || '';
                let url         = baseUrl;
                if (district) url += '?district=' + encodeURIComponent(district);
                window.location.href = url;
            });
        },
      
        open(cardId, districts = []) {
          // 1) pull URLs off the clicked card
          const $card      = $(`.card.${cardId}`);
          const detailsUrl = $card.data('details-url');
          const excelUrl   = $card.data('download-url');
          const district   = $card.data('district') || '';
      
          // 2) stash them on the modal container
          const $modalCont = $('#modalOverlay .modal-container')
            .data('details-url', detailsUrl).attr('data-details-url', detailsUrl)
            .data('excel-url',   excelUrl).  attr('data-excel-url',   excelUrl)
            .data('district',    district). attr('data-district',    district);
      
          // 3) rest of your open() as before…
          const template = cardTemplates[cardId] || { /* … */ };
      
          // destroy old charts, reset class, show spinner…
          Object.values(window.highValueCharts).forEach(c=>c.destroy());
          window.highValueCharts = {};
      
          const modalContainer = document.querySelector('#modalOverlay .modal-container');
          modalContainer.className = 'modal-container ' + cardId;
      
          $('#modalTitle').text(template.title);
          $('#modalContent').html(`
            <div class="loading-spinner">
              <div class="spinner"></div>
              <p>Loading ${template.title}...</p>
            </div>
          `);
          $('#modalOverlay').fadeIn(200);
          $('body').css('overflow', 'hidden');
      
          // inject real content after spinner
          setTimeout(() => {
            $('#modalContent').html(template.content);
            if (template.postRender) template.postRender(districts);
            this.adjustModalScroll();
          }, 300);
        },
      
        close() {
          $('#modalOverlay').fadeOut(200);
          $('body').css('overflow', 'auto');
        },
      
        adjustModalScroll() {
          const $c = $('#modalContent');
          $c.scrollTop(0);
          const el = $c[0];
          el.style.overflowY = el.scrollHeight > el.clientHeight ? 'auto' : 'hidden';
        }
    };
    
    // Helper function to get selected districts
    function getSelectedDistricts() {
        return $('.district-checkbox:checked:not(#selectAll)').map(function() {
            return $(this).val();
        }).get();
    }
    
    // Initialize on load
    $(window).on('load', function() {
        $('#modalOverlay').hide().removeClass('show');
        ModalController.init();
    });
});