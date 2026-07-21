--  Lightweight multi-hop domain pathway (product surface; not SPARK).

with PFLT_Domains;

package PFLT_Pathway
  with SPARK_Mode => Off
is

   type Domain_Score is record
      Dom   : PFLT_Domains.Domain_Id;
      Score : Long_Float := 0.0;
   end record;

   type Score_List is array (1 .. 5) of Domain_Score;

   type Pathway_Result is record
      Primary : PFLT_Domains.Domain_Id;
      Top     : Score_List;
      Conf    : Long_Float := 0.0;
      Hops    : Natural := 0;
   end record;

   function Reason (Text : String; Hops : Natural := 3) return Pathway_Result;

   function Format_Chain (R : Pathway_Result) return String;

end PFLT_Pathway;
