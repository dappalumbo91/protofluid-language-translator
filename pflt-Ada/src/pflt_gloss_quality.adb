package body PFLT_Gloss_Quality
  with SPARK_Mode => Off
is

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

   function Is_Content_Gloss (G : String) return Boolean is
      L : constant String := To_Lower (G);
   begin
      if L'Length = 0 or else L'Length > 64 then
         return False;
      end if;
      --  Grammatical meta (dictionary residue Ada forced us to see)
      if Contains (L, "dative")
        or else Contains (L, "genitive")
        or else Contains (L, "accusative")
        or else Contains (L, "nominative")
        or else Contains (L, "vocative")
        or else Contains (L, "ablative")
        or else Contains (L, "singular of")
        or else Contains (L, "plural of")
        or else Contains (L, "inflection")
        or else Contains (L, "participle of")
        or else Contains (L, "imperative of")
        or else Contains (L, "subjunctive")
        or else Contains (L, "indicative")
        or else Contains (L, "the compound")
        or else Contains (L, "compound of")
        or else Contains (L, "see also")
        or else Contains (L, "etymolog")
        or else Contains (L, "unresolved")
        or else Contains (L, "heritage_flow")
        or else Contains (L, "narrative_flow")
        or else Contains (L, "generic_dynamics")
      then
         return False;
      end if;
      --  Bracket-heavy meta
      if L (L'First) = '[' or else L (L'First) = '(' then
         if Contains (L, "with genitive") or else Contains (L, "with dative") then
            return False;
         end if;
      end if;
      return True;
   end Is_Content_Gloss;

   function Clean_Gloss (G : String) return String is
      L : constant String := G;
      --  take first clause before ; or |
      End_P : Natural := L'Last;
   begin
      if not Is_Content_Gloss (G) then
         --  try last whitespace token if short content word
         declare
            P : Natural := L'Last;
         begin
            while P >= L'First and then L (P) /= ' ' loop
               P := P - 1;
            end loop;
            if P < L'Last then
               declare
                  Tail : constant String := L (P + 1 .. L'Last);
               begin
                  if Is_Content_Gloss (Tail) and then Tail'Length <= 24 then
                     return Tail;
                  end if;
               end;
            end if;
         end;
         return "";
      end if;
      for I in L'Range loop
         if L (I) = ';' or else L (I) = '|' or else L (I) = ',' then
            End_P := I - 1;
            exit;
         end if;
      end loop;
      if End_P < L'First then
         return "";
      end if;
      declare
         Head : constant String := L (L'First .. End_P);
         --  strip leading articles for stability
         H2 : constant String := To_Lower (Head);
      begin
         if H2'Length > 4 and then H2 (H2'First .. H2'First + 3) = "the " then
            return Head (Head'First + 4 .. Head'Last);
         elsif H2'Length > 3 and then H2 (H2'First .. H2'First + 2) = "an " then
            return Head (Head'First + 3 .. Head'Last);
         elsif H2'Length > 2 and then H2 (H2'First .. H2'First + 1) = "a " then
            return Head (Head'First + 2 .. Head'Last);
         elsif H2'Length > 3 and then H2 (H2'First .. H2'First + 2) = "to " then
            return Head (Head'First + 3 .. Head'Last);
         end if;
         return Head;
      end;
   end Clean_Gloss;

   function Score_Gloss (G : String) return Long_Float is
      C : constant String := Clean_Gloss (G);
      S : Long_Float := 0.0;
   begin
      if C'Length = 0 then
         return 0.0;
      end if;
      S := 0.5;
      if C'Length <= 12 then
         S := S + 0.3;
      elsif C'Length <= 24 then
         S := S + 0.15;
      end if;
      if not Contains (To_Lower (C), " ") then
         S := S + 0.15;  -- single token preferred for map
      end if;
      return S;
   end Score_Gloss;

end PFLT_Gloss_Quality;
