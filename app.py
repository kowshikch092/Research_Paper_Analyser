import os
import uuid
import json
import pickle
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
import markdown
from fpdf import FPDF

# Import your existing modules
from src.extractortext import extract_text_images_from_pdf
from src.pre_processing import preprocess_research_paper_text
from src.extract_sections_wise import extract_sections, debug_extraction
from src.writing_quality import analyze_writing_quality
from src.section_analysis import analyze_section_structure, print_section_analysis_report
from src.novelty_scibert_corpus import build_corpus_embeddings, compute_novelty_against_corpus, aggregate_novelty
from src.final_report import generate_final_report, print_report

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'data/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('reports', exist_ok=True)
os.makedirs('data/corpus', exist_ok=True)
os.makedirs('images', exist_ok=True)

# Store analysis history in memory (no database)
analysis_history = []

def allowed_file(filename):
    return '.' in filename and filename.lower().endswith('pdf')

def load_corpus_embeddings():
    """Load or build corpus embeddings"""
    corpus_path = "data/corpus_embeddings.pkl"
    if os.path.exists(corpus_path):
        try:
            with open(corpus_path, 'rb') as f:
                return pickle.load(f)
        except:
            pass
    
    # Build if not exists
    if os.path.exists("data/corpus") and os.listdir("data/corpus"):
        return build_corpus_embeddings(corpus_dir="data/corpus", cache_path=corpus_path)
    return {}

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'AI Research Paper Review Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def section_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, self._sanitize(title), 0, 1, 'L', 1)
        self.ln(4)

    def section_body(self, text):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 5, self._sanitize(text))
        self.ln(4)

    def _sanitize(self, text):
        return str(text).encode('latin-1', 'replace').decode('latin-1')

    def score_chart(self, scores):
        self.set_font('Arial', 'B', 11)
        for key, value in scores.items():
            self.cell(60, 8, f"{key.replace('_', ' ').title()}:", 0, 0)
            self.set_font('Arial', '', 11)
            self.cell(30, 8, f"{value}/100", 0, 1)
            self.ln(2)

def generate_pdf_report(report_data, filename):
    """Generate PDF report from analysis data"""
    pdf = PDFReport()
    pdf.add_page()
    
    # Metadata
    pdf.set_font('Arial', 'I', 10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1)
    pdf.cell(0, 6, f"Paper: {report_data.get('filename', 'Unknown')}", 0, 1)
    pdf.ln(10)
    
    # Overall Scores
    pdf.section_title("Overall Quality Scores")
    scores = report_data.get('overall_scores', {})
    pdf.score_chart(scores)
    pdf.ln(5)
    
    # Novelty Score
    if 'novelty_score' in scores:
        pdf.section_title(f"Novelty Score: {scores['novelty_score']}/100")
        if scores['novelty_score'] < 40:
            pdf.section_body("Warning: Low novelty - Paper shows high similarity to existing corpus.")
        elif scores['novelty_score'] < 70:
            pdf.section_body("Moderate novelty - Some unique elements present.")
        else:
            pdf.section_body("High novelty - Significant unique contribution!")
    
    # Section Analysis
    pdf.section_title("Section Analysis")
    for section in report_data.get('per_section', []):
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 6, f"Section: {section['section'].title()}", 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, f"   Words: {section['word_count']}", 0, 1)
        if section.get('novelty'):
            pdf.cell(0, 5, f"   Novelty: {section['novelty']}/100", 0, 1)
        
        if section.get('issues'):
            pdf.set_text_color(255, 0, 0)
            for issue in section['issues']:
                pdf.cell(0, 5, f"   Warning: {issue}", 0, 1)
            pdf.set_text_color(0, 0, 0)
        
        if section.get('suggestions'):
            pdf.set_text_color(0, 100, 0)
            for suggestion in section['suggestions'][:2]:  # Limit to 2 suggestions per section
                pdf.section_body(f"Suggestion: {suggestion}")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
    
    # Missing Sections
    missing = report_data.get('missing_sections', [])
    if missing:
        pdf.section_title("Missing Standard Sections")
        for section in missing:
            pdf.cell(0, 6, f"Missing: {section}", 0, 1)
    
    # Top Recommendations
    pdf.section_title("Top 5 Recommendations")
    recs = report_data.get('summary', '').split('\n')
    for rec in recs[:5]:
        if rec.strip() and not rec.startswith('Final'):
            pdf.section_body(f"- {rec}")
    
    pdf.output(filename)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', history=analysis_history[-5:])  # Show last 5 analyses

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/history')
def history():
    return render_template('history.html', history=analysis_history)

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400
    
    # Generate unique ID for this analysis
    analysis_id = str(uuid.uuid4())[:8]
    filename = secure_filename(file.filename)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{analysis_id}_{filename}")
    file.save(pdf_path)
    
    try:
        # Step 1: Extract text
        raw_text = extract_text_images_from_pdf(pdf_path)
        
        # Step 2: Preprocess
        preprocessed_text = preprocess_research_paper_text(raw_text)
        
        # Step 3: Extract sections
        sections = extract_sections(preprocessed_text)
        
        # Step 4: Analyze sections
        section_analysis = analyze_section_structure(sections)
        
        # Step 5: Writing quality
        writing_quality = analyze_writing_quality(sections)
        
        # Step 6: Novelty analysis
        novelty_map = {}
        try:
            corpus_emb = load_corpus_embeddings()
            if corpus_emb:
                novelty_map = compute_novelty_against_corpus(sections, corpus_emb, method="max")
        except Exception as e:
            print(f"Novelty analysis skipped: {e}")
        
        # Step 7: Generate final report
        report = generate_final_report(writing_quality, section_analysis, novelty_map)
        
        # Add metadata
        report['filename'] = filename
        report['analysis_id'] = analysis_id
        report['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report['missing_sections'] = section_analysis.get('missing_standard_sections', [])
        
        # Save to history
        analysis_entry = {
            'id': analysis_id,
            'filename': filename,
            'timestamp': report['timestamp'],
            'scores': report['overall_scores'],
            'report': report
        }
        analysis_history.append(analysis_entry)
        
        # Generate PDF report
        pdf_filename = f"reports/report_{analysis_id}.pdf"
        try:
            generate_pdf_report(report, pdf_filename)
            report['pdf_path'] = pdf_filename
        except Exception as e:
            print(f"Error generating PDF: {e}")
            report['pdf_path'] = None
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'report': report
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/report/<analysis_id>')
def view_report(analysis_id):
    # Find report in history
    for entry in analysis_history:
        if entry['id'] == analysis_id:
            return render_template('report.html', report=entry['report'])
    return redirect(url_for('dashboard'))

@app.route('/download/<analysis_id>')
def download_report(analysis_id):
    pdf_path = f"reports/report_{analysis_id}.pdf"
    if os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True, download_name=f"paper_review_{analysis_id}.pdf")
    
    # If not exists, try to generate from history
    for entry in analysis_history:
        if entry['id'] == analysis_id:
            try:
                generate_pdf_report(entry['report'], pdf_path)
                if os.path.exists(pdf_path):
                    return send_file(pdf_path, as_attachment=True, download_name=f"paper_review_{analysis_id}.pdf")
            except Exception as e:
                print(f"Error generating PDF on download: {e}")
    
    return jsonify({'error': 'Report not found or PDF generation failed'}), 404

@app.route('/clear_history', methods=['POST'])
def clear_history():
    analysis_history.clear()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)