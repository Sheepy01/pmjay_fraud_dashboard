document.addEventListener('DOMContentLoaded', () => {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const cards = document.querySelectorAll('.upload-card');
    const modal = document.getElementById('dataModal');

    cards.forEach(card => {
        const fileInput = card.querySelector('.file-input');
        const uploadBtn = card.querySelector('.upload-btn');
        const viewBtn = card.querySelector('.view-btn');
        const fileName = card.querySelector('.file-name');
        const progressContainer = card.querySelector('.progress-container');
        const progressBar = card.querySelector('.progress-bar');

        uploadBtn.addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', function(e) {
            if (this.files.length > 0) {
                handleFileUpload(
                    this.files[0], 
                    this.dataset.model, 
                    progressContainer, 
                    progressBar, 
                    fileName, 
                    viewBtn,
                    csrftoken
                );
            }
        });
    });

    // Delegated event listener for view buttons
    document.querySelector('.upload-section').addEventListener('click', (e) => {
        if (e.target.closest('.view-btn')) {
            const btn = e.target.closest('.view-btn');
            if (!btn.disabled) {
                const modelType = btn.closest('.upload-card').querySelector('.file-input').dataset.model;
                showDataModal(modelType);
            }
        }
    });

    // Modal close handlers
    modal.querySelector('.close-btn').addEventListener('click', () => {
        modal.classList.remove('show');
    });

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });
    });

    function generatePreviewThumbnail(file, card) {
        const reader = new FileReader();
        reader.onload = e => {
            // parse workbook
            const data = new Uint8Array(e.target.result);
            const wb = XLSX.read(data, { type: 'array' });
            // grab first sheet, convert to HTML table
            const firstSheetName = wb.SheetNames[0];
            const htmlTable = XLSX.utils.sheet_to_html(wb.Sheets[firstSheetName], { header: '', 
            blankrows: false, // drop blank rows
            editable: false
            });
            
            // inject into hidden container
            const previewContainer = card.querySelector('.preview-container');
            previewContainer.innerHTML = htmlTable;
            previewContainer.style.display = 'block';
            
            // use html2canvas to snapshot it
            html2canvas(previewContainer, { scale: 0.5 }).then(canvas => {
            // turn into a data‑URL
            const imgData = canvas.toDataURL();
            // put it as background on the card
            card.style.backgroundImage = `url(${imgData})`;
            card.style.backgroundSize = 'cover';
            card.style.backgroundPosition = 'center';
            // hide the table container again
            previewContainer.style.display = 'none';
            })
            .catch(err => console.error('Preview capture failed', err));
        };
        reader.readAsArrayBuffer(file);
    }

    function handleFileUpload(file, modelType, progressContainer, progressBar, fileNameElem, viewBtn, csrftoken) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('model_type', modelType);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload-management-data/', true);

        // Progress handler
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                progressBar.style.width = `${percent}%`;
            }
        });

        xhr.onloadstart = () => {
            progressContainer.classList.add('active'); // Use class instead of direct style
            fileNameElem.textContent = file.name;
            viewBtn.disabled = true; // Disable view button during upload
        };

        xhr.onload = function() {
            progressContainer.classList.remove('active');
            progressBar.style.width = '0';
            
            if (xhr.status === 200) {
                viewBtn.disabled = false;
                // Update UI with new data
                const event = new CustomEvent('data-updated', { detail: { modelType } });
                document.dispatchEvent(event);
                // generatePreviewThumbnail(file, card);
            } else {
                try {
                const response = JSON.parse(xhr.responseText);
                console.error('Upload failed:', response.message);
                fileNameElem.textContent = `Upload failed: ${response.message}`;
                } catch {
                    console.error('Upload failed with status:', xhr.status);
                    fileNameElem.textContent = 'Upload failed: Unknown error';
                }
            }
        };

        document.addEventListener('data-updated', () => {
            // Fetch the latest filenames/timestamps
            fetch('/api/latest-uploads/')
                .then(res => res.json())
                .then(data => {
                // For each model type, update its .file-name span
                Object.entries(data).forEach(([modelType, info]) => {
                    // Find the matching card
                    const card = document.querySelector(`.upload-card .file-input[data-model="${modelType}"]`)
                                    .closest('.upload-card');
                    const fileNameElem = card.querySelector('.file-name');
                    const viewBtn      = card.querySelector('.view-btn');
                    fileNameElem.textContent = `${info.filename} (uploaded at ${info.uploaded_at})`;
                    viewBtn.disabled = false;
                });
                })
                .catch(err => console.error('Failed to refresh filenames:', err));
            });

        xhr.onerror = function() {
            progressContainer.classList.remove('active');
            console.error('Upload error');
            fileNameElem.textContent = 'Upload error - try again';
        };

        xhr.setRequestHeader('X-CSRFToken', csrftoken);
        xhr.send(formData);
    }

    function showDataModal(modelType) {
        const modal = document.getElementById('dataModal');
        const modalTitle = modal.querySelector('.modal-title');
        const modalContent = document.getElementById('modalTableContent');
        
        modalContent.innerHTML = '<div class="loading">Loading...</div>';
        modal.classList.add('show');

        fetch(`/get-management-data/?model_type=${modelType}`)
            .then(response => response.text())
            .then(html => {
                modalTitle.textContent = modelType === 'suspicious' 
                    ? 'Suspicious Hospital List' 
                    : 'Hospital Beds Data';
                modalContent.innerHTML = html;
            })
            .catch(error => {
                console.error('Error loading data:', error);
                modalContent.innerHTML = 'Error loading data';
            });
    }