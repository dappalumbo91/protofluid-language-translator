(* FSOT 2.1 Symbolic Math Microscope — rebuild from seeds *)
(* Formula: S = K*(T1 + T2 + T3)  — zero free params beyond seeds *)
ClearAll[FSOTSeeds, FSOTDerived, FSOTScalarSym, FSOTPrintPathway];

FSOTSeeds[] := Association[
  "pi" -> Pi,
  "e"  -> E,
  "phi" -> (1 + Sqrt[5])/2,
  "gamma" -> EulerGamma,
  "G_cat" -> Catalan
];

FSOTDerived[] := Module[{s = FSOTSeeds[], pi, e, phi, gamma, G},
  pi = s["pi"]; e = s["e"]; phi = s["phi"]; gamma = s["gamma"]; G = s["G_cat"];
  Association[
    "alpha"    -> Log[pi]/(e*phi^13),
    "psi_con"  -> 1 - 1/e,
    "eta_eff"  -> 1/(pi - 1),
    "beta"     -> Exp[-(pi^pi + (e - 1))],
    "gamma_c"  -> -Log[2]/phi,
    "omega"    -> Sin[pi/e]*Sqrt[2],
    "theta_s"  -> Sin[(1 - 1/e)*(1/(pi - 1))],
    "poof"     -> Exp[(-Log[pi]/e)/((1/(pi - 1))*Log[phi])],
    "c_eff"    -> (1 - Exp[(-Log[pi]/e)/((1/(pi - 1))*Log[phi])]*Sin[Sin[(1-1/e)*(1/(pi-1))]])
                   *(1 + 0.01*G/(pi*phi)),
    "a_bleed"  -> Sin[pi/e]*phi/Sqrt[2],
    "p_var"    -> -Cos[Sin[(1-1/e)*(1/(pi-1))] + pi],
    "b_in"     -> With[{ce = (1 - Exp[(-Log[pi]/e)/((1/(pi-1))*Log[phi])]*Sin[Sin[(1-1/e)*(1/(pi-1))]])*(1+0.01*G/(pi*phi)),
                        ts = Sin[(1-1/e)*(1/(pi-1))]}, ce*(1 - Sin[ts]/phi)],
    "a_in"     -> With[{ab = Sin[pi/e]*phi/Sqrt[2], ts = Sin[(1-1/e)*(1/(pi-1))]}, ab*(1 + Cos[ts]/phi)],
    "suction"  -> With[{pf = Exp[(-Log[pi]/e)/((1/(pi-1))*Log[phi])], ts = Sin[(1-1/e)*(1/(pi-1))]}, pf*(-Cos[ts - pi])],
    "chaos"    -> (-Log[2]/phi)/(Sin[pi/e]*Sqrt[2]),
    "p_base"   -> gamma/e,
    "p_new"    -> (gamma/e)*Sqrt[2],
    "c_factor" -> With[{ce = (1 - Exp[(-Log[pi]/e)/((1/(pi-1))*Log[phi])]*Sin[Sin[(1-1/e)*(1/(pi-1))]])*(1+0.01*G/(pi*phi))},
                    ce*(gamma/e)*Sqrt[2]],
    "K"        -> phi*(gamma/e)*Sqrt[2]/Log[pi]*0.99
  ]
];

(* Numeric domain scalar: same structure as Python microscope *)
FSOTScalarSym[opts:OptionsPattern[{
  N->1., P->1., DEff->12., RecentHits->0., DeltaPsi->0.8, DeltaTheta->1.,
  Rho->1., Scale->1., Amplitude->1., TrendBias->0., Observed->True
}]] := Module[{
  d = FSOTDerived[], s = FSOTSeeds[],
  n, p, de, hits, dp, dt, rho, sc, amp, tb, obs,
  growth, npSqrt, cosPsi, expD, coh, base, dScale, t1, qm, t2,
  chaosMod, poofMod, valve, acoustic, phase, t3, raw, S, steps = {}
  },
  n = OptionValue[N]; p = OptionValue[P]; de = OptionValue[DEff];
  hits = OptionValue[RecentHits]; dp = OptionValue[DeltaPsi]; dt = OptionValue[DeltaTheta];
  rho = OptionValue[Rho]; sc = OptionValue[Scale]; amp = OptionValue[Amplitude];
  tb = OptionValue[TrendBias]; obs = OptionValue[Observed];
  growth = Exp[d["alpha"]*(1 - hits/n)*s["gamma"]/s["phi"]];
  npSqrt = n*p/Sqrt[de];
  cosPsi = Cos[(d["psi_con"] + dp)/d["eta_eff"]];
  expD = Exp[-d["alpha"]*hits/n + rho + d["b_in"]*dp];
  coh = 1 + growth*d["c_eff"];
  base = npSqrt*cosPsi*expD*coh;
  dScale = 1 + d["p_new"]*Log[de/25];
  t1 = base*dScale; qm = 1;
  If[obs, qm = Exp[d["c_factor"]*d["p_var"]]*Cos[dp + d["p_var"]]; t1 = t1*qm];
  t2 = sc*amp + tb;
  chaosMod = 1 + d["chaos"]*(de - 25)/25;
  poofMod = 1 + d["poof"]*Cos[d["theta_s"] + Pi] + d["suction"]*Sin[d["theta_s"]];
  valve = d["beta"]*Cos[dp]*npSqrt*chaosMod*poofMod;
  acoustic = 1 + (d["a_bleed"]*Sin[dt]^2)/s["phi"] + (d["a_in"]*Cos[dt]^2)/s["phi"];
  phase = 1 + d["b_in"]*d["p_var"];
  t3 = valve*acoustic*phase;
  raw = t1 + t2 + t3; S = d["K"]*raw;
  Association[
    "K" -> N[d["K"]], "T1" -> N[t1], "T2" -> N[t2], "T3" -> N[t3],
    "raw" -> N[raw], "S" -> N[S], "quirk_mod" -> N[qm], "growth" -> N[growth]
  ]
];

FSOTPrintPathway[] := Module[{d = N[FSOTDerived[]], panel},
  Print["=== FSOT Symbolic Microscope (numeric eval of seeds→derived) ==="];
  Print["K = ", d["K"]];
  Print["psi_con, eta_eff, c_eff, p_var = ", d["psi_con"], ", ", d["eta_eff"], ", ", d["c_eff"], ", ", d["p_var"]];
  panel = FSOTScalarSym[DEff -> 12., DeltaPsi -> 0.8, Observed -> True];
  Print["linguistic panel: ", panel];
  panel
];

(* Usage:
     Get["…/FSOT_Symbolic_Microscope.wl"]
     FSOTPrintPathway[]
     FSOTScalarSym[DEff->6., Observed->True]  (* quantum-like *)
*)
