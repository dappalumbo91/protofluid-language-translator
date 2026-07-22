theory PFLTGolden
  imports Main
begin

(* Auto-generated PFLT golden — formal/run_formal_asserts.py *)
definition golden_K :: real where "golden_K = 0.42022166416069667"
definition golden_phi :: real where "golden_phi = 1.6180339887498949"
definition golden_psi_con :: real where "golden_psi_con = 0.63212055882855767"
definition golden_c_eff :: real where "golden_c_eff = 0.95770220262056127"

definition golden_S_linguistic :: real where "golden_S_linguistic = 0.65132476188489685"
definition golden_S_historical :: real where "golden_S_historical = 0.63257833601362834"
definition golden_S_mythological :: real where "golden_S_mythological = 0.63257833601362834"
definition golden_S_quantum :: real where "golden_S_quantum = 0.95550630010271964"
definition golden_S_cosmological :: real where "golden_S_cosmological = -0.5024559462100433"

datatype trinary = SpinDown | Superposed | SpinUp

fun trinary_to_bits :: "trinary ⇒ nat" where
  "trinary_to_bits SpinDown = 0" |
  "trinary_to_bits Superposed = 1" |
  "trinary_to_bits SpinUp = 2"

fun trinary_of_bits :: "nat ⇒ trinary option" where
  "trinary_of_bits 0 = Some SpinDown" |
  "trinary_of_bits 1 = Some Superposed" |
  "trinary_of_bits 2 = Some SpinUp" |
  "trinary_of_bits _ = None"

lemma trinary_roundtrip: "trinary_of_bits (trinary_to_bits t) = Some t"
  by (cases t) simp_all

lemma golden_K_pos: "golden_K > 0"
  by (simp add: golden_K_def)

lemma golden_phi_gt1: "golden_phi > 1"
  by (simp add: golden_phi_def)

end
