with PFLT_Archive;
with PFLT_Atlas;
with PFLT_Authority;
with PFLT_Cert;
with PFLT_Domains;
with PFLT_Ledger;
with PFLT_LTM;
with PFLT_Pathway;
with PFLT_Scalar;
with PFLT_Teach;
with PFLT_Translate;

package body PFLT_Converse
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

   function Img (X : Long_Float) return String is
   begin
      return Long_Float'Image (X);
   end Img;

   function Reply_Slice (R : Converse_Result) return String is
   begin
      if R.Reply_Last = 0 then
         return "";
      end if;
      return R.Reply (1 .. R.Reply_Last);
   end Reply_Slice;

   function Converse
     (User_Text : String; Store : Boolean := True) return Converse_Result
   is
      R    : Converse_Result;
      Tr   : PFLT_Translate.Translate_Result :=
        PFLT_Translate.Translate (User_Text);
      Auth : constant PFLT_Authority.Authority_Status :=
        PFLT_Authority.Kernel_Pin_Status;
      Arch : constant PFLT_Archive.Archive_Status := PFLT_Archive.Probe;
      Atl  : constant PFLT_Atlas.Atlas_Hit := PFLT_Atlas.Match (User_Text);
      Dom  : constant String := PFLT_Domains.Domain_Name (Tr.Domain);
      Gloss : constant String := PFLT_Translate.Gloss_Slice (Tr);
      Cert : PFLT_Cert.Cert_Report;
      Panel : PFLT_Scalar.Scalar_Panel := Tr.Panel;
      Mull : constant String :=
        PFLT_LTM.Mull_Note (Tr.Map_Rate, Tr.Unresolved_N);
      Rec  : constant String := PFLT_LTM.Recall (User_Text, 2);
   begin
      R.Tr := Tr;
      R.Reply := (others => ' ');
      R.Reply_Last := 0;

      --  Prefer atlas domain params when keyword match is strong
      if Atl.Found and then Atl.Score >= 2.0 then
         Panel := PFLT_Scalar.Compute_Panel (PFLT_Atlas.Input_Of (Atl));
      end if;

      Append_Line
        (R.Reply, R.Reply_Last,
         "[Protofluid-Ada · domain=" & Dom
         & " · S=" & Img (Panel.S)
         & " · map_rate=" & Img (Tr.Map_Rate)
         & " · authority_ok="
         & (if Auth.Ok then "true" else "false")
         & " · live_pin="
         & (if Arch.Live_Hash_Ok then "true" else "false")
         & " · pin=D1D38A]");

      if Atl.Found and then Atl.Score >= 2.0 then
         Append_Line
           (R.Reply, R.Reply_Last,
            "Atlas: "
            & PFLT_Atlas.Name_Slice (Atl)
            & "  D_eff="
            & Img (Atl.D_Eff)
            & "  score="
            & Img (Atl.Score)
            & "  (archive ~400-domain catalog)");
      end if;

      declare
         Path : constant PFLT_Pathway.Pathway_Result :=
           PFLT_Pathway.Reason (User_Text, 3);
         Teach : constant PFLT_Teach.Teach_Result :=
           PFLT_Teach.Build (User_Text);
         Teach_S : constant String := PFLT_Teach.Format_Block (Teach);
      begin
         Append_Line
           (R.Reply, R.Reply_Last,
            "Pathway: " & PFLT_Pathway.Format_Chain (Path)
            & "  conf=" & Img (Path.Conf));
         if Teach_S'Length > 0 then
            Append (R.Reply, R.Reply_Last, Teach_S);
            if R.Reply_Last < R.Reply'Last
              and then R.Reply (R.Reply_Last) /= ASCII.LF
            then
               Append_Line (R.Reply, R.Reply_Last, "");
            end if;
         end if;
      end;

      Append_Line
        (R.Reply, R.Reply_Last, "Surface gloss: " & Gloss);
      Append_Line
        (R.Reply, R.Reply_Last,
         "Tokens: mapped="
         & Natural'Image (Tr.Mapped_N)
         & " morph="
         & Natural'Image (Tr.Morph_N)
         & " unresolved="
         & Natural'Image (Tr.Unresolved_N)
         & " total="
         & Natural'Image (Tr.Token_N));
      Append_Line
        (R.Reply, R.Reply_Last,
         "FSOT law: S=K(T1+T2+T3)  T1="
         & Img (Panel.T1)
         & " T2="
         & Img (Panel.T2)
         & " T3="
         & Img (Panel.T3));

      --  Certified math / linguistics anchors
      Cert := PFLT_Cert.Certify_Turn (User_Text, Panel);
      declare
         CB : constant String := PFLT_Cert.Block_Slice (Cert);
      begin
         if CB'Length > 0 then
            Append (R.Reply, R.Reply_Last, CB);
         end if;
      end;

      Append_Line
        (R.Reply, R.Reply_Last,
         "Factual base: FSOT 2.1 archive law (D1D38A); "
         & "atlas+anchors+densify; students never rewrite law.");
      Append_Line (R.Reply, R.Reply_Last, Mull);

      if Rec'Length > 0 then
         Append_Line (R.Reply, R.Reply_Last, "LTM recall:");
         Append_Line (R.Reply, R.Reply_Last, Rec);
      end if;

      if Store then
         PFLT_Ledger.Append_Claim
           (Source_Text  => User_Text,
            Domain       => Tr.Domain,
            Gloss        => Gloss,
            Panel        => Panel,
            Authority_Ok => Auth.Ok and then Arch.Live_Hash_Ok);
         PFLT_LTM.Remember
           (Text   => User_Text,
            Domain => Dom,
            Gloss  => Gloss,
            S      => Panel.S,
            Note   => Mull);
         Append_Line
           (R.Reply, R.Reply_Last,
            "Ledger: claim stored (append-only). n="
            & Natural'Image (PFLT_Ledger.Claim_Count)
            & "  LTM episodes="
            & Natural'Image (PFLT_LTM.Episode_Count));
      end if;

      return R;
   end Converse;

end PFLT_Converse;
