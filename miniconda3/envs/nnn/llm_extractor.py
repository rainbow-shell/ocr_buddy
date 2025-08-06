import json
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime
import google.generativeai as genai
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMFieldExtractor:
    """Extract commercial real estate fields from email content using Google Gemini."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-pro"):
        """Initialize LLM extractor with Google Gemini API configuration."""
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self.model = model
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            
            # Configure safety settings to be more permissive for business content
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_ONLY_HIGH"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH"
                }
            ]
            
            self.client = genai.GenerativeModel(model, safety_settings=safety_settings)
            logger.info(f"LLM extractor initialized with model: {model}")
        else:
            logger.warning("No Google API key provided")
            self.client = None
    
    def create_extraction_prompt(self, email_content: str) -> str:
        """Create detailed prompt for commercial real estate field extraction."""
        
        prompt = f"""You are a commercial real estate analyst tasked with extracting key information from marketing emails. 
Analyze the following email content and extract the specified fields in JSON format.

IMPORTANT: Pay special attention to the email subject line, as it often contains key property information like location, NOI, lease terms, and property type.

EMAIL CONTENT:
{email_content}

INSTRUCTIONS:
Extract the following fields from the email. If a field is not found or unclear, use null. 
Be precise with numbers, dates, and percentages. Focus on the primary property being marketed.

REQUIRED FIELDS:
{{
    "deal_name": "Descriptive name of the property (e.g., 'Scottsdale Shopping Center')",
    "asset_class": "Type of property: Office, Industrial, Retail, Mixed Use, etc.",
    "description": "Brief description like 'multi-tenant', 'sale leaseback', 'single tenant', 'triple net'",
    "pricing_guidance": "Expected price as number (e.g., 31000000 for $31M)",
    "price_psf": "Price per square foot as number",
    "cap_rate": "Cap rate as percentage (e.g., 5.0 for 5.0%)",
    "address": "Street address only, no city/state",
    "city": "City name",
    "state": "State abbreviation (e.g., 'AZ')",
    "zip_code": "Zip code if mentioned",
    "year_built_reno": "Year built and/or renovation year (e.g., '1986' or '1986 / 2010')",
    "square_footage": "Total square footage as number",
    "land_size": "Land size in acres as number",
    "number_of_buildings": "Number of buildings as number",
    "current_occupancy": "Occupancy percentage (e.g., 90.0 for 90%)",
    "parking_ratio": "Parking ratio as number (e.g., 3.5)",
    "clear_height": "Clear height in feet as number",
    "major_tenants": "Primary tenant names",
    "credit_rating": "Credit rating (e.g., 'BBB+', 'Baa1')",
    "remaining_term": "Remaining lease term in years as number",
    "annual_lease_escalations": "Annual escalation percentage (e.g., 3.0 for 3%)",
    "current_owner": "Current property owner name",
    "broker": "Broker/brokerage company name",
    "broker_contact": "Broker contact person name",
    "broker_phone": "Broker phone number",
    "broker_email": "Broker email address"
}}

EXTRACTION RULES:
- Convert all monetary values to numbers (remove $ and commas)
- Convert percentages to decimal numbers (5% = 5.0)
- Extract only primary property information if multiple properties mentioned
- For ranges, use the midpoint or most likely value
- Be conservative - use null if uncertain
- Focus on factual data, not marketing language

