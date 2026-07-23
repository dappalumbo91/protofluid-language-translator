# FSOT seed-only derive — linguistics domain

**Built:** 2026-07-23T23:31:02.256508+00:00  
**Pin D1D38A:** **True**  
**Formula:** \(S = K(T_1+T_2+T_3)\)  
**No free parameters · no LLM judge · no ad-hoc knobs**

| System | sacreBLEU |
|--------|----------:|
| **FSOT_product_S** | **36.83** |
| FSOT_product_lin | 36.85 |
| NLLB-3.3B gen (student) | 36.79 |
| DeepL mid | ~40 |

**Best FSOT:** FSOT_product_lin **36.85** · vs student gen gap **-0.06** · vs DeepL mid **3.15**

## Seeds / domain

- K=0.420222 · φ=1.618034 · e=2.718282 · C_eff=0.957702
- D_eff=12.0 (archive domain table) · breath target φ·e=4.3983
- Golden split for P: φ/(1+φ) on NLL rank, 1/(1+φ) on gen rank

## Puzzle study (correct merges)

{
  "n_clear_gold": 1344,
  "mean_S_when_hyp_good": 0.8159725971868903,
  "mean_S_when_hyp_worst": 0.7030231342730047,
  "mean_T1_good": 0.3831771584789129,
  "mean_T1_worst": 0.29187385771560104,
  "note": "When a candidate already aligns with gold (sb\u22650.45), observe its panel. Good hyps should show higher S than worst in same pool if the map is right. No free-fit \u2014 diagnostic for arranging seeds only.",
  "S_separation": 0.11294946291388563
}

Good hyp should sit higher in S than worst in the same pool if the seed map is arranged correctly. Use that separation to refine the *arrangement*, not free parameters.

## Law

Candidates from students. **FSOT ranks.** Stagnation comes from hacks; growth comes from better seed arrangement.
