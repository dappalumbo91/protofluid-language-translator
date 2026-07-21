--  Protofluid converse surface: translate + law + ledger (no LLM).

with PFLT_Translate;

package PFLT_Converse
  with SPARK_Mode => Off
is

   type Converse_Result is record
      Reply      : String (1 .. 4096);
      Reply_Last : Natural := 0;
      Tr         : PFLT_Translate.Translate_Result;
   end record;

   function Converse
     (User_Text : String; Store : Boolean := True) return Converse_Result;

   function Reply_Slice (R : Converse_Result) return String;

end PFLT_Converse;
