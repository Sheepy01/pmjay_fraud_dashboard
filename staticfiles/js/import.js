document.addEventListener('DOMContentLoaded', () => {
    const importBtn = document.getElementById('import-btn');
    const importModal = document.getElementById('importModal');
    const progressModal = document.getElementById('progressModal');
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    let files = [];

    // Open modal
    importBtn.addEventListener('click', () => {
        importModal.classList.add('show');
    });

    // Close modal
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            importModal.classList.remove('show');
            progressModal.classList.remove('show');
        });
    });

    // Drag & drop handling
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    // File input handling
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => handleFiles(fileInput.files));

    function handleFiles(newFiles) {
        files = [...files, ...Array.from(newFiles).filter(file => 
            file.name.match(/\.xlsx?$/i) && 
            !files.some(f => f.name === file.name)
        )];
        
        renderFileList();
        updateProcessButton();
    }

    function renderFileList() {
        const fileList = document.getElementById('fileList');
        fileList.innerHTML = files.map((file, index) => `
            <div class="file-item">
                <i class="fas fa-file-excel"></i>
                <div class="file-info">
                    <div>${file.name}</div>
                    <div class="file-size">${(file.size/1024/1024).toFixed(2)} MB</div>
                </div>
                <i class="fas fa-times remove-file" data-index="${index}"></i>
            </div>
        `).join('');

        document.querySelectorAll('.remove-file').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = e.target.dataset.index;
                files.splice(index, 1);
                renderFileList();
                updateProcessButton();
            });
        });
    }

    function updateProcessButton() {
        document.getElementById('processBtn').disabled = files.length === 0;
    }

    // Process files
    document.getElementById('processBtn').addEventListener('click', async () => {
        if (files.length === 0) return;

        importModal.classList.remove('show');
        progressModal.classList.add('show');

        const formData = new FormData();
        files.forEach(file => formData.append('files', file));

        try {
            const response = await fetch('/import-data/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
                body: formData
            });

            if (!response.ok) throw new Error('Server error');
            
            const result = await response.json();
            if (result.success) {
                showSuccessMessage('Files processed successfully!');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showErrorMessage(result.message || 'Processing failed');
            }
        } catch (error) {
            showErrorMessage(error.message);
        } finally {
            progressModal.classList.remove('show');
            files = [];
            renderFileList();
        }
    });

    function showSuccessMessage(text) {
        // Implement toast notification
    }

    function showErrorMessage(text) {
        // Implement toast notification
    }
});