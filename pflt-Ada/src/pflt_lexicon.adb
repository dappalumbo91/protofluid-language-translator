package body PFLT_Lexicon
  with SPARK_Mode => On
is

   function Lower_Char (C : Character) return Character is
   begin
      if C >= 'A' and then C <= 'Z' then
         return Character'Val (Character'Pos (C) - Character'Pos ('A')
                               + Character'Pos ('a'));
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

   function Pad_Gloss (G : String) return Gloss_Result is
      R : Gloss_Result;
      N : constant Natural := Natural'Min (G'Length, Max_Gloss_Len);
   begin
      R.Found := True;
      R.Gloss := (others => ' ');
      R.Gloss_Last := N;
      if N > 0 then
         R.Gloss (1 .. N) := G (G'First .. G'First + N - 1);
      end if;
      return R;
   end Pad_Gloss;

   function Map_Token (Form : String) return Gloss_Result is
      F : constant String := To_Lower (Form);
      Empty : Gloss_Result;
   begin
      Empty.Found := False;
      Empty.Gloss := (others => ' ');
      Empty.Gloss_Last := 0;

      --  Classical + modern converse seeds (product demos; beat peel pollution)
      if F = "aqua" or else F = "agua" then
         return Pad_Gloss ("water");
      elsif F = "manus" or else F = "manibus" then
         return Pad_Gloss ("hand");
      elsif F = "lingua" then
         return Pad_Gloss ("language");
      elsif F = "verbum" then
         return Pad_Gloss ("word");
      elsif F = "logos" then
         return Pad_Gloss ("word");
      elsif F = "theos" or else F = "deus" then
         return Pad_Gloss ("god");
      elsif F = "rex" then
         return Pad_Gloss ("king");
      elsif F = "lex" then
         return Pad_Gloss ("law");
      elsif F = "templum" or else F = "temple" then
         return Pad_Gloss ("temple");
      elsif F = "zeus" then
         return Pad_Gloss ("zeus");
      elsif F = "divine" then
         return Pad_Gloss ("divine");
      elsif F = "soul" then
         return Pad_Gloss ("soul");
      elsif F = "water" then
         return Pad_Gloss ("water");
      elsif F = "hand" or else F = "hands" then
         return Pad_Gloss ("hand");
      elsif F = "latin" then
         return Pad_Gloss ("latin");
      elsif F = "hola" or else F = "bonjour" or else F = "ciao"
        or else F = "hallo" or else F = "hello"
      then
         return Pad_Gloss ("hello");
      elsif F = "mundo" or else F = "world" then
         return Pad_Gloss ("world");
      elsif F = "gracias" or else F = "merci" or else F = "danke"
        or else F = "thanks"
      then
         return Pad_Gloss ("thanks");
      elsif F = "amor" then
         return Pad_Gloss ("love");
      elsif F = "vita" then
         return Pad_Gloss ("life");
      elsif F = "pax" then
         return Pad_Gloss ("peace");
      elsif F = "casa" then
         return Pad_Gloss ("house");
      elsif F = "libro" then
         return Pad_Gloss ("book");
      elsif F = "luna" then
         return Pad_Gloss ("moon");
      elsif F = "terra" then
         return Pad_Gloss ("earth");
      elsif F = "mare" then
         return Pad_Gloss ("sea");
      elsif F = "ignis" then
         return Pad_Gloss ("fire");
      elsif F = "ventus" then
         return Pad_Gloss ("wind");
      else
         return Empty;
      end if;
   end Map_Token;

   function Translate_Exact (Text : String) return String is
      --  Simple space tokenizer; build result in bounded buffer
      Buf : String (1 .. 512) := (others => ' ');
      Last : Natural := 0;
      I : Natural := Text'First;
      Start : Natural;
      Tok : String (1 .. Max_Form_Len);
      Tok_Last : Natural;
      G : Gloss_Result;
      First_Out : Boolean := True;
   begin
      while I <= Text'Last loop
         while I <= Text'Last and then Text (I) = ' ' loop
            I := I + 1;
         end loop;
         exit when I > Text'Last;
         Start := I;
         while I <= Text'Last and then Text (I) /= ' ' loop
            I := I + 1;
         end loop;
         Tok_Last := Natural'Min (I - Start, Max_Form_Len);
         Tok := (others => ' ');
         if Tok_Last > 0 then
            Tok (1 .. Tok_Last) := Text (Start .. Start + Tok_Last - 1);
            G := Map_Token (Tok (1 .. Tok_Last));
            if not First_Out and then Last < Buf'Last then
               Last := Last + 1;
               Buf (Last) := ' ';
            end if;
            First_Out := False;
            if G.Found then
               for J in 1 .. G.Gloss_Last loop
                  exit when Last >= Buf'Last;
                  Last := Last + 1;
                  Buf (Last) := G.Gloss (J);
               end loop;
            else
               declare
                  U : constant String := "unresolved";
               begin
                  for J in U'Range loop
                     exit when Last >= Buf'Last;
                     Last := Last + 1;
                     Buf (Last) := U (J);
                  end loop;
               end;
            end if;
         end if;
      end loop;
      if Last = 0 then
         return "";
      end if;
      return Buf (1 .. Last);
   end Translate_Exact;

end PFLT_Lexicon;
