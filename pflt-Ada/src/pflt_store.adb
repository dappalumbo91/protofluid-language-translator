with Ada.Containers.Indefinite_Hashed_Maps;
with Ada.Containers.Indefinite_Vectors;
with Ada.Directories;
with Ada.Strings.Hash;
with Ada.Strings.Unbounded; use Ada.Strings.Unbounded;
with Ada.Text_IO;
with PFLT_Gloss_Quality;

package body PFLT_Store is

   package Maps is new Ada.Containers.Indefinite_Hashed_Maps
     (Key_Type        => String,
      Element_Type    => String,
      Hash            => Ada.Strings.Hash,
      Equivalent_Keys => "=");

   package String_Vectors is new Ada.Containers.Indefinite_Vectors
     (Index_Type   => Positive,
      Element_Type => String);

   package Prefix_Maps is new Ada.Containers.Indefinite_Hashed_Maps
     (Key_Type        => String,
      Element_Type    => String_Vectors.Vector,
      Hash            => Ada.Strings.Hash,
      Equivalent_Keys => "=",
      "="             => String_Vectors."=");

   Table     : Maps.Map;
   Prefixes  : Prefix_Maps.Map;
   Data_Root_U : Unbounded_String := To_Unbounded_String ("data");

   function Lower_Char (C : Character) return Character is
   begin
      if C >= 'A' and then C <= 'Z' then
         return Character'Val
           (Character'Pos (C) - Character'Pos ('A') + Character'Pos ('a'));
      end if;
      return C;
   end Lower_Char;

   function To_Lower (S : String) return String is
      R : String (S'Range);
   begin
      for I in S'Range loop
         R (I) := Lower_Char (S (I));
      end loop;
      return R;
   end To_Lower;

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

   function Prefix3 (S : String) return String is
      L : constant String := To_Lower (S);
   begin
      if L'Length >= 3 then
         return L (L'First .. L'First + 2);
      elsif L'Length > 0 then
         return L;
      else
         return "";
      end if;
   end Prefix3;

   procedure Index_Form (Form : String) is
      P : constant String := Prefix3 (Form);
      C : Prefix_Maps.Cursor;
      V : String_Vectors.Vector;
   begin
      if P'Length = 0 or else Form'Length < 3 then
         return;
      end if;
      --  only index bare forms (no lang|)
      for Ch of Form loop
         if Ch = '|' then
            return;
         end if;
      end loop;
      C := Prefixes.Find (P);
      if Prefix_Maps.Has_Element (C) then
         V := Prefix_Maps.Element (C);
         if Natural (V.Length) < 240 then
            V.Append (To_Lower (Form));
            Prefixes.Replace_Element (C, V);
         end if;
      else
         V.Append (To_Lower (Form));
         Prefixes.Include (P, V);
      end if;
   end Index_Form;

   procedure Clear is
   begin
      Table.Clear;
      Prefixes.Clear;
   end Clear;

   procedure Put_Pair (Key, Val : String) is
      K  : constant String := Strip (Key);
      V0 : constant String := Strip (Val);
      V  : constant String := PFLT_Gloss_Quality.Clean_Gloss (V0);
   begin
      if K'Length = 0 or else V'Length = 0 then
         return;
      end if;
      --  Prefer higher-scoring gloss if key exists; on tie prefer longer content.
      declare
         C : constant Maps.Cursor := Table.Find (K);
         New_S : Long_Float;
         Old_S : Long_Float;
      begin
         if Maps.Has_Element (C) then
            New_S := PFLT_Gloss_Quality.Score_Gloss (V);
            Old_S := PFLT_Gloss_Quality.Score_Gloss (Maps.Element (C));
            if New_S > Old_S
              or else
                (New_S = Old_S and then V'Length > Maps.Element (C)'Length)
            then
               Table.Replace_Element (C, V);
            end if;
         else
            Table.Include (K, V);
         end if;
      end;
      declare
         Kl : constant String := To_Lower (K);
         C2 : constant Maps.Cursor := Table.Find (Kl);
      begin
         if Kl /= K then
            if Maps.Has_Element (C2) then
               declare
                  New_S : constant Long_Float :=
                    PFLT_Gloss_Quality.Score_Gloss (V);
                  Old_S : constant Long_Float :=
                    PFLT_Gloss_Quality.Score_Gloss (Maps.Element (C2));
               begin
                  if New_S > Old_S
                    or else
                      (New_S = Old_S
                       and then V'Length > Maps.Element (C2)'Length)
                  then
                     Table.Replace_Element (C2, V);
                  end if;
               end;
            else
               Table.Include (Kl, V);
            end if;
         end if;
         Index_Form (Kl);
      end;
   end Put_Pair;

   function Load_TSV_Map (Path : String) return Natural is
      use Ada.Text_IO;
      F : File_Type;
      N : Natural := 0;
   begin
      if not Ada.Directories.Exists (Path) then
         return 0;
      end if;
      Open (F, In_File, Path);
      while not End_Of_File (F) loop
         declare
            Line : constant String := Get_Line (F);
            Tab  : Natural := 0;
         begin
            for I in Line'Range loop
               if Line (I) = ASCII.HT then
                  Tab := I;
                  exit;
               end if;
            end loop;
            if Tab > Line'First and then Tab < Line'Last then
               Put_Pair
                 (Line (Line'First .. Tab - 1), Line (Tab + 1 .. Line'Last));
               N := N + 1;
            end if;
         end;
      end loop;
      Close (F);
      return N;
   end Load_TSV_Map;

   function Load_Gold_TSV (Path : String) return Natural is
      use Ada.Text_IO;
      F : File_Type;
      N : Natural := 0;
   begin
      if not Ada.Directories.Exists (Path) then
         return 0;
      end if;
      Open (F, In_File, Path);
      while not End_Of_File (F) loop
         declare
            Line     : constant String := Get_Line (F);
            T1, T2   : Natural := 0;
            Tabs     : Natural := 0;
         begin
            for I in Line'Range loop
               if Line (I) = ASCII.HT then
                  Tabs := Tabs + 1;
                  if Tabs = 1 then
                     T1 := I;
                  elsif Tabs = 2 then
                     T2 := I;
                     exit;
                  end if;
               end if;
            end loop;
            if T1 > Line'First and then T2 > T1 and then T2 < Line'Last then
               declare
                  Lang  : constant String :=
                    Strip (Line (Line'First .. T1 - 1));
                  Form  : constant String := Strip (Line (T1 + 1 .. T2 - 1));
                  Gloss : constant String := Strip (Line (T2 + 1 .. Line'Last));
                  Fl    : constant String := To_Lower (Form);
               begin
                  Put_Pair (Form, Gloss);
                  Put_Pair (Fl, Gloss);
                  if Lang'Length > 0 then
                     Put_Pair (Lang & "|" & Form, Gloss);
                     Put_Pair (Lang & "|" & Fl, Gloss);
                  end if;
                  N := N + 1;
               end;
            end if;
         end;
      end loop;
      Close (F);
      return N;
   end Load_Gold_TSV;

   function Lookup (Form : String) return String is
      F  : constant String := Strip (Form);
      Fl : constant String := To_Lower (F);
      C  : Maps.Cursor;
      Best : Unbounded_String := Null_Unbounded_String;
      Best_S : Long_Float := 0.0;

      procedure Consider (Key : String) is
         Cc : Maps.Cursor;
         G  : Unbounded_String;
         Sc : Long_Float;
      begin
         Cc := Table.Find (Key);
         if Maps.Has_Element (Cc) then
            G := To_Unbounded_String (Maps.Element (Cc));
            Sc := PFLT_Gloss_Quality.Score_Gloss (To_String (G));
            if Sc > Best_S then
               Best_S := Sc;
               Best := G;
            end if;
         end if;
      end Consider;
   begin
      if F'Length = 0 then
         return "";
      end if;
      Consider (F);
      Consider (Fl);
      Consider ("la|" & Fl);
      Consider ("grc|" & Fl);
      Consider ("egy|" & Fl);
      Consider ("ang|" & Fl);
      Consider ("en|" & Fl);
      Consider ("ar|" & Fl);
      Consider ("cu|" & Fl);
      Consider ("cop|" & Fl);
      Consider ("arc|" & Fl);
      Consider ("akk|" & Fl);
      Consider ("got|" & Fl);
      Consider ("non|" & Fl);
      Consider ("san|" & Fl);
      Consider ("he|" & Fl);
      if Best_S <= 0.0 then
         return "";
      end if;
      return To_String (Best);
   end Lookup;

   function Edit_Distance (A, B : String) return Natural is
      --  Classic DP on small strings (len <= 24)
      N : constant Natural := A'Length;
      M : constant Natural := B'Length;
      type Row is array (0 .. 24) of Natural;
      Prev, Cur : Row := (others => 0);
   begin
      if N > 24 or else M > 24 then
         return 99;
      end if;
      for J in 0 .. M loop
         Prev (J) := J;
      end loop;
      for I in 1 .. N loop
         Cur (0) := I;
         for J in 1 .. M loop
            declare
               Cost : Natural := 1;
            begin
               if A (A'First + I - 1) = B (B'First + J - 1) then
                  Cost := 0;
               end if;
               Cur (J) := Natural'Min
                 (Natural'Min (Cur (J - 1) + 1, Prev (J) + 1),
                  Prev (J - 1) + Cost);
            end;
         end loop;
         Prev := Cur;
      end loop;
      return Prev (M);
   end Edit_Distance;

   function Lookup_Neighbor
     (Form : String; Max_Dist : Natural := 2) return String
   is
      Fl : constant String := To_Lower (Strip (Form));
      P  : constant String := Prefix3 (Fl);
      C  : Prefix_Maps.Cursor;
      Best_Key : Unbounded_String;
      Best_D : Natural := 99;
      --  Short forms: only dist-1; long forms may use Max_Dist (cap 2).
      Cap : Natural;
   begin
      if Fl'Length < 4 or else P'Length = 0 then
         return "";
      end if;
      if Fl'Length < 7 then
         Cap := 1;
      else
         Cap := Natural'Min (Max_Dist, 2);
      end if;
      --  exact already handled by Lookup
      if Lookup (Fl)'Length > 0 then
         return Lookup (Fl);
      end if;
      C := Prefixes.Find (P);
      if not Prefix_Maps.Has_Element (C) then
         return "";
      end if;
      declare
         V : constant String_Vectors.Vector := Prefix_Maps.Element (C);
      begin
         for I in V.First_Index .. V.Last_Index loop
            declare
               Cand : constant String := V.Element (I);
               D    : Natural;
               Len_Diff : Natural;
            begin
               if Cand'Length >= 4 then
                  if Cand'Length > Fl'Length then
                     Len_Diff := Cand'Length - Fl'Length;
                  else
                     Len_Diff := Fl'Length - Cand'Length;
                  end if;
                  --  reject wild length mismatch (false morph neighbors)
                  if Len_Diff <= Cap + 1 then
                     D := Edit_Distance (Fl, Cand);
                     if D > 0 and then D <= Cap and then D < Best_D then
                        Best_D := D;
                        Best_Key := To_Unbounded_String (Cand);
                     end if;
                  end if;
               end if;
            end;
         end loop;
      end;
      if Best_D <= Cap then
         return Lookup (To_String (Best_Key));
      end if;
      return "";
   end Lookup_Neighbor;

   function Count return Natural is
   begin
      return Natural (Table.Length);
   end Count;

   procedure Set_Data_Root (Root : String) is
   begin
      Data_Root_U := To_Unbounded_String (Root);
   end Set_Data_Root;

   function Data_Root return String is
   begin
      return To_String (Data_Root_U);
   end Data_Root;

   function Join (A, B : String) return String is
   begin
      if A'Length = 0 then
         return B;
      elsif A (A'Last) = '\' or else A (A'Last) = '/' then
         return A & B;
      else
         return A & "\" & B;
      end if;
   end Join;

   procedure Load_Default_Packs
     (Densify_N : out Natural; Gold_N : out Natural)
   is
      R : constant String := To_String (Data_Root_U);
   begin
      --  Gold first (mass inventory), densify last so preferred product senses win.
      Gold_N    := Load_Gold_TSV (Join (R, "gold_core.tsv"));
      Densify_N := Load_TSV_Map (Join (R, "densify.tsv"));
   end Load_Default_Packs;

   function Load_Open_Set_Train return Natural is
      R    : constant String := To_String (Data_Root_U);
      Path : constant String := Join (R, "train_mass.tsv");
      N    : Natural;
   begin
      Clear;
      if Ada.Directories.Exists (Path) then
         N := Load_TSV_Map (Path);
      else
         N := Load_TSV_Map (Join (R, "densify.tsv"));
      end if;
      return N;
   end Load_Open_Set_Train;

   procedure Inject_Pair (Form, Gloss : String; Ok : out Boolean) is
      use Ada.Text_IO;
      R    : constant String := To_String (Data_Root_U);
      Path : constant String := Join (R, "densify.tsv");
      F    : File_Type;
      V    : constant String := PFLT_Gloss_Quality.Clean_Gloss (Strip (Gloss));
      K    : constant String := Strip (Form);
   begin
      Ok := False;
      if K'Length = 0 or else V'Length = 0 then
         return;
      end if;
      Put_Pair (K, V);
      begin
         if Ada.Directories.Exists (Path) then
            Open (F, Append_File, Path);
         else
            Create (F, Out_File, Path);
         end if;
         Put_Line (F, K & ASCII.HT & V);
         Close (F);
         Ok := True;
      exception
         when others =>
            if Is_Open (F) then
               Close (F);
            end if;
            Ok := False;
      end;
   end Inject_Pair;

end PFLT_Store;