Respond with ONLY the JSON object, no additional text."""
        
        return prompt
    
    def extract_fields(self, email_content: str) -> Dict:
        """Extract fields using Gemini analysis."""
        if not self.client:
            logger.error("No Gemini client available for LLM extraction")
            return self._get_empty_fields()
        
        try:
            # Clean email content more aggressively for Gemini
            cleaned_content = self._clean_for_gemini(email_content)
            prompt = self.create_extraction_prompt(cleaned_content)
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2000,
                candidate_count=1,
            )
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Check if response was blocked by safety filters
            if not response.candidates or not response.candidates[0].content.parts:
                finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
                logger.warning(f"Gemini response blocked or empty. Finish reason: {finish_reason}")
                return self._get_empty_fields()
            
            extracted_text = response.text.strip()
            
            # Clean up markdown code blocks if present
            if extracted_text.startswith('```json') and extracted_text.endswith('```'):
                # Remove markdown code blocks
                extracted_text = extracted_text[7:-3].strip()  # Remove ```json from start and ``` from end
            elif extracted_text.startswith('```') and extracted_text.endswith('```'):
                # Remove generic code blocks
                extracted_text = extracted_text[3:-3].strip()
            
            # Parse JSON response
            try:
                extracted_fields = json.loads(extracted_text)
                logger.info("Successfully extracted fields using Gemini")
                return self._validate_and_clean_fields(extracted_fields)
            except json.JSONDecodeError:
                # Try to repair truncated JSON
                logger.warning("JSON parsing failed, attempting to repair truncated response")
                repaired_json = self._repair_truncated_json(extracted_text)
                if repaired_json:
                    try:
                        extracted_fields = json.loads(repaired_json)
                        logger.info("Successfully repaired and parsed JSON")
                        return self._validate_and_clean_fields(extracted_fields)
                    except json.JSONDecodeError:
                        pass
                
                logger.error(f"Failed to parse Gemini JSON response: {extracted_text}")
                return self._get_empty_fields()
                
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return self._get_empty_fields()
    
    def _clean_for_gemini(self, content: str) -> str:
        """Clean content for Gemini to avoid safety filter issues."""
        # Remove URLs which might trigger safety filters
        content = re.sub(r'https?://[^\s<>"{}|\\^`[\]]+', '[URL]', content)
        
        # Remove long encoded URL parameters
        content = re.sub(r'%[0-9A-Fa-f]{2}', '', content)
        
        # Remove email headers and technical content
        lines = content.split('\n')
        cleaned_lines = []
        skip_headers = True
        
        for line in lines:
            line = line.strip()
            # Skip empty lines at start
            if not line and skip_headers:
                continue
            # Skip header lines
            if skip_headers and ('Received:' in line or 'X-' in line or 'Content-' in line):
                continue
            # Found content, stop skipping headers
            if line and not line.startswith(('Received:', 'X-', 'Content-', 'From:', 'To:', 'Subject:')):
                skip_headers = False
            
            if not skip_headers:
                cleaned_lines.append(line)
        
        cleaned_content = '\n'.join(cleaned_lines)
        
        # Truncate if still too long
        if len(cleaned_content) > 12000:
            logger.info("Truncating long email content for Gemini processing")
            cleaned_content = cleaned_content[:12000] + "...[TRUNCATED]"
        
        return cleaned_content
    
    def _repair_truncated_json(self, json_text: str) -> Optional[str]:
        """Attempt to repair truncated JSON by adding missing closing braces."""
        try:
            # Count opening and closing braces
            open_braces = json_text.count('{')
            close_braces = json_text.count('}')
            
            if open_braces > close_braces:
                # Add missing closing braces
                missing_braces = open_braces - close_braces
                repaired = json_text + '}' * missing_braces
                return repaired
            
            return None
        except Exception:
            return None
    
    def _validate_and_clean_fields(self, fields: Dict) -> Dict:
        """Validate and clean extracted fields."""
        cleaned = {}
        
        # String fields
        string_fields = [
            'deal_name', 'asset_class', 'description', 'address', 'city', 'state', 
            'zip_code', 'year_built_reno', 'major_tenants', 'credit_rating', 
            'current_owner', 'broker', 'broker_contact', 'broker_phone', 'broker_email'
        ]
        
        for field in string_fields:
            value = fields.get(field)
            cleaned[field] = self._clean_string(value) if value else None
        
        # Numeric fields
        numeric_fields = [
            'pricing_guidance', 'price_psf', 'cap_rate', 'square_footage', 
            'land_size', 'number_of_buildings', 'current_occupancy', 
            'parking_ratio', 'clear_height', 'remaining_term', 'annual_lease_escalations'
        ]
        
        for field in numeric_fields:
            value = fields.get(field)
            cleaned[field] = self._clean_numeric(value) if value is not None else None
        
        return cleaned
    
    def _clean_string(self, value) -> Optional[str]:
        """Clean string values."""
        if not value or value == 'null':
            return None
        
        cleaned = str(value).strip()
        if cleaned.lower() in ['', 'null', 'none', 'n/a', 'not available']:
            return None
        
        return cleaned
    
    def _clean_numeric(self, value) -> Optional[float]:
        """Clean numeric values."""
        if value is None or value == 'null':
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Clean string numeric values
        if isinstance(value, str):
            # Remove common formatting
            cleaned = re.sub(r'[,$%]', '', value.strip())
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def _get_empty_fields(self) -> Dict:
        """Return empty fields structure."""
        return {
            'deal_name': None,
            'asset_class': None,
            'description': None,
            'pricing_guidance': None,
            'price_psf': None,
            'cap_rate': None,
            'address': None,
            'city': None,
            'state': None,
            'zip_code': None,
            'year_built_reno': None,
            'square_footage': None,
            'land_size': None,
            'number_of_buildings': None,
            'current_occupancy': None,
            'parking_ratio': None,
            'clear_height': None,
            'major_tenants': None,
            'credit_rating': None,
            'remaining_term': None,
            'annual_lease_escalations': None,
            'current_owner': None,
            'broker': None,
            'broker_contact': None,
            'broker_phone': None,
            'broker_email': None
        }
    
    def assess_extraction_quality(self, extracted_fields: Dict) -> Dict:
        """Assess quality of field extraction."""
        total_fields = len(extracted_fields)
        filled_fields = sum(1 for v in extracted_fields.values() if v is not None)
        
        # Critical fields for commercial real estate
        critical_fields = [
            'deal_name', 'asset_class', 'pricing_guidance', 'address', 
            'city', 'state', 'square_footage'
        ]
        
        filled_critical = sum(1 for field in critical_fields 
                            if extracted_fields.get(field) is not None)
        
        quality_score = (filled_fields / total_fields) * 100
        critical_score = (filled_critical / len(critical_fields)) * 100
        
        assessment = {
            'quality_score': quality_score,
            'critical_score': critical_score,
            'filled_fields': filled_fields,
            'total_fields': total_fields,
            'filled_critical': filled_critical,
            'total_critical': len(critical_fields),
            'is_sufficient': critical_score >= 60  # At least 60% of critical fields
        }
        
        logger.info(f"Extraction quality: {quality_score:.1f}% overall, {critical_score:.1f}% critical fields")
        
        return assessment