--  Protofluid Language Translator -- Ada/SPARK product binary (V6).
--  Gaps filled: atlas · live SHA256 · U-Net hyp · LTM · cert · anchors.

with Ada.Command_Line;
with Ada.Text_IO; use Ada.Text_IO;
with PFLT_Anchors;
with PFLT_Archive;
with PFLT_Atlas;
with PFLT_Audio;
with PFLT_Authority;
with PFLT_Cert;
with PFLT_Constants;
with PFLT_Converse;
with PFLT_Domains;
with PFLT_Eval;
with PFLT_Golden;
with PFLT_Ledger;
with PFLT_LTM;
with PFLT_Scalar;
with PFLT_Store;
with PFLT_Vision;

procedure PFLT_Main is

   package FIO is new Ada.Text_IO.Float_IO (Long_Float);

   procedure Put_LF (X : Long_Float) is
   begin
      FIO.Put (X, Fore => 2, Aft => 12, Exp => 0);
   end Put_LF;

   procedure Show_Panel
     (Domain : String; Panel : PFLT_Scalar.Scalar_Panel; Auth_Ok : Boolean)
   is
   begin
      Put_Line
        ("[Protofluid-Ada · domain="
         & Domain
         & " · authority_ok="
         & (if Auth_Ok then "true" else "false")
         & " · pin=D1D38A]");
      Put ("  S=");
      Put_LF (Panel.S);
      Put ("  T1=");
      Put_LF (Panel.T1);
      Put ("  T2=");
      Put_LF (Panel.T2);
      Put ("  T3=");
      Put_LF (Panel.T3);
      New_Line;
      Put ("  K=");
      Put_LF (Panel.K);
      Put ("  D_eff=");
      Put_LF (Panel.D_Eff);
      Put_Line ("  observed=" & Boolean'Image (Panel.Observed));
      Put_Line ("  formula=" & PFLT_Constants.Formula);
   end Show_Panel;

   Auth : constant PFLT_Authority.Authority_Status :=
     PFLT_Authority.Kernel_Pin_Status;
   Fail : Natural;
   Argc : constant Natural := Ada.Command_Line.Argument_Count;
   Densify_N, Gold_N : Natural := 0;
   Atlas_Loaded, Anchors_Loaded : Boolean := False;

   procedure Ensure_Support is
   begin
      if not Atlas_Loaded then
         PFLT_Atlas.Load_Default;
         Atlas_Loaded := True;
         Put_Line
           ("atlas_domains=" & Natural'Image (PFLT_Atlas.Count));
      end if;
      if not Anchors_Loaded then
         PFLT_Anchors.Load_Default;
         Anchors_Loaded := True;
         Put_Line
           ("linguistics_anchors=" & Natural'Image (PFLT_Anchors.Count));
      end if;
      PFLT_LTM.Load_Default_Path;
   end Ensure_Support;

   procedure Ensure_Lexicon is
   begin
      Ensure_Support;
      Put_Line ("Loading densify + gold_core TSV packs...");
      PFLT_Store.Load_Default_Packs (Densify_N, Gold_N);
      Put_Line
        ("store: densify_rows="
         & Natural'Image (Densify_N)
         & " gold_rows="
         & Natural'Image (Gold_N)
         & " map_entries="
         & Natural'Image (PFLT_Store.Count));
   end Ensure_Lexicon;

begin
   Put_Line ("====================================================");
   Put_Line ("  Protofluid Language Translator -- Ada/SPARK V6");
   Put_Line ("  Gaps: atlas · live-pin · unet · ltm · cert · anchors");
   Put_Line ("====================================================");

   PFLT_Store.Set_Data_Root
     ("C:\Users\damia\Desktop\pflt\pflt-Ada\data");
   PFLT_Ledger.Set_Path
     ("C:\Users\damia\Desktop\pflt\pflt-Ada\data\knowledge_ledger_ada.jsonl");
   PFLT_LTM.Load_Default_Path;

   if Argc >= 1 then
      declare
         Cmd : constant String := Ada.Command_Line.Argument (1);
      begin
         if Cmd = "archive" or else Cmd = "archive-status" then
            declare
               St : constant PFLT_Archive.Archive_Status :=
                 PFLT_Archive.Probe;
            begin
               PFLT_Archive.Print_Status (St);
               Put_Line
                 ("kernel_pin_ok=" & Boolean'Image (Auth.Ok));
               return;
            end;
         elsif Cmd = "atlas" then
            Ensure_Support;
            if Argc >= 2 then
               declare
                  Q : constant String := Ada.Command_Line.Argument (2);
                  H : constant PFLT_Atlas.Atlas_Hit :=
                    PFLT_Atlas.Match (Q);
               begin
                  if H.Found then
                     Put_Line
                       ("match="
                        & PFLT_Atlas.Name_Slice (H)
                        & " D_eff="
                        & Long_Float'Image (H.D_Eff)
                        & " score="
                        & Long_Float'Image (H.Score));
                  else
                     Put_Line ("no atlas match");
                  end if;
               end;
            else
               Put_Line
                 ("atlas_domains=" & Natural'Image (PFLT_Atlas.Count));
            end if;
            return;
         elsif Cmd = "anchors" or else Cmd = "cert" then
            Ensure_Support;
            declare
               Text : constant String :=
                 (if Argc >= 2 then Ada.Command_Line.Argument (2)
                  else "zipf entropy fsot scalar S=");
               Panel : constant PFLT_Scalar.Scalar_Panel :=
                 PFLT_Scalar.Compute_Panel
                   (PFLT_Domains.Default_Input (PFLT_Domains.Linguistic));
               Cr : constant PFLT_Cert.Cert_Report :=
                 PFLT_Cert.Certify_Turn (Text, Panel);
            begin
               Put_Line (PFLT_Cert.Block_Slice (Cr));
               Put_Line
                 ("certified_n="
                  & Natural'Image (Cr.Certified_N)
                  & " refused_n="
                  & Natural'Image (Cr.Refused_N));
            end;
            return;
         elsif Cmd = "ltm" then
            Ensure_Support;
            if Argc >= 2 and then Ada.Command_Line.Argument (2) = "recall"
              and then Argc >= 3
            then
               Put_Line
                 (PFLT_LTM.Recall (Ada.Command_Line.Argument (3), 5));
            else
               Put_Line
                 ("LTM episodes_this_session="
                  & Natural'Image (PFLT_LTM.Episode_Count));
               Put_Line
                 ("path=C:\Users\damia\Desktop\pflt\pflt-Ada\data\"
                  & "ltm_mulling.jsonl");
               Put_Line ("usage: ltm recall KEYWORD");
            end if;
            return;
         elsif Cmd = "eval" then
            declare
               Ev : constant PFLT_Eval.Eval_Report :=
                 PFLT_Eval.Run_Sample
                   ("C:\Users\damia\Desktop\pflt\pflt-Ada\data\eval_sample.tsv");
            begin
               PFLT_Eval.Print_Report (Ev);
               return;
            end;
         elsif Cmd = "eval-product" then
            declare
               Ev : constant PFLT_Eval.Eval_Report :=
                 PFLT_Eval.Run_Sample
                   ("C:\Users\damia\Desktop\pflt\pflt-Ada\data\eval_sample.tsv",
                    8000,
                    PFLT_Eval.Product);
            begin
               PFLT_Eval.Print_Report (Ev);
               return;
            end;
         elsif Cmd = "vision" then
            Ensure_Lexicon;
            if Argc >= 2 then
               declare
                  Arg2 : constant String := Ada.Command_Line.Argument (2);
               begin
                  if Arg2 = "demo" then
                     PFLT_Vision.Run_Demo;
                  elsif Arg2 = "hyp" or else Arg2 = "unet" then
                     declare
                        Path : constant String :=
                          (if Argc >= 3 then Ada.Command_Line.Argument (3)
                           else
                             "C:\Users\damia\Desktop\pflt\pflt-Ada\data\"
                             & "unet_hypotheses_sample.tsv");
                        Img  : constant String :=
                          (if Argc >= 4 then Ada.Command_Line.Argument (4)
                           else "sample_wall.png");
                        R    : constant PFLT_Vision.Vision_Readout :=
                          PFLT_Vision.Load_Hypotheses_File (Path, Img);
                     begin
                        Put_Line
                          ("class="
                           & PFLT_Vision.Class_Slice (R)
                           & " conf="
                           & Long_Float'Image (R.Confidence));
                        Put_Line
                          ("tokens=" & PFLT_Vision.Tokens_Slice (R));
                        Put_Line
                          ("gloss=" & PFLT_Vision.Gloss_Slice (R));
                     end;
                  else
                     declare
                        Codes : String (1 .. 256) := (others => ' ');
                        Last  : Natural := 0;
                     begin
                        for K in 2 .. Argc loop
                           declare
                              P : constant String :=
                                Ada.Command_Line.Argument (K);
                           begin
                              if Last > 0 and then Last < Codes'Last then
                                 Last := Last + 1;
                                 Codes (Last) := ' ';
                              end if;
                              for C of P loop
                                 exit when Last >= Codes'Last;
                                 Last := Last + 1;
                                 Codes (Last) := C;
                              end loop;
                           end;
                        end loop;
                        declare
                           R : constant PFLT_Vision.Vision_Readout :=
                             PFLT_Vision.Gardiner_Student
                               (Codes (1 .. Last));
                        begin
                           Put_Line
                             ("class="
                              & PFLT_Vision.Class_Slice (R)
                              & " conf="
                              & Long_Float'Image (R.Confidence));
                           Put_Line
                             ("tokens=" & PFLT_Vision.Tokens_Slice (R));
                           Put_Line
                             ("gloss=" & PFLT_Vision.Gloss_Slice (R));
                        end;
                     end;
                  end if;
               end;
            else
               PFLT_Vision.Run_Demo;
            end if;
            return;
         elsif Cmd = "audio" then
            Ensure_Lexicon;
            if Argc >= 2 then
               declare
                  Word : constant String := Ada.Command_Line.Argument (2);
                  Lang : constant String :=
                    (if Argc >= 3 then Ada.Command_Line.Argument (3)
                     else "la");
                  Has_Space : Boolean := False;
                  A : PFLT_Audio.Articulation;
               begin
                  for C of Word loop
                     if C = ' ' then
                        Has_Space := True;
                        exit;
                     end if;
                  end loop;
                  if Has_Space then
                     A := PFLT_Audio.Articulate_Phrase (Word, Lang);
                  else
                     A := PFLT_Audio.Articulate (Word, Lang);
                  end if;
                  Put_Line
                    ("ipa="
                     & PFLT_Audio.IPA_Slice (A)
                     & " gloss="
                     & PFLT_Audio.Gloss_Slice (A));
                  Put ("tempo=");
                  Put_LF (A.Tempo);
                  Put (" energy=");
                  Put_LF (A.Energy);
                  Put (" S=");
                  Put_LF (A.Panel.S);
                  New_Line;
               end;
            else
               PFLT_Audio.Run_Demo;
            end if;
            return;
         elsif Cmd = "inject" and then Argc >= 3 then
            declare
               Form  : constant String := Ada.Command_Line.Argument (2);
               Gloss : constant String := Ada.Command_Line.Argument (3);
               Ok    : Boolean;
            begin
               Ensure_Lexicon;
               PFLT_Store.Inject_Pair (Form, Gloss, Ok);
               if Ok then
                  Put_Line
                    ("inject_ok form="
                     & Form
                     & " gloss="
                     & Gloss
                     & " map_entries="
                     & Natural'Image (PFLT_Store.Count));
               else
                  Put_Line ("inject_fail");
                  Ada.Command_Line.Set_Exit_Status
                    (Ada.Command_Line.Failure);
               end if;
               return;
            end;
         elsif (Cmd = "translate" or else Cmd = "converse")
           and then Argc >= 2
         then
            Ensure_Lexicon;
            declare
               Text : constant String := Ada.Command_Line.Argument (2);
               C    : constant PFLT_Converse.Converse_Result :=
                 PFLT_Converse.Converse (Text, Store => True);
            begin
               Put_Line (PFLT_Converse.Reply_Slice (C));
               return;
            end;
         elsif Cmd = "status" then
            Ensure_Lexicon;
            declare
               St : constant PFLT_Archive.Archive_Status :=
                 PFLT_Archive.Probe;
            begin
               Put_Line ("product=Protofluid-Ada V6");
               Put_Line
                 ("capacity=law+live-pin+atlas+anchors+cert+ltm+"
                  & "vision-unet+audio+morph+converse+eval");
               Put_Line
                 ("lexicon_entries=" & Natural'Image (PFLT_Store.Count));
               Put_Line
                 ("atlas_domains=" & Natural'Image (PFLT_Atlas.Count));
               Put_Line
                 ("linguistics_anchors="
                  & Natural'Image (PFLT_Anchors.Count));
               Put_Line
                 ("live_hash_ok="
                  & Boolean'Image (St.Live_Hash_Ok));
               Put_Line ("primary=Ada");
               return;
            end;
         end if;
      end;
   end if;

   --  Default demo suite
   Ensure_Lexicon;
   declare
      St : constant PFLT_Archive.Archive_Status := PFLT_Archive.Probe;
   begin
      Put_Line
        ("pin_prefix="
         & Auth.Prefix
         & " kernel_ok="
         & Boolean'Image (Auth.Ok)
         & " live_hash_ok="
         & Boolean'Image (St.Live_Hash_Ok));
   end;

   declare
      use PFLT_Domains;
      use PFLT_Scalar;
   begin
      New_Line;
      Show_Panel
        ("linguistic",
         Compute_Panel (Default_Input (Linguistic)),
         Auth.Ok);
   end;

   New_Line;
   Fail := PFLT_Golden.Run_Golden_Checks;
   if Fail = 0 then
      Put_Line ("GOLDEN: linguistic+historical S/T1/T2 PASS");
   else
      Put_Line ("GOLDEN: FAIL checks=" & Natural'Image (Fail));
   end if;

   New_Line;
   Put_Line ("--- converse (cert + atlas + LTM) ---");
   declare
      C : constant PFLT_Converse.Converse_Result :=
        PFLT_Converse.Converse
          ("what is zipf and fsot scalar for aqua lingua", Store => True);
   begin
      Put_Line (PFLT_Converse.Reply_Slice (C));
   end;

   Put_Line
     ("V6 gaps: atlas · live SHA256 · unet hyp · LTM · cert anchors.");

   if Fail /= 0 then
      Ada.Command_Line.Set_Exit_Status (Ada.Command_Line.Failure);
   end if;
end PFLT_Main;
