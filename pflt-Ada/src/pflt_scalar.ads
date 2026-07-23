--  FSOT 2.1 scalar panel for Protofluid — SPARK-mode pure compute.
--  Parity target: Python PFLT_FSOT_2_1_aligned.compute_S_D_chaotic
--                 / fsot_law_bridge.compute_law_scalar (archive path)
--
--  Domain-realistic subtypes keep GNATprove float-overflow checks
--  dischargeable. Atlas uses D_eff in ~5..25; N,P near order-1.

with PFLT_Constants;

package PFLT_Scalar
  with SPARK_Mode => On
is

   --  Physical domain bounds (archive 35-domain table + extension atlas)
   subtype Positive_Mass is Long_Float range 1.0e-3 .. 1.0e3;
   subtype Nonneg_Mass  is Long_Float range 0.0 .. 1.0e3;
   subtype Domain_D_Eff is Long_Float range 1.0 .. 50.0;
   subtype Phase_Angle  is Long_Float range -8.0 .. 8.0;
   subtype Unitish      is Long_Float range -10.0 .. 10.0;

   type Scalar_Input is record
      N           : Positive_Mass := 1.0;
      P           : Nonneg_Mass := 1.0;
      D_Eff       : Domain_D_Eff := 12.0;
      Recent_Hits : Nonneg_Mass := 0.0;
      Delta_Psi   : Phase_Angle := 0.8;
      Delta_Theta : Phase_Angle := 1.0;
      Rho         : Unitish := 1.0;
      Scale       : Unitish := 1.0;
      Amplitude   : Unitish := 1.0;
      Trend_Bias  : Unitish := 0.0;
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
       Pre    => Input.D_Eff >= 1.0
                 and then Input.N >= 1.0e-3
                 and then Input.P >= 0.0
                 and then Input.Recent_Hits >= 0.0
                 and then Input.Recent_Hits <= Input.N * 10.0,
       Post   =>
         Compute_Panel'Result.K = PFLT_Constants.K
         and then Compute_Panel'Result.D_Eff = Input.D_Eff
         and then Compute_Panel'Result.Observed = Input.Observed;

   --  Convenience: S only — same Pre as Compute_Panel (aligned contract)
   function Compute_S (Input : Scalar_Input) return Long_Float
     with
       Global => null,
       Pre    => Input.D_Eff >= 1.0
                 and then Input.N >= 1.0e-3
                 and then Input.P >= 0.0
                 and then Input.Recent_Hits >= 0.0
                 and then Input.Recent_Hits <= Input.N * 10.0,
       Post   => Compute_S'Result = Compute_Panel (Input).S;

end PFLT_Scalar;
