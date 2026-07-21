with Ada.Calendar;
with Ada.Calendar.Formatting;
with Ada.Directories;
with Ada.Strings.Unbounded; use Ada.Strings.Unbounded;
with Ada.Text_IO;
with PFLT_Domains;

package body PFLT_Ledger
  with SPARK_Mode => Off
is

   Ledger_Path : Unbounded_String :=
     To_Unbounded_String ("data/knowledge_ledger_ada.jsonl");
   Count : Natural := 0;

   procedure Set_Path (Path : String) is
   begin
      Ledger_Path := To_Unbounded_String (Path);
   end Set_Path;

   function Escape (S : String) return String is
      Buf : String (1 .. S'Length * 2 + 2);
      L   : Natural := 0;
   begin
      L := L + 1;
      Buf (L) := '"';
      for C of S loop
         if C = '"' or else C = '\' then
            L := L + 1;
            Buf (L) := '\';
         end if;
         if C = ASCII.LF or else C = ASCII.CR or else C = ASCII.HT then
            L := L + 1;
            Buf (L) := ' ';
         else
            L := L + 1;
            Buf (L) := C;
         end if;
      end loop;
      L := L + 1;
      Buf (L) := '"';
      return Buf (1 .. L);
   end Escape;

   function Iso_Now return String is
      use Ada.Calendar;
      T : constant Time := Clock;
   begin
      return Ada.Calendar.Formatting.Image (T);
   end Iso_Now;

   procedure Append_Claim
     (Source_Text  : String;
      Domain       : PFLT_Domains.Domain_Id;
      Gloss        : String;
      Panel        : PFLT_Scalar.Scalar_Panel;
      Authority_Ok : Boolean)
   is
      use Ada.Text_IO;
      F    : File_Type;
      Pstr : constant String := To_String (Ledger_Path);
      Dir  : constant String :=
        Ada.Directories.Containing_Directory (Pstr);
   begin
      if Dir'Length > 0 and then not Ada.Directories.Exists (Dir) then
         Ada.Directories.Create_Path (Dir);
      end if;
      if Ada.Directories.Exists (Pstr) then
         Open (F, Append_File, Pstr);
      else
         Create (F, Out_File, Pstr);
      end if;
      Put (F, "{");
      Put (F, """built_utc"":" & Escape (Iso_Now) & ",");
      Put (F, """source_text"":" & Escape (Source_Text) & ",");
      Put (F, """domain"":"
          & Escape (PFLT_Domains.Domain_Name (Domain)) & ",");
      Put (F, """claim_text"":" & Escape (Gloss) & ",");
      Put (F, """S"":" & Long_Float'Image (Panel.S) & ",");
      Put (F, """D_eff"":" & Long_Float'Image (Panel.D_Eff) & ",");
      Put (F, """authority_ok"":"
          & (if Authority_Ok then "true" else "false") & ",");
      Put (F, """engine"":""pflt_ada_v1""");
      Put_Line (F, "}");
      Close (F);
      Count := Count + 1;
   end Append_Claim;

   function Claim_Count return Natural is
   begin
      return Count;
   end Claim_Count;

end PFLT_Ledger;
