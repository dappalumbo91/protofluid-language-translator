--  Bind Protofluid-Ada to I:\FSOT-Physical-Archive as law master.
--  Live SHA-256 of vendor/fsot_compute.py vs pin D1D38A.

package PFLT_Archive
  with SPARK_Mode => Off
is

   Archive_Root : constant String :=
     "I:\FSOT-Physical-Archive";

   Lean_Hub : constant String :=
     "I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full";

   Authority_Compute : constant String :=
     "I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\fsot_compute.py";

   Linguistics_JSON : constant String :=
     "I:\FSOT-Physical-Archive\02_FSOT-2.1-Lean-Full\vendor\linguistics\linguistics_derivations.json";

   Founding_PFLT_PDF : constant String :=
     "I:\FSOT-Physical-Archive\06_Founding-Archives\fsuft_aasb\fsuft-u 9.2\FSUFT-U 8.7\A Proto-Fluid Language Translator Grok.pdf";

   Founding_Voice_PDF : constant String :=
     "I:\FSOT-Physical-Archive\06_Founding-Archives\fsuft_aasb\Decoding the Proto-Fluid Voice - Grok.pdf";

   SR_ITE_Root : constant String :=
     "I:\FSOT-Physical-Archive\01_SR-ITE-USB-Original";

   Realities_OS : constant String :=
     "I:\FSOT-Physical-Archive\10_Realities-OS";

   Authority_SHA256 : constant String :=
     "D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70";

   type Archive_Status is record
      Root_Exists      : Boolean := False;
      Compute_Exists   : Boolean := False;
      Linguistics_Ok   : Boolean := False;
      Live_Hash_Ok     : Boolean := False;
      Live_Hash        : String (1 .. 64) := (others => '0');
      Pin_Prefix       : String (1 .. 6) := "D1D38A";
      Formula          : String (1 .. 16) := "S=K*(T1+T2+T3)  ";
      Note             : String (1 .. 80) := (others => ' ');
      Note_Last        : Natural := 0;
   end record;

   --  Probe paths + live SHA-256 of fsot_compute.py
   function Probe return Archive_Status;

   procedure Print_Status (S : Archive_Status);

end PFLT_Archive;
