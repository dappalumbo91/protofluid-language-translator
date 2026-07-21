--  Protofluid articulatory / audio channel (Ada).
--  Mirrors Python audio_articulation: IPA + articulatory features + FSOT S
--  for tempo/energy proxies. Waveform is optional external link only —
--  not the truth core (same policy as Python).

with PFLT_Domains;
with PFLT_Scalar;

package PFLT_Audio
  with SPARK_Mode => Off
is

   type Artic_Features is record
      Voicing   : Long_Float := 0.0;
      Nasality  : Long_Float := 0.0;
      Frontness : Long_Float := 0.5;
      Openness  : Long_Float := 0.5;
      Length    : Long_Float := 0.0;
      Stress    : Long_Float := 0.0;
      N_Seg     : Natural := 0;
   end record;

   type Articulation is record
      Text       : String (1 .. 128) := (others => ' ');
      Text_Last  : Natural := 0;
      Lang       : String (1 .. 8) := (others => ' ');
      Lang_Last  : Natural := 0;
      IPA        : String (1 .. 96) := (others => ' ');
      IPA_Last   : Natural := 0;
      Features   : Artic_Features;
      Tempo      : Long_Float := 1.0;  -- FSOT-modulated proxy
      Energy     : Long_Float := 1.0;
      Panel      : PFLT_Scalar.Scalar_Panel;
      Gloss      : String (1 .. 128) := (others => ' ');
      Gloss_Last : Natural := 0;
      Notes      : String (1 .. 160) := (others => ' ');
      Notes_Last : Natural := 0;
   end record;

   function Articulate
     (Word : String; Lang : String := "la") return Articulation;

   function Articulate_Phrase
     (Text : String; Lang : String := "la") return Articulation;

   procedure Run_Demo;

   function IPA_Slice (A : Articulation) return String;
   function Gloss_Slice (A : Articulation) return String;

end PFLT_Audio;
