--  Minimal exact-map lexicon surface (V0).
--  Full densify / open-set morph remains in Python climb until ported.

package PFLT_Lexicon
  with SPARK_Mode => On
is

   Max_Form_Len : constant := 64;
   Max_Gloss_Len : constant := 96;

   subtype Form_String is String (1 .. Max_Form_Len);
   subtype Gloss_String is String (1 .. Max_Gloss_Len);

   type Gloss_Result is record
      Found      : Boolean;
      Gloss      : Gloss_String;
      Gloss_Last : Natural;
   end record;

   --  Exact surface → English gloss (seed table only in V0).
   function Map_Token (Form : String) return Gloss_Result
     with Global => null;

   --  Space-separated forms → space-separated glosses (exact only).
   function Translate_Exact (Text : String) return String
     with Global => null;

end PFLT_Lexicon;
