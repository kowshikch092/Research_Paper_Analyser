import os
from src.extractortext import extract_text_images_from_pdf
from src.pre_processing import preprocess_research_paper_text
from src.extract_sections_wise import extract_sections, debug_extraction
from src.writing_quality import analyze_writing_quality
from src.section_analysis import print_section_analysis_report
from src.novelty_scibert_corpus import build_corpus_embeddings, compute_novelty_against_corpus, aggregate_novelty
from src.final_report import generate_final_report, print_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pdf_path = os.path.join(BASE_DIR, "data", "sample.pdf")

# Step 1: Extract raw text from PDF
print("Step 1: Extracting text from PDF...")
raw_text = extract_text_images_from_pdf(pdf_path)
# Step 2: Preprocess the text
print("Step 2: Preprocessing text...")
preprocessed_text = preprocess_research_paper_text(raw_text)

# Debug: show what's being detected
print("\nDebug extraction patterns:")
debug_extraction(preprocessed_text)

sec = extract_sections(preprocessed_text)
print("\n=== EXTRACTED SECTIONS ===")
print(f"Total sections found: {len(sec)}")

# Step 3: Analyze section structure and detect weak sections
print_section_analysis_report(sec)

# Step 4: Analyze writing quality (readability, grammar, style, coherence) per section
print("\n=== WRITING QUALITY BY SECTION ===")
analysis = analyze_writing_quality(sec)
print(analysis)
#What education level is needed to understand this?

# Step 5: Build/load corpus embeddings and compute novelty vs corpus
print("\n=== NOVELTY AGAINST CORPUS (SciBERT) ===")
try:
	corpus_emb = build_corpus_embeddings(corpus_dir="data/cropus", cache_path="data/corpus_embeddings.pkl")
	novelty_map = compute_novelty_against_corpus(sec, corpus_emb, method="max")
	for sname, score in novelty_map.items():
		print(f"  - {sname}: Novelty = {score}/100")
	overall = aggregate_novelty(novelty_map)
	print(f"\nOverall novelty score: {overall}/100")
except Exception as e:
	print(f"Could not compute corpus novelty: {e}")

# Step 6: Generate final review report with suggestions and scores
try:
	# For section_analysis data structure, reuse analyze_section_structure if available
	# We already printed section structure via print_section_analysis_report; load minimal structure
	# Reconstruct minimal section_analysis dict
	from src.section_analysis import analyze_section_structure
	section_struct = analyze_section_structure(sec)

	report = generate_final_report(analysis, section_struct, novelty_map if 'novelty_map' in locals() else {})
	print_report(report)
except Exception as e:
	print(f"Could not generate final report: {e}")
