--  Golden fixture checks vs formal/golden_fsot_pflt.json (embedded expected S).

with PFLT_Scalar;

package PFLT_Golden
  with SPARK_Mode => Off
is

   Eps : constant Long_Float := 1.0e-9;

   type Fixture is record
      Domain   : String (1 .. 16);
      Input    : PFLT_Scalar.Scalar_Input;
      Expect_S : Long_Float;
      Expect_T1 : Long_Float;
      Expect_T2 : Long_Float;
   end record;

   function Linguistic_Fixture return Fixture;
   function Historical_Fixture return Fixture;

   function Abs_Diff (A, B : Long_Float) return Long_Float;

   --  Returns number of failing checks (0 = all ok).
   function Run_Golden_Checks return Natural;

end PFLT_Golden;
