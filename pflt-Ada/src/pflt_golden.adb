with PFLT_Scalar;

package body PFLT_Golden
  with SPARK_Mode => Off
is

   function Abs_Diff (A, B : Long_Float) return Long_Float is
   begin
      if A >= B then
         return A - B;
      else
         return B - A;
      end if;
   end Abs_Diff;

   function Linguistic_Fixture return Fixture is
      F : Fixture;
      I : PFLT_Scalar.Scalar_Input;
   begin
      F.Domain := "linguistic      ";
      I.N := 1.0;
      I.P := 1.0;
      I.D_Eff := 12.0;
      I.Recent_Hits := 0.0;
      I.Delta_Psi := 0.8;
      I.Delta_Theta := 1.0;
      I.Rho := 1.0;
      I.Scale := 1.0;
      I.Amplitude := 1.0;
      I.Trend_Bias := 0.0;
      I.Observed := True;
      F.Input := I;
      F.Expect_S := 0.651_324_761_884_896_9;
      F.Expect_T1 := 0.549_955_219_909_424_1;
      F.Expect_T2 := 1.0;
      return F;
   end Linguistic_Fixture;

   function Historical_Fixture return Fixture is
      F : Fixture;
      I : PFLT_Scalar.Scalar_Input;
   begin
      --  Match Python DOMAIN_PARAMS historical if available; golden file
      --  uses D_eff from fixture — read from golden historical block if present.
      F.Domain := "historical      ";
      I.N := 1.0;
      I.P := 1.0;
      I.D_Eff := 21.0;
      I.Recent_Hits := 0.0;
      I.Delta_Psi := 0.8;
      I.Delta_Theta := 1.0;
      I.Rho := 1.0;
      I.Scale := 1.0;
      I.Amplitude := 1.0;
      I.Trend_Bias := 0.0;
      I.Observed := True;
      F.Input := I;
      F.Expect_S := 0.632_578_336_013_628_3;
      F.Expect_T1 := 0.505_344_416_921_171_6;
      F.Expect_T2 := 1.0;
      return F;
   end Historical_Fixture;

   function Run_Golden_Checks return Natural is
      Fail : Natural := 0;
      procedure Check (F : Fixture) is
         P : constant PFLT_Scalar.Scalar_Panel :=
           PFLT_Scalar.Compute_Panel (F.Input);
      begin
         if Abs_Diff (P.S, F.Expect_S) > Eps then
            Fail := Fail + 1;
         end if;
         if Abs_Diff (P.T1, F.Expect_T1) > 1.0e-8 then
            Fail := Fail + 1;
         end if;
         if Abs_Diff (P.T2, F.Expect_T2) > Eps then
            Fail := Fail + 1;
         end if;
         if P.T3 < 0.0 then
            Fail := Fail + 1;
         end if;
      end Check;
   begin
      Check (Linguistic_Fixture);
      Check (Historical_Fixture);
      return Fail;
   end Run_Golden_Checks;

end PFLT_Golden;
