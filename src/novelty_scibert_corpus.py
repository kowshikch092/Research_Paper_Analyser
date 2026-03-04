
"""
SciBERT corpus novelty module (Hugging Face transformers implementation).

This file replaces the previous implementation and uses the Hugging Face
`allenai/scibert_scivocab_uncased` model for section-wise embeddings.

Features:
- Section-wise SciBERT embeddings with chunking and mean pooling
- Build/cache corpus embeddings from `data/cropus/` (PDFs)
- Compute section-wise novelty against the corpus (0-100)
- Simple aggregation to an overall novelty score

Requirements: `transformers`, `torch`, `scikit-learn`
"""

from typing import Dict, List, Tuple
import os
import pickle
import numpy as np

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    _HAS_TRANSFORMERS = True
except Exception:
    _HAS_TRANSFORMERS = False

from sklearn.metrics.pairwise import cosine_similarity
from src.extractortext import extract_text_images_from_pdf
from src.extract_sections_wise import extract_sections


CACHE_DEFAULT = "data/corpus_embeddings.pkl"


def _mean_pooling(model_output, attention_mask):
    token_embeddings = model_output.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask


def embed_sections_scibert(sections: Dict[str, str], model_name: str = "allenai/scibert_scivocab_uncased", device: str = None, max_length: int = 256) -> Dict[str, np.ndarray]:
    """Embed each section with SciBERT and return a mapping section->embedding.

    The function chunks long sections (by tokenizer tokens), encodes each chunk,
    mean-pools token embeddings per chunk and averages chunk embeddings to
    produce a single vector per section.
    """
    if not _HAS_TRANSFORMERS:
        raise RuntimeError("transformers and torch are required for SciBERT embeddings")

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device)
    model.eval()

    dim = model.config.hidden_size
    embeddings: Dict[str, np.ndarray] = {}

    for name, text in sections.items():
        txt = (text or "").strip()
        if not txt:
            embeddings[name] = np.zeros(dim, dtype=float)
            continue

        # Naive sentence-like fragments
        fragments = [s.strip() for s in txt.replace('\n', ' ').split('. ') if s.strip()]
        if not fragments:
            fragments = [txt]

        # Group fragments into chunks by token length
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0
        for frag in fragments:
            toks = tokenizer.tokenize(frag)
            l = len(toks)
            if current_len + l > max_length and current:
                chunks.append('. '.join(current))
                current = [frag]
                current_len = l
            else:
                current.append(frag)
                current_len += l
        if current:
            chunks.append('. '.join(current))

        chunk_embs: List[np.ndarray] = []
        for chunk in chunks:
            inputs = tokenizer(chunk, return_tensors="pt", truncation=True, padding=True, max_length=max_length)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                out = model(**inputs)
                pooled = _mean_pooling(out, inputs["attention_mask"])  # (1, dim)
                emb = pooled[0].cpu().numpy()
                chunk_embs.append(emb)

        if chunk_embs:
            sec_emb = np.mean(np.vstack(chunk_embs), axis=0)
        else:
            sec_emb = np.zeros(dim, dtype=float)

        embeddings[name] = sec_emb

    return embeddings


def build_corpus_embeddings(corpus_dir: str = "data/cropus", cache_path: str = CACHE_DEFAULT, model_name: str = "allenai/scibert_scivocab_uncased") -> Dict[str, Dict[str, np.ndarray]]:
    """Build or load cached embeddings for all PDFs in `corpus_dir`.

    Returns: mapping paper_filename -> { section_name -> embedding }
    """
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                data = pickle.load(f)
            return data
        except Exception:
            pass

    if not _HAS_TRANSFORMERS:
        raise RuntimeError("transformers/torch required to build SciBERT embeddings")

    papers = [p for p in os.listdir(corpus_dir) if p.lower().endswith('.pdf')]
    corpus_emb: Dict[str, Dict[str, np.ndarray]] = {}

    for paper in papers:
        pdf_path = os.path.join(corpus_dir, paper)
        try:
            text = extract_text_images_from_pdf(pdf_path)
            sections = extract_sections(text)
            if not sections:
                sections = {"full_text": text}
            emb_map = embed_sections_scibert(sections, model_name=model_name)
            corpus_emb[paper] = emb_map
        except Exception:
            corpus_emb[paper] = {}

    os.makedirs(os.path.dirname(cache_path) or '.', exist_ok=True)
    with open(cache_path, "wb") as f:
        pickle.dump(corpus_emb, f)

    return corpus_emb


def _flatten_corpus_embeddings(corpus_emb: Dict[str, Dict[str, np.ndarray]]) -> Tuple[List[Tuple[str, str]], np.ndarray]:
    keys: List[Tuple[str, str]] = []
    mats: List[np.ndarray] = []
    for paper, secmap in corpus_emb.items():
        for secname, emb in secmap.items():
            keys.append((paper, secname))
            mats.append(emb)
    if mats:
        mat = np.vstack(mats)
    else:
        mat = np.zeros((0, 0))
    return keys, mat


def compute_novelty_against_corpus(target_sections: Dict[str, str], corpus_emb: Dict[str, Dict[str, np.ndarray]], method: str = "max", top_k: int = 3) -> Dict[str, float]:
    """Compute per-section novelty (0-100) of `target_sections` against `corpus_emb`.

    method: 'max' | 'topk' | 'avg'
    """
    keys, mat = _flatten_corpus_embeddings(corpus_emb)
    result: Dict[str, float] = {}
    if mat.size == 0:
        for s in target_sections.keys():
            result[s] = 100.0
        return result

    target_emb_map = embed_sections_scibert(target_sections)
    target_names = list(target_emb_map.keys())
    target_embs = np.vstack([target_emb_map[n] for n in target_names])

    sim = cosine_similarity(target_embs, mat)

    for i, name in enumerate(target_names):
        sims = sim[i]
        if sims.size == 0:
            rep_sim = 0.0
        else:
            if method == "max":
                rep_sim = float(np.max(sims))
            elif method == "topk":
                k = min(top_k, sims.size)
                rep_sim = float(np.mean(np.sort(sims)[-k:]))
            else:
                rep_sim = float(np.mean(sims))

        novelty = max(0.0, 1.0 - rep_sim) * 100.0
        result[name] = round(novelty, 2)

    return result


def aggregate_novelty(novelty_map: Dict[str, float], weights: Dict[str, float] = None) -> float:
    if not novelty_map:
        return 0.0
    names = list(novelty_map.keys())
    if weights:
        total_w = sum(weights.get(n, 1.0) for n in names)
        score = sum(novelty_map[n] * weights.get(n, 1.0) for n in names) / total_w
    else:
        score = sum(novelty_map.values()) / len(novelty_map)
    return round(float(score), 2)


if __name__ == "__main__":
    corpus_dir = "data/cropus"
    cache = "data/corpus_embeddings.pkl"
    try:
        corpus_emb = build_corpus_embeddings(corpus_dir=corpus_dir, cache_path=cache)
        target_pdf = "data/sample.pdf"
        txt = extract_text_images_from_pdf(target_pdf)
        target_sections = extract_sections(txt)
        if not target_sections:
            target_sections = {"full_text": txt}
        nov = compute_novelty_against_corpus(target_sections, corpus_emb)
        print("Per-section novelty:")
        for k, v in nov.items():
            print(f" - {k}: {v}")
        print("Overall:", aggregate_novelty(nov))
    except Exception as e:
        print("Error or missing dependencies:", e)
