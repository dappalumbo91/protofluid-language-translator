package body PFLT_Teach
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

   procedure Put_Pair
     (T : in out Teach_Result;
      Gloss, Form, Lang : String)
   is
      procedure Fill (Target : in out String; Src : String) is
         N : constant Natural := Natural'Min (Src'Length, Target'Length);
      begin
         Target := (others => ' ');
         if N > 0 then
            Target (1 .. N) := Src (Src'First .. Src'First + N - 1);
         end if;
      end Fill;
   begin
      if T.Count >= T.Pairs'Last then
         return;
      end if;
      T.Count := T.Count + 1;
      T.Pairs (T.Count).Ok := True;
      Fill (T.Pairs (T.Count).Gloss, Gloss);
      Fill (T.Pairs (T.Count).Form, Form);
      Fill (T.Pairs (T.Count).Lang, Lang);
   end Put_Pair;

   function Build (Text : String) return Teach_Result is
      T : Teach_Result;
      L : constant String := To_Lower (Text);
      Lang : String (1 .. 8) := "la      ";
   begin
      T.Label := "Latin           ";
      if Contains (L, "greek") then
         Lang := "grc     ";
         T.Label := "Greek           ";
      elsif Contains (L, "old english") or else Contains (L, "anglo") then
         Lang := "ang     ";
         T.Label := "Old English     ";
      end if;

      if Lang (1 .. 2) = "la" then
         if Contains (L, "water") then
            Put_Pair (T, "water", "aqua", "la");
         end if;
         if Contains (L, "hand") then
            Put_Pair (T, "hand", "manus", "la");
         end if;
         if Contains (L, "language") or else Contains (L, "tongue") then
            Put_Pair (T, "language", "lingua", "la");
         end if;
         if Contains (L, "word") then
            Put_Pair (T, "word", "verbum", "la");
         end if;
         if Contains (L, "king") then
            Put_Pair (T, "king", "rex", "la");
         end if;
         if Contains (L, "law") then
            Put_Pair (T, "law", "lex", "la");
         end if;
         if Contains (L, "god") then
            Put_Pair (T, "god", "deus", "la");
         end if;
         if Contains (L, "temple") then
            Put_Pair (T, "temple", "templum", "la");
         end if;
      elsif Lang (1 .. 3) = "grc" then
         if Contains (L, "word") then
            Put_Pair (T, "word", "logos", "grc");
         end if;
         if Contains (L, "god") then
            Put_Pair (T, "god", "theos", "grc");
         end if;
         if Contains (L, "man") or else Contains (L, "human") then
            Put_Pair (T, "man", "anthropos", "grc");
         end if;
         if Contains (L, "soul") then
            Put_Pair (T, "soul", "psyche", "grc");
         end if;
      end if;
      return T;
   end Build;

   function Format_Block (T : Teach_Result) return String is
      Buf : String (1 .. 512) := (others => ' ');
      L   : Natural := 0;
      procedure App (S : String) is
      begin
         for C of S loop
            exit when L >= Buf'Last;
            L := L + 1;
            Buf (L) := C;
         end loop;
      end App;
      procedure Trim_App (S : String) is
         R : Natural := S'Last;
      begin
         while R >= S'First and then S (R) = ' ' loop
            R := R - 1;
         end loop;
         if R >= S'First then
            App (S (S'First .. R));
         end if;
      end Trim_App;
   begin
      if T.Count = 0 then
         return "";
      end if;
      App ("Teaching (");
      Trim_App (T.Label);
      App (" form <-> English gloss):");
      App (String'(1 => ASCII.LF));
      for I in 1 .. T.Count loop
         App ("  . ");
         Trim_App (T.Pairs (I).Gloss);
         App (" <-> ");
         Trim_App (T.Pairs (I).Form);
         App (String'(1 => ASCII.LF));
      end loop;
      return Buf (1 .. L);
   end Format_Block;

end PFLT_Teach;
