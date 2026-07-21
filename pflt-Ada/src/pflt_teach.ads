--  English-meta teach panel: gloss -> classical form (finite table).

package PFLT_Teach
  with SPARK_Mode => Off
is

   type Pair is record
      Gloss : String (1 .. 24) := (others => ' ');
      Form  : String (1 .. 24) := (others => ' ');
      Lang  : String (1 .. 8) := (others => ' ');
      Ok    : Boolean := False;
   end record;

   type Pair_List is array (1 .. 8) of Pair;

   type Teach_Result is record
      Pairs : Pair_List;
      Count : Natural := 0;
      Label : String (1 .. 16) := (others => ' ');
   end record;

   function Build (Text : String) return Teach_Result;

   function Format_Block (T : Teach_Result) return String;

end PFLT_Teach;
