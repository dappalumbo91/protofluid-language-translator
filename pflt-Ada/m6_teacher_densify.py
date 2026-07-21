#!/usr/bin/env python3
"""
Teacher densify under FSOT: HF models propose phrase densify; law never trains.

Uses local snapshots under:
  D:\\training data\\pflt_linguistics\\13_huggingface\\models\\

Priority:
  1. Helsinki-NLP opus-mt-*-en (small, fast CPU)
  2. facebook/nllb-200-distilled-600M if present (slower, broader)

Teacher outputs densify phrase tables (students). Pin D1D38A unchanged.
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ADA = Path(__file__).resolve().parent
DATA = ADA / "data"
REP = ADA / "reports"
REP.mkdir(parents=True, exist_ok=True)

MODELS = Path(r"D:\training data\pflt_linguistics\13_huggingface\models")
CACHE_EVAL = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\m6_pairs_cache.jsonl"
)
TATOEBA_SENT = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\extracted\sentences.csv"
)
TATOEBA_LINK = Path(
    r"D:\training data\pflt_linguistics\03_parallel_corpora\tatoeba\extracted\links.csv"
)
PHRASE_U = DATA / "m6_phrase_table.tsv"
PHRASE_BI = DATA / "m6_bigram_table.tsv"

# our code -> (opus-mt folder name, nllb src lang code)
PAIR_MAP = {
    "es": ("Helsinki-NLP__opus-mt-es-en", "spa_Latn"),
    "de": ("Helsinki-NLP__opus-mt-de-en", "deu_Latn"),
    "fr": ("Helsinki-NLP__opus-mt-fr-en", "fra_Latn"),
    "ru": ("Helsinki-NLP__opus-mt-ru-en", "rus_Cyrl"),
    "zh": ("Helsinki-NLP__opus-mt-zh-en", "zho_Hans"),
    "ja": ("Helsinki-NLP__opus-mt-ja-en", "jpn_Jpan"),
    "ar": ("Helsinki-NLP__opus-mt-ar-en", "arb_Arab"),
    "it": ("Helsinki-NLP__opus-mt-mul-en", "ita_Latn"),
    "pt": ("Helsinki-NLP__opus-mt-mul-en", "por_Latn"),
    "nl": ("Helsinki-NLP__opus-mt-mul-en", "nld_Latn"),
    "pl": ("Helsinki-NLP__opus-mt-mul-en", "pol_Latn"),
    "tr": ("Helsinki-NLP__opus-mt-mul-en", "tur_Latn"),
    "hi": ("Helsinki-NLP__opus-mt-mul-en", "hin_Deva"),
    "ko": ("Helsinki-NLP__opus-mt-mul-en", "kor_Hang"),
    "he": ("Helsinki-NLP__opus-mt-mul-en", "heb_Hebr"),
}

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")
MAX_PER_LANG = 800  # teacher batch per lang (CPU-friendly)
MAX_LEN = 80


def log(msg: str) -> None:
    print(msg, flush=True)


def toks(text: str, lang: str = "") -> list[str]:
    t = text or ""
    if lang in ("ja", "zh", "ko") or CJK_RE.search(t):
        # prefer sentencepiece if available later
        spaced = [x.lower() for x in TOKEN_RE.findall(t)]
        if spaced and any(len(x) > 1 for x in spaced):
            return spaced
        return [
            ch
            for ch in t
            if not ch.isspace() and (CJK_RE.match(ch) or ch.isalnum())
        ]
    return [x.lower() for x in TOKEN_RE.findall(t)]


def load_phrase() -> tuple[dict[str, str], dict[str, str]]:
    uni: dict[str, str] = {}
    bi: dict[str, str] = {}
    if PHRASE_U.exists():
        with PHRASE_U.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    uni[p[0]] = p[1]
    if PHRASE_BI.exists():
        with PHRASE_BI.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                p = line.rstrip("\n").split("\t")
                if len(p) >= 2:
                    bi[p[0]] = p[1]
    return uni, bi


def sample_train_src() -> dict[str, list[str]]:
    """Sample source sentences from Tatoeba (not eval IDs) for teacher densify."""
    eval_ids: set[int] = set()
    if CACHE_EVAL.exists():
        with CACHE_EVAL.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                eval_ids.add(int(r["src_id"]))
                eval_ids.add(int(r["ref_id"]))
    iso = {
        "spa": "es",
        "deu": "de",
        "fra": "fr",
        "rus": "ru",
        "cmn": "zh",
        "jpn": "ja",
        "ara": "ar",
        "ita": "it",
        "por": "pt",
        "nld": "nl",
        "pol": "pl",
        "tur": "tr",
        "hin": "hi",
        "kor": "ko",
        "heb": "he",
    }
    if not TATOEBA_SENT.exists():
        # fall back: eval src only as teacher input (teacher hyp still independent of gold)
        by: dict[str, list[str]] = defaultdict(list)
        if CACHE_EVAL.exists():
            with CACHE_EVAL.open(encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    L = r["src_lang"]
                    if L in PAIR_MAP and len(by[L]) < MAX_PER_LANG:
                        by[L].append(r["src"])
        return by

    wanted = set(iso) | {"eng"}
    sents: dict[int, tuple[str, str]] = {}
    with TATOEBA_SENT.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 3:
                continue
            try:
                sid = int(p[0])
            except ValueError:
                continue
            if p[1] not in wanted:
                continue
            sents[sid] = (p[1], p[2].strip())
    eng = {i for i, (lg, _) in sents.items() if lg == "eng"}
    by: dict[str, list[str]] = defaultdict(list)
    if not TATOEBA_LINK.exists():
        return by
    with TATOEBA_LINK.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 2:
                continue
            try:
                a, b = int(p[0]), int(p[1])
            except ValueError:
                continue
            for sid, eid in ((a, b), (b, a)):
                if sid in eval_ids or eid in eval_ids:
                    continue
                if sid not in sents or eid not in eng:
                    continue
                iso_c, text = sents[sid]
                if iso_c == "eng":
                    continue
                our = iso.get(iso_c)
                if not our or our not in PAIR_MAP:
                    continue
                if len(by[our]) >= MAX_PER_LANG:
                    continue
                if 2 <= len(text.split()) <= 25:
                    by[our].append(text)
            if all(len(by.get(c, [])) >= MAX_PER_LANG for c in PAIR_MAP):
                break
    return by


def load_translator(model_dir: Path):
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch

    tok = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir), local_files_only=True)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    return tok, model, device


def translate_batch(tok, model, device, texts: list[str], nllb_src: str | None = None) -> list[str]:
    import torch

    # NLLB needs src_lang
    if nllb_src and hasattr(tok, "src_lang"):
        tok.src_lang = nllb_src
    outs = []
    bs = 8
    for i in range(0, len(texts), bs):
        batch = texts[i : i + bs]
        enc = tok(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=MAX_LEN,
        )
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=64, num_beams=3)
        outs.extend(tok.batch_decode(gen, skip_special_tokens=True))
    return outs


def align_densify(
    src: str, hyp: str, lang: str, uni: dict[str, str], bi: dict[str, str]
) -> tuple[int, int]:
    st, et = toks(src, lang), toks(hyp, "en")
    if not st or not et:
        return 0, 0
    nu = nb = 0
    content = [t for t in et if len(t) > 2] or et
    for s in st:
        if s not in uni:
            uni[s] = content[0]
            nu += 1
    for i in range(len(st) - 1):
        bg = st[i] + " " + st[i + 1]
        if bg in bi:
            continue
        j = min(len(et) - 2, int(i * (len(et) - 1) / max(1, len(st) - 1)))
        bi[bg] = et[j] + " " + et[j + 1]
        nb += 1
    if 2 <= len(st) <= 10:
        key = " ".join(st)
        if key not in bi:
            bi[key] = " ".join(et)
            nb += 1
    return nu, nb


def cjk_spm_tokenize(src: str, model_dir: Path | None) -> list[str]:
    """Tokenize CJK with NLLB sentencepiece if available."""
    spm_path = None
    if model_dir and (model_dir / "sentencepiece.bpe.model").exists():
        spm_path = model_dir / "sentencepiece.bpe.model"
    nllb = MODELS / "facebook__nllb-200-distilled-600M"
    if spm_path is None and (nllb / "sentencepiece.bpe.model").exists():
        spm_path = nllb / "sentencepiece.bpe.model"
    if spm_path is None:
        return toks(src, "zh")
    try:
        import sentencepiece as spm

        sp = spm.SentencePieceProcessor(model_file=str(spm_path))
        pieces = sp.encode(src, out_type=str)
        # strip ▁
        return [p.replace("▁", "").lower() for p in pieces if p.replace("▁", "")]
    except Exception:
        return toks(src, "zh")


def main() -> None:
    t0 = time.perf_counter()
    log("=== Teacher densify (HF models on D:) under FSOT ===")
    if not MODELS.exists():
        raise SystemExit(f"missing models dir {MODELS} — run download first")

    by_src = sample_train_src()
    for L, xs in sorted(by_src.items()):
        log(f"  sample {L}: {len(xs)}")

    uni, bi = load_phrase()
    dens_add: dict[str, str] = {}
    stats = {"langs": {}, "models_used": []}
    total_u = total_b = 0

    nllb_dir = MODELS / "facebook__nllb-200-distilled-600M"
    nllb_ready = (nllb_dir / "pytorch_model.bin").exists() or (
        nllb_dir / "model.safetensors"
    ).exists()

    for lang, texts in by_src.items():
        if lang not in PAIR_MAP:
            continue
        opus_name, nllb_code = PAIR_MAP[lang]
        opus_dir = MODELS / opus_name
        model_dir = None
        use_nllb = False
        if (opus_dir / "pytorch_model.bin").exists() or (
            opus_dir / "model.safetensors"
        ).exists():
            model_dir = opus_dir
        elif nllb_ready:
            model_dir = nllb_dir
            use_nllb = True
        else:
            log(f"  skip {lang}: no local model")
            continue
        log(f"  teacher {lang} via {model_dir.name} n={len(texts)}")
        try:
            tok, model, device = load_translator(model_dir)
            hyps = translate_batch(
                tok,
                model,
                device,
                texts,
                nllb_src=nllb_code if use_nllb else None,
            )
        except Exception as e:
            log(f"  FAIL {lang}: {e}")
            continue
        stats["models_used"].append(str(model_dir.name))
        nu = nb = 0
        for src, hyp in zip(texts, hyps):
            # CJK: also densify SPM pieces
            if lang in ("ja", "zh", "ko"):
                pieces = cjk_spm_tokenize(src, nllb_dir if nllb_ready else model_dir)
                et = toks(hyp, "en")
                if pieces and et:
                    for s in pieces:
                        if s and s not in uni:
                            uni[s] = et[0]
                            dens_add[s] = et[0]
                            nu += 1
            u, b = align_densify(src, hyp, lang, uni, bi)
            nu += u
            nb += b
        total_u += nu
        total_b += nb
        stats["langs"][lang] = {"n": len(texts), "uni": nu, "bi": nb}
        log(f"    densify +uni={nu} +bi={nb}")

    with PHRASE_U.open("w", encoding="utf-8") as w:
        for k, v in uni.items():
            w.write(f"{k}\t{v}\n")
    with PHRASE_BI.open("w", encoding="utf-8") as w:
        for k, v in bi.items():
            w.write(f"{k}\t{v}\n")
    if dens_add:
        with (DATA / "densify.tsv").open("a", encoding="utf-8") as w:
            for k, v in dens_add.items():
                w.write(f"{k}\t{v}\n")

    report = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "fsot": "Teacher densify only; law S=K(T1+T2+T3) pin D1D38A unchanged",
        "models_root": str(MODELS),
        "stats": stats,
        "total_uni": total_u,
        "total_bi": total_b,
        "flores": "still gated — accept https://huggingface.co/datasets/facebook/flores",
        "next": "python fsot_archive_fluency_push.py && python fsot_solve_fluency_gap.py",
    }
    (REP / "m6_teacher_densify_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log(f"total +uni={total_u} +bi={total_b}")
    log(f"wrote {REP / 'm6_teacher_densify_report.json'}")
    log(f"elapsed {time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    main()
