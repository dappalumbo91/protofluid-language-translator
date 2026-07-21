--  Finite reverse morphology (Latin / Greek-Latin / OE strips).
--  Peel endings and probe PFLT_Store for lemma hits.
--  Not SPARK -- algorithmic open-set surface.

package PFLT_Morph
  with SPARK_Mode => Off
is

   type Morph_Hit is record
      Found      : Boolean := False;
      Gloss      : String (1 .. 96) := (others => ' ');
      Gloss_Last : Natural := 0;
      Method     : String (1 .. 24) := (others => ' ');
      Method_Last : Natural := 0;
   end record;

   --  Try exact store, then peels + lemma reattach for lang hint.
   --  Lang_Hint: "la", "grc", "ang", or "" for auto.
   function Resolve
     (Form : String; Lang_Hint : String := "") return Morph_Hit;

end PFLT_Morph;
