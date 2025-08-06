#!/usr/bin/env python3
"""
Commercial Real Estate Email Scanner
Processes marketing emails and extracts key deal information to CSV format.
"""

import os
import sys
import argparse
import logging
import tempfile
import shutil
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

from email_parser import EmailParser
from ocr_processor import OCRProcessor
from llm_extractor import LLMFieldExtractor
from csv_generator import CSVGenerator

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailScanner:
    """Main class for processing commercial real estate marketing emails."""
    
    def __init__(self, 
                 google_api_key: Optional[str] = None,
                 tesseract_path: Optional[str] = None,
                 model: str = "gemini-2.5-pro"):
        """Initialize the email scanner with required components."""
        self.email_parser = EmailParser()
        self.ocr_processor = OCRProcessor(tesseract_path)
        self.llm_extractor = LLMFieldExtractor(google_api_key, model)
        self.csv_generator = CSVGenerator()
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'ocr_used': 0,
            'errors': 0
        }
    
    def process_single_email(self, email_path: str, temp_dir: str) -> Dict:
        """Process a single email file and extract deal information."""
        logger.info(f"Processing email: {os.path.basename(email_path)}")
        
        result = {
            'source_email': email_path,
            'success': False,
            'ocr_used': False,
            'extracted_fields': {},
            'quality_score': 0,
            'critical_score': 0,
            'error': None
        }
        
        try:
            # Step 1: Parse email content
            email_data = self.email_parser.parse_eml_file(email_path)
            if not email_data:
                result['error'] = "Failed to parse email file"
                return result
            
            # Step 2: Initial LLM extraction from text content
            initial_fields = self.llm_extractor.extract_fields(email_data['clean_text'])
            quality_assessment = self.llm_extractor.assess_extraction_quality(initial_fields)
            
            # Step 3: Determine if OCR is needed
            should_ocr = self.ocr_processor.should_use_ocr(
                email_data['clean_text'], 
                initial_fields
            )
            
            final_fields = initial_fields
            
            if should_ocr and (email_data['images'] or email_data['attachments']):
                logger.info("OCR triggered - processing images")
                result['ocr_used'] = True
                
                # Download and process images
                image_dir = os.path.join(temp_dir, f"images_{os.path.basename(email_path)}")
                os.makedirs(image_dir, exist_ok=True)
                
                # Process embedded images
                image_files = []
                if email_data['images']:
                    downloaded_images = self.email_parser.download_images(
                        email_data['images'], image_dir
                    )
                    image_files.extend(downloaded_images)
                
                # Process attachments
                if email_data['attachments']:
                    attachment_files = self.email_parser.save_attachments(
                        email_data['attachments'], image_dir
                    )
                    image_files.extend(attachment_files)
                
                # Run OCR on images
                if image_files:
                    ocr_results = self.ocr_processor.process_multiple_images(image_files)
                    
                    # Merge text with OCR results
                    combined_text = self.ocr_processor.merge_text_and_ocr(
                        email_data['clean_text'], ocr_results
                    )
                    
                    # Re-run LLM extraction with combined text
                    final_fields = self.llm_extractor.extract_fields(combined_text)
                    quality_assessment = self.llm_extractor.assess_extraction_quality(final_fields)
                    
                    logger.info(f"OCR processed {len(image_files)} images")
            
            # Step 4: Update results
            result['extracted_fields'] = final_fields
            result['quality_score'] = quality_assessment['quality_score']
            result['critical_score'] = quality_assessment['critical_score']
            result['success'] = True
            
            logger.info(f"Successfully processed {os.path.basename(email_path)} - Quality: {quality_assessment['quality_score']:.1f}%")
            
        except Exception as e:
            logger.error(f"Error processing {email_path}: {str(e)}")
            result['error'] = str(e)
        
        return result
    
    def scan_email_directory(self, 
                           email_dir: str, 
                           output_csv: str,
                           summary_file: Optional[str] = None) -> bool:
        """Scan directory of email files and generate CSV output."""
        
        if not os.path.exists(email_dir):
            logger.error(f"Email directory not found: {email_dir}")
            return False
        
        # Find all .eml files
        email_files = []
        for root, dirs, files in os.walk(email_dir):
            for file in files:
                if file.lower().endswith('.eml'):
                    email_files.append(os.path.join(root, file))
        
        if not email_files:
            logger.warning(f"No .eml files found in {email_dir}")
            return False
        
        logger.info(f"Found {len(email_files)} email files to process")
        
        # Create temporary directory for image processing
        with tempfile.TemporaryDirectory() as temp_dir:
            processing_results = []
            csv_rows = []
            
            # Process each email
            for email_file in email_files:
                result = self.process_single_email(email_file, temp_dir)
                processing_results.append(result)
                
                # Update statistics
                self.stats['total_processed'] += 1
                if result['success']:
                    self.stats['successful'] += 1
                if result['ocr_used']:
                    self.stats['ocr_used'] += 1
                if result.get('error'):
                    self.stats['errors'] += 1
                
                # Create CSV row if successful
                if result['success'] and result['extracted_fields']:
                    csv_row = self.csv_generator.create_pipeline_row(
                        result['extracted_fields'], 
                        email_file
                    )
                    csv_rows.append(csv_row)
            
            # Generate outputs
            success = True
            
            # Write CSV file
            if csv_rows:
                success &= self.csv_generator.write_csv(csv_rows, output_csv)
                logger.info(f"Generated CSV with {len(csv_rows)} deals")
            else:
                logger.warning("No successful extractions - no CSV generated")
                success = False
            
            # Write summary report
            if summary_file:
                success &= self.csv_generator.write_summary_report(processing_results, summary_file)
            
            # Print statistics
            self._print_statistics()
            
            return success
    
    def process_single_file(self, email_file: str, output_csv: str) -> bool:
        """Process a single email file."""
        if not os.path.exists(email_file):
            logger.error(f"Email file not found: {email_file}")
            return False
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.process_single_email(email_file, temp_dir)
            
            if result['success'] and result['extracted_fields']:
                csv_row = self.csv_generator.create_pipeline_row(
                    result['extracted_fields'], 
                    email_file
                )
                
                success = self.csv_generator.write_csv([csv_row], output_csv)
                if success:
                    logger.info(f"Successfully processed {email_file}")
                    logger.info(f"Quality Score: {result['quality_score']:.1f}%")
                    logger.info(f"Critical Fields Score: {result['critical_score']:.1f}%")
                
                return success
            else:
                logger.error(f"Failed to process {email_file}: {result.get('error', 'Unknown error')}")
                return False
    
    def _print_statistics(self):
        """Print processing statistics."""
        logger.info("\n" + "="*50)
        logger.info("PROCESSING STATISTICS")
        logger.info("="*50)
        logger.info(f"Total emails processed: {self.stats['total_processed']}")
        logger.info(f"Successful extractions: {self.stats['successful']}")
        logger.info(f"Success rate: {(self.stats['successful']/self.stats['total_processed']*100):.1f}%")
        logger.info(f"OCR usage: {self.stats['ocr_used']} emails")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("="*50)

