with Ada.Directories;
with Ada.Text_IO; use Ada.Text_IO;
with PFLT_Constants;
with PFLT_Domains;
with PFLT_Scalar;
with PFLT_Store;
with PFLT_Translate;

package body PFLT_Vision
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

   procedure Set_Class (R : in out Vision_Readout; S : String) is
   begin
      R.Scene_Class := (others => ' ');
      R.Class_Last := Natural'Min (S'Length, R.Scene_Class'Length);
      if R.Class_Last > 0 then
         R.Scene_Class (1 .. R.Class_Last) :=
           S (S'First .. S'First + R.Class_Last - 1);
      end if;
   end Set_Class;

   procedure Set_Source (R : in out Vision_Readout; S : String) is
   begin
      R.Source := (others => ' ');
      R.Source_Last := Natural'Min (S'Length, R.Source'Length);
      if R.Source_Last > 0 then
         R.Source (1 .. R.Source_Last) :=
           S (S'First .. S'First + R.Source_Last - 1);
      end if;
   end Set_Source;

   --  Seed-derived band amplitudes (no free color knobs).
   --  Scene kind sets relative gray/UV/NIR/R structure for the student.
   function Synthetic_Stats (Scene : Scene_Kind) return Band_Stats is
      Phi_Inv : constant Long_Float := 1.0 / Phi;
      Base_S  : constant Long_Float :=
        Long_Float (0.55) + Phi_Inv * 0.05;
      St : Band_Stats;
   begin
      case Scene is
         when Plain_Substrate =>
            St :=
              (Mean_Gray => 0.04, Mean_UV => 0.02, Mean_NIR => 0.02,
               Mean_S => Base_S, Peak_UV => 0.03, Peak_NIR => 0.03,
               Peak_Gray => 0.05, Mean_R => 0.05);
         when Ink_Surface =>
            St :=
              (Mean_Gray => 0.12, Mean_UV => 0.06, Mean_NIR => 0.05,
               Mean_S => Base_S + 0.02, Peak_UV => 0.08, Peak_NIR => 0.07,
               Peak_Gray => 0.18, Mean_R => 0.10);
         when Ochre_Pigment =>
            St :=
              (Mean_Gray => 0.10, Mean_UV => 0.07, Mean_NIR => 0.14,
               Mean_S => Base_S + 0.01, Peak_UV => 0.09, Peak_NIR => 0.22,
               Peak_Gray => 0.12, Mean_R => 0.48);
         when Hidden_Underdrawing =>
            St :=
              (Mean_Gray => 0.05, Mean_UV => 0.18, Mean_NIR => 0.16,
               Mean_S => Base_S + 0.04, Peak_UV => 0.28, Peak_NIR => 0.24,
               Peak_Gray => 0.07, Mean_R => 0.06);
         when Visible_Plus_Hidden =>
            St :=
              (Mean_Gray => 0.11, Mean_UV => 0.16, Mean_NIR => 0.14,
               Mean_S => Base_S + 0.03, Peak_UV => 0.22, Peak_NIR => 0.18,
               Peak_Gray => 0.15, Mean_R => 0.20);
      end case;
      return St;
   end Synthetic_Stats;

   procedure Classify
     (St : Band_Stats;
      R  : in out Vision_Readout)
   is
      Machine_Peak : constant Boolean :=
        (St.Peak_UV > 0.14 and then St.Peak_NIR > 0.12)
        or else (St.Peak_UV + St.Peak_NIR > 1.35 * Long_Float'Max (St.Peak_Gray, 0.05));
      Weak_Vis : constant Boolean :=
        St.Peak_Gray < 0.12 and then St.Mean_Gray < 0.085;
   begin
      R.Stats := St;
      R.Tokens := (others => ' ');
      R.Tokens_Last := 0;
      R.Notes := (others => ' ');
      R.Notes_Last := 0;

      if Machine_Peak and then Weak_Vis then
         Set_Class (R, "machine_only_underdrawing");
         R.Confidence := 0.88;
         Put_Str (R.Tokens, R.Tokens_Last, "hidden_structure uv_band nir_band");
         Put_Str
           (R.Notes, R.Notes_Last,
            "Peak UV/NIR with weak gray → beyond-eye content");
      elsif Machine_Peak then
         Set_Class (R, "visible_mark_plus_hidden");
         R.Confidence := 0.82;
         Put_Str
           (R.Tokens, R.Tokens_Last,
            "surface_mark hidden_structure uv_band");
         Put_Str
           (R.Notes, R.Notes_Last, "Localized UV/NIR peaks on surface mark");
      elsif St.Mean_R > 0.40 and then St.Peak_NIR >= St.Peak_UV * 0.9 then
         Set_Class (R, "ochre_like_pigment");
         R.Confidence := 0.78;
         Put_Str (R.Tokens, R.Tokens_Last, "ochre pigment nir_band");
         Put_Str (R.Notes, R.Notes_Last, "Red-lean VIS + NIR → ochre-like");
      elsif St.Peak_Gray > 0.10 or else St.Mean_Gray > 0.075 then
         Set_Class (R, "ink_or_surface_mark");
         R.Confidence := 0.72;
         Put_Str (R.Tokens, R.Tokens_Last, "surface_mark ink");
         Put_Str (R.Notes, R.Notes_Last, "Gray structure dominant");
      else
         Set_Class (R, "plain_substrate");
         R.Confidence := 0.65;
         Put_Str (R.Tokens, R.Tokens_Last, "substrate stone");
         Put_Str (R.Notes, R.Notes_Last, "Low structure across bands");
      end if;

      --  Map tokens through product lexicon (student → teacher)
      declare
         Tr : constant PFLT_Translate.Translate_Result :=
           PFLT_Translate.Translate (R.Tokens (1 .. R.Tokens_Last));
      begin
         R.Gloss := (others => ' ');
         R.Gloss_Last := Tr.Gloss_Last;
         if R.Gloss_Last > 0 then
            R.Gloss (1 .. R.Gloss_Last) := Tr.Gloss (1 .. Tr.Gloss_Last);
         end if;
      end;

      R.Domain := PFLT_Domains.Hieroglyphic;
      R.Panel :=
        PFLT_Scalar.Compute_Panel
          (PFLT_Domains.Default_Input (PFLT_Domains.Hieroglyphic));
      --  fold mean_S into note (law panel remains seed-derived)
      Put_Str (R.Notes, R.Notes_Last, " | multilayer L0-L4 FSOT student");
   end Classify;

   function Field_Student (Scene : Scene_Kind) return Vision_Readout is
      R : Vision_Readout;
   begin
      Set_Source (R, "rule_field");
      Classify (Synthetic_Stats (Scene), R);
      return R;
   end Field_Student;

   --  Minimal Gardiner seed meanings (Unikemet-class); store may override.
   function Gardiner_Gloss (Code : String) return String is
      C : constant String := Code;
      Hit : constant String := PFLT_Store.Lookup (C);
   begin
      if Hit'Length > 0 then
         return Hit;
      end if;
      --  Built-in demo floor (common textbook signs)
      if C = "A1" or else C = "a1" then
         return "man";
      elsif C = "N5" or else C = "n5" then
         return "sun";
      elsif C = "S34" or else C = "s34" then
         return "life";
      elsif C = "D21" or else C = "d21" then
         return "mouth";
      elsif C = "G17" or else C = "g17" then
         return "owl";
      elsif C = "I9" or else C = "i9" then
         return "viper";
      elsif C = "N35" or else C = "n35" then
         return "water";
      elsif C = "X1" or else C = "x1" then
         return "bread";
      else
         return "glyph";
      end if;
   end Gardiner_Gloss;

   function Gardiner_Student (Codes : String) return Vision_Readout is
      R     : Vision_Readout;
      I     : Natural := Codes'First;
      Start : Natural;
      First : Boolean := True;
      St    : Band_Stats :=
        (Mean_Gray => 0.11, Mean_UV => 0.09, Mean_NIR => 0.08,
         Mean_S => 0.60, Peak_UV => 0.12, Peak_NIR => 0.11,
         Peak_Gray => 0.16, Mean_R => 0.15);
   begin
      Set_Source (R, "gardiner_labels");
      Set_Class (R, "glyph_label_path");
      R.Confidence := 0.90;
      R.Stats := St;
      R.Tokens := (others => ' ');
      R.Tokens_Last := 0;
      R.Gloss := (others => ' ');
      R.Gloss_Last := 0;
      R.Notes := (others => ' ');
      R.Notes_Last := 0;
      Put_Str
        (R.Notes, R.Notes_Last,
         "U-Net slot: labels/hypotheses → Unikemet/store; not free NN truth");

      while I <= Codes'Last loop
         while I <= Codes'Last and then Codes (I) = ' ' loop
            I := I + 1;
         end loop;
         exit when I > Codes'Last;
         Start := I;
         while I <= Codes'Last and then Codes (I) /= ' ' loop
            I := I + 1;
         end loop;
         declare
            Code : constant String := Codes (Start .. I - 1);
            G    : constant String := Gardiner_Gloss (Code);
         begin
            if not First then
               Put_Str (R.Tokens, R.Tokens_Last, " ");
               Put_Str (R.Gloss, R.Gloss_Last, " ");
            end if;
            First := False;
            Put_Str (R.Tokens, R.Tokens_Last, Code);
            Put_Str (R.Gloss, R.Gloss_Last, G);
         end;
      end loop;

      R.Domain := PFLT_Domains.Hieroglyphic;
      R.Panel :=
        PFLT_Scalar.Compute_Panel
          (PFLT_Domains.Default_Input (PFLT_Domains.Hieroglyphic));
      return R;
   end Gardiner_Student;

   function Class_Slice (R : Vision_Readout) return String is
   begin
      if R.Class_Last = 0 then
         return "";
      end if;
      return R.Scene_Class (1 .. R.Class_Last);
   end Class_Slice;

   function Tokens_Slice (R : Vision_Readout) return String is
   begin
      if R.Tokens_Last = 0 then
         return "";
      end if;
      return R.Tokens (1 .. R.Tokens_Last);
   end Tokens_Slice;

   function Gloss_Slice (R : Vision_Readout) return String is
   begin
      if R.Gloss_Last = 0 then
         return "";
      end if;
      return R.Gloss (1 .. R.Gloss_Last);
   end Gloss_Slice;

   procedure Print_One (R : Vision_Readout) is
      package FIO is new Ada.Text_IO.Float_IO (Long_Float);
   begin
      Put_Line
        ("[vision · class="
         & Class_Slice (R)
         & " · conf="
         & Long_Float'Image (R.Confidence)
         & " · source="
         & R.Source (1 .. R.Source_Last)
         & " · pin=D1D38A]");
      Put_Line ("  tokens: " & Tokens_Slice (R));
      Put_Line ("  gloss:  " & Gloss_Slice (R));
      Put ("  bands gray/uv/nir/S peaks: ");
      FIO.Put (R.Stats.Peak_Gray, Fore => 1, Aft => 3, Exp => 0);
      Put (" / ");
      FIO.Put (R.Stats.Peak_UV, Fore => 1, Aft => 3, Exp => 0);
      Put (" / ");
      FIO.Put (R.Stats.Peak_NIR, Fore => 1, Aft => 3, Exp => 0);
      Put (" / S=");
      FIO.Put (R.Panel.S, Fore => 1, Aft => 6, Exp => 0);
      New_Line;
      if R.Notes_Last > 0 then
         Put_Line ("  notes: " & R.Notes (1 .. R.Notes_Last));
      end if;
   end Print_One;

   function Load_Hypotheses_File
     (Path : String; Image_Path : String := "") return Vision_Readout
   is
      R     : Vision_Readout;
      F     : File_Type;
      Codes : String (1 .. 256) := (others => ' ');
      CL    : Natural := 0;
      First : Boolean := True;
      Conf_Sum : Long_Float := 0.0;
      Conf_N   : Natural := 0;
      Line_N   : Natural := 0;
   begin
      Set_Source (R, "unet_hypotheses");
      Set_Class (R, "unet_file_path");
      R.Tokens := (others => ' ');
      R.Tokens_Last := 0;
      R.Gloss := (others => ' ');
      R.Gloss_Last := 0;
      R.Notes := (others => ' ');
      R.Notes_Last := 0;
      Put_Str
        (R.Notes, R.Notes_Last,
         "U-Net hyp file → teacher lexicon; law not rewritten");
      if Image_Path'Length > 0 then
         Put_Str (R.Notes, R.Notes_Last, " | image=");
         Put_Str (R.Notes, R.Notes_Last, Image_Path);
      end if;

      if not Ada.Directories.Exists (Path) then
         Set_Class (R, "unet_file_missing");
         R.Confidence := 0.0;
         return R;
      end if;

      Open (F, In_File, Path);
      while not End_Of_File (F) loop
         declare
            Line : constant String := Get_Line (F);
            Tab  : Natural := 0;
         begin
            Line_N := Line_N + 1;
            if Line_N = 1
              and then Line'Length >= 8
              and then Line (Line'First .. Line'First + 7) = "gardiner"
            then
               goto Next_Line;
            end if;
            for I in Line'Range loop
               if Line (I) = ASCII.HT then
                  Tab := I;
                  exit;
               end if;
            end loop;
            if Tab > Line'First then
               declare
                  Code : constant String :=
                    Line (Line'First .. Tab - 1);
                  Rest : constant String := Line (Tab + 1 .. Line'Last);
                  Tab2 : Natural := 0;
                  Conf : Long_Float := 0.8;
               begin
                  for I in Rest'Range loop
                     if Rest (I) = ASCII.HT then
                        Tab2 := I;
                        exit;
                     end if;
                  end loop;
                  if Tab2 > Rest'First then
                     begin
                        Conf :=
                          Long_Float'Value
                            (Rest (Rest'First .. Tab2 - 1));
                     exception
                        when others =>
                           Conf := 0.8;
                     end;
                  end if;
                  Conf_Sum := Conf_Sum + Conf;
                  Conf_N := Conf_N + 1;
                  if not First then
                     Put_Str (Codes, CL, " ");
                  end if;
                  First := False;
                  Put_Str (Codes, CL, Code);
               end;
            end if;
            <<Next_Line>>
         end;
      end loop;
      Close (F);

      if CL > 0 then
         R := Gardiner_Student (Codes (1 .. CL));
         Set_Source (R, "unet_hypotheses");
         if Conf_N > 0 then
            R.Confidence := Conf_Sum / Long_Float (Conf_N);
         end if;
         Put_Str
           (R.Notes, R.Notes_Last,
            " | loaded from hyp file (student eyes)");
      else
         R.Confidence := 0.0;
         Set_Class (R, "unet_empty");
      end if;
      return R;
   end Load_Hypotheses_File;

   procedure Run_Demo is
   begin
      Put_Line ("=== Ada FSOT multilayer vision student ===");
      Put_Line
        ("Layers: L0 gray · L1 VIS · L2 UV · L3 NIR · L4 S (seed field)");
      Put_Line
        ("U-Net is student eyes only; meaning = Unikemet/store + FSOT law");
      New_Line;
      Print_One (Field_Student (Plain_Substrate));
      Print_One (Field_Student (Ink_Surface));
      Print_One (Field_Student (Ochre_Pigment));
      Print_One (Field_Student (Hidden_Underdrawing));
      Print_One (Field_Student (Visible_Plus_Hidden));
      New_Line;
      Put_Line ("--- Gardiner label path (U-Net contract fill) ---");
      Print_One (Gardiner_Student ("A1 N5 S34"));
      Print_One (Gardiner_Student ("D21 G17 I9 N35"));
      New_Line;
      Put_Line ("--- U-Net hypotheses sample file ---");
      Print_One
        (Load_Hypotheses_File
           ("C:\Users\damia\Desktop\pflt\pflt-Ada\data\"
            & "unet_hypotheses_sample.tsv",
            "sample_wall.png"));
   end Run_Demo;

end PFLT_Vision;
