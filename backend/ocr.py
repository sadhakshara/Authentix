from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
import cv2
import re
import os

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def ocr_full_text(image_path):
    """
    Performs full-page OCR and returns the text as a single string.
    
    Args:
        image_path (str): The file path to the image.
        
    Returns:
        str: The extracted text from the image.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found at path: {image_path}")
        
        # Convert the image to grayscale for better OCR performance.
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        pil_img = Image.fromarray(gray_img)
        full_text = pytesseract.image_to_string(pil_img)
        
        return full_text

    except Exception as e:
        return f"An error occurred during OCR processing: {e}"

def extract_data_with_regex(text):
    """
    Uses regular expressions to extract specific fields from the OCR text.
    
    Args:
        text (str): The full text string from OCR.
    
    Returns:
        dict: A dictionary containing the extracted fields.
    """
    extracted_fields = {
        'enrollment_no': 'Not Found',
        'dc_no': 'Not Found',
        'name': 'Not Found',
        'degree': 'Not Found',
        'year_of_passing': 'Not Found',
        'division': 'Not Found',
        'institution': 'Not Found'
    }
    
    id_match = re.search(r'Enrolment No\.?:\s*(\S+)\s*Dc:\s*(\S+)', text, re.IGNORECASE)
    if id_match:
        extracted_fields['enrollment_no'] = id_match.group(1).strip()
        extracted_fields['dc_no'] = id_match.group(2).strip()
    
    # Regex for Student's Name
    name_match = re.search(r'(?<=conferred upon\s)[\s\S]*?(?=\sthe degree of)', text, re.IGNORECASE | re.DOTALL)
    if name_match:
        extracted_fields['name'] = name_match.group(0).strip()
    
    # Regex for Degree
    degree_match = re.search(r'(?<=the degree of\s)[\s\S]*?(?=\shaving passed the examination)', text, re.IGNORECASE | re.DOTALL)
    if degree_match:
        extracted_fields['degree'] = degree_match.group(0).strip()
    
    # Regex for Year of Passing
    year_match = re.search(r'(?<=examination of\s)\d{4}', text, re.IGNORECASE)
    if year_match:
        extracted_fields['year_of_passing'] = year_match.group(0).strip()

    # Regex for Division
    division_match = re.search(r'(?<=in\s)[\s\S]*?(?=Division)', text, re.IGNORECASE)
    if division_match:
        extracted_fields['division'] = division_match.group(0).strip() + ' Division'

    # Regex for Institution
    institution_match = re.search(r'([A-Z][a-z]+\s*){1,3}(UNIVERSITY|INSTITUTE|COLLEGE)', text, re.IGNORECASE | re.DOTALL)
    if institution_match:
        extracted_fields['institution'] = institution_match.group(0).strip()
        
    return extracted_fields



@app.route('/extract', methods=['POST'])
def extract_from_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        full_text = ocr_full_text(filepath)
        os.remove(filepath)

        if "An error occurred" in full_text:
            return jsonify({"error": full_text}), 500

        extracted_data = extract_data_with_regex(full_text)
        
        return jsonify({
            
            "extracted_data": extracted_data
        })

if __name__ == '__main__':
    app.run(debug=True)
