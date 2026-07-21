# FSOT law audit — linguistics / translation path

**Date:** 2026-07-21  
**Archive master:** `I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\fsot_compute.py`  
**Product:** Ada/SPARK `pflt_main.exe` + Python data factory  

## Authority pin

| Check | Result |
|-------|--------|
| SHA-256 of archive `fsot_compute.py` | `d1d38a185487b452e470ac68ece2eb45aeb1ca9ce25fc9bf9564c19633ffbe70` |
| Prefix | **D1D38A** |
| Ada `PFLT_Authority.Expected_Digest` | matches full digest |
| Live pin in product | `authority_ok` / `live_pin` |

## Formula (no free fit knobs)

\[
S = K(T_1 + T_2 + T_3)
\]

- Seeds: \(\pi, e, \varphi, \gamma, G_{\mathrm{Catalan}}\)  
- Layer-1/2 constants derived only from seeds (see archive §1–§3)  
- **No ad-hoc** \(\exp(-\eta)/m_{\mathrm{pl}}\) damping found in scalar engine  

### Term structure (archive = Ada = PFLT Python)

| Term | Role |
|------|------|
| **T1** | Observer-modulated base: \(NP/\sqrt{D}\), cos/exp/growth, \(D\)-scale, optional quirk if observed |
| **T2** | Linear modulation: `scale * amplitude + trend_bias` |
| **T3** | Valve × acoustic × phase |
| **S** | \(K \times (T1+T2+T3)\) |

## Cross-verify (archive vs `PFLT_FSOT_2_1_aligned.compute_S_D_chaotic`)

| Domain inputs | Archive \(S\) | PFLT Python \(S\) | \|diff\| |
|---------------|---------------|-------------------|---------|
| Linguistic (D=12, obs) | 0.6513247618849 | 0.6513247618849 | **0** |
| Cosmological (D=25) | −0.5024559462100 | −0.5024559462100 | **0** |
| Historical (D=21, obs) | 0.6325783360136 | 0.6325783360136 | **0** |

Ada converse linguistic panel reports the same \(S \approx 0.651324761884897\).

## How law touches linguistics (not ad-hoc)

| Layer | Uses law? | Notes |
|-------|-----------|--------|
| Form→gloss densify / train_mass | **No free S** | Lexical densify; students never rewrite law |
| `PFLT_Translate` / morph peels | Surface map | Gloss inventory only |
| `PFLT_Converse` | **Yes** | Every turn: domain route → `Compute_Panel` → print \(S,T1,T2,T3\) + pin D1D38A |
| `PFLT_Cert` | **Yes** | Blocks ungrounded numeric law claims |
| Domain atlas / anchors | Inputs to panel | \(D_{\mathrm{eff}}\) etc. from domain catalog, not fitted BLEU knobs |
| M6 sentence BLEU | Surface metric | Phrase table climb; **not** a replacement for \(S=K(T1+T2+T3)\) |

## Ad-hoc scan result

| Location | Finding |
|----------|---------|
| Archive `compute_scalar` | Canonical; zero free params beyond seeds |
| Ada `PFLT_Scalar.Compute_Panel` | Structural match to archive |
| Ada `PFLT_Constants` | Frozen f64 seeds/derived constants |
| Python `compute_S_D_chaotic` | Bit-for-bit panel match on domain fixtures |
| M6 / densify / peels | **Not** alternate scalars; surface translation only |

**Conclusion:** Linguistics densifies knowledge **under** FSOT. Translation quality metrics do not redefine \(K\) or \(T_i\). Law remains master; students densify only.

## Coverage snapshot (at audit)

See `reports/gap_fill_verify.json` / `COMPETITOR_PUSH.md`:

- **113** language codes solidified (n≥200 for former thin set)  
- OPEN/PRODUCT form→gloss **~99.99%**  
- M6 sentence path: climbing offline (not neural parity)  
- Unique: pin + classical/visual + offline densify  
