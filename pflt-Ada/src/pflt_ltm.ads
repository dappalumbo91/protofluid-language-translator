--  SR-ITE-style LTM / mulling stream (append-only).
--  Dense knowledge grows; law is never rewritten.
--  Bound to archive SR-ITE philosophy: streams → readout → long-term store.

package PFLT_LTM
  with SPARK_Mode => Off
is

   procedure Set_Path (Path : String);

   --  Store a mull/memory episode (text + domain + S summary).
   procedure Remember
     (Text   : String;
      Domain : String;
      Gloss  : String;
      S      : Long_Float;
      Note   : String := "");

   --  Keyword recall of recent LTM lines (max hits).
   function Recall (Query : String; Max_Hits : Natural := 3) return String;

   function Episode_Count return Natural;

   --  Mulling: if knowledge thin (low map rate), propose densify note.
   function Mull_Note
     (Map_Rate : Long_Float; Unresolved_N : Natural) return String;

   procedure Load_Default_Path;

end PFLT_LTM;
