with PFLT_Anchors;
with PFLT_Authority;

package body PFLT_Cert
  with SPARK_Mode => Off
is

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

   procedure Append_Line
     (Buf : in out String; Last : in out Natural; Piece : String)
   is
   begin
      Append (Buf, Last, Piece);
      Append (Buf, Last, String'(1 => ASCII.LF));
   end Append_Line;

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

   function Img (X : Long_Float) return String is
   begin
      return Long_Float'Image (X);
   end Img;

   function Block_Slice (R : Cert_Report) return String is
   begin
      if R.Block_Last = 0 then
         return "";
      end if;
      return R.Block (1 .. R.Block_Last);
   end Block_Slice;

   function Certify_Turn
     (Text  : String;
      Panel : PFLT_Scalar.Scalar_Panel) return Cert_Report
   is
      T    : constant String := To_Lower (Text);
      R    : Cert_Report;
      Auth : constant PFLT_Authority.Authority_Status :=
        PFLT_Authority.Kernel_Pin_Status;
      Want_S : constant Boolean :=
        Contains (T, "fsot")
        or else Contains (T, "scalar")
        or else Contains (T, "coherence")
        or else Contains (T, "s=")
        or else Contains (T, "t1")
        or else Contains (T, "t2")
        or else Contains (T, "t3")
        or else Contains (T, "d_eff")
        or else Contains (T, "domain scalar")
        or else Contains (T, "zipf")
        or else Contains (T, "entropy");
      --  zipf/entropy turns also surface certified S panel (law context)
      Want_Ling : constant Boolean :=
        Contains (T, "zipf")
        or else Contains (T, "entropy")
        or else Contains (T, "heaps")
        or else Contains (T, "shannon")
        or else Contains (T, "type-token")
        or else Contains (T, "type token")
        or else Contains (T, "phoneme")
        or else Contains (T, "bits");
      Want_Math : constant Boolean :=
        Contains (T, "what is s")
        or else Contains (T, "compute s")
        or else Contains (T, "value of");
   begin
      R.Block := (others => ' ');
      R.Block_Last := 0;
      R.Ok := True;

      if Want_S or else Want_Math then
         Append_Line
           (R.Block, R.Block_Last,
            "Certified law (pin D1D38A, S=K*(T1+T2+T3)):");
         Append_Line
           (R.Block, R.Block_Last,
            "  S="
            & Img (Panel.S)
            & " T1="
            & Img (Panel.T1)
            & " T2="
            & Img (Panel.T2)
            & " T3="
            & Img (Panel.T3)
            & " K="
            & Img (Panel.K)
            & " D_eff="
            & Img (Panel.D_Eff));
         Append_Line
           (R.Block, R.Block_Last,
            "  authority_ok="
            & (if Auth.Ok then "true" else "false")
            & " engine=pflt_scalar_spark");
         R.Certified_N := R.Certified_N + 1;
      end if;

      if Want_Ling then
         declare
            procedure Try (Key, Label : String) is
               A : constant PFLT_Anchors.Anchor := PFLT_Anchors.Find (Key);
            begin
               if A.Found then
                  Append_Line
                    (R.Block, R.Block_Last,
                     "Certified linguistics anchor ("
                     & Label
                     & "):");
                  Append_Line
                    (R.Block, R.Block_Last,
                     "  "
                     & PFLT_Anchors.Name_Slice (A)
                     & " = "
                     & Img (A.Value)
                     & "  err_pct="
                     & Img (A.Error_Pct));
                  Append_Line
                    (R.Block, R.Block_Last,
                     "  formula="
                     & PFLT_Anchors.Formula_Slice (A)
                     & "  source=archive_linguistics_derivations");
                  R.Certified_N := R.Certified_N + 1;
               end if;
            end Try;
         begin
            if Contains (T, "zipf") then
               Try ("zipf", "zipf");
            end if;
            if Contains (T, "entropy") or else Contains (T, "shannon")
              or else Contains (T, "bits")
            then
               Try ("entropy", "entropy");
            end if;
            if Contains (T, "type") then
               Try ("type_token", "type_token");
            end if;
            if Contains (T, "phoneme") then
               Try ("phoneme", "phoneme");
            end if;
            if Contains (T, "heaps") then
               Try ("heaps", "heaps");
            end if;
            if R.Certified_N = 0 and then Want_Ling then
               Try ("Zipf", "zipf");
               Try ("Entropy", "entropy");
            end if;
         end;
      end if;

      --  Refuse free vibes if someone asserts random S= without law path
      if Contains (T, "s=") and then not Want_S and then not Want_Math then
         Append_Line
           (R.Block, R.Block_Last,
            "Refused: bare S= claim without FSOT/scalar context "
            & "(use certified law panel).");
         R.Refused_N := R.Refused_N + 1;
         R.Ok := False;
      end if;

      if R.Certified_N = 0 and then R.Refused_N = 0 then
         Append_Line
           (R.Block, R.Block_Last,
            "Cert gate: no law/linguistics numeric claim in turn "
            & "(surface translate only).");
      end if;

      return R;
   end Certify_Turn;

end PFLT_Cert;
