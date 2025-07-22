from flask import Flask, request, render_template, send_file
import fitz  # PyMuPDF
import requests
import os
from dotenv import load_dotenv
import markdown
from fpdf import FPDF
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def get_concept_explanation(text, concept):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    context_text = text[:8000]

    prompt = f"""
You are an expert AI tutor. Using the textbook material below, explain the concept '**{concept}**' in a **detailed and structured** manner.

✅ Format the explanation using:
- **Bold section headings** (e.g., **Overview**, **Causes**, **Effects**, **Applications**, **Conclusion**)
- Bullet points under each section
- Clear and student-friendly language
- Avoid making up content not found in the material

📚 Textbook Content:
{context_text}
"""

    payload = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(GROQ_ENDPOINT, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0]["message"]["content"]
        else:
            return "❌ Response format invalid from Groq API."
    else:
        return f"❌ Groq API error {response.status_code}: {response.text}"

def save_to_pdf(text, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.set_font("Arial", size=12)

    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)

    pdf.output(filename)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        pdf = request.files["pdf"]
        concept = request.form["concept"]

        os.makedirs("uploads", exist_ok=True)
        os.makedirs("outputs", exist_ok=True)

        pdf_path = os.path.join("uploads", pdf.filename)
        pdf.save(pdf_path)

        text = extract_text_from_pdf(pdf_path)
        explanation = get_concept_explanation(text, concept)
        explanation_html = markdown.markdown(explanation)

        # Save explanation as PDF
        pdf_filename = f"outputs/explanation_{uuid.uuid4().hex}.pdf"
        save_to_pdf(explanation, pdf_filename)

        return render_template("index.html", explanation=explanation_html, concept=concept, download_link=pdf_filename)

    return render_template("index.html")

@app.route("/download/<path:filename>")
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)







