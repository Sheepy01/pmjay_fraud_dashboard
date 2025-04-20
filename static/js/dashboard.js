$(document).ready(function() {
    window.highValueCharts = {};
    let agePieChart, genderPieChart;

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
                    <button class="table-download-btn">
                        <i class="fas fa-download"></i> Export CSV
                    </button>
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
                        Showing <span id="rowCount">0</span> records
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
                console.log("Starting data load for districts:", districts); // Debug log
                
                const tableUrl = '/get-flagged-claims-details/' + 
                    (districts.length ? `?district=${districts.join(',')}` : '');
                
                console.log("Fetching table data from:", tableUrl); // Debug log
                
                fetch(tableUrl, {
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                    .then(response => {
                        console.log("Table response status:", response.status); // Debug log
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log("Received table data:", data); // Debug log
                        const tableBody = document.getElementById('flaggedClaimsData');
                        tableBody.innerHTML = data.map(item => `
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
                        
                        document.getElementById('rowCount').textContent = data.length;
            
                        // Now load chart data
                        const chartUrl = '/get-flagged-claims-by-district/' + 
                            (districts.length ? `?district=${districts.join(',')}` : '');
                        
                        console.log("Fetching chart data from:", chartUrl); // Debug log
                        
                        return fetch(chartUrl);

                    })
                    .then(response => {
                        console.log("Chart response status:", response.status); // Debug log
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(chartData => {
                        console.log("Received chart data:", chartData); // Debug log
                        renderFlaggedClaimsChart(chartData);
                        initDemographicCharts(districts);
                    })
                    .catch(error => {
                        console.error('Error loading data:', error);
                        // Show error in console and on page
                        const errorElement = document.createElement('div');
                        errorElement.className = 'error-message';
                        errorElement.textContent = `Error: ${error.message}`;
                        document.getElementById('flaggedClaimsData').innerHTML = `
                            <tr>
                                <td colspan="7" class="error-message">
                                    Failed to load data. ${error.message}
                                </td>
                            </tr>
                        `;
                    });
            }
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
                    <button class="table-download-btn">
                        <i class="fas fa-download"></i> Export CSV
                    </button>
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
                        Showing <span id="highValueRowCount">0</span> records
                    </div>
                </div>

                <!-- Charts Container -->
                <div class="charts-container" id="highValueCharts"></div>
            `,
            postRender: function(districts) {
                const initialType = 'all';
                this.handleCaseTypeChange(initialType, districts);
                this.initCaseTypeButtons(districts);
            },
            handleCaseTypeChange: function(caseType, districts) {
                this.loadTableData(caseType, districts);
                this.loadCharts(caseType, districts);
            },
            loadTableData: function(caseType, districts) {
                const url = `/get-high-value-claims-details/?case_type=${caseType}&district=${districts.join(',')}`;
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {
                        const tbody = document.getElementById('highValueClaimsData');
                        tbody.innerHTML = data.map(item => `
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
                        document.getElementById('highValueRowCount').textContent = data.length;
                    })
                    .catch(error => console.error('Table load error:', error));
            },
            loadCharts: function(caseType, districts) {
                const container = document.getElementById('highValueCharts');
                container.innerHTML = caseType === 'all' ? `
                    <div class="chart-group">
                        <!-- Bar Charts -->
                        <div class="chart-container">
                            <h4>Combined District Distribution</h4>
                            <canvas id="highValueAllChart"></canvas>
                        </div>
                        <div class="chart-container">
                            <h4>Medical Cases Distribution</h4>
                            <canvas id="highValueMedicalChart"></canvas>
                        </div>
                        <div class="chart-container">
                            <h4>Surgical Cases Distribution</h4>
                            <canvas id="highValueSurgicalChart"></canvas>
                        </div>
                        
                        <!-- Pie Charts -->
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
                ` : `
                    <div class="chart-group">
                        <div class="chart-container">
                            <h4>District Distribution (${caseType})</h4>
                            <canvas id="highValue${caseType}Chart"></canvas>
                        </div>
                        
                        <div class="dual-pie-container">
                            <div class="pie-card">
                                <h4>${this.capitalize(caseType)} Age Distribution</h4>
                                <canvas id="highValue${caseType}AgeChart"></canvas>
                                <div class="chart-callouts" id="highValue${caseType}AgeCallouts"></div>
                            </div>
                            <div class="pie-card">
                                <h4>${this.capitalize(caseType)} Gender Distribution</h4>
                                <canvas id="highValue${caseType}GenderChart"></canvas>
                                <div class="chart-callouts" id="highValue${caseType}GenderCallouts"></div>
                            </div>
                        </div>
                    </div>
                `;
        
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
                    this.loadChartData(caseType, districts, `highValue${caseType}Chart`);
                    this.loadDemographics(caseType, districts, `highValue${caseType}AgeChart`, 
                        `highValue${caseType}GenderChart`, `highValue${caseType}AgeCallouts`, 
                        `highValue${caseType}GenderCallouts`);
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
                        ${data.data[i]} (${Math.round((data.data[i]/total))*100}%)
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
            }
        },
        'hospital-beds': {
            title: "Hospital Bed Cases",
            content: `<div class="card-details">
                        <h4>Hospital Bed Violations</h4>
                        <div class="violation-list">
                            <div class="violation-item">
                                <span>Exceeded Capacity:</span>
                                <span>87 cases</span>
                            </div>
                        </div>
                      </div>`
        },
        'family-id': {
            title: "Family ID Cases",
            content: `<div class="card-details">
                        <h4>Family ID Anomalies</h4>
                        <div class="anomaly-grid">
                            <div class="anomaly-item">
                                <span>Duplicate Claims:</span>
                                <span>42 cases</span>
                            </div>
                        </div>
                      </div>`
        },
        'geo-anomalies': {
            title: "Geographic Anomalies",
            content: `<div class="card-details">
                        <h4>Suspicious Geographic Patterns</h4>
                        <div class="map-container">
                            <p>Heatmap visualization</p>
                        </div>
                      </div>`
        },
        'ophthalmology': {
            title: "Ophthalmology Overview",
            content: `<div class="card-details">
                        <h4>Cataract Surgery Metrics</h4>
                        <div class="sub-card-nav">
                            <button class="sub-card-link" data-card="age">Age Analysis</button>
                            <button class="sub-card-link" data-card="ot-cases">OT Cases</button>
                        </div>
                      </div>`
        },
        'age': {
            title: "Age Analysis",
            content: `<div class="card-details">
                        <h4>Patient Age Distribution</h4>
                        <div class="age-metrics">
                            <div class="metric">
                                <span>Under 40:</span>
                                <span>64 cases</span>
                            </div>
                        </div>
                      </div>`
        },
        'ot-cases': {
            title: "OT Cases",
            content: `<div class="card-details">
                        <h4>Operation Theater Cases</h4>
                        <div class="ot-metrics">
                            <div class="metric">
                                <span>This Month:</span>
                                <span>183 cases</span>
                            </div>
                        </div>
                      </div>`
        }
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

    const ModalController = {
        init: function() {
            $('#modalOverlay').hide().removeClass('show');
            this.setupEventListeners();
        },
        
        setupEventListeners: function() {
            // Remove any existing handlers to prevent duplicates
            $(document)
                .off('click', '.card')
                .off('click', '.modal-close')
                .off('click', '.modal-overlay')
                .off('click', '.modal-pdf-download')
                .off('click', '.table-download-btn');
            
            // Card click handler
            $(document).on('click', '.card', function(e) {
                if ($(e.target).is('.download-btn, .download-btn *')) return;
                const cardId = $(this).attr('class').split(' ')[1];
                const districts = getSelectedDistricts(); // Get current district filters
                ModalController.open(cardId, districts);
            });
            
            // Close button handler
            $(document).on('click', '.modal-close', function(e) {
                e.stopPropagation();
                ModalController.close();
            });
            
            // Overlay click handler
            $(document).on('click', '.modal-overlay', function(e) {
                if (e.target === this) ModalController.close();
            });
            
            // ESC key handler
            $(document).on('keyup', function(e) {
                if (e.key === 'Escape' && $('#modalOverlay').is(':visible')) {
                    ModalController.close();
                }
            });
        },
        
        open: function(cardId, districts = []) {
            const template = cardTemplates[cardId] || {
                title: "Details",
                content: `<div class="card-details"><p>Content not available</p></div>`
            };

            Object.values(window.highValueCharts).forEach(chart => chart.destroy());
            window.highValueCharts = {};

            // Set modal container class
            const modalContainer = document.querySelector('.modal-container');
            modalContainer.className = 'modal-container ' + cardId; // Reset and add card class
            
            $('#modalTitle').text(template.title);
            $('#modalContent').html(`
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <p>Loading ${template.title}...</p>
                </div>
            `);
            
            $('#modalOverlay').fadeIn(200);
            $('body').css('overflow', 'hidden');
            
            // Load content after short delay (for spinner visibility)
            setTimeout(() => {
                $('#modalContent').html(template.content);

                const container = document.getElementById('highValueCharts');
                if (container) container.offsetHeight;
                
                // If template has postRender, execute it with districts
                if (template.postRender) {
                    template.postRender(districts);
                }
                
                // Set up download button handlers
                $('.modal-pdf-download').click(function() {
                    generatePDFReport(cardId, districts);
                });
                
                $('.table-download-btn').click(function() {
                    exportTableToCSV(cardId);
                });

                this.adjustModalScroll();
            }, 300);
        },
        
        close: function() {
            $('#modalOverlay').fadeOut(200);
            $('body').css('overflow', 'auto');
        },

        adjustModalScroll: function() {
            // Reset scroll position when opening new modal
            $('#modalContent').scrollTop(0);
            
            // Handle any dynamic content adjustments
            const modalContent = $('#modalContent')[0];
            if (modalContent.scrollHeight > modalContent.clientHeight) {
                modalContent.style.overflowY = 'auto';
            } else {
                modalContent.style.overflowY = 'hidden';
            }
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