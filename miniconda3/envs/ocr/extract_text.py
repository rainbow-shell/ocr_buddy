from pdf2image import convert_from_path
import pytesseract

# Path to your PDF
pdf_path = "/Users/austinalter/miniconda3/envs/ocr/dot.pdf"

# Convert PDF pages to images
pages = convert_from_path(pdf_path, dpi=300)

# Run OCR and collect text
text = "\n".join(pytesseract.image_to_string(page) for page in pages)

# Save to TXT file
output_path = "dot.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"OCR text saved to {output_path}")
