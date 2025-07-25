from flask import Flask, request, render_template, jsonify, send_file
from pdf2image import convert_from_path
import pytesseract
import os
import tempfile
import uuid
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'pdf'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using OCR"""
    try:
        # Convert PDF pages to images
        pages = convert_from_path(pdf_path, dpi=300)
        
        # Run OCR and collect text
        text = "\n".join(pytesseract.image_to_string(page) for page in pages)
        
        return text
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        upload_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
        
        # Save uploaded file
        file.save(upload_path)
        
        # Extract text using OCR
        extracted_text = extract_text_from_pdf(upload_path)
        
        # Save extracted text
        output_filename = f"{file_id}_output.txt"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        # Clean up uploaded PDF
        os.remove(upload_path)
        
        return jsonify({
            'success': True,
            'message': 'OCR processing completed successfully',
            'output_file': output_filename,
            'text_preview': extracted_text[:500] + ('...' if len(extracted_text) > 500 else '')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(OUTPUT_FOLDER, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)