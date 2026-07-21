--  Full FSOT domain atlas (export from archive/catalog ~400 domains).
--  Keyword route → D_eff / observer params for scalar panel.

with PFLT_Scalar;

package PFLT_Atlas
  with SPARK_Mode => Off
is

   type Atlas_Hit is record
      Found      : Boolean := False;
      Name       : String (1 .. 64) := (others => ' ');
      Name_Last  : Natural := 0;
      D_Eff      : Long_Float := 12.0;
      Delta_Psi  : Long_Float := 0.8;
      Delta_Theta : Long_Float := 1.0;
      Observed   : Boolean := True;
      Score      : Long_Float := 0.0;
   end record;

   function Load (Path : String) return Natural;
   function Count return Natural;

   --  Best keyword match against user text / domain name.
   function Match (Text : String) return Atlas_Hit;

   function Name_Slice (H : Atlas_Hit) return String;

   function Input_Of (H : Atlas_Hit) return PFLT_Scalar.Scalar_Input;

   procedure Load_Default;

end PFLT_Atlas;
