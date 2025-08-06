#!/usr/bin/env python3
"""
Setup script for Commercial Real Estate Email Scanner
"""

import os
import sys
import subprocess
import platform

def install_system_dependencies():
    """Install system-level dependencies for OCR."""
    system = platform.system().lower()
    
    print("Installing system dependencies for OCR...")
    
    if system == "darwin":  # macOS
        try:
            # Check if Homebrew is installed
            subprocess.run(["brew", "--version"], check=True, capture_output=True)
            print("Installing Tesseract via Homebrew...")
            subprocess.run(["brew", "install", "tesseract"], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Homebrew not found. Please install Tesseract manually:")
            print("1. Install Homebrew: https://brew.sh/")
            print("2. Run: brew install tesseract")
            
    elif system == "linux":
        try:
            # Try apt-get (Ubuntu/Debian)
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "tesseract-ocr"], check=True)
        except subprocess.CalledProcessError:
            try:
                # Try yum (CentOS/RHEL)
                subprocess.run(["sudo", "yum", "install", "-y", "tesseract"], check=True)
            except subprocess.CalledProcessError:
                print("Could not install Tesseract automatically.")
                print("Please install manually: sudo apt-get install tesseract-ocr")
                
    elif system == "windows":
        print("Windows detected. Please install Tesseract manually:")
        print("1. Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. Add to PATH or specify path with --tesseract option")
    
    print("System dependencies installation completed.")

def install_python_dependencies():
    """Install Python package dependencies."""
    print("Installing Python dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        print("Python dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Python dependencies: {e}")
        return False
    
    return True

def verify_installation():
    """Verify that all components are properly installed."""
    print("\nVerifying installation...")
    
    # Check Python imports
    try:
        import anthropic
        import pytesseract
        import cv2
        import PIL
        from bs4 import BeautifulSoup
        print("✓ All Python packages imported successfully")
    except ImportError as e:
        print(f"✗ Missing Python package: {e}")
        return False
    
    # Check Tesseract
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract OCR version: {version}")
    except Exception as e:
        print(f"✗ Tesseract not available: {e}")
        print("  OCR functionality will be disabled")
    
    # Check API key
    google_key = os.getenv('GOOGLE_API_KEY')
    if google_key:
        print("✓ Google API key found in environment")
    else:
        print("⚠ Google API key not found in GOOGLE_API_KEY environment variable")
        print("  You'll need to provide it with --google-key option")
    
    return True

def create_example_config():
    """Create example configuration files."""
    print("\nCreating example configuration...")
    
    # Create example environment file
    env_example = """# Commercial Real Estate Email Scanner Configuration
# Copy this to .env and fill in your API key

# Required: Google API key for Gemini
GOOGLE_API_KEY=your_google_api_key_here

# Optional: Custom Tesseract path (if not in system PATH)
# TESSERACT_PATH=/usr/local/bin/tesseract
"""
    
    with open(".env.example", "w") as f:
        f.write(env_example)
    
    print("Created .env.example - copy to .env and add your API key")

def main():
    """Main setup function."""
    print("Commercial Real Estate Email Scanner Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"Python version: {sys.version}")
    
    # Install dependencies
    if not install_python_dependencies():
        sys.exit(1)
    
    # Install system dependencies
    install_system_dependencies()
    
    # Verify installation
    if not verify_installation():
        print("\nSetup completed with warnings. Some features may not work properly.")
    else:
        print("\n✓ Setup completed successfully!")
    
    # Create example config
    create_example_config()
    
    print("\nNext steps:")
    print("1. Set your Google API key: export GOOGLE_API_KEY='your_key'")
    print("2. Test the scanner: python email_scanner.py -f sample.eml -o test.csv")
    print("3. Process your emails: python email_scanner.py -d marketing-emails/ -o deals.csv")

if __name__ == "__main__":
    main()