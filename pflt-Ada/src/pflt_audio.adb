with Ada.Text_IO; use Ada.Text_IO;
with PFLT_Constants;
with PFLT_Domains;
with PFLT_Scalar;
with PFLT_Store;
with PFLT_Translate;

package body PFLT_Audio
  with SPARK_Mode => Off
is
   use PFLT_Constants;

   procedure Put_Str
     (Buf : in out String; Last : in out Natural; Piece : String)
   is
   begin
      for C of Piece loop
         exit when Last >= Buf'Last;
         Last := Last + 1;
         Buf (Last) := C;
      end loop;
   end Put_Str;

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

   --  Starter G2P (Latin / English product floor). Full Phoible later.
   function G2P (Word, Lang : String) return String is
      W : constant String := To_Lower (Word);
      L : constant String := To_Lower (Lang);
   begin
      if L = "la" or else L = "lat" then
         if W = "aqua" then
            return "a.kwa";
         elsif W = "lingua" then
            return "lin.gwa";
         elsif W = "manus" then
            return "ma.nus";
         elsif W = "rex" then
            return "reks";
         elsif W = "lux" then
            return "lu:ks";
         elsif W = "deus" then
            return "de.us";
         elsif W = "lex" then
            return "leks";
         elsif W = "vita" then
            return "wi.ta";
         elsif W = "virtus" then
            return "wir.tus";
         end if;
      end if;
      if L = "en" then
         if W = "water" then
            return "wO.t@r";
         elsif W = "language" then
            return "laN.gwIdZ";
         elsif W = "law" then
            return "lO:";
         elsif W = "king" then
            return "kIN";
         elsif W = "sun" then
            return "sVn";
         elsif W = "soul" then
            return "soUl";
         elsif W = "temple" then
            return "tem.p@l";
         end if;
      end if;
      if L = "grc" or else L = "el" then
         if W = "logos" then
            return "lo.gos";
         elsif W = "theos" then
            return "t_e.os";
         end if;
      end if;
      --  Fallback: approximate from orthography
      return W;
   end G2P;

   function Features_Of (IPA : String) return Artic_Features is
      F : Artic_Features;
      Has_Voice : Boolean := False;
      Has_Nas   : Boolean := False;
      Has_Front : Boolean := False;
      Has_Back  : Boolean := False;
      Has_Open  : Boolean := False;
      Has_Close : Boolean := False;
      Segs      : Natural := 0;
   begin
      for C of IPA loop
         if C /= '.' and then C /= ' ' and then C /= ':' and then C /= ''' then
            Segs := Segs + 1;
         end if;
         case C is
            when 'b' | 'd' | 'g' | 'z' | 'v' | 'm' | 'n' | 'l' | 'r' | 'w' |
              'j' | 'a' | 'e' | 'i' | 'o' | 'u' | 'A' | 'E' | 'I' | 'O' |
              'U' | '@' | 'V' =>
               Has_Voice := True;
            when others =>
               null;
         end case;
         if C = 'm' or else C = 'n' or else C = 'N' then
            Has_Nas := True;
         end if;
         if C = 'i' or else C = 'e' or else C = 'I' or else C = 'E' then
            Has_Front := True;
         end if;
         if C = 'u' or else C = 'o' or else C = 'U' or else C = 'O' then
            Has_Back := True;
         end if;
         if C = 'a' or else C = 'A' or else C = 'O' then
            Has_Open := True;
         end if;
         if C = 'i' or else C = 'u' or else C = 'I' or else C = 'U' then
            Has_Close := True;
         end if;
         if C = ':' then
            F.Length := 1.0;
         end if;
         if C = ''' then
            F.Stress := 1.0;
         end if;
      end loop;
      F.N_Seg := Segs;
      F.Voicing := (if Has_Voice then 1.0 else 0.3);
      F.Nasality := (if Has_Nas then 1.0 else 0.0);
      if Has_Front and then not Has_Back then
         F.Frontness := 0.8;
      elsif Has_Back and then not Has_Front then
         F.Frontness := 0.2;
      else
         F.Frontness := 0.5;
      end if;
      if Has_Open and then not Has_Close then
         F.Openness := 0.8;
      elsif Has_Close and then not Has_Open then
         F.Openness := 0.2;
      else
         F.Openness := 0.5;
      end if;
      return F;
   end Features_Of;

   function Articulate
     (Word : String; Lang : String := "la") return Articulation
   is
      A    : Articulation;
      IPA0 : constant String := G2P (Word, Lang);
      Hit  : constant String := PFLT_Store.Lookup (Word);
      Dom  : constant PFLT_Domains.Domain_Id := PFLT_Domains.Linguistic;
      Inp  : PFLT_Scalar.Scalar_Input :=
        PFLT_Domains.Default_Input (Dom);
   begin
      A.Text_Last := Natural'Min (Word'Length, A.Text'Length);
      if A.Text_Last > 0 then
         A.Text (1 .. A.Text_Last) :=
           Word (Word'First .. Word'First + A.Text_Last - 1);
      end if;
      A.Lang_Last := Natural'Min (Lang'Length, A.Lang'Length);
      if A.Lang_Last > 0 then
         A.Lang (1 .. A.Lang_Last) :=
           Lang (Lang'First .. Lang'First + A.Lang_Last - 1);
      end if;
      A.IPA_Last := Natural'Min (IPA0'Length, A.IPA'Length);
      if A.IPA_Last > 0 then
         A.IPA (1 .. A.IPA_Last) :=
           IPA0 (IPA0'First .. IPA0'First + A.IPA_Last - 1);
      end if;
      A.Features := Features_Of (IPA0);

      --  FSOT modulates tempo/energy (seed S, not free TTS knobs)
      Inp.Delta_Psi :=
        0.5 + 0.3 * A.Features.Frontness + 0.2 * A.Features.Voicing;
      Inp.Delta_Theta :=
        0.5 + 0.4 * A.Features.Openness + 0.1 * A.Features.Nasality;
      Inp.Recent_Hits := Long_Float (A.Features.N_Seg);
      A.Panel := PFLT_Scalar.Compute_Panel (Inp);
      A.Tempo :=
        0.85 + 0.30 * Long_Float'Min (1.0, Long_Float'Max (0.0, A.Panel.S));
      A.Energy :=
        0.70
        + 0.25 * A.Features.Voicing
        + 0.15 * A.Features.Stress
        + 0.10 * A.Features.Length;

      if Hit'Length > 0 then
         A.Gloss_Last := Natural'Min (Hit'Length, A.Gloss'Length);
         A.Gloss (1 .. A.Gloss_Last) :=
           Hit (Hit'First .. Hit'First + A.Gloss_Last - 1);
      else
         declare
            Tr : constant PFLT_Translate.Translate_Result :=
              PFLT_Translate.Translate (Word);
         begin
            A.Gloss_Last := Tr.Gloss_Last;
            if A.Gloss_Last > 0 then
               A.Gloss (1 .. A.Gloss_Last) := Tr.Gloss (1 .. Tr.Gloss_Last);
            end if;
         end;
      end if;

      Put_Str
        (A.Notes, A.Notes_Last,
         "articulatory+FSOT; waveform optional external only");
      return A;
   end Articulate;

   function Articulate_Phrase
     (Text : String; Lang : String := "la") return Articulation
   is
      --  First token articulation + whole-phrase gloss via translate
      I     : Natural := Text'First;
      Start : Natural;
      Word  : String (1 .. 64) := (others => ' ');
      WL    : Natural := 0;
      A     : Articulation;
      Tr    : PFLT_Translate.Translate_Result;
   begin
      while I <= Text'Last and then Text (I) = ' ' loop
         I := I + 1;
      end loop;
      Start := I;
      while I <= Text'Last and then Text (I) /= ' ' loop
         I := I + 1;
      end loop;
      if Start <= Text'Last and then I > Start then
         WL := Natural'Min (I - Start, Word'Length);
         Word (1 .. WL) := Text (Start .. Start + WL - 1);
         A := Articulate (Word (1 .. WL), Lang);
      else
         A := Articulate ("", Lang);
      end if;
      --  overwrite gloss with full phrase map
      Tr := PFLT_Translate.Translate (Text);
      A.Gloss := (others => ' ');
      A.Gloss_Last := Tr.Gloss_Last;
      if A.Gloss_Last > 0 then
         A.Gloss (1 .. A.Gloss_Last) := Tr.Gloss (1 .. Tr.Gloss_Last);
      end if;
      A.Text_Last := Natural'Min (Text'Length, A.Text'Length);
      if A.Text_Last > 0 then
         A.Text (1 .. A.Text_Last) :=
           Text (Text'First .. Text'First + A.Text_Last - 1);
      end if;
      return A;
   end Articulate_Phrase;

   function IPA_Slice (A : Articulation) return String is
   begin
      if A.IPA_Last = 0 then
         return "";
      end if;
      return A.IPA (1 .. A.IPA_Last);
   end IPA_Slice;

   function Gloss_Slice (A : Articulation) return String is
   begin
      if A.Gloss_Last = 0 then
         return "";
      end if;
      return A.Gloss (1 .. A.Gloss_Last);
   end Gloss_Slice;

   procedure Print_One (A : Articulation) is
      package FIO is new Ada.Text_IO.Float_IO (Long_Float);
   begin
      Put_Line
        ("[audio · lang="
         & A.Lang (1 .. A.Lang_Last)
         & " · text="
         & A.Text (1 .. A.Text_Last)
         & " · pin=D1D38A]");
      Put_Line ("  ipa:   " & IPA_Slice (A));
      Put_Line ("  gloss: " & Gloss_Slice (A));
      Put ("  features voice/nas/front/open: ");
      FIO.Put (A.Features.Voicing, Fore => 1, Aft => 2, Exp => 0);
      Put ("/");
      FIO.Put (A.Features.Nasality, Fore => 1, Aft => 2, Exp => 0);
      Put ("/");
      FIO.Put (A.Features.Frontness, Fore => 1, Aft => 2, Exp => 0);
      Put ("/");
      FIO.Put (A.Features.Openness, Fore => 1, Aft => 2, Exp => 0);
      New_Line;
      Put ("  tempo=");
      FIO.Put (A.Tempo, Fore => 1, Aft => 3, Exp => 0);
      Put (" energy=");
      FIO.Put (A.Energy, Fore => 1, Aft => 3, Exp => 0);
      Put (" S=");
      FIO.Put (A.Panel.S, Fore => 1, Aft => 6, Exp => 0);
      New_Line;
   end Print_One;

   procedure Run_Demo is
   begin
      Put_Line ("=== Ada FSOT articulatory audio channel ===");
      Put_Line
        ("IPA + place/manner proxies; S→tempo/energy; no free TTS knobs");
      New_Line;
      Print_One (Articulate ("aqua", "la"));
      Print_One (Articulate ("lingua", "la"));
      Print_One (Articulate ("water", "en"));
      Print_One (Articulate ("logos", "grc"));
      Print_One (Articulate_Phrase ("aqua lingua manus", "la"));
   end Run_Demo;

end PFLT_Audio;
