class OCRApp {
    constructor() {
        this.initializeElements();
        this.attachEventListeners();
        this.outputFilename = null;
    }

    initializeElements() {
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('fileInput');
        this.browseBtn = document.getElementById('browseBtn');
        this.uploadSection = document.querySelector('.upload-section');
        this.loadingSection = document.getElementById('loadingSection');
        this.resultSection = document.getElementById('resultSection');
        this.errorSection = document.getElementById('errorSection');
        this.textPreview = document.getElementById('textPreview');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.newFileBtn = document.getElementById('newFileBtn');
        this.tryAgainBtn = document.getElementById('tryAgainBtn');
        this.errorMessage = document.getElementById('errorMessage');
    }

    attachEventListeners() {
        // Drag and drop events
        this.dropZone.addEventListener('dragover', this.handleDragOver.bind(this));
        this.dropZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.dropZone.addEventListener('drop', this.handleDrop.bind(this));
        this.dropZone.addEventListener('click', () => this.fileInput.click());

        // File input events
        this.browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.fileInput.click();
        });
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));

        // Button events
        this.downloadBtn.addEventListener('click', this.handleDownload.bind(this));
        this.newFileBtn.addEventListener('click', this.resetApp.bind(this));
        this.tryAgainBtn.addEventListener('click', this.resetApp.bind(this));
    }

    handleDragOver(e) {
        e.preventDefault();
        this.dropZone.classList.add('dragover');
    }

    handleDragLeave(e) {
        e.preventDefault();
        this.dropZone.classList.remove('dragover');
    }

    handleDrop(e) {
        e.preventDefault();
        this.dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const files = e.target.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    processFile(file) {
        // Validate file type
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            this.showError('Please select a PDF file.');
            return;
        }

        // Validate file size (16MB limit)
        const maxSize = 16 * 1024 * 1024; // 16MB
        if (file.size > maxSize) {
            this.showError('File size exceeds 16MB limit. Please select a smaller file.');
            return;
        }

        // Show loading state
        this.showLoading();

        // Create FormData and upload
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showResult(data);
            } else {
                this.showError(data.error || 'An error occurred during processing.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showError('Network error occurred. Please try again.');
        });
    }

    showLoading() {
        this.uploadSection.style.display = 'none';
        this.resultSection.style.display = 'none';
        this.errorSection.style.display = 'none';
        this.loadingSection.style.display = 'block';
    }

    showResult(data) {
        this.loadingSection.style.display = 'none';
        this.errorSection.style.display = 'none';
        this.uploadSection.style.display = 'none';
        
        this.textPreview.textContent = data.text_preview;
        this.outputFilename = data.output_file;
        this.resultSection.style.display = 'block';
    }

    showError(message) {
        this.loadingSection.style.display = 'none';
        this.resultSection.style.display = 'none';
        this.uploadSection.style.display = 'none';
        
        this.errorMessage.textContent = message;
        this.errorSection.style.display = 'block';
    }

    handleDownload() {
        if (this.outputFilename) {
            window.location.href = `/download/${this.outputFilename}`;
        }
    }

    resetApp() {
        this.loadingSection.style.display = 'none';
        this.resultSection.style.display = 'none';
        this.errorSection.style.display = 'none';
        this.uploadSection.style.display = 'block';
        
        this.fileInput.value = '';
        this.outputFilename = null;
        this.dropZone.classList.remove('dragover');
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new OCRApp();
});