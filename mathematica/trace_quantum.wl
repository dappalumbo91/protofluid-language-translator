(* Auto-generated FSOT 2.1 Math Microscope for PFLT *)
(* domain = quantum  built = 2026-07-18T13:04:07.542442+00:00 *)
(* Formula: S = K*(T1+T2+T3)  — zero free params beyond seeds *)
ClearAll[FSOTTrace, FSOTConstants, FSOTScalar];

FSOTConstants[] := Module[{},
  Association[
    "pi" -> 3.1415926535897931, (* Pi *)
    "e" -> 2.7182818284590451, (* E *)
    "phi" -> 1.6180339887498949, (* (1+Sqrt[5])/2 *)
    "gamma" -> 0.57721566490153287, (* EulerGamma *)
    "G_cat" -> 0.91596559417721901, (* Catalan *)
    "alpha" -> 0.00080829374141404048, (* Log[π]/(e·φ^13) *)
    "psi_con" -> 0.63212055882855767, (* 1-1/e *)
    "eta_eff" -> 0.46694220692425986, (* 1/(π-1) *)
    "beta" -> 2.6208669113332232e-17, (* Exp[-(π^π+(e-1))] *)
    "gamma_c" -> -0.42838851679220658, (* -Log[2]/φ *)
    "omega" -> 1.2941305780559662, (* Sin[π/e]·√2 *)
    "theta_s" -> 0.29089654054517305, (* Sin[ψ_con·η_eff] *)
    "poof" -> 0.1534822148944508, (* Exp[(-Log[π]/e)/(η_eff·Log[φ])] *)
    "c_eff" -> 0.95770220262056127, (* (1-poof·Sin[θ_s])·(1+0.01·G/(π·φ)) *)
    "a_bleed" -> 1.046973630587551, (* Sin[π/e]·φ/√2 *)
    "p_var" -> 0.9579871226722757, (* -Cos[θ_s+π] *)
    "b_in" -> 0.78794079227644354, (* c_eff·(1-Sin[θ_s]/φ) *)
    "a_in" -> 1.6668538450045731, (* a_bleed·(1+Cos[θ_s]/φ) *)
    "suction" -> 0.14703398542810284, (* poof·(-Cos[θ_s-π]) *)
    "chaos" -> -0.33102418261048183, (* γ_c/ω *)
    "p_base" -> 0.21234577623937842, (* γ/e *)
    "p_new" -> 0.30030227667037146, (* p_base·√2 *)
    "c_factor" -> 0.28760015181918397, (* c_eff·p_new *)
    "K" -> 0.42022166416069667, (* φ·(γ/e)·√2/Log[π]·0.99 *)
    "end" -> True
  ]];

FSOTTrace[] := Module[{steps = {}, c, add,
  N = 1;
  P = 1;
  D_eff = 6;
  recent_hits = 0;
  delta_psi = 1;
  delta_theta = 1;
  rho = 1;
  scale = 1;
  amplitude = 1;
  trend_bias = 0;
  observed = True;
  c = FSOTConstants[];
  add[id_, val_] := AppendTo[steps, {id, val}];
  (* --- reconstruct T1/T2/T3 from constants + inputs --- *)
  phi = c["phi"]; e = c["e"]; pi = c["pi"];
  alpha = c["alpha"]; psiCon = c["psi_con"]; etaEff = c["eta_eff"];
  beta = c["beta"]; thetaS = c["theta_s"]; poof = c["poof"];
  cEff = c["c_eff"]; aBleed = c["a_bleed"]; pVar = c["p_var"];
  bIn = c["b_in"]; aIn = c["a_in"]; suction = c["suction"];
  chaos = c["chaos"]; pNew = c["p_new"]; cFactor = c["c_factor"];
  k = c["K"]; gamma = c["gamma"];
  growth = Exp[alpha*(1 - recent_hits/N)*gamma/phi]; add["growth", growth];
  npSqrt = N*P/Sqrt[D_eff]; add["np_sqrtD", npSqrt];
  cosPsi = Cos[(psiCon + delta_psi)/etaEff]; add["cos_psi", cosPsi];
  expD = Exp[-alpha*recent_hits/N + rho + bIn*delta_psi]; add["exp_damp", expD];
  coh = 1 + growth*cEff; add["coh_term", coh];
  base = npSqrt*cosPsi*expD*coh; add["base", base];
  dScale = 1 + pNew*Log[D_eff/25]; add["d_scale", dScale];
  t1 = base*dScale;
  qm = 1;
  If[observed, qm = Exp[cFactor*pVar]*Cos[delta_psi + pVar]; t1 = t1*qm];
  add["quirk_mod", qm]; add["T1", t1];
  t2 = scale*amplitude + trend_bias; add["T2", t2];
  chaosMod = 1 + chaos*(D_eff - 25)/25; add["chaos_mod", chaosMod];
  poofMod = 1 + poof*Cos[thetaS + Pi] + suction*Sin[thetaS]; add["poof_mod", poofMod];
  valve = beta*Cos[delta_psi]*npSqrt*chaosMod*poofMod; add["valve", valve];
  acoustic = 1 + (aBleed*Sin[delta_theta]^2)/phi + (aIn*Cos[delta_theta]^2)/phi; add["acoustic", acoustic];
  phase = 1 + bIn*pVar; add["phase", phase];
  t3 = valve*acoustic*phase; add["T3", t3];
  raw = t1 + t2 + t3; add["raw", raw];
  S = k*raw; add["S", S];
  Association["domain" -> "quantum", "S" -> S, "T1" -> t1, "T2" -> t2, "T3" -> t3, "steps" -> steps]
];

(* Python microscope reference panel for cross-check *)
FSOTPythonPanel = <|"S" -> 0.95550630010271964, "T1" -> 1.2738149448128526, "T2" -> 1, "T3" -> 1.9990920171588205e-17|>;
FSOTDiff[] := Module[{m = FSOTTrace[]},
  Association["dS" -> Abs[m["S"] - FSOTPythonPanel["S"]],
    "dT1" -> Abs[m["T1"] - FSOTPythonPanel["T1"]],
    "dT2" -> Abs[m["T2"] - FSOTPythonPanel["T2"]],
    "dT3" -> Abs[m["T3"] - FSOTPythonPanel["T3"]]]];

(* Usage: FSOTTrace[]  or  FSOTDiff[] *)
