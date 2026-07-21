package body PFLT_Route
  with SPARK_Mode => Off
is

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

   function Route_Domain (Text : String) return PFLT_Domains.Domain_Id is
      T : constant String := To_Lower (Text);
   begin
      if Contains (T, "zipf") or else Contains (T, "entropy")
        or else Contains (T, "phoneme") or else Contains (T, "language")
        or else Contains (T, "lingua") or else Contains (T, "verbum")
        or else Contains (T, "translate")
      then
         return PFLT_Domains.Linguistic;
      end if;
      if Contains (T, "quantum") or else Contains (T, "photon")
        or else Contains (T, "qubit")
      then
         return PFLT_Domains.Quantum;
      end if;
      if Contains (T, "zeus") or else Contains (T, "temple")
        or else Contains (T, "myth") or else Contains (T, "divine")
        or else Contains (T, "theos") or else Contains (T, "soul")
      then
         return PFLT_Domains.Mythological;
      end if;
      if Contains (T, "latin") or else Contains (T, "aqua")
        or else Contains (T, "manus") or else Contains (T, "rome")
        or else Contains (T, "king") or else Contains (T, "war")
      then
         return PFLT_Domains.Historical;
      end if;
      if Contains (T, "hieroglyph") or else Contains (T, "gardiner") then
         return PFLT_Domains.Hieroglyphic;
      end if;
      if Contains (T, "cosmos") or else Contains (T, "galaxy")
        or else Contains (T, "universe")
      then
         return PFLT_Domains.Cosmological;
      end if;
      if Contains (T, "cell") or else Contains (T, "gene")
        or else Contains (T, "dna") or else Contains (T, "life")
      then
         return PFLT_Domains.Biological;
      end if;
      if Contains (T, "mind") or else Contains (T, "conscious")
        or else Contains (T, "observer")
      then
         return PFLT_Domains.Consciousness;
      end if;
      return PFLT_Domains.Linguistic;
   end Route_Domain;

end PFLT_Route;
