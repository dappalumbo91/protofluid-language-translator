--  Competitive self-eval: form->gloss exact/soft.
--  OPEN-SET: train_mass only (morph stress).
--  PRODUCT: full densify+gold (shipping path; competitor-class inventory).

package PFLT_Eval
  with SPARK_Mode => Off
is

   type Eval_Mode is (Open_Set, Product);

   type Eval_Report is record
      N            : Natural := 0;
      Exact        : Natural := 0;
      Soft         : Natural := 0;
      Miss         : Natural := 0;
      Train_N      : Natural := 0;
      Morph_Hits   : Natural := 0;
      Exact_Rate   : Long_Float := 0.0;
      Partial_Rate : Long_Float := 0.0;
      Mode         : Eval_Mode := Open_Set;
   end record;

   function Run_Sample (Path : String) return Eval_Report;

   function Run_Sample (Path : String; Max_N : Natural) return Eval_Report;

   function Run_Sample
     (Path : String; Max_N : Natural; Mode : Eval_Mode) return Eval_Report;

   procedure Print_Report (R : Eval_Report);

end PFLT_Eval;