def main():
    """Main entry point for the email scanner."""
    parser = argparse.ArgumentParser(
        description="Commercial Real Estate Email Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single email file
  python email_scanner.py -f marketing-emails/neptune.eml -o output.csv
  
  # Process entire directory
  python email_scanner.py -d marketing-emails/ -o pipeline_deals.csv -s summary.txt
  
  # Use custom API key and Tesseract path
  python email_scanner.py -d marketing-emails/ -o deals.csv --google-key YOUR_KEY --tesseract /usr/local/bin/tesseract
        """
    )
    
    # Input options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help='Single email file to process')
    group.add_argument('-d', '--directory', help='Directory containing email files')
    
    # Output options
    parser.add_argument('-o', '--output', required=True, help='Output CSV file path')
    parser.add_argument('-s', '--summary', help='Summary report file path')
    
    # Configuration options
    parser.add_argument('--google-key', help='Google API key (or set GOOGLE_API_KEY env var)')
    parser.add_argument('--tesseract', help='Path to Tesseract executable')
    parser.add_argument('--model', default='gemini-2.5-pro', help='Gemini model to use')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize scanner
    scanner = EmailScanner(
        google_api_key=args.google_key,
        tesseract_path=args.tesseract,
        model=args.model
    )
    
    # Process emails
    if args.file:
        success = scanner.process_single_file(args.file, args.output)
    else:
        success = scanner.scan_email_directory(args.directory, args.output, args.summary)
    
    if success:
        logger.info("Email scanning completed successfully!")
        sys.exit(0)
    else:
        logger.error("Email scanning failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()