with Ada.Numerics.Long_Elementary_Functions;
with PFLT_Constants;

package body PFLT_Scalar
  with SPARK_Mode => On
is
   package EF renames Ada.Numerics.Long_Elementary_Functions;
   use PFLT_Constants;

   function Compute_Panel (Input : Scalar_Input) return Scalar_Panel is
      N_m  : constant Long_Float := Input.N;
      P_m  : constant Long_Float := Input.P;
      D_m  : constant Long_Float := Input.D_Eff;
      Hits : constant Long_Float := Input.Recent_Hits;
      Dp   : constant Long_Float := Input.Delta_Psi;
      Dt   : constant Long_Float := Input.Delta_Theta;

      Growth : constant Long_Float :=
        EF.Exp (Alpha * (1.0 - Hits / N_m) * Gamma_E / Phi);

      Base : constant Long_Float :=
        (N_m * P_m / EF.Sqrt (D_m))
        * EF.Cos ((Psi_Con + Dp) / Eta_Eff)
        * EF.Exp (-Alpha * Hits / N_m + Input.Rho + B_In * Dp)
        * (1.0 + Growth * C_Eff);

      T1_0 : constant Long_Float :=
        Base * (1.0 + P_New * EF.Log (D_m / 25.0));

      Qm : Long_Float := 1.0;
      T1 : Long_Float;
      T2 : Long_Float;
      T3 : Long_Float;
      Valve : Long_Float;
      Acoustic : Long_Float;
      Phase : Long_Float;
      Raw : Long_Float;
      Panel : Scalar_Panel;
   begin
      if Input.Observed then
         Qm := EF.Exp (C_Factor * P_Var) * EF.Cos (Dp + P_Var);
         T1 := T1_0 * Qm;
      else
         T1 := T1_0;
      end if;

      T2 := Input.Scale * Input.Amplitude + Input.Trend_Bias;

      Valve :=
        Beta
        * EF.Cos (Dp)
        * (N_m * P_m / EF.Sqrt (D_m))
        * (1.0 + Chaos * (D_m - 25.0) / 25.0)
        * (1.0 + Poof * EF.Cos (Theta_S + Pi) + Suction * EF.Sin (Theta_S));

      Acoustic :=
        1.0
        + (A_Bleed * EF.Sin (Dt) ** 2) / Phi
        + (A_In * EF.Cos (Dt) ** 2) / Phi;

      Phase := 1.0 + B_In * P_Var;
      T3 := Valve * Acoustic * Phase;

      Raw := T1 + T2 + T3;

      Panel :=
        (S           => K * Raw,
         T1          => T1,
         T2          => T2,
         T3          => T3,
         K           => K,
         D_Eff       => Input.D_Eff,
         Observed    => Input.Observed,
         Delta_Psi   => Input.Delta_Psi,
         Delta_Theta => Input.Delta_Theta,
         Recent_Hits => Input.Recent_Hits,
         Quirk_Mod   => Qm,
         Growth      => Growth);
      return Panel;
   end Compute_Panel;

   function Compute_S (Input : Scalar_Input) return Long_Float is
   begin
      return Compute_Panel (Input).S;
   end Compute_S;

end PFLT_Scalar;
