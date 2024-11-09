from flask import Flask, request, render_template, send_file
import os
import random
import string
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import io
import PyPDF2

app = Flask(__name__)

# Dictionary to map letters to visually similar numbers
letter_to_number = {
    'a': '4', 'A': '4',
    'e': '3', 'E': '3',
    'i': '1', 'I': '1',
    'o': '0', 'O': '0',
    's': '5', 'S': '5',
    'g': '9', 'G': '9'
}

# Function to generate a random password with changes in the fixed_part
def generate_password():
    fixed_part = "H4CkFlu3nCy"
    num_changes = random.randint(1, 3)  # Randomly choose between 1 and 3 changes
    indices = random.sample(range(len(fixed_part)), num_changes)  # Random indices to change
    
    fixed_part_list = list(fixed_part)  # Convert string to list for mutability
    
    for idx in indices:
        char = fixed_part_list[idx]
        if char in letter_to_number:  # If the character can be replaced with a number
            fixed_part_list[idx] = letter_to_number[char]
        else:  # Change case
            if char.islower():
                fixed_part_list[idx] = char.upper()
            elif char.isupper():
                fixed_part_list[idx] = char.lower()

    fixed_part_modified = ''.join(fixed_part_list)
    
    # Generate random part: 2 symbols, 2 digits, and 2 lowercase letters
    symbols = random.choices(string.punctuation, k=2)
    digits = random.choices(string.digits, k=2)
    letters = random.choices(string.ascii_lowercase, k=2)
    
    random_part = ''.join(symbols + digits + letters)
    
    # Concatenate both parts
    password = fixed_part_modified + random_part
    return password

# Function to extract high-resolution images from each page of the PDF
def extract_images_from_pdf(input_pdf):
    doc = fitz.open(input_pdf)
    images = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        matrix = fitz.Matrix(3, 3)  # Increase resolution 3x
        pix = page.get_pixmap(matrix=matrix)
        img_data = pix.tobytes("png")
        images.append(img_data)
    
    return images

# Function to add noise to the image
def add_noise_to_image(image):
    pixels = image.load()
    width, height = image.size
    
    # Add random noise to pixels
    for i in range(width):
        for j in range(height):
            if random.random() < 0.05:  # 5% chance to alter pixel
                r, g, b = pixels[i, j]
                noise = random.randint(-30, 30)  # Noise range
                pixels[i, j] = (max(0, min(r + noise, 255)),
                                max(0, min(g + noise, 255)),
                                max(0, min(b + noise, 255)))
    return image

# Function to create the PDF from extracted images, adding noise
def create_pdf_from_images_with_noise(images, output_pdf):
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    
    for index, img_data in enumerate(images):
        img = Image.open(io.BytesIO(img_data))  # Load image from bytes
        
        # Add noise to the image
        img = add_noise_to_image(img)
        
        img_path = f"temp_image_{index}.png"
        img.save(img_path)  # Temporarily save the image with noise
        
        # Calculate image size and adjust its scale to fit the page
        img_width, img_height = img.size
        aspect_ratio = img_width / img_height
        if aspect_ratio > 1:  # Wider than tall
            new_width = width
            new_height = width / aspect_ratio
        else:  # Taller than wide
            new_height = height
            new_width = height * aspect_ratio
        
        # Center the image on the page
        x_offset = (width - new_width) / 2
        y_offset = (height - new_height) / 2

        c.drawImage(img_path, x_offset, y_offset, new_width, new_height)
        c.showPage()  # Add a new page
        
        if os.path.exists(img_path):
            os.remove(img_path)

    c.save()

# Function to encrypt the generated PDF with a password
def encrypt_pdf(input_pdf, output_pdf, password):
    with open(input_pdf, "rb") as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        writer = PyPDF2.PdfWriter()

        for page_num in range(len(reader.pages)):
            writer.add_page(reader.pages[page_num])

        # Encrypt the PDF file with the generated password
        writer.encrypt(password)

        with open(output_pdf, "wb") as encrypted_pdf_file:
            writer.write(encrypted_pdf_file)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf_file' not in request.files:
        return "No file part"
    
    file = request.files['pdf_file']
    if file.filename == '':
        return "No selected file"

    # Save the uploaded file
    input_pdf_path = "uploaded_pdf.pdf"
    file.save(input_pdf_path)

    # Process the PDF
    images = extract_images_from_pdf(input_pdf_path)
    output_pdf_path = "output_pdf.pdf"
    create_pdf_from_images_with_noise(images, output_pdf_path)
    
    # Generate the password
    password = generate_password()
    print(f"Contraseña generada: {password}")

    # Encrypt the PDF with the generated password
    encrypted_pdf_path = "protected_pdf.pdf"
    encrypt_pdf(output_pdf_path, encrypted_pdf_path, password)

    # Return the encrypted PDF as a download
    return render_template('download.html', password=password, pdf_path=encrypted_pdf_path)


@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_file(filename, as_attachment=True), 200


if __name__ == '__main__':
    app.run(debug=True)