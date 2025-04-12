$(document).ready(function() {
    // ======================
    // Sidebar Toggle (jQuery)
    // ======================
    $('#toggle-btn').on('click', function() {
        $('#sidebar').toggleClass('collapsed');
        $('#main-content').toggleClass('expanded');
        localStorage.setItem('sidebarCollapsed', $('#sidebar').hasClass('collapsed'));
    });

    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        $('#sidebar').addClass('collapsed');
        $('#main-content').addClass('expanded');
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
        
        // District checkbox selection
        $(document).on('change', '.district-checkbox:not(#selectAll)', function() {
            const district = $(this).val();
            const hiddenOption = $('#districtDropdown option[value="' + district + '"]');
            
            if ($(this).is(':checked')) {
                hiddenOption.prop('selected', true);
                // Uncheck "All Districts" if a specific district is selected
                $('#selectAll').prop('checked', false);
            } else {
                hiddenOption.prop('selected', false);
            }
            
            updateSelectedDisplay();
        });
        
        // "All Districts" checkbox
        $(document).on('change', '#selectAll', function() {
            const isChecked = $(this).is(':checked');
            
            // Toggle all district checkboxes
            $('.district-checkbox:not(#selectAll)').prop('checked', isChecked);
            
            // Update hidden select
            if (isChecked) {
                $('#districtDropdown option').prop('selected', false);
                $('#districtDropdown option[value=""]').prop('selected', true);
            } else {
                $('#districtDropdown option').prop('selected', false);
            }
            
            updateSelectedDisplay();
        });
    }

    loadDistricts();
    initDistrictDropdown();

    // ======================
    // Enhanced Modal Controller
    // ======================
    const cardTemplates = {
        'flagged-claims': {
            title: "Flagged Claims Analysis",
            content: `<div class="card-details">
                        <h4>Flagged Claims Analysis</h4>
                        <div class="data-grid">
                            <div class="data-item">
                                <span class="data-label">Total Flagged:</span>
                                <span class="data-value">1,248</span>
                            </div>
                            <div class="data-item">
                                <span class="data-label">High Risk:</span>
                                <span class="data-value">328</span>
                            </div>
                        </div>
                      </div>`
        },
        'high-value': {
            title: "High Value Claims",
            content: `<div class="card-details">
                        <h4>High Value Trends</h4>
                        <div class="chart-container">
                            <p>Chart showing claim values over time</p>
                        </div>
                      </div>`
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
                .off('click', '.modal-overlay');
            
            // Card click handler
            $(document).on('click', '.card', function(e) {
                if ($(e.target).is('.download-btn, .download-btn *')) return;
                const cardId = $(this).attr('class').split(' ')[1];
                ModalController.open(cardId);
            });
            
            // Close button handler - more specific targeting
            $(document).on('click', '.modal-close', function(e) {
                e.stopPropagation(); // Prevent event from reaching overlay
                ModalController.close();
            });
            
            // Overlay click handler
            $(document).on('click', '.modal-overlay', function(e) {
                if (e.target === this) { // Only if clicking directly on overlay
                    ModalController.close();
                }
            });
            
            // ESC key handler
            $(document).on('keyup', function(e) {
                if (e.key === 'Escape' && $('#modalOverlay').is(':visible')) {
                    ModalController.close();
                }
            });
        },
        
        open: function(cardId) {
            const template = cardTemplates[cardId] || {
                title: "Details",
                content: `<div class="card-details"><p>Content not available</p></div>`
            };
            
            $('#modalTitle').text(template.title);
            $('#modalContent').html(`
                <div class="loading-spinner">
                    <div class="spinner"></div>
                    <p>Loading ${template.title}...</p>
                </div>
            `);
            
            $('#modalOverlay').fadeIn(200);
            $('body').css('overflow', 'hidden');
            
            setTimeout(() => {
                $('#modalContent').html(template.content);
            }, 300);
        },
        
        close: function() {
            $('#modalOverlay').fadeOut(200);
            $('body').css('overflow', 'auto');
        }
    };
    
    // Initialize
    $(window).on('load', function() {
        $('#modalOverlay').hide().removeClass('show');
        ModalController.init();
    });
});