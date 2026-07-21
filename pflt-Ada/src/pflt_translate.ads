--  Product translate path: route domain -> law panel -> store/seed map.

with PFLT_Domains;
with PFLT_Scalar;

package PFLT_Translate
  with SPARK_Mode => Off
is

   type Translate_Result is record
      Domain       : PFLT_Domains.Domain_Id;
      Gloss        : String (1 .. 1024);
      Gloss_Last   : Natural := 0;
      Unresolved_N : Natural := 0;
      Token_N      : Natural := 0;
      Mapped_N     : Natural := 0;
      Morph_N      : Natural := 0;
      Panel        : PFLT_Scalar.Scalar_Panel;
      Map_Rate     : Long_Float := 0.0;
   end record;

   function Translate (Text : String) return Translate_Result;

   function Gloss_Slice (R : Translate_Result) return String;

end PFLT_Translate;
