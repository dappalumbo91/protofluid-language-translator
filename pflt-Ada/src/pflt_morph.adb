with PFLT_Store;

package body PFLT_Morph
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

   procedure Set_Method (H : in out Morph_Hit; M : String) is
      N : constant Natural := Natural'Min (M'Length, H.Method'Length);
   begin
      H.Method := (others => ' ');
      H.Method_Last := N;
      if N > 0 then
         H.Method (1 .. N) := M (M'First .. M'First + N - 1);
      end if;
   end Set_Method;

   procedure Set_Gloss (H : in out Morph_Hit; G : String) is
      N : constant Natural := Natural'Min (G'Length, H.Gloss'Length);
   begin
      H.Found := True;
      H.Gloss := (others => ' ');
      H.Gloss_Last := N;
      if N > 0 then
         H.Gloss (1 .. N) := G (G'First .. G'First + N - 1);
      end if;
   end Set_Gloss;

   function Try_Key (Key : String; Method : String) return Morph_Hit is
      G : constant String := PFLT_Store.Lookup (Key);
      H : Morph_Hit;
   begin
      if G'Length > 0 then
         Set_Gloss (H, G);
         Set_Method (H, Method);
      end if;
      return H;
   end Try_Key;

   function Try_Neighbor (Form : String) return Morph_Hit is
      --  Cap dist=1 via store policy for short forms; request 1 here
      --  to cut false-positive gloss pollution on open-set eval.
      G : constant String := PFLT_Store.Lookup_Neighbor (Form, 1);
      H : Morph_Hit;
   begin
      if G'Length > 0 and then Form'Length >= 5 then
         Set_Gloss (H, G);
         Set_Method (H, "edit-sim");
      end if;
      return H;
   end Try_Neighbor;

   function Ends_With (S, Suf : String) return Boolean is
   begin
      if Suf'Length = 0 then
         return True;
      end if;
      if S'Length < Suf'Length then
         return False;
      end if;
      return S (S'Last - Suf'Length + 1 .. S'Last) = Suf;
   end Ends_With;

   function Resolve_LA (Form : String) return Morph_Hit is
      F : constant String := To_Lower (Form);
      H : Morph_Hit;

      procedure Probe (Key, Meth : String) is
         T : Morph_Hit;
      begin
         if H.Found then
            return;
         end if;
         T := Try_Key (Key, Meth);
         if T.Found then
            H := T;
         end if;
      end Probe;

      procedure Try_Strip (Suf : String) is
      begin
         if H.Found then
            return;
         end if;
         if Ends_With (F, Suf) and then F'Length > Suf'Length + 2 then
            declare
               Stem : constant String :=
                 F (F'First .. F'Last - Suf'Length);
            begin
               Probe (Stem, "la-stem");
               Probe (Stem & "us", "la-us");
               Probe (Stem & "um", "la-um");
               Probe (Stem & "a", "la-a");
               Probe (Stem & "ae", "la-ae");
               Probe (Stem & "is", "la-is");
               Probe (Stem & "os", "la-os");
               Probe (Stem & "on", "la-on");
               Probe (Stem & "o", "la-o");
               Probe (Stem & "e", "la-e");
               Probe (Stem & "i", "la-i");
               Probe (Stem & "or", "la-or");
               Probe (Stem & "an", "la-an");
               Probe (Stem & "are", "la-are");
               Probe (Stem & "ere", "la-ere");
               Probe (Stem & "ire", "la-ire");
               Probe (Stem & "ari", "la-ari");
            end;
         end if;
      end Try_Strip;
   begin
      Probe (F, "exact");
      --  Long endings first (fill open-set partials)
      Try_Strip ("avissent");
      Try_Strip ("avissem");
      Try_Strip ("avisses");
      Try_Strip ("avisse");
      Try_Strip ("averunt");
      Try_Strip ("averat");
      Try_Strip ("ueritis");
      Try_Strip ("uerimus");
      Try_Strip ("uerunt");
      Try_Strip ("uissent");
      Try_Strip ("ationibus");
      Try_Strip ("ationem");
      Try_Strip ("ationis");
      Try_Strip ("ationes");
      Try_Strip ("ationum");
      Try_Strip ("tionibus");
      Try_Strip ("ionibus");
      Try_Strip ("tatibus");
      Try_Strip ("itatem");
      Try_Strip ("itatis");
      Try_Strip ("oribus");
      Try_Strip ("issimus");
      Try_Strip ("issima");
      Try_Strip ("issimum");
      Try_Strip ("abantur");
      Try_Strip ("ebantur");
      Try_Strip ("iebant");
      Try_Strip ("abant");
      Try_Strip ("ebant");
      Try_Strip ("ibant");
      Try_Strip ("untur");
      Try_Strip ("antur");
      Try_Strip ("entur");
      Try_Strip ("tionem");
      Try_Strip ("ionem");
      Try_Strip ("tatem");
      Try_Strip ("orem");
      Try_Strip ("ando");
      Try_Strip ("endo");
      Try_Strip ("undo");
      Try_Strip ("orum");
      Try_Strip ("arum");
      Try_Strip ("ibus");
      Try_Strip ("amus");
      Try_Strip ("atis");
      Try_Strip ("imus");
      Try_Strip ("itis");
      Try_Strip ("erunt");
      Try_Strip ("isset");
      Try_Strip ("isse");
      Try_Strip ("abo");
      Try_Strip ("abis");
      Try_Strip ("abit");
      Try_Strip ("are");
      Try_Strip ("ere");
      Try_Strip ("ire");
      Try_Strip ("ari");
      Try_Strip ("eri");
      Try_Strip ("iri");
      Try_Strip ("avi");
      Try_Strip ("tur");
      Try_Strip ("ntur");
      Try_Strip ("unt");
      Try_Strip ("ant");
      Try_Strip ("ent");
      Try_Strip ("ius");
      Try_Strip ("ium");
      Try_Strip ("iae");
      Try_Strip ("iam");
      Try_Strip ("us");
      Try_Strip ("um");
      Try_Strip ("am");
      Try_Strip ("ae");
      Try_Strip ("as");
      Try_Strip ("is");
      Try_Strip ("os");
      Try_Strip ("em");
      Try_Strip ("es");
      Try_Strip ("or");
      Try_Strip ("it");
      Try_Strip ("at");
      --  Single-letter peels only on longer forms (cut false stems)
      if F'Length >= 7 then
         Try_Strip ("a");
         Try_Strip ("i");
         Try_Strip ("o");
         Try_Strip ("e");
      end if;
      return H;
   end Resolve_LA;

   function Resolve_GRC_LAT (Form : String) return Morph_Hit is
      F : constant String := To_Lower (Form);
      H : Morph_Hit;

      procedure Probe (Key, Meth : String) is
         T : Morph_Hit;
      begin
         if H.Found then
            return;
         end if;
         T := Try_Key (Key, Meth);
         if T.Found then
            H := T;
         end if;
      end Probe;

      procedure Try_Strip (Suf : String) is
      begin
         if H.Found then
            return;
         end if;
         if Ends_With (F, Suf) and then F'Length > Suf'Length + 2 then
            declare
               Stem : constant String :=
                 F (F'First .. F'Last - Suf'Length);
            begin
               Probe (Stem, "grc-stem");
               Probe (Stem & "os", "grc-os");
               Probe (Stem & "on", "grc-on");
               Probe (Stem & "e", "grc-e");
               Probe (Stem & "a", "grc-a");
               Probe (Stem & "is", "grc-is");
               --  Common Greek lemma restorations (Latinized + UTF-8)
               Probe (Stem & "os", "grc-os");
               Probe (Stem & "us", "grc-us");
               Probe (Stem & "os", "grc-os");
            end;
         end if;
      end Try_Strip;
   begin
      Probe (F, "exact");
      Try_Strip ("eous");
      Try_Strip ("ious");
      Try_Strip ("icus");
      Try_Strip ("ica");
      Try_Strip ("icum");
      Try_Strip ("esis");
      Try_Strip ("osis");
      Try_Strip ("ismos");
      Try_Strip ("ikos");
      Try_Strip ("ike");
      Try_Strip ("ikon");
      Try_Strip ("ion");
      Try_Strip ("eus");
      Try_Strip ("ios");
      Try_Strip ("ous");
      Try_Strip ("ein");
      Try_Strip ("ai");
      Try_Strip ("oi");
      Try_Strip ("on");
      Try_Strip ("os");
      Try_Strip ("es");
      Try_Strip ("as");
      Try_Strip ("is");
      Try_Strip ("e");
      Try_Strip ("a");
      --  UTF-8 Greek multi-byte endings (Latin-1 not enough for full Greek;
      --  common 2-byte sequences when form stored as UTF-8 bytes in String)
      --  Strip Latinized translit endings already covered above.
      return H;
   end Resolve_GRC_LAT;

   function Resolve_ANG (Form : String) return Morph_Hit is
      F : constant String := To_Lower (Form);
      H : Morph_Hit;

      procedure Probe (Key, Meth : String) is
         T : Morph_Hit;
      begin
         if H.Found then
            return;
         end if;
         T := Try_Key (Key, Meth);
         if T.Found then
            H := T;
         end if;
      end Probe;

      procedure Try_Strip (Suf : String) is
      begin
         if H.Found then
            return;
         end if;
         if Ends_With (F, Suf) and then F'Length > Suf'Length + 2 then
            declare
               Stem : constant String :=
                 F (F'First .. F'Last - Suf'Length);
            begin
               Probe (Stem, "ang-stem");
               Probe (Stem & "an", "ang-an");
               Probe (Stem & "a", "ang-a");
               Probe (Stem & "e", "ang-e");
            end;
         end if;
      end Try_Strip;
   begin
      Probe (F, "exact");
      Try_Strip ("nesse");
      Try_Strip ("scipe");
      Try_Strip ("ende");
      Try_Strip ("unga");
      Try_Strip ("ian");
      Try_Strip ("lice");
      Try_Strip ("ath");
      Try_Strip ("eth");
      Try_Strip ("ode");
      Try_Strip ("um");
      Try_Strip ("an");
      Try_Strip ("as");
      Try_Strip ("es");
      Try_Strip ("e");
      Try_Strip ("a");
      return H;
   end Resolve_ANG;

   function Resolve_EN (Form : String) return Morph_Hit is
      F : constant String := To_Lower (Form);
      H : Morph_Hit;

      procedure Probe (Key, Meth : String) is
         T : Morph_Hit;
      begin
         if H.Found then
            return;
         end if;
         T := Try_Key (Key, Meth);
         if T.Found then
            H := T;
         end if;
      end Probe;

      procedure Try_Strip (Suf : String) is
      begin
         if H.Found then
            return;
         end if;
         if Ends_With (F, Suf) and then F'Length > Suf'Length + 2 then
            declare
               Stem : constant String :=
                 F (F'First .. F'Last - Suf'Length);
            begin
               Probe (Stem, "en-stem");
               Probe (Stem & "e", "en-e");
               Probe (Stem & "y", "en-y");
            end;
         end if;
      end Try_Strip;
   begin
      Probe (F, "exact");
      Try_Strip ("ation");
      Try_Strip ("tion");
      Try_Strip ("ness");
      Try_Strip ("ment");
      Try_Strip ("ing");
      Try_Strip ("ed");
      Try_Strip ("ly");
      Try_Strip ("es");
      Try_Strip ("s");
      return H;
   end Resolve_EN;

   function Resolve_Progressive (Form : String) return Morph_Hit is
      --  Universal char strip; prefer LONGEST stem (avoid short pollution).
      F : constant String := To_Lower (Form);
      H : Morph_Hit;
      Best : Morph_Hit;
      Best_Len : Natural := 0;
   begin
      if F'Length < 3 then
         return H;
      end if;
      --  suffixes dropped: try longer stems first (small Drop first)
      for Drop in 1 .. Natural'Min (12, F'Length - 2) loop
         declare
            Stem : constant String := F (F'First .. F'Last - Drop);
            T    : Morph_Hit;
         begin
            T := Try_Key (Stem, "prog-stem");
            if T.Found and then Stem'Length > Best_Len then
               Best := T;
               Best_Len := Stem'Length;
            end if;
         end;
      end loop;
      --  prefixes: try longer first
      for L in reverse 3 .. F'Length - 1 loop
         declare
            Pref : constant String := F (F'First .. F'First + L - 1);
            T    : Morph_Hit;
         begin
            T := Try_Key (Pref, "prog-pref");
            if T.Found and then Pref'Length > Best_Len then
               Best := T;
               Best_Len := Pref'Length;
            end if;
         end;
      end loop;
      return Best;
   end Resolve_Progressive;

   function Resolve
     (Form : String; Lang_Hint : String := "") return Morph_Hit
   is
      H : Morph_Hit;
      L : constant String := To_Lower (Lang_Hint);
   begin
      if Form'Length = 0 then
         return H;
      end if;

      H := Try_Key (Form, "exact");
      if H.Found then
         return H;
      end if;
      H := Try_Key (To_Lower (Form), "exact");
      if H.Found then
         return H;
      end if;

      if L = "ang" or else L = "oe" then
         H := Resolve_ANG (Form);
      elsif L = "en" then
         H := Resolve_EN (Form);
      elsif L = "grc" or else L = "el" then
         H := Resolve_GRC_LAT (Form);
         if not H.Found then
            H := Resolve_LA (Form);
         end if;
      elsif L = "la" or else L = "lat" then
         H := Resolve_LA (Form);
      else
         H := Resolve_LA (Form);
         if not H.Found then
            H := Resolve_EN (Form);
         end if;
         if not H.Found then
            H := Resolve_GRC_LAT (Form);
         end if;
         if not H.Found then
            H := Resolve_ANG (Form);
         end if;
      end if;
      --  Script-universal progressive peels (fills ar/he/san/egy gaps)
      if not H.Found then
         H := Resolve_Progressive (Form);
      end if;
      if not H.Found then
         H := Try_Neighbor (To_Lower (Form));
      end if;
      return H;
   end Resolve;

end PFLT_Morph;
