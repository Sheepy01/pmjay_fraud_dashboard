document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.upload-card');
  const modal = document.getElementById('dataModal');
  const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

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
        handleFileUpload(this.files[0], card.dataset.model, progressContainer, progressBar, fileName, viewBtn);
      }
    });
  });

  // View button handlers
  document.querySelectorAll('.view-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const modelType = this.closest('.upload-card').querySelector('.file-input').dataset.model;
      showDataModal(modelType);
    });
  });

  // Modal close handlers
  modal.querySelector('.close-btn').addEventListener('click', () => {
    modal.style.display = 'none';
  });
});

function handleFileUpload(file, modelType, progressContainer, progressBar, fileNameElem, viewBtn) {
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
    progressContainer.style.display = 'block';
    fileNameElem.textContent = file.name;
  };

  xhr.onload = function() {
    progressContainer.style.display = 'none';
    progressBar.style.width = '0';
    
    if (xhr.status === 200) {
      viewBtn.disabled = false;
      // You could add a success notification here
    } else {
      console.error('Upload failed');
      // Handle error
    }
  };

  xhr.setRequestHeader('X-CSRFToken', csrftoken);
  xhr.send(formData);
}

function showDataModal(modelType) {
  const modal = document.getElementById('dataModal');
  const modalTitle = modal.querySelector('.modal-title');
  const modalContent = document.getElementById('modalTableContent');
  
  fetch(`/get-management-data/?model_type=${modelType}`)
    .then(response => response.text())
    .then(html => {
      modalTitle.textContent = modelType === 'suspicious' 
        ? 'Suspicious Hospital List' 
        : 'Hospital Beds Data';
      modalContent.innerHTML = html;
      modal.style.display = 'block';
    });
}