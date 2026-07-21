--  Central gloss quality policy (refinement debt Ada exposed).
--  Rejects grammatical meta / compound dictionary noise so product
--  glosses compete with real translators, not dictionary headers.

package PFLT_Gloss_Quality
  with SPARK_Mode => Off
is

   --  True if gloss is usable as surface English meaning.
   function Is_Content_Gloss (G : String) return Boolean;

   --  Return cleaned head gloss, or empty if unusable.
   function Clean_Gloss (G : String) return String;

   --  Higher is better (0.0 .. 1.0). Used when choosing among senses.
   function Score_Gloss (G : String) return Long_Float;

end PFLT_Gloss_Quality;
