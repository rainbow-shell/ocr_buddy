class OCRApp {
    constructor() {
        this.initializeElements();
        this.attachEventListeners();
        this.outputFilename = null;
        this.initializeApiKey();
    }

    initializeElements() {
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('fileInput');
        this.browseBtn = document.getElementById('browseBtn');
        this.uploadSection = document.querySelector('.upload-section');
        this.loadingSection = document.getElementById('loadingSection');
        this.resultSection = document.getElementById('resultSection');
        this.errorSection = document.getElementById('errorSection');
        this.textEditor = document.getElementById('textEditor');
        this.cleanupBtn = document.getElementById('cleanupBtn');
        this.saveBtn = document.getElementById('saveBtn');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.newFileBtn = document.getElementById('newFileBtn');
        this.tryAgainBtn = document.getElementById('tryAgainBtn');
        this.errorMessage = document.getElementById('errorMessage');
        
        // API Key elements
        this.apiKeyToggle = document.getElementById('apiKeyToggle');
        this.apiKeyInput = document.getElementById('apiKeyInput');
        this.apiKeyField = document.getElementById('apiKeyField');
        this.saveApiKeyBtn = document.getElementById('saveApiKey');
        this.clearApiKeyBtn = document.getElementById('clearApiKey');
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
        this.cleanupBtn.addEventListener('click', this.handleCleanup.bind(this));
        this.saveBtn.addEventListener('click', this.handleSave.bind(this));
        this.downloadBtn.addEventListener('click', this.handleDownload.bind(this));
        this.newFileBtn.addEventListener('click', this.resetApp.bind(this));
        this.tryAgainBtn.addEventListener('click', this.resetApp.bind(this));
        
        // API Key events
        this.apiKeyToggle.addEventListener('click', this.toggleApiKeyInput.bind(this));
        this.saveApiKeyBtn.addEventListener('click', this.saveApiKey.bind(this));
        this.clearApiKeyBtn.addEventListener('click', this.clearApiKey.bind(this));
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
        
        this.textEditor.value = data.extracted_text;
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

    handleSave() {
        if (!this.outputFilename) {
            alert('No file to save.');
            return;
        }

        const textContent = this.textEditor.value;
        
        // Disable save button during request
        this.saveBtn.disabled = true;
        this.saveBtn.textContent = 'Saving...';

        fetch(`/save/${this.outputFilename}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text: textContent })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success feedback
                const originalText = this.saveBtn.textContent;
                this.saveBtn.textContent = 'Saved!';
                setTimeout(() => {
                    this.saveBtn.textContent = 'Save Changes';
                    this.saveBtn.disabled = false;
                }, 2000);
            } else {
                alert('Error saving file: ' + (data.error || 'Unknown error'));
                this.saveBtn.textContent = 'Save Changes';
                this.saveBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Network error occurred while saving. Please try again.');
            this.saveBtn.textContent = 'Save Changes';
            this.saveBtn.disabled = false;
        });
    }

    handleDownload() {
        if (this.outputFilename) {
            window.location.href = `/download/${this.outputFilename}`;
        }
    }

    handleCleanup() {
        const textContent = this.textEditor.value;
        
        if (!textContent.trim()) {
            alert('No text to clean up.');
            return;
        }

        // Check if API key is available
        const apiKey = this.getApiKey();
        if (!apiKey) {
            alert('OpenAI API key is required for text cleanup. Please configure your API key first.');
            this.showApiKeyInput();
            return;
        }

        // Disable cleanup button during request
        this.cleanupBtn.disabled = true;
        
        // Check text length to show appropriate message
        if (textContent.length > 10000) {
            this.cleanupBtn.textContent = 'Processing large file...';
        } else {
            this.cleanupBtn.textContent = 'Cleaning up...';
        }

        fetch('/cleanup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                text: textContent,
                api_key: apiKey
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Replace text with cleaned version
                this.textEditor.value = data.cleaned_text;
                
                // Show success feedback
                this.cleanupBtn.textContent = 'Cleaned!';
                setTimeout(() => {
                    this.cleanupBtn.textContent = 'Cleanup with AI';
                    this.cleanupBtn.disabled = false;
                }, 2000);
            } else {
                alert('Error cleaning up text: ' + (data.error || 'Unknown error'));
                this.cleanupBtn.textContent = 'Cleanup with AI';
                this.cleanupBtn.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Network error occurred during cleanup. Please try again.');
            this.cleanupBtn.textContent = 'Cleanup with AI';
            this.cleanupBtn.disabled = false;
        });
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

    // API Key Management Methods
    initializeApiKey() {
        // Load saved API key on startup
        const savedKey = this.getApiKey();
        if (savedKey) {
            this.apiKeyField.value = savedKey;
            this.updateToggleButtonText(true);
        }
    }

    toggleApiKeyInput() {
        const isVisible = this.apiKeyInput.style.display !== 'none';
        if (isVisible) {
            this.apiKeyInput.style.display = 'none';
        } else {
            this.showApiKeyInput();
        }
    }

    showApiKeyInput() {
        this.apiKeyInput.style.display = 'block';
        this.apiKeyField.focus();
    }

    saveApiKey() {
        const apiKey = this.apiKeyField.value.trim();
        
        if (!apiKey) {
            alert('Please enter an API key.');
            return;
        }

        if (!apiKey.startsWith('sk-')) {
            alert('OpenAI API keys should start with "sk-".');
            return;
        }

        // Save to localStorage
        localStorage.setItem('openai_api_key', apiKey);
        
        // Update UI
        this.updateToggleButtonText(true);
        this.apiKeyInput.style.display = 'none';
        
        // Show success feedback
        const originalText = this.saveApiKeyBtn.textContent;
        this.saveApiKeyBtn.textContent = 'Saved!';
        setTimeout(() => {
            this.saveApiKeyBtn.textContent = originalText;
        }, 2000);
    }

    clearApiKey() {
        // Clear from localStorage
        localStorage.removeItem('openai_api_key');
        
        // Clear the input field
        this.apiKeyField.value = '';
        
        // Update UI
        this.updateToggleButtonText(false);
        this.apiKeyInput.style.display = 'none';
        
        // Show success feedback
        const originalText = this.clearApiKeyBtn.textContent;
        this.clearApiKeyBtn.textContent = 'Cleared!';
        setTimeout(() => {
            this.clearApiKeyBtn.textContent = originalText;
        }, 2000);
    }

    getApiKey() {
        return localStorage.getItem('openai_api_key');
    }

    updateToggleButtonText(hasKey) {
        const button = this.apiKeyToggle;
        if (hasKey) {
            button.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <circle cx="12" cy="16" r="1"></circle>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                API Key Configured ✓
            `;
            button.style.background = 'rgba(76, 175, 80, 0.2)';
            button.style.borderColor = 'rgba(76, 175, 80, 0.3)';
        } else {
            button.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                    <circle cx="12" cy="16" r="1"></circle>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                Configure OpenAI API Key
            `;
            button.style.background = 'rgba(255, 255, 255, 0.1)';
            button.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new OCRApp();
});