import email
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailParser:
    """Parse .eml files and extract text content and images for OCR processing."""
    
    def __init__(self):
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.pdf'}
    
    def parse_eml_file(self, file_path: str) -> Dict:
        """Parse an .eml file and extract content."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                msg = email.message_from_file(f)
            
            result = {
                'subject': msg.get('Subject', ''),
                'from': msg.get('From', ''),
                'to': msg.get('To', ''),
                'date': msg.get('Date', ''),
                'text_content': '',
                'html_content': '',
                'images': [],
                'attachments': []
            }
            
            # Extract text and HTML content
            if msg.is_multipart():
                for part in msg.walk():
                    self._process_email_part(part, result)
            else:
                self._process_email_part(msg, result)
            
            # Clean and extract final text
            result['clean_text'] = self._extract_clean_text(result)
            
            # Add subject line to clean text for better LLM analysis
            if result['subject']:
                result['clean_text'] = f"SUBJECT: {result['subject']}\n\n{result['clean_text']}"
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing email {file_path}: {str(e)}")
            return {}
    
    def _process_email_part(self, part, result: Dict):
        """Process individual email part (text, HTML, attachment)."""
        content_type = part.get_content_type()
        
        if content_type == 'text/plain':
            payload = part.get_payload(decode=True)
            if payload:
                result['text_content'] += payload.decode('utf-8', errors='ignore')
        
        elif content_type == 'text/html':
            payload = part.get_payload(decode=True)
            if payload:
                result['html_content'] += payload.decode('utf-8', errors='ignore')
        
        elif part.get_content_disposition() == 'attachment':
            filename = part.get_filename()
            if filename and any(filename.lower().endswith(ext) for ext in self.image_extensions):
                result['attachments'].append({
                    'filename': filename,
                    'content': part.get_payload(decode=True)
                })
    
    def _extract_clean_text(self, result: Dict) -> str:
        """Extract clean text from email content."""
        text_content = result.get('text_content', '')
        html_content = result.get('html_content', '')
        
        # If we have plain text, use it
        if text_content.strip():
            return self._clean_text(text_content)
        
        # Otherwise, extract text from HTML
        if html_content.strip():
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract image URLs for potential OCR
            images = soup.find_all('img')
            for img in images:
                src = img.get('src')
                if src:
                    result['images'].append({
                        'url': src,
                        'alt': img.get('alt', ''),
                        'title': img.get('title', '')
                    })
            
            # Extract clean text
            text = soup.get_text()
            return self._clean_text(text)
        
        return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove email headers and signatures
        text = re.sub(r'Received:.*?(?=\n[A-Z]|\n\n|\Z)', '', text, flags=re.DOTALL)
        text = re.sub(r'X-.*?(?=\n[A-Z]|\n\n|\Z)', '', text, flags=re.DOTALL)
        # Remove unsubscribe links and legal disclaimers
        text = re.sub(r'Unsubscribe.*?(?=\n\n|\Z)', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'The information contained herein.*?(?=\n\n|\Z)', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        return text.strip()
    
    def download_images(self, images: List[Dict], output_dir: str) -> List[str]:
        """Download images from email for OCR processing."""
        downloaded_files = []
        os.makedirs(output_dir, exist_ok=True)
        
        for i, img in enumerate(images):
            try:
                url = img['url']
                if not url.startswith('http'):
                    continue  # Skip data URLs and relative paths for now
                
                # Add headers to avoid blocking
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(url, timeout=15, headers=headers)
                if response.status_code == 200:
                    # Determine file extension
                    parsed_url = urlparse(url)
                    filename = os.path.basename(parsed_url.path)
                    if not filename or '.' not in filename:
                        # Try to determine from content type
                        content_type = response.headers.get('content-type', '')
                        if 'jpeg' in content_type or 'jpg' in content_type:
                            filename = f"image_{i}.jpg"
                        elif 'png' in content_type:
                            filename = f"image_{i}.png"
                        else:
                            filename = f"image_{i}.jpg"  # Default
                    
                    file_path = os.path.join(output_dir, filename)
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    downloaded_files.append(file_path)
                    logger.info(f"Downloaded image: {filename} ({len(response.content)} bytes)")
                else:
                    logger.warning(f"Failed to download image {url}: HTTP {response.status_code}")
                
            except Exception as e:
                logger.warning(f"Failed to download image {img['url']}: {str(e)}")
        
        return downloaded_files
    
    def save_attachments(self, attachments: List[Dict], output_dir: str) -> List[str]:
        """Save email attachments to disk."""
        saved_files = []
        os.makedirs(output_dir, exist_ok=True)
        
        for attachment in attachments:
            try:
                filename = attachment['filename']
                content = attachment['content']
                
                file_path = os.path.join(output_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                saved_files.append(file_path)
                logger.info(f"Saved attachment: {filename}")
                
            except Exception as e:
                logger.warning(f"Failed to save attachment {attachment['filename']}: {str(e)}")
        
        return saved_files