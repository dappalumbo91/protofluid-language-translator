# FSOT derive rank — \(S=K(T_1+T_2+T_3)\)

**Built:** 2026-07-23T23:23:24.559258+00:00  
**Pin D1D38A:** **True**  
**K:** 0.42022166 · **mean S:** 0.660844  

| System | sacreBLEU | Role |
|--------|----------:|------|
| **FSOT_product_S** | **36.40** | **argmax archive S** |
| FSOT_product_lin | 36.43 | T1·C_EFF + T2 + T3/Φ |
| NLLB-3.3B gen max | 36.79 | student only |
| DeepL mid bar | ~40 | external |

**Best FSOT product:** FSOT_product_lin **36.43** · gap to DeepL mid-40: **3.57**  
**S-pick = gen-pick:** 36.73% of sentences  

## Derivation

```
observables (enc_norm, tf_nll, spm_*, lengths, gen)
  → ScalarInput (N, P, δψ, δθ, ρ, scale, amplitude, …)
  → T1, T2, T3 from archive term structure
  → S = K · (T1 + T2 + T3)
  → pick argmax S
```

Students supply candidates. **The formula ranks.** No Qwen. No free-fit of K.
