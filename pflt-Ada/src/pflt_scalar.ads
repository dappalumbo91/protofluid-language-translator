--  FSOT 2.1 scalar panel for Protofluid — SPARK-mode pure compute.
--  Parity target: Python PFLT_FSOT_2_1_aligned.compute_S_D_chaotic
--                 / fsot_law_bridge.compute_law_scalar (archive path)

with PFLT_Constants;

package PFLT_Scalar
  with SPARK_Mode => On
is

   type Scalar_Input is record
      N           : Long_Float := 1.0;
      P           : Long_Float := 1.0;
      D_Eff       : Long_Float := 12.0;
      Recent_Hits : Long_Float := 0.0;
      Delta_Psi   : Long_Float := 0.8;
      Delta_Theta : Long_Float := 1.0;
      Rho         : Long_Float := 1.0;
      Scale       : Long_Float := 1.0;
      Amplitude   : Long_Float := 1.0;
      Trend_Bias  : Long_Float := 0.0;
      Observed    : Boolean := True;
   end record;

   type Scalar_Panel is record
      S         : Long_Float;
      T1        : Long_Float;
      T2        : Long_Float;
      T3        : Long_Float;
      K         : Long_Float;
      D_Eff     : Long_Float;
      Observed  : Boolean;
      Delta_Psi : Long_Float;
      Delta_Theta : Long_Float;
      Recent_Hits : Long_Float;
      Quirk_Mod : Long_Float;
      Growth    : Long_Float;
   end record;

   function Compute_Panel (Input : Scalar_Input) return Scalar_Panel
     with
       Global => null,
       Pre    => Input.D_Eff > 0.0
                 and then Input.N > 0.0
                 and then Input.P >= 0.0
                 and then Input.Recent_Hits >= 0.0,
       Post   =>
         Compute_Panel'Result.K = PFLT_Constants.K
         and then Compute_Panel'Result.D_Eff = Input.D_Eff
         and then Compute_Panel'Result.Observed = Input.Observed;

   --  Convenience: S only
   function Compute_S (Input : Scalar_Input) return Long_Float
     with
       Global => null,
       Pre    => Input.D_Eff > 0.0 and then Input.N > 0.0,
       Post   => Compute_S'Result = Compute_Panel (Input).S;

end PFLT_Scalar;
