// static/js/high_alert.js
$(function(){
    let currentStartDate = null, currentEndDate = null;
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

    function daysInMonth(year, month) {
        return new Date(year, month, 0).getDate();
    }

    function getDateRange() {
        const pad = (s) => String(s).padStart(2, '0');
        const y1 = $('#from-year').val(),  m1 = pad($('#from-month').val()), d1 = pad($('#from-day').val());
        const y2 = $('#to-year').val(),    m2 = pad($('#to-month').val()),   d2 = pad($('#to-day').val());
        return {
            startDate: `${y1}-${m1}-${d1}`,
            endDate:   `${y2}-${m2}-${d2}`
        };
    }

    function populateDateDropdowns() {
        const today = new Date();
        const curYear = today.getFullYear();
        const years = [];
        for (let y = 2000; y <= curYear; y++) years.push(y);

        // helper to fill one set
        function fillOne(prefix, defaultDate) {
            const [m, d, y] = [defaultDate.getMonth() + 1, defaultDate.getDate(), defaultDate.getFullYear()];
            const monthSel = $(`#${prefix}-month`);
            const daySel   = $(`#${prefix}-day`);
            const yearSel  = $(`#${prefix}-year`);

            // months
            const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
            monthSel.empty();
            monthNames.forEach((name, idx) => {
                monthSel.append(`<option value="${idx+1}">${name}</option>`);
            });
            

            // years
            yearSel.empty();
            years.forEach(yr => yearSel.append(`<option value="${yr}">${yr}</option>`));

            // set defaults
            monthSel.val(m);
            yearSel.val(y);

            // populate days based on month/year
            function refreshDays() {
            const mm = parseInt(monthSel.val(), 10);
            const yy = parseInt(yearSel.val(), 10);
            const dim = daysInMonth(yy, mm);
            daySel.empty();
            for (let dd = 1; dd <= dim; dd++) daySel.append(`<option value="${dd}">${dd}</option>`);
            daySel.val(d);
            }
            refreshDays();

            // when month or year changes, refresh days (and clamp day)
            monthSel.add(yearSel).on('change', refreshDays);
        }

        // fill both from/to with today
        populateDateDropdowns = null; // prevent re-definition
        fillOne('from', today);
        fillOne('to', today);
    }

    // ======================
    // Sidebar Toggle (jQuery)
    // ======================
    $('#toggle-btn').on('click', function() {
        $('#sidebar').toggleClass('collapsed');
        $('#main-content').toggleClass('expanded');
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

    $('#apply-date-filter').on('click', function() {
        const {startDate, endDate} = getDateRange();
        if (new Date(startDate) > new Date(endDate)) {
            alert('Start date cannot be after end date.');
            return;
        }

        currentStartDate = startDate;
        currentEndDate = endDate;

        triggerFilterUpdate();
    });

    // ======================
    // Table Handling
    // ======================
    const table = $('#highAlertTable');
    const tbody = table.find('tbody');
    const paginationControls = $('.pagination-controls');

    function loadTableData(page=1) {
        const params = {
            page: page,
            page_sise: 50,
            district: selectedDistricts.join(',')
        };
        if (currentStartDate && currentEndDate) {
            params.start_date = currentStartDate;
            params.end_date = currentEndDate;
        }
        $.ajax({
            url: '/high-alert/',
            data: params,
            success: function(response) {
                renderTable(response.data);
                renderPagination(response.pagination);
            }
        });
    }

    // Excel Export Handler
    $('#exportExcel').on('click', function() {
        const districts = $('#districtDropdown').val() || [];

        // Build query params
        const params = new URLSearchParams();
        if (districts.length) {
            params.set('district', districts.join(','));
        }
        if (currentStartDate) {
            params.set('start_date', currentStartDate);
        }
        if (currentEndDate) {
            params.set('end_date', currentEndDate);
        }

        // Create temporary link
        const link = document.createElement('a');
        link.href = `${window.HIGH_ALERT_URLS.excel}?${params.toString()}`;
        link.download = 'high_alerts_export.xlsx';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // Add CSRF token handling
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    function generateHighAlertPDF() {
        const {startDate, endDate} = getDateRange();
        const loader = document.getElementById('pdfLoader');
        const progressBar = document.getElementById('pdfProgressBar');
        const progressTxt = document.getElementById('pdfProgressText');
        const downloadBtn = document.getElementById('exportPdf');
        
        // Show loader & disable button
        loader.classList.add('show');
        downloadBtn.disabled = true;
    
        // Simulate progress to 90%
        let prog = 0;
        progressBar.style.width = '0%';
        progressTxt.textContent = '0%';
        const interval = setInterval(() => {
            if (prog < 90) {
                prog++;
                progressBar.style.width = `${prog}%`;
                progressTxt.textContent = `${prog}%`;
            } else {
                clearInterval(interval);
            }
        }, 50);
    
        // Build payload
        const districts = $('#districtDropdown').val() || [];
        const fd = new FormData();
        if(districts)    fd.append('district', districts);
        if(startDate)    fd.append('start_date', startDate);
        if(endDate)      fd.append('end_date', endDate);
        
        // Add CSRF token
        fd.append('csrfmiddlewaretoken', getCSRFToken());
        
        // Add charts and filters
        ['district', 'age', 'gender'].forEach(type => {
            const chartMap = {
                district: 'districtChart',
                age: 'ageChart',
                gender: 'genderChart'
            };
            const canvas = document.getElementById(chartMap[type]);
            fd.append(`${type}_chart`, canvas.toDataURL());
        });
        
        
        fd.append('district', districts.join(','));
        
        // --- ArcGIS Map Screenshot ---
        if (window.highAlertMapView && window.highAlertMapView.ready) {
            window.highAlertMapView.takeScreenshot().then(function(screenshot) {
                fd.append('map_image', screenshot.dataUrl); // <-- Add map image as base64 PNG

                // Now send the request
                fetch(window.HIGH_ALERT_URLS.pdf, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: fd
                })
                .then(response => response.blob())
                .then(blob => {
                    clearInterval(interval);
                    progressBar.style.width = '100%';
                    progressTxt.textContent = '100%';
                    setTimeout(() => {
                        loader.classList.remove('show');
                        downloadBtn.disabled = false;
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = `high_alerts_report_${Date.now()}.pdf`;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        URL.revokeObjectURL(url);
                    }, 200);
                })
                .catch(err => {
                    console.error('PDF generation failed:', err);
                    clearInterval(interval);
                    loader.classList.remove('show');
                    downloadBtn.disabled = false;
                });
            });
        } else {
            // fallback: send without map image
            fetch(window.HIGH_ALERT_URLS.pdf, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                body: fd
            })
            .then(response => response.blob())
            .then(blob => {
                clearInterval(interval);
                progressBar.style.width = '100%';
                progressTxt.textContent = '100%';
                setTimeout(() => {
                    loader.classList.remove('show');
                    downloadBtn.disabled = false;
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `high_alerts_report_${Date.now()}.pdf`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }, 200);
            })
            .catch(err => {
                console.error('PDF generation failed:', err);
                clearInterval(interval);
                loader.classList.remove('show');
                downloadBtn.disabled = false;
            });
        }
    }

    // Add PDF button click handler
    $('#exportPdf').on('click', generateHighAlertPDF);

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
        Chart.register(window.ChartDataLabels);
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
            },
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
        const {startDate, endDate} = getDateRange()
        loadTableData();
        loadChartData();
        loadDemographics();
        const url = `/high-alerts-geo/?district=${selectedDistricts.join(',')}&start_date=${startDate}&end_date=${endDate}`;
        renderGeoMap({
            url: url,
            containerId: "highAlertMap",
            countKey: "count", // or whatever your API returns
            fidKey: "fid"      // or "FID" if uppercase
        });
    }

    function loadChartData() {
        const params = {
            district: selectedDistricts.join(','),
        };
        if (currentStartDate && currentEndDate) {
            params.start_date = currentStartDate;
            params.end_date = currentEndDate;
        }

        $.ajax({
            url: window.HIGH_ALERT_URLS.districts,
            data: params,
            success: data => {
                districtChart.data.labels = data.labels;
                districtChart.data.datasets[0].data = data.counts;
                districtChart.update();

                const countLookup = {};
                data.labels.forEach((district, i) => {
                    countLookup[district] = data.counts[i];
                });
                // initHighAlertMap(countLookup);
            }
        });
    }

    function loadDemographics() {
        const params = {
            district: selectedDistricts.join(','),
        };
        if (currentStartDate && currentEndDate) {
            params.start_date = currentStartDate;
            params.end_date = currentEndDate;
        }
        ['age', 'gender'].forEach(type => {
            $.ajax({
                url: window.HIGH_ALERT_URLS.demographics.replace('type', type),
                data: params,
                success: data => {
                    const chart = type === 'age' ? ageChart : genderChart;
                    chart.data.labels = data.labels;
                    chart.data.datasets[0].data = data.data;
                    chart.update();
                }
            });
        });
    }

    function initHighAlertMap(countLookup, containerId="highAlertMap") {
        // console.log(countLookup)
        if (window.highAlertMapView) {
            window.highAlertMapView.destroy();
            window.highAlertMapView = null;
            // Also clear the container's innerHTML to remove any leftover DOM
            document.getElementById(containerId).innerHTML = "";
        }
        const colorPalettes = {
            highAlertMap: ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"], // or use mapViewNode palette
            mapViewNode:  ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5", "#08306b"],
        };
        const palette = colorPalettes[containerId] || colorPalettes.mapViewNode;
        require([
            "esri/Map",
            "esri/views/MapView",
            "esri/layers/FeatureLayer",
            "esri/layers/GraphicsLayer",
            "esri/Graphic",
            "esri/widgets/Legend"
        ], (EsriMap, MapView, FeatureLayer, GraphicsLayer, Graphic, Legend) => {
            const map = new EsriMap({ basemap: null });
            const svcLayer = new FeatureLayer({
                url: "https://services6.arcgis.com/D79Nl8HOYMCU0cVt/arcgis/rest/services/bihar_districts/FeatureServer/0",
                outFields: ["FID","DISTRICT"]
            });
            map.add(svcLayer);

            const view = new MapView({
                container: containerId,
                map,
                center: [85.8, 25.9],
                zoom: 7,
                constraints: { rotationEnabled: false, minZoom: 7, maxZoom: 7 },
                ui: { components: [] }
            });

            const legend = new Legend({ view: view });
            view.ui.add(legend, "top-right");

            window.highAlertMapView = view;

            view.navigation.mouseWheelZoomEnabled  = false;
            view.navigation.browserTouchPanEnabled = false;
            view.on("drag",       e => e.stopPropagation(), true);
            view.on("mouse-wheel", e => e.stopPropagation(), true);
            view.on("key-down",   e => { if (e.key.startsWith("Arrow")) e.stopPropagation(); }, true);

            view.whenLayerView(svcLayer)
            .then(() => svcLayer.queryFeatures({
                where: "1=1",
                outFields: ["FID","DISTRICT"],
                returnGeometry: true
            }))
            .then(featureSet => {
                featureSet.features.forEach(f => {
                    f.attributes.count = countLookup[f.attributes.FID] || 0;
                    console.log("Sample feature attributes:", featureSet.features[0].attributes);
                });
                const counts   = Object.values(countLookup);
                const maxCount = counts.length ? Math.max(...counts) : 1;
                const colorStops = [
                    { value: 0,               color: palette[0] },
                    { value: maxCount * 0.25, color: palette[1] },
                    { value: maxCount * 0.5,  color: palette[2] },
                    { value: maxCount * 0.75, color: palette[3] },
                    { value: maxCount,        color: palette[4] }
                ];
                const memoryPolygons = new FeatureLayer({
                    source: featureSet.features,
                    fields: [
                        ...svcLayer.fields,
                        { name: "count", alias: "High Alert Count", type: "integer" }
                    ],
                    objectIdField: svcLayer.objectIdField,
                    geometryType: svcLayer.geometryType,
                    spatialReference: svcLayer.spatialReference,
                    renderer: {
                        type: "simple",
                        symbol: { type: "simple-fill", outline: { color: "#aaa", width: 0.5 } },
                        visualVariables: [{
                            type: "color",
                            field: "count",
                            stops: colorStops
                        }]
                    },
                    labelingInfo: [{
                        labelExpressionInfo: { expression: "$feature.DISTRICT" },
                        symbol: {
                            type: "text",
                            color: "#000",
                            haloColor: "#fff",
                            haloSize: "1px",
                            font: { size: "12px", weight: "bold" }
                        },
                        labelPlacement: "always-horizontal"
                    }]
                });
                map.remove(svcLayer);
                map.add(memoryPolygons);

                // Circles
                const circleLayer = new GraphicsLayer();
                map.add(circleLayer);
                const minSize = 12, maxSize = 60;
                featureSet.features.forEach(feat => {
                    const cnt = feat.attributes.count;
                    if (!cnt) return;
                    const center = feat.geometry.extent.center;
                    const size   = minSize + (cnt / maxCount) * (maxSize - minSize);
                    circleLayer.add(new Graphic({
                        geometry: center,
                        symbol: {
                            type: "simple-marker",
                            style: "circle",
                            size: size,
                            color: "#e34234",
                            outline: { color: "#fff", width: 0.5 }
                        }
                    }));
                    circleLayer.add(new Graphic({
                        geometry: center,
                        symbol: {
                            type: "text",
                            text: String(cnt),
                            color: "#fff",
                            haloColor: "#000",
                            haloSize: "0.5px",
                            font: { size: "14px", weight: "bold" },
                            horizontalAlignment: "center",
                            verticalAlignment: "middle",
                            xoffset: 0,
                            yoffset: 4
                        }
                    }));
                });
            })
            .catch(err => console.error("Map layering error:", err));
        });
    }

    function renderGeoMap({ url, containerId, countKey="count", fidKey="fid" }) {
        fetch(url)
            .then(r => r.json())
            .then(geoCounts => {
                const lookup = {};
                geoCounts.forEach(d => { lookup[d.fid] = d[countKey]; });
                initHighAlertMap(lookup, containerId);
            })
            .catch(err => console.error("Geo-counts fetch error:", err));
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
        populateDateDropdowns();
        initCharts();
        loadAllVisualizations();
    }

    initializeDashboard();
});