with PFLT_Domains; use PFLT_Domains;
with PFLT_Route;

package body PFLT_Pathway
  with SPARK_Mode => Off
is

   type Score_Map is array (Domain_Id) of Long_Float;

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

   procedure Bump
     (Scores : in out Score_Map;
      D      : Domain_Id;
      W      : Long_Float)
   is
   begin
      Scores (D) := Scores (D) + W;
   end Bump;

   function Reason
     (Text : String; Hops : Natural := 3) return Pathway_Result
   is
      T : constant String := To_Lower (Text);
      Scores : Score_Map := (others => 0.05);
      R : Pathway_Result;
      Best : Domain_Id := Linguistic;
      Best_S : Long_Float := 0.0;
      Second : Long_Float := 0.0;
      Seed : constant Domain_Id := PFLT_Route.Route_Domain (Text);
   begin
      Bump (Scores, Seed, 1.2);

      if Contains (T, "aqua") or else Contains (T, "manus")
        or else Contains (T, "latin") or else Contains (T, "rome")
      then
         Bump (Scores, Historical, 1.0);
         Bump (Scores, Linguistic, 0.4);
      end if;
      if Contains (T, "lingua") or else Contains (T, "logos")
        or else Contains (T, "zipf") or else Contains (T, "word")
      then
         Bump (Scores, Linguistic, 1.1);
      end if;
      if Contains (T, "zeus") or else Contains (T, "temple")
        or else Contains (T, "myth") or else Contains (T, "divine")
      then
         Bump (Scores, Mythological, 1.2);
         Bump (Scores, Historical, 0.3);
      end if;
      if Contains (T, "quantum") or else Contains (T, "photon") then
         Bump (Scores, Quantum, 1.3);
      end if;
      if Contains (T, "hieroglyph") then
         Bump (Scores, Hieroglyphic, 1.2);
      end if;

      for Hop in 1 .. Natural'Max (1, Hops) loop
         declare
            Next : Score_Map := Scores;
         begin
            Next (Linguistic) := Next (Linguistic)
              + 0.15 * Scores (Historical)
              + 0.15 * Scores (Mythological)
              + 0.1 * Scores (English);
            Next (Historical) := Next (Historical)
              + 0.12 * Scores (Linguistic)
              + 0.1 * Scores (Mythological);
            Next (Mythological) := Next (Mythological)
              + 0.12 * Scores (Historical);
            Next (Quantum) := Next (Quantum)
              + 0.08 * Scores (Cosmological);
            Scores := Next;
         end;
      end loop;

      for D in Domain_Id loop
         if Scores (D) > Best_S then
            Second := Best_S;
            Best_S := Scores (D);
            Best := D;
         elsif Scores (D) > Second then
            Second := Scores (D);
         end if;
      end loop;

      R.Primary := Best;
      R.Hops := Hops;
      if Best_S + Second > 0.0 then
         R.Conf := Best_S / (Best_S + Second);
      else
         R.Conf := 0.5;
      end if;

      declare
         Used : array (Domain_Id) of Boolean := (others => False);
      begin
         for I in R.Top'Range loop
            declare
               B : Domain_Id := Linguistic;
               Bs : Long_Float := -1.0;
            begin
               for D in Domain_Id loop
                  if not Used (D) and then Scores (D) > Bs then
                     Bs := Scores (D);
                     B := D;
                  end if;
               end loop;
               Used (B) := True;
               R.Top (I) := (Dom => B, Score => Bs);
            end;
         end loop;
      end;
      return R;
   end Reason;

   function Format_Chain (R : Pathway_Result) return String is
      Buf : String (1 .. 200) := (others => ' ');
      L   : Natural := 0;
      procedure App (S : String) is
      begin
         for C of S loop
            exit when L >= Buf'Last;
            L := L + 1;
            Buf (L) := C;
         end loop;
      end App;
   begin
      for I in R.Top'Range loop
         if I > 1 then
            App (" -> ");
         end if;
         App (Domain_Name (R.Top (I).Dom));
         exit when I = 4;
      end loop;
      if L = 0 then
         return "";
      end if;
      return Buf (1 .. L);
   end Format_Chain;

end PFLT_Pathway;
