with Ada.Directories;
with Ada.Text_IO; use Ada.Text_IO;
with PFLT_Authority;
with PFLT_SHA256;

package body PFLT_Archive
  with SPARK_Mode => Off
is

   Cached     : Archive_Status;
   Has_Cache  : Boolean := False;

   procedure Set_Note (S : in out Archive_Status; Msg : String) is
      N : constant Natural := Natural'Min (Msg'Length, S.Note'Length);
   begin
      S.Note := (others => ' ');
      S.Note_Last := N;
      if N > 0 then
         S.Note (1 .. N) := Msg (Msg'First .. Msg'First + N - 1);
      end if;
   end Set_Note;

   function Probe return Archive_Status is
      S : Archive_Status;
      Dig : String (1 .. 64);
      Dig_L : Natural := 0;
      Auth : PFLT_Authority.Authority_Status;
   begin
      if Has_Cache then
         return Cached;
      end if;

      S.Root_Exists := Ada.Directories.Exists (Archive_Root);
      S.Compute_Exists := Ada.Directories.Exists (Authority_Compute);
      S.Linguistics_Ok := Ada.Directories.Exists (Linguistics_JSON);

      declare
         H : constant String := PFLT_SHA256.File_Hex (Authority_Compute);
      begin
         if H'Length = 64 then
            Dig := H;
            Dig_L := 64;
         end if;
      end;

      if Dig_L = 64 then
         S.Live_Hash := Dig;
         Auth := PFLT_Authority.Verify_Pin (Dig);
         S.Live_Hash_Ok := Auth.Ok;
      else
         S.Live_Hash_Ok := False;
         S.Live_Hash := (others => '0');
      end if;

      if S.Root_Exists and then S.Compute_Exists and then S.Live_Hash_Ok then
         Set_Note
           (S, "LIVE pin OK: archive fsot_compute.py SHA256 = D1D38A");
      elsif S.Root_Exists and then S.Compute_Exists then
         Set_Note
           (S, "archive present but LIVE hash mismatch or unreadable");
      elsif S.Root_Exists then
         Set_Note (S, "archive root ok but fsot_compute.py missing");
      else
         Set_Note
           (S, "I: archive not mounted; Ada embeds golden law panel");
      end if;
      Cached := S;
      Has_Cache := True;
      return S;
   end Probe;

   procedure Print_Status (S : Archive_Status) is
   begin
      Put_Line ("=== FSOT Physical Archive binding ===");
      Put_Line ("archive_root=" & Archive_Root);
      Put_Line ("root_exists=" & Boolean'Image (S.Root_Exists));
      Put_Line ("authority_compute=" & Authority_Compute);
      Put_Line ("compute_exists=" & Boolean'Image (S.Compute_Exists));
      Put_Line ("linguistics_json=" & Boolean'Image (S.Linguistics_Ok));
      Put_Line ("live_hash_ok=" & Boolean'Image (S.Live_Hash_Ok));
      Put_Line ("live_sha256=" & S.Live_Hash);
      Put_Line ("expected_sha256=" & Authority_SHA256);
      Put_Line ("pin_prefix=" & S.Pin_Prefix);
      Put_Line ("formula=" & S.Formula);
      Put_Line ("lean_hub=" & Lean_Hub);
      Put_Line ("sr_ite=" & SR_ITE_Root);
      Put_Line ("realities_os=" & Realities_OS);
      if S.Note_Last > 0 then
         Put_Line ("note=" & S.Note (1 .. S.Note_Last));
      end if;
      Put_Line
        ("policy: I: definitive master; students densify knowledge only.");
   end Print_Status;

end PFLT_Archive;
