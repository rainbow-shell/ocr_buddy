# PDF OCR Web Application

A simple web-based PDF OCR (Optical Character Recognition) tool that allows users to upload PDF files and extract text content using Tesseract OCR.

## Features

- **Drag & Drop Interface**: Easy file upload with drag-and-drop functionality
- **File Browser**: Traditional file selection option
- **Loading Spinner**: Visual feedback during processing
- **Text Preview**: Preview extracted text before downloading
- **File Download**: Download extracted text as a .txt file
- **Error Handling**: User-friendly error messages
- **Responsive Design**: Works on desktop and mobile devices

## Requirements

- Python 3.7+
- Tesseract OCR (must be installed on system)
- Flask and other Python dependencies (see requirements.txt)

## Installation

1. Install Tesseract OCR on your system:
   - **macOS**: `brew install tesseract`
   - **Ubuntu**: `sudo apt-get install tesseract-ocr`
   - **Windows**: Download from [GitHub releases](https://github.com/tesseract-ocr/tesseract/releases)

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the application:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Upload a PDF file using drag & drop or the file browser
4. Wait for the OCR processing to complete
5. Preview the extracted text and download the .txt file

## File Limitations

- Maximum file size: 16MB
- Supported format: PDF only
- Processing time depends on PDF size and complexity

## How It Works

1. **Upload**: PDF file is uploaded to the server
2. **Conversion**: PDF pages are converted to images using pdf2image
3. **OCR**: Tesseract processes each image to extract text
4. **Output**: Extracted text is saved as a .txt file and made available for download
5. **Cleanup**: Temporary files are removed after processing

## API Endpoints

- `GET /`: Main application interface
- `POST /upload`: Upload and process PDF file
- `GET /download/<filename>`: Download processed text file

## Technology Stack

- **Backend**: Flask (Python)
- **OCR**: Tesseract OCR with pytesseract wrapper
- **PDF Processing**: pdf2image
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **UI**: Responsive design with CSS Grid/Flexbox