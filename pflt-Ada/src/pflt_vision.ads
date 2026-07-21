--  FSOT multilayer vision student for Protofluid-Ada.
--
--  Mirrors Python fsot_multilayer_vision + vision_field_student:
--    L0 gray, L1 VIS, L2 UV, L3 NIR, L4 S/coherence field state
--  Rule student classifies scene → PFLT tokens → store/gloss.
--
--  U-Net slot: optional future detector fills Glyph_Hypothesis list;
--  meaning always stays FSOT-gated lexicon + law (never free NN truth).

with PFLT_Domains;
with PFLT_Scalar;

package PFLT_Vision
  with SPARK_Mode => Off
is

   type Band_Stats is record
      Mean_Gray : Long_Float := 0.0;
      Mean_UV   : Long_Float := 0.0;
      Mean_NIR  : Long_Float := 0.0;
      Mean_S    : Long_Float := 0.0;
      Peak_UV   : Long_Float := 0.0;
      Peak_NIR  : Long_Float := 0.0;
      Peak_Gray : Long_Float := 0.0;
      Mean_R    : Long_Float := 0.0;
   end record;

   type Vision_Readout is record
      Scene_Class : String (1 .. 48) := (others => ' ');
      Class_Last  : Natural := 0;
      Confidence  : Long_Float := 0.0;
      Stats       : Band_Stats;
      Tokens      : String (1 .. 256) := (others => ' ');
      Tokens_Last : Natural := 0;
      Gloss       : String (1 .. 256) := (others => ' ');
      Gloss_Last  : Natural := 0;
      Panel       : PFLT_Scalar.Scalar_Panel;
      Domain      : PFLT_Domains.Domain_Id := PFLT_Domains.Hieroglyphic;
      --  Student source: rule_field | gardiner_labels | unet_slot
      Source      : String (1 .. 24) := (others => ' ');
      Source_Last : Natural := 0;
      Notes       : String (1 .. 256) := (others => ' ');
      Notes_Last  : Natural := 0;
   end record;

   --  Synthetic multilayer field scenes (FSOT phi-probes, no external image lib).
   type Scene_Kind is
     (Plain_Substrate,
      Ink_Surface,
      Ochre_Pigment,
      Hidden_Underdrawing,
      Visible_Plus_Hidden);

   function Field_Student (Scene : Scene_Kind) return Vision_Readout;

   --  Gardiner / Unikemet label path (U-Net student contract fill-in).
   --  Codes space-separated e.g. "A1 N5 S34"
   function Gardiner_Student (Codes : String) return Vision_Readout;

   --  Load U-Net hypothesis TSV (gardiner\tconfidence\tsource\tbbox)
   --  and map through teacher (store/Unikemet). Image path is optional
   --  metadata only until a real decoder is linked.
   function Load_Hypotheses_File
     (Path : String; Image_Path : String := "") return Vision_Readout;

   --  Demo battery used by CLI
   procedure Run_Demo;

   function Class_Slice (R : Vision_Readout) return String;
   function Tokens_Slice (R : Vision_Readout) return String;
   function Gloss_Slice (R : Vision_Readout) return String;

end PFLT_Vision;
