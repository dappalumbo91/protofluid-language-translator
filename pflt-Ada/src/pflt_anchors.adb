with Ada.Directories;
with Ada.Text_IO;

package body PFLT_Anchors
  with SPARK_Mode => Off
is

   Max_A : constant := 128;
   type Rec is record
      Name       : String (1 .. 48) := (others => ' ');
      Name_Last  : Natural := 0;
      Value      : Long_Float := 0.0;
      Error_Pct  : Long_Float := 0.0;
      Formula    : String (1 .. 96) := (others => ' ');
      Formula_Last : Natural := 0;
      Status     : String (1 .. 24) := (others => ' ');
      Status_Last : Natural := 0;
   end record;

   Table : array (1 .. Max_A) of Rec;
   N     : Natural := 0;

   function To_Lower (S : String) return String is
      R : String (S'Range);
   begin
      for I in S'Range loop
         if S (I) >= 'A' and then S (I) <= 'Z' then
            R (I) := Character'Val
              (Character'Pos (S (I)) - Character'Pos ('A')
               + Character'Pos ('a'));
         else
            R (I) := S (I);
         end if;
      end loop;
      return R;
   end To_Lower;

   function Contains (Hay, Needle : String) return Boolean is
   begin
      if Needle'Length = 0 or else Hay'Length < Needle'Length then
         return False;
      end if;
      for I in Hay'First .. Hay'Last - Needle'Length + 1 loop
         if Hay (I .. I + Needle'Length - 1) = Needle then
            return True;
         end if;
      end loop;
      return False;
   end Contains;

   function Strip (S : String) return String is
      L : Natural := S'First;
      R : Natural := S'Last;
   begin
      while L <= R and then (S (L) = ' ' or else S (L) = ASCII.HT) loop
         L := L + 1;
      end loop;
      while R >= L
        and then (S (R) = ' ' or else S (R) = ASCII.HT or else S (R) = ASCII.CR)
      loop
         R := R - 1;
      end loop;
      if L > R then
         return "";
      end if;
      return S (L .. R);
   end Strip;

   function Load (Path : String) return Natural is
      use Ada.Text_IO;
      F : File_Type;
      First : Boolean := True;
   begin
      N := 0;
      if not Ada.Directories.Exists (Path) then
         return 0;
      end if;
      Open (F, In_File, Path);
      while not End_Of_File (F) and then N < Max_A loop
         declare
            Line : constant String := Get_Line (F);
            Tabs : array (1 .. 4) of Natural := (others => 0);
            Tc   : Natural := 0;
         begin
            if First then
               First := False;
               if Line'Length >= 4
                 and then Line (Line'First .. Line'First + 3) = "name"
               then
                  goto Cont;
               end if;
            end if;
            for I in Line'Range loop
               if Line (I) = ASCII.HT then
                  Tc := Tc + 1;
                  if Tc <= 4 then
                     Tabs (Tc) := I;
                  end if;
               end if;
            end loop;
            if Tc >= 4 then
               N := N + 1;
               declare
                  Nm : constant String :=
                    Strip (Line (Line'First .. Tabs (1) - 1));
                  Cv : constant String :=
                    Strip (Line (Tabs (1) + 1 .. Tabs (2) - 1));
                  Er : constant String :=
                    Strip (Line (Tabs (2) + 1 .. Tabs (3) - 1));
                  Fm : constant String :=
                    Strip (Line (Tabs (3) + 1 .. Tabs (4) - 1));
                  St : constant String :=
                    Strip (Line (Tabs (4) + 1 .. Line'Last));
                  R  : Rec;
               begin
                  R.Name_Last := Natural'Min (Nm'Length, R.Name'Length);
                  if R.Name_Last > 0 then
                     R.Name (1 .. R.Name_Last) :=
                       Nm (Nm'First .. Nm'First + R.Name_Last - 1);
                  end if;
                  begin
                     R.Value := Long_Float'Value (Cv);
                  exception
                     when others =>
                        R.Value := 0.0;
                  end;
                  begin
                     R.Error_Pct := Long_Float'Value (Er);
                  exception
                     when others =>
                        R.Error_Pct := 0.0;
                  end;
                  R.Formula_Last := Natural'Min (Fm'Length, R.Formula'Length);
                  if R.Formula_Last > 0 then
                     R.Formula (1 .. R.Formula_Last) :=
                       Fm (Fm'First .. Fm'First + R.Formula_Last - 1);
                  end if;
                  R.Status_Last := Natural'Min (St'Length, R.Status'Length);
                  if R.Status_Last > 0 then
                     R.Status (1 .. R.Status_Last) :=
                       St (St'First .. St'First + R.Status_Last - 1);
                  end if;
                  Table (N) := R;
               end;
            end if;
            <<Cont>>
         end;
      end loop;
      Close (F);
      return N;
   end Load;

   function Count return Natural is
   begin
      return N;
   end Count;

   function Find (Key : String) return Anchor is
      K : constant String := To_Lower (Key);
      A : Anchor;
   begin
      for I in 1 .. N loop
         declare
            Nm : constant String :=
              To_Lower (Table (I).Name (1 .. Table (I).Name_Last));
         begin
            if Contains (Nm, K) then
               A.Found := True;
               A.Name := Table (I).Name;
               A.Name_Last := Table (I).Name_Last;
               A.Value := Table (I).Value;
               A.Error_Pct := Table (I).Error_Pct;
               A.Formula := Table (I).Formula;
               A.Formula_Last := Table (I).Formula_Last;
               A.Status := Table (I).Status;
               A.Status_Last := Table (I).Status_Last;
               return A;
            end if;
         end;
      end loop;
      return A;
   end Find;

   function Name_Slice (A : Anchor) return String is
   begin
      if A.Name_Last = 0 then
         return "";
      end if;
      return A.Name (1 .. A.Name_Last);
   end Name_Slice;

   function Formula_Slice (A : Anchor) return String is
   begin
      if A.Formula_Last = 0 then
         return "";
      end if;
      return A.Formula (1 .. A.Formula_Last);
   end Formula_Slice;

   procedure Load_Default is
      Dummy : Natural;
   begin
      Dummy :=
        Load
          ("C:\Users\damia\Desktop\pflt\pflt-Ada\data\linguistics_anchors.tsv");
   end Load_Default;

end PFLT_Anchors;
