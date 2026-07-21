with PFLT_Domains;
with PFLT_Lexicon;
with PFLT_Morph;
with PFLT_Pathway;
with PFLT_Route;
with PFLT_Scalar;
with PFLT_Store;

package body PFLT_Translate
  with SPARK_Mode => Off
is

   function Looks_Junk (Tok : String) return Boolean is
      Has_Vowel : Boolean := False;
   begin
      if Tok'Length < 3 then
         return False;
      end if;
      --  triple letter
      for I in Tok'First .. Tok'Last - 2 loop
         if Tok (I) = Tok (I + 1) and then Tok (I) = Tok (I + 2) then
            return True;
         end if;
      end loop;
      for C of Tok loop
         if C = 'a' or else C = 'e' or else C = 'i' or else C = 'o'
           or else C = 'u' or else C = 'y'
           or else C = 'A' or else C = 'E' or else C = 'I' or else C = 'O'
           or else C = 'U' or else C = 'Y'
         then
            Has_Vowel := True;
         end if;
      end loop;
      if not Has_Vowel and then Tok'Length >= 4 then
         return True;
      end if;
      return False;
   end Looks_Junk;

   function Gloss_Slice (R : Translate_Result) return String is
   begin
      if R.Gloss_Last = 0 then
         return "";
      end if;
      return R.Gloss (1 .. R.Gloss_Last);
   end Gloss_Slice;

   procedure Append
     (Buf : in out String; Last : in out Natural; Piece : String)
   is
   begin
      for C of Piece loop
         exit when Last >= Buf'Last;
         Last := Last + 1;
         Buf (Last) := C;
      end loop;
   end Append;

   function Translate (Text : String) return Translate_Result is
      R     : Translate_Result;
      I     : Natural := Text'First;
      Start : Natural;
      First : Boolean := True;
      Seed : PFLT_Lexicon.Gloss_Result;
      Morph : PFLT_Morph.Morph_Hit;
      Path  : constant PFLT_Pathway.Pathway_Result :=
        PFLT_Pathway.Reason (Text, 3);
   begin
      --  Prefer pathway primary when confident; else keyword route
      if Path.Conf >= 0.55 then
         R.Domain := Path.Primary;
      else
         R.Domain := PFLT_Route.Route_Domain (Text);
      end if;
      R.Gloss := (others => ' ');
      R.Gloss_Last := 0;
      R.Unresolved_N := 0;
      R.Token_N := 0;
      R.Mapped_N := 0;
      R.Morph_N := 0;
      R.Panel :=
        PFLT_Scalar.Compute_Panel (PFLT_Domains.Default_Input (R.Domain));

      while I <= Text'Last loop
         while I <= Text'Last and then Text (I) = ' ' loop
            I := I + 1;
         end loop;
         exit when I > Text'Last;
         Start := I;
         while I <= Text'Last and then Text (I) /= ' ' loop
            I := I + 1;
         end loop;
         declare
            Tok_Raw : constant String := Text (Start .. I - 1);
            Tok     : String (Tok_Raw'Range);
            Hit     : String (1 .. 96);
            Hit_L   : Natural := 0;
            Out_G   : String (1 .. 96) := (others => ' ');
            Out_L   : Natural := 0;
            Ok      : Boolean := False;

            function Lower_Tok return String is
               R : String (Tok_Raw'Range);
            begin
               for J in Tok_Raw'Range loop
                  if Tok_Raw (J) >= 'A' and then Tok_Raw (J) <= 'Z' then
                     R (J) := Character'Val
                       (Character'Pos (Tok_Raw (J))
                        - Character'Pos ('A')
                        + Character'Pos ('a'));
                  else
                     R (J) := Tok_Raw (J);
                  end if;
               end loop;
               return R;
            end Lower_Tok;

            function Is_Closed (S : String) return Boolean is
            begin
               return S = "a" or else S = "an" or else S = "the"
                 or else S = "and" or else S = "in" or else S = "of"
                 or else S = "to" or else S = "for" or else S = "me"
                 or else S = "my" or else S = "is" or else S = "or"
                 or else S = "on" or else S = "at" or else S = "by"
                 or else S = "tell" or else S = "about" or else S = "with"
                 or else S = "from" or else S = "what" or else S = "who"
                 or else S = "how" or else S = "when" or else S = "where";
            end Is_Closed;

            function Clean_Hit (H : String) return String is
            begin
               if H'Length = 0 then
                  return "";
               end if;
               if H'Length >= 7
                 and then
                   (H (H'First .. H'First + 6) = "dative "
                    or else H (H'First .. H'First + 6) = "The com"
                    or else H (H'First .. H'First + 6) = "accusat")
               then
                  return "";
               end if;
               --  Prefer short content glosses
               if H'Length <= 40 then
                  return H;
               end if;
               declare
                  P : Natural := H'Last;
               begin
                  while P >= H'First and then H (P) /= ' ' loop
                     P := P - 1;
                  end loop;
                  if P < H'Last and then H'Last - P <= 24 then
                     return H (P + 1 .. H'Last);
                  end if;
               end;
               return "";
            end Clean_Hit;
         begin
            Tok := Lower_Tok;
            declare
               Raw_Hit : constant String := PFLT_Store.Lookup (Tok);
               CH : constant String := Clean_Hit (Raw_Hit);
            begin
               if CH'Length > 0 then
                  Hit_L := Natural'Min (CH'Length, Hit'Length);
                  Hit (1 .. Hit_L) := CH (CH'First .. CH'First + Hit_L - 1);
               end if;
            end;

            R.Token_N := R.Token_N + 1;
            if Looks_Junk (Tok) then
               Append (Out_G, Out_L, "unresolved");
               R.Unresolved_N := R.Unresolved_N + 1;
            elsif Is_Closed (Tok) then
               Append (Out_G, Out_L, Tok);
               Ok := True;
            else
               Seed := PFLT_Lexicon.Map_Token (Tok);
               if Seed.Found then
                  Append (Out_G, Out_L, Seed.Gloss (1 .. Seed.Gloss_Last));
                  Ok := True;
               elsif Hit_L > 0 then
                  Append (Out_G, Out_L, Hit (1 .. Hit_L));
                  Ok := True;
               else
                  Morph := PFLT_Morph.Resolve (Tok);
                  if Morph.Found then
                     Append
                       (Out_G, Out_L, Morph.Gloss (1 .. Morph.Gloss_Last));
                     Ok := True;
                     R.Morph_N := R.Morph_N + 1;
                  else
                     Append (Out_G, Out_L, "unresolved");
                     R.Unresolved_N := R.Unresolved_N + 1;
                  end if;
               end if;
            end if;
            if Ok then
               R.Mapped_N := R.Mapped_N + 1;
            end if;
            if not First then
               Append (R.Gloss, R.Gloss_Last, " ");
            end if;
            First := False;
            Append (R.Gloss, R.Gloss_Last, Out_G (1 .. Out_L));
         end;
      end loop;

      if R.Token_N > 0 then
         R.Map_Rate :=
           Long_Float (R.Mapped_N) / Long_Float (R.Token_N);
      else
         R.Map_Rate := 0.0;
      end if;
      return R;
   end Translate;

end PFLT_Translate;
