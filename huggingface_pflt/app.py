"""
Hugging Face Space demo — PFLT form→gloss + FSOT linguistic panel.

Full multi-GB densify packs are NOT on the Space. Uses sample_densify.tsv.
Law: S = K*(T1+T2+T3) with frozen seed-derived constants (pin D1D38A culture).
"""
from __future__ import annotations

import math
from pathlib import Path

import gradio as gr

# --- FSOT 2.1 frozen f64 seeds/constants (match pflt-Ada PFLT_Constants) ---
PI = 3.141592653589793
E = 2.718281828459045
PHI = 1.618033988749895
GAMMA = 0.5772156649015329
ALPHA = 0.0008082937414140405
PSI_CON = 0.6321205588285577
ETA_EFF = 0.46694220692425986
BETA = 2.620866911333223e-17
THETA_S = 0.29089654054517305
POOF = 0.1534822148944508
C_EFF = 0.9577022026205613
A_BLEED = 1.046973630587551
P_VAR = 0.9579871226722757
B_IN = 0.7879407922764435
A_IN = 1.6668538450045731
SUCTION = 0.14703398542810284
CHAOS = -0.33102418261048183
P_NEW = 0.30030227667037146
C_FACTOR = 0.28760015181918397
K = 0.4202216641606967


def compute_panel(
    *,
    N: float = 1.0,
    P: float = 1.0,
    D_eff: float = 12.0,
    recent_hits: float = 0.0,
    delta_psi: float = 0.8,
    delta_theta: float = 1.0,
    rho: float = 1.0,
    scale: float = 1.0,
    amplitude: float = 1.0,
    trend_bias: float = 0.0,
    observed: bool = True,
) -> dict[str, float]:
    """Canonical S = K*(T1+T2+T3) — no free fit knobs."""
    growth = math.exp(ALPHA * (1.0 - recent_hits / N) * GAMMA / PHI)
    base = (
        (N * P / math.sqrt(D_eff))
        * math.cos((PSI_CON + delta_psi) / ETA_EFF)
        * math.exp(-ALPHA * recent_hits / N + rho + B_IN * delta_psi)
        * (1.0 + growth * C_EFF)
    )
    t1 = base * (1.0 + P_NEW * math.log(D_eff / 25.0))
    if observed:
        t1 *= math.exp(C_FACTOR * P_VAR) * math.cos(delta_psi + P_VAR)
    t2 = scale * amplitude + trend_bias
    valve = (
        BETA
        * math.cos(delta_psi)
        * (N * P / math.sqrt(D_eff))
        * (1.0 + CHAOS * (D_eff - 25.0) / 25.0)
        * (1.0 + POOF * math.cos(THETA_S + PI) + SUCTION * math.sin(THETA_S))
    )
    acoustic = (
        1.0
        + (A_BLEED * math.sin(delta_theta) ** 2) / PHI
        + (A_IN * math.cos(delta_theta) ** 2) / PHI
    )
    phase = 1.0 + B_IN * P_VAR
    t3 = valve * acoustic * phase
    raw = t1 + t2 + t3
    return {"S": K * raw, "T1": t1, "T2": t2, "T3": t3, "K": K, "D_eff": D_eff}


def load_lexicon(path: Path) -> dict[str, str]:
    store: dict[str, str] = {}
    if not path.exists():
        return store
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2 and p[0] and p[1]:
                store[p[0].strip().lower()] = p[1].strip()[:48]
    return store


LEX = load_lexicon(Path(__file__).parent / "sample_densify.tsv")


def resolve(tok: str) -> str:
    fl = tok.lower().strip()
    if not fl:
        return tok
    if fl in LEX:
        return LEX[fl]
    # progressive peels (longest stem)
    best = None
    best_len = 0
    if len(fl) >= 4:
        for drop in range(1, min(10, len(fl) - 1)):
            stem = fl[:-drop]
            if stem in LEX and len(stem) > best_len:
                best, best_len = LEX[stem], len(stem)
        for L in range(len(fl) - 1, 2, -1):
            pref = fl[:L]
            if pref in LEX and len(pref) > best_len:
                best, best_len = LEX[pref], len(pref)
    return best.split()[0] if best else f"[{tok}]"


def translate(text: str) -> tuple[str, str, str]:
    toks = [t for t in text.replace(",", " ").split() if t]
    if not toks:
        return "", "0%", ""
    outs = [resolve(t) for t in toks]
    mapped = sum(1 for o in outs if not o.startswith("["))
    cov = f"{100 * mapped / len(toks):.0f}%"
    panel = compute_panel()  # linguistic default
    law = (
        f"FSOT pin D1D38A · S=K(T1+T2+T3)\n"
        f"S={panel['S']:.12f}\n"
        f"T1={panel['T1']:.12f}  T2={panel['T2']:.12f}  T3={panel['T3']:.6e}\n"
        f"K={panel['K']:.12f}  D_eff={panel['D_eff']}\n"
        f"lexicon_sample_keys={len(LEX)} (demo only; full packs local)"
    )
    return " ".join(outs), cov, law


DEMO = """# Protofluid Language Translator · FSOT

**Law:** \(S = K(T_1+T_2+T_3)\) · pin **D1D38A**  
**Demo:** form→gloss surface from a *sample* densify pack (not full multi‑GB inventory).

Honest framing: not Google/DeepL neural BLEU parity. Offline densify under FSOT.
"""

with gr.Blocks(title="PFLT FSOT Translator") as demo:
    gr.Markdown(DEMO)
    inp = gr.Textbox(
        label="Input (any language surface tokens)",
        value="hola mundo aqua lingua",
        lines=2,
    )
    btn = gr.Button("Translate (form→gloss)", variant="primary")
    out = gr.Textbox(label="Surface gloss (EN-ish)", lines=2)
    cov = gr.Textbox(label="Token coverage", lines=1)
    law = gr.Textbox(label="FSOT linguistic panel", lines=6)
    btn.click(translate, inputs=inp, outputs=[out, cov, law])
    gr.Examples(
        examples=[
            ["hola mundo aqua lingua"],
            ["bonjour monde"],
            ["hallo welt"],
            ["ciao mondo"],
            ["merhaba dünya"],
            ["привет мир"],
            ["水"],
        ],
        inputs=inp,
    )
    gr.Markdown(
        "Source: [GitHub protofluid-language-translator]"
        "(https://github.com/dappalumbo91/protofluid-language-translator) · "
        "Full Ada binary + densify packs run offline under archive law."
    )

if __name__ == "__main__":
    demo.launch()
