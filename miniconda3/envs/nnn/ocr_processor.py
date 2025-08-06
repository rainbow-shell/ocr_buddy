import os
import logging
from typing import List, Dict, Optional
from PIL import Image
import pytesseract
import cv2
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    """Handle OCR processing for images and PDFs."""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """Initialize OCR processor with optional Tesseract path."""
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Test if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
            self.ocr_available = True
            logger.info("Tesseract OCR initialized successfully")
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
            self.ocr_available = False
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR accuracy."""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed for {image_path}: {e}")
            # Fallback to original image
            return cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    def extract_text_from_image(self, image_path: str) -> Dict[str, any]:
        """Extract text from image using OCR."""
        if not self.ocr_available:
            return {'text': '', 'confidence': 0, 'error': 'OCR not available'}
        
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_path)
            
            # Configure Tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,$%()-/:; '
            
            # Extract text with confidence scores
            data = pytesseract.image_to_data(
                processed_img, 
                config=custom_config, 
                output_type=pytesseract.Output.DICT
            )
            
            # Filter out low-confidence text
            min_confidence = 30
            text_parts = []
            confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > min_confidence:
                    text = data['text'][i].strip()
                    if text:
                        text_parts.append(text)
                        confidences.append(int(data['conf'][i]))
            
            extracted_text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            logger.info(f"OCR extracted {len(text_parts)} text elements from {os.path.basename(image_path)}")
            
            return {
                'text': extracted_text,
                'confidence': avg_confidence,
                'word_count': len(text_parts),
                'source_file': image_path
            }
            
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return {'text': '', 'confidence': 0, 'error': str(e)}
    
    def process_multiple_images(self, image_paths: List[str]) -> List[Dict]:
        """Process multiple images and return OCR results."""
        results = []
        for image_path in image_paths:
            if os.path.exists(image_path):
                result = self.extract_text_from_image(image_path)
                results.append(result)
            else:
                logger.warning(f"Image file not found: {image_path}")
                results.append({
                    'text': '', 
                    'confidence': 0, 
                    'error': 'File not found',
                    'source_file': image_path
                })
        
        return results
    
    def should_use_ocr(self, text_content: str, extracted_fields: Dict) -> bool:
        """Determine if OCR should be used based on text analysis."""
        # Count non-empty critical fields
        critical_fields = [
            'pricing_guidance', 'address', 'city', 'state', 
            'square_footage', 'asset_class', 'cap_rate'
        ]
        
        filled_critical = sum(1 for field in critical_fields if extracted_fields.get(field))
        critical_threshold = len(critical_fields) * 0.4  # 40% of critical fields
        
        # Check text content length
        text_length = len(text_content.strip())
        
        # Triggers for OCR
        triggers = [
            filled_critical < critical_threshold,  # Missing critical data
            text_length < 500,  # Very short email text
            'image' in text_content.lower() and 'click' in text_content.lower(),  # Image-heavy email
            'view with images' in text_content.lower()  # Common image email phrase
        ]
        
        should_ocr = any(triggers)
        
        logger.info(f"OCR decision: {should_ocr} (filled_critical: {filled_critical}/{len(critical_fields)}, text_length: {text_length})")
        
        return should_ocr
    
    def merge_text_and_ocr(self, email_text: str, ocr_results: List[Dict]) -> str:
        """Merge email text with OCR results for comprehensive analysis."""
        combined_text = email_text + "\n\n"
        
        for i, ocr_result in enumerate(ocr_results):
            if ocr_result.get('text') and ocr_result.get('confidence', 0) > 20:
                combined_text += f"\n--- OCR Text from Image {i+1} ---\n"
                combined_text += ocr_result['text'] + "\n"
        
        return combined_text.strip()