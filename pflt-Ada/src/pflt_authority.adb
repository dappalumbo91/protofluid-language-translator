package body PFLT_Authority
  with SPARK_Mode => On
is

   subtype Note_Str is String (1 .. 48);

   function Pad48 (S : String) return Note_Str
     with Global => null
   is
      R : Note_Str := (others => ' ');
      N : Natural;
   begin
      if S'Length = 0 then
         return R;
      end if;
      if S'Length >= 48 then
         N := 48;
      else
         N := S'Length;
      end if;
      --  Copy with bounds safe for any String slice
      for I in 1 .. N loop
         R (I) := S (S'First + (I - 1));
      end loop;
      return R;
   end Pad48;

   function Verify_Pin (Observed_SHA256 : String) return Authority_Status is
      R : Authority_Status;
   begin
      R.Prefix := Expected_Prefix;
      if Observed_SHA256'Length = 0 then
         R.Ok := False;
         R.Note := Pad48 ("no digest provided (kernel pin still D1D38A)");
         return R;
      end if;
      if Observed_SHA256'Length = Expected_SHA256'Length
        and then Observed_SHA256 = Expected_SHA256
      then
         R.Ok := True;
         R.Note := Pad48 ("archive fsot_compute pin matches D1D38A");
      else
         R.Ok := False;
         R.Note := Pad48 ("hash mismatch vs expected D1D38A authority pin");
      end if;
      return R;
   end Verify_Pin;

   function Kernel_Pin_Status return Authority_Status is
      R : Authority_Status;
   begin
      R.Ok := True;
      R.Prefix := Expected_Prefix;
      R.Note := Pad48 ("Ada/SPARK kernel embeds expected pin D1D38A");
      return R;
   end Kernel_Pin_Status;

end PFLT_Authority;
