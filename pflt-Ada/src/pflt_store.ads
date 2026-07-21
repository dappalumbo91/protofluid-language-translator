--  Runtime lexicon store (densify + gold + train_mass). Not SPARK.
--  Quality gate: PFLT_Gloss_Quality rejects meta dictionary noise.
--  Neighbor lookup: prefix-bucket edit distance for open-set forms.

package PFLT_Store is

   procedure Clear;

   function Load_TSV_Map (Path : String) return Natural;
   function Load_Gold_TSV (Path : String) return Natural;

   --  Exact / lang-prefixed lookup with quality-scored sense pick.
   function Lookup (Form : String) return String;

   --  Open-set: same 3-char prefix, edit distance <= Max_Dist.
   function Lookup_Neighbor
     (Form : String; Max_Dist : Natural := 2) return String;

   function Count return Natural;

   procedure Set_Data_Root (Root : String);
   function Data_Root return String;

   --  Deploy path: gold_core + densify (full product lexicon).
   procedure Load_Default_Packs
     (Densify_N : out Natural;
      Gold_N    : out Natural);

   --  Honest open-set train: train_mass.tsv if present, else densify.tsv.
   function Load_Open_Set_Train return Natural;

   --  Append form->gloss to densify.tsv and live map (Ada self-climb).
   procedure Inject_Pair (Form, Gloss : String; Ok : out Boolean);

end PFLT_Store;
