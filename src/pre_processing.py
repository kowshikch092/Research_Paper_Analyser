import re
import nltk
import spacy
import string
import textstat

from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

# Download once (safe even if already present)
nltk.download("punkt")
nltk.download("punkt_tab")
nltk.download("stopwords")

stop_words = set(stopwords.words("english"))

# Lazy-load spaCy (safer)
_nlp = None
def get_spacy_model():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp



def preprocess_research_paper_text(raw_text: str):
    if raw_text is None:
        raise ValueError("Input text is None")

    # ---------------------------
    # 1. Basic cleaning
    # ---------------------------
    text = raw_text


    text = re.sub(r'digital object identifier.*', '', text, flags=re.I)
    text = re.sub(r'received.*?version.*?\.', '', text, flags=re.I)
    text = re.sub(r'figure\s*\d+.*', '', text, flags=re.I)
    text = re.sub(r'volume\s*\d+.*?\d+', '', text, flags=re.I)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\[[0-9]+\]', '', text)      # remove citations [1]
    text = re.sub(r'\(.?\d{4}.?\)', '', text)
    text = re.sub(r'\n+', '\n', text)
    translator=str.maketrans(" "," ",string.punctuation)
    text=text.translate(translator)
    text = re.sub(r'\s+', ' ', text).strip()

    # ---------------------------
    # 2. Sentence segmentation
    # ---------------------------
    sentences = sent_tokenize(text)

    # ---------------------------
    # 3. Tokenization 
    tokens = []
    for sent in sentences:
        words = word_tokenize(sent)
        words = [w for w in words]
        tokens.extend(words)

   

    # ---------------------------
    # 5. Final output
    # ---------------------------
    cleaned_text = " ".join(tokens)

    return cleaned_text


