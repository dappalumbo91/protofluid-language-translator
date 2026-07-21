with Ada.Directories;
with Ada.Text_IO;

package body PFLT_Atlas
  with SPARK_Mode => Off
is

   Max_Domains : constant := 512;

   type Domain_Rec is record
      Name       : String (1 .. 64) := (others => ' ');
      Name_Last  : Natural := 0;
      Keywords   : String (1 .. 128) := (others => ' ');
      Kw_Last    : Natural := 0;
      D_Eff      : Long_Float := 12.0;
      Delta_Psi  : Long_Float := 0.8;
      Delta_Theta : Long_Float := 1.0;
      Observed   : Boolean := True;
   end record;

   Table : array (1 .. Max_Domains) of Domain_Rec;
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
      while R >= L and then (S (R) = ' ' or else S (R) = ASCII.HT
        or else S (R) = ASCII.CR)
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
      First_Line : Boolean := True;
   begin
      N := 0;
      if not Ada.Directories.Exists (Path) then
         return 0;
      end if;
      Open (F, In_File, Path);
      while not End_Of_File (F) and then N < Max_Domains loop
         declare
            Line : constant String := Get_Line (F);
            Tabs : array (1 .. 5) of Natural := (others => 0);
            Tc   : Natural := 0;
         begin
            if First_Line then
               First_Line := False;
               if Line'Length >= 4
                 and then (Line (Line'First .. Line'First + 3) = "name"
                   or else Line (Line'First .. Line'First + 3) = "Name")
               then
                  goto Continue;
               end if;
            end if;
            for I in Line'Range loop
               if Line (I) = ASCII.HT then
                  Tc := Tc + 1;
                  if Tc <= 5 then
                     Tabs (Tc) := I;
                  end if;
               end if;
            end loop;
            if Tc >= 5 then
               N := N + 1;
               declare
                  Nm : constant String :=
                    Strip (Line (Line'First .. Tabs (1) - 1));
                  De : constant String :=
                    Strip (Line (Tabs (1) + 1 .. Tabs (2) - 1));
                  Dp : constant String :=
                    Strip (Line (Tabs (2) + 1 .. Tabs (3) - 1));
                  Dt : constant String :=
                    Strip (Line (Tabs (3) + 1 .. Tabs (4) - 1));
                  Ob : constant String :=
                    Strip (Line (Tabs (4) + 1 .. Tabs (5) - 1));
                  Kw : constant String :=
                    Strip (Line (Tabs (5) + 1 .. Line'Last));
                  Rec : Domain_Rec;
               begin
                  Rec.Name_Last := Natural'Min (Nm'Length, Rec.Name'Length);
                  if Rec.Name_Last > 0 then
                     Rec.Name (1 .. Rec.Name_Last) :=
                       Nm (Nm'First .. Nm'First + Rec.Name_Last - 1);
                  end if;
                  Rec.Kw_Last := Natural'Min (Kw'Length, Rec.Keywords'Length);
                  if Rec.Kw_Last > 0 then
                     Rec.Keywords (1 .. Rec.Kw_Last) :=
                       Kw (Kw'First .. Kw'First + Rec.Kw_Last - 1);
                  end if;
                  begin
                     Rec.D_Eff := Long_Float'Value (De);
                  exception
                     when others =>
                        Rec.D_Eff := 12.0;
                  end;
                  begin
                     Rec.Delta_Psi := Long_Float'Value (Dp);
                  exception
                     when others =>
                        Rec.Delta_Psi := 0.8;
                  end;
                  begin
                     Rec.Delta_Theta := Long_Float'Value (Dt);
                  exception
                     when others =>
                        Rec.Delta_Theta := 1.0;
                  end;
                  Rec.Observed := Ob = "1" or else Ob = "true" or else Ob = "True";
                  Table (N) := Rec;
               end;
            end if;
            <<Continue>>
         end;
      end loop;
      Close (F);
      return N;
   end Load;

   function Count return Natural is
   begin
      return N;
   end Count;

   function Match (Text : String) return Atlas_Hit is
      T : constant String := To_Lower (Text);
      Best : Atlas_Hit;
      Best_Sc : Long_Float := 0.0;
   begin
      for I in 1 .. N loop
         declare
            Sc : Long_Float := 0.0;
            Nm : constant String :=
              To_Lower (Table (I).Name (1 .. Table (I).Name_Last));
            Kw : constant String :=
              To_Lower (Table (I).Keywords (1 .. Table (I).Kw_Last));
         begin
            if Nm'Length > 0 and then Contains (T, Nm) then
               Sc := Sc + 3.0;
            end if;
            --  token-wise keyword hits
            declare
               Start : Natural := Kw'First;
               J     : Natural;
            begin
               J := Start;
               while J <= Kw'Last loop
                  while J <= Kw'Last and then Kw (J) = ' ' loop
                     J := J + 1;
                  end loop;
                  exit when J > Kw'Last;
                  Start := J;
                  while J <= Kw'Last and then Kw (J) /= ' ' loop
                     J := J + 1;
                  end loop;
                  if J > Start then
                     declare
                        Tok : constant String := Kw (Start .. J - 1);
                     begin
                        --  skip tiny/common tokens (and/the/for noise)
                        if Tok'Length >= 4 and then Contains (T, Tok) then
                           Sc := Sc + 1.0;
                        end if;
                     end;
                  end if;
               end loop;
            end;
            if Sc > Best_Sc then
               Best_Sc := Sc;
               Best.Found := True;
               Best.Name := Table (I).Name;
               Best.Name_Last := Table (I).Name_Last;
               Best.D_Eff := Table (I).D_Eff;
               Best.Delta_Psi := Table (I).Delta_Psi;
               Best.Delta_Theta := Table (I).Delta_Theta;
               Best.Observed := Table (I).Observed;
               Best.Score := Sc;
            end if;
         end;
      end loop;
      return Best;
   end Match;

   function Name_Slice (H : Atlas_Hit) return String is
   begin
      if H.Name_Last = 0 then
         return "";
      end if;
      return H.Name (1 .. H.Name_Last);
   end Name_Slice;

   function Input_Of (H : Atlas_Hit) return PFLT_Scalar.Scalar_Input is
      I : PFLT_Scalar.Scalar_Input;
   begin
      I.N := 1.0;
      I.P := 1.0;
      I.D_Eff := H.D_Eff;
      I.Recent_Hits := 0.0;
      I.Delta_Psi := H.Delta_Psi;
      I.Delta_Theta := H.Delta_Theta;
      I.Rho := 1.0;
      I.Scale := 1.0;
      I.Amplitude := 1.0;
      I.Trend_Bias := 0.0;
      I.Observed := H.Observed;
      return I;
   end Input_Of;

   procedure Load_Default is
      Dummy : Natural;
   begin
      Dummy :=
        Load
          ("C:\Users\damia\Desktop\pflt\pflt-Ada\data\domain_atlas.tsv");
   end Load_Default;

end PFLT_Atlas;
