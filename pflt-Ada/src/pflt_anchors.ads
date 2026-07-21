--  Archive linguistics derivations as certified numeric anchors.
--  Source: I:\...\vendor\linguistics\linguistics_derivations.json

package PFLT_Anchors
  with SPARK_Mode => Off
is

   type Anchor is record
      Found      : Boolean := False;
      Name       : String (1 .. 48) := (others => ' ');
      Name_Last  : Natural := 0;
      Value      : Long_Float := 0.0;
      Error_Pct  : Long_Float := 0.0;
      Formula    : String (1 .. 96) := (others => ' ');
      Formula_Last : Natural := 0;
      Status     : String (1 .. 24) := (others => ' ');
      Status_Last : Natural := 0;
   end record;

   function Load (Path : String) return Natural;
   function Count return Natural;

   --  Lookup by substring in name (zipf, entropy, heaps, …)
   function Find (Key : String) return Anchor;

   function Name_Slice (A : Anchor) return String;
   function Formula_Slice (A : Anchor) return String;

   procedure Load_Default;

end PFLT_Anchors;
