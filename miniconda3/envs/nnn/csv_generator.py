import csv
import os
import logging
from typing import Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CSVGenerator:
    """Generate CSV output matching the pipeline format."""
    
    def __init__(self):
        # Define the column mapping from extracted fields to pipeline CSV columns
        self.column_mapping = {
            'Deal': 'deal_name',
            'Entry Date': 'entry_date',
            'Asset Class': 'asset_class', 
            'Description': 'description',
            'Pricing Guidance': 'pricing_guidance',
            'Price PSF': 'price_psf',
            'Cap Rate': 'cap_rate',
            'Address': 'address',
            'City': 'city',
            'State': 'state',
            'Zip Code': 'zip_code',
            'Year Built / Last Reno': 'year_built_reno',
            'Square Footage': 'square_footage',
            'Land Size': 'land_size',
            '# of Bldgs': 'number_of_buildings',
            'Current Occupancy': 'current_occupancy',
            'Parking Ratio': 'parking_ratio',
            'Clear Height': 'clear_height',
            'Major Tenant(s)': 'major_tenants',
            'Credit Rating': 'credit_rating',
            'Remaining Term': 'remaining_term',
            'Annual Lease Escalations': 'annual_lease_escalations',
            'Current Owner': 'current_owner',
            'Broker': 'broker',
            'Contact': 'broker_contact',
            'Phone Number': 'broker_phone',
            'Email': 'broker_email'
        }
        
        # Pipeline CSV headers (from your original file)
        self.pipeline_headers = [
            'Deal', 'Book #', 'Next Steps', 'Entry Date', 'Bid Date', 'Deal Lead',
            'Capitalization', 'Asset Class', 'Description', 'Pricing Guidance', 'Price PSF',
            'Cap Rate', 'Address', 'City', 'State', 'Year Built / Last Reno', 'Square Footage',
            'Land Size', '# of Bldgs', 'Current Occupancy', 'Parking Ratio', 'Clear Height',
            'Major Tenant(s)', 'Credit Rating', 'Remaining Term', 'Annual Lease Escalations',
            'Current Owner', 'Desktop Due Date', 'Desktop Complete', 'One Pager Due Date',
            'One Pager Complete', 'VAL or One Pager', 'Virtual Deal Room Link', 'Materials Received',
            'BAFO Date', 'LOI Sent', 'Date Awarded', 'Status', 'Comments', 'Broker', 'Contact',
            'Phone Number', 'Email', 'FD LOI Price', 'Final Price vs Stonewater Price', 'Seller',
            'Buyer', 'Final Price', 'Final Price vs Guidance Price', 'Closing Date & Comments',
            'Government Adjacent', 'Parent Row', 'New Venture', 'Up-Date', 'Sent CA',
            'Origination Type', 'Classification', 'Reviewed (Date) Year', 'LOI Year',
            'Risk Profile', 'Deal Type'
        ]
    
    def format_value(self, value, field_type: str = 'string') -> str:
        """Format values for CSV output."""
        if value is None:
            return ''
        
        if field_type == 'currency' and isinstance(value, (int, float)):
            return f"${value:,.2f}" if value != int(value) else f"${int(value):,}"
        
        if field_type == 'percentage' and isinstance(value, (int, float)):
            return f"{value}%"
        
        if field_type == 'number' and isinstance(value, (int, float)):
            return f"{int(value):,}" if value == int(value) else f"{value:,.2f}"
        
        return str(value)
    
    def create_pipeline_row(self, extracted_fields: Dict, source_email: str = '') -> Dict:
        """Create a pipeline CSV row from extracted fields."""
        row = {}
        
        # Initialize all columns as empty
        for header in self.pipeline_headers:
            row[header] = ''
        
        # Fill in extracted data
        for csv_column, field_key in self.column_mapping.items():
            if csv_column in row and field_key in extracted_fields:
                value = extracted_fields[field_key]
                
                # Format specific field types
                if csv_column == 'Pricing Guidance':
                    row[csv_column] = self.format_value(value, 'currency')
                elif csv_column in ['Cap Rate', 'Current Occupancy', 'Annual Lease Escalations']:
                    row[csv_column] = self.format_value(value, 'percentage')
                elif csv_column in ['Square Footage', 'Land Size', '# of Bldgs']:
                    row[csv_column] = self.format_value(value, 'number')
                else:
                    row[csv_column] = self.format_value(value)
        
        # Add metadata
        row['Entry Date'] = datetime.now().strftime('%m/%d/%y')
        row['Comments'] = f'Extracted from email: {os.path.basename(source_email)}' if source_email else 'Extracted from marketing email'
        
        return row
    
    def write_csv(self, deals_data: List[Dict], output_file: str) -> bool:
        """Write deals data to CSV file."""
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.pipeline_headers)
                
                # Write header
                writer.writeheader()
                
                # Write data rows
                for deal in deals_data:
                    writer.writerow(deal)
            
            logger.info(f"Successfully wrote {len(deals_data)} deals to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write CSV file {output_file}: {e}")
            return False
    
    def append_to_existing_csv(self, deals_data: List[Dict], csv_file: str) -> bool:
        """Append new deals to existing pipeline CSV."""
        try:
            # Check if file exists
            file_exists = os.path.exists(csv_file)
            
            with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.pipeline_headers)
                
                # Write header only if new file
                if not file_exists:
                    writer.writeheader()
                
                # Write data rows
                for deal in deals_data:
                    writer.writerow(deal)
            
            action = "appended to" if file_exists else "created"
            logger.info(f"Successfully {action} {csv_file} with {len(deals_data)} deals")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write/append to CSV file {csv_file}: {e}")
            return False
    
    def create_summary_report(self, processing_results: List[Dict]) -> Dict:
        """Create summary report of processing results."""
        total_emails = len(processing_results)
        successful_extractions = sum(1 for r in processing_results if r.get('success', False))
        ocr_used = sum(1 for r in processing_results if r.get('ocr_used', False))
        
        # Quality metrics
        quality_scores = [r.get('quality_score', 0) for r in processing_results if r.get('success')]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Critical field completion
        critical_scores = [r.get('critical_score', 0) for r in processing_results if r.get('success')]
        avg_critical = sum(critical_scores) / len(critical_scores) if critical_scores else 0
        
        summary = {
            'total_emails_processed': total_emails,
            'successful_extractions': successful_extractions,
            'success_rate': (successful_extractions / total_emails * 100) if total_emails > 0 else 0,
            'ocr_usage_count': ocr_used,
            'ocr_usage_rate': (ocr_used / total_emails * 100) if total_emails > 0 else 0,
            'average_quality_score': avg_quality,
            'average_critical_score': avg_critical,
            'processing_timestamp': datetime.now().isoformat()
        }
        
        return summary
    
    def write_summary_report(self, processing_results: List[Dict], output_file: str) -> bool:
        """Write processing summary to file."""
        try:
            summary = self.create_summary_report(processing_results)
            
            with open(output_file, 'w') as f:
                f.write("COMMERCIAL REAL ESTATE EMAIL PROCESSING SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Processing Date: {summary['processing_timestamp']}\n")
                f.write(f"Total Emails Processed: {summary['total_emails_processed']}\n")
                f.write(f"Successful Extractions: {summary['successful_extractions']}\n")
                f.write(f"Success Rate: {summary['success_rate']:.1f}%\n")
                f.write(f"OCR Usage: {summary['ocr_usage_count']} emails ({summary['ocr_usage_rate']:.1f}%)\n")
                f.write(f"Average Quality Score: {summary['average_quality_score']:.1f}%\n")
                f.write(f"Average Critical Fields Score: {summary['average_critical_score']:.1f}%\n\n")
                
                f.write("INDIVIDUAL EMAIL RESULTS:\n")
                f.write("-" * 30 + "\n")
                
                for i, result in enumerate(processing_results, 1):
                    f.write(f"{i}. {result.get('source_email', 'Unknown')}\n")
                    f.write(f"   Success: {result.get('success', False)}\n")
                    f.write(f"   Quality: {result.get('quality_score', 0):.1f}%\n")
                    f.write(f"   OCR Used: {result.get('ocr_used', False)}\n")
                    if result.get('error'):
                        f.write(f"   Error: {result['error']}\n")
                    f.write("\n")
            
            logger.info(f"Summary report written to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write summary report: {e}")
            return False