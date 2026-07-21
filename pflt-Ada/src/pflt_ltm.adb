with Ada.Directories;
with Ada.Text_IO;
with Ada.Strings.Unbounded; use Ada.Strings.Unbounded;

package body PFLT_LTM
  with SPARK_Mode => Off
is

   Path_U : Unbounded_String :=
     To_Unbounded_String
       ("C:\Users\damia\Desktop\pflt\pflt-Ada\data\ltm_mulling.jsonl");
   Episodes : Natural := 0;

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

   procedure Escape_JSON (Src : String; Dst : in out String; Last : out Natural)
   is
   begin
      Last := 0;
      for C of Src loop
         exit when Last >= Dst'Last - 1;
         if C = '"' or else C = '\' then
            Last := Last + 1;
            Dst (Last) := '\';
            exit when Last >= Dst'Last;
            Last := Last + 1;
            Dst (Last) := C;
         elsif C = ASCII.LF or else C = ASCII.CR then
            Last := Last + 1;
            Dst (Last) := ' ';
         else
            Last := Last + 1;
            Dst (Last) := C;
         end if;
      end loop;
   end Escape_JSON;

   procedure Set_Path (Path : String) is
   begin
      Path_U := To_Unbounded_String (Path);
   end Set_Path;

   procedure Load_Default_Path is
   begin
      Set_Path
        ("C:\Users\damia\Desktop\pflt\pflt-Ada\data\ltm_mulling.jsonl");
   end Load_Default_Path;

   procedure Remember
     (Text   : String;
      Domain : String;
      Gloss  : String;
      S      : Long_Float;
      Note   : String := "")
   is
      use Ada.Text_IO;
      Path : constant String := To_String (Path_U);
      F    : File_Type;
      Te, Dom_E, Gl, No : String (1 .. 256);
      TeL, DomL, GlL, NoL : Natural;
   begin
      Escape_JSON (Text, Te, TeL);
      Escape_JSON (Domain, Dom_E, DomL);
      Escape_JSON (Gloss, Gl, GlL);
      Escape_JSON (Note, No, NoL);
      begin
         if Ada.Directories.Exists (Path) then
            Open (F, Append_File, Path);
         else
            Create (F, Out_File, Path);
         end if;
         Put (F, "{""text"":""");
         if TeL > 0 then
            Put (F, Te (1 .. TeL));
         end if;
         Put (F, """,""domain"":""");
         if DomL > 0 then
            Put (F, Dom_E (1 .. DomL));
         end if;
         Put (F, """,""gloss"":""");
         if GlL > 0 then
            Put (F, Gl (1 .. GlL));
         end if;
         Put (F, """,""S"":");
         Put (F, Long_Float'Image (S));
         Put (F, ",""note"":""");
         if NoL > 0 then
            Put (F, No (1 .. NoL));
         end if;
         Put_Line (F, """,""law_rewritten"":false}");
         Close (F);
         Episodes := Episodes + 1;
      exception
         when others =>
            if Is_Open (F) then
               Close (F);
            end if;
      end;
   end Remember;

   function Recall (Query : String; Max_Hits : Natural := 3) return String is
      use Ada.Text_IO;
      Path : constant String := To_String (Path_U);
      F    : File_Type;
      Q    : constant String := To_Lower (Query);
      OutB : String (1 .. 1024) := (others => ' ');
      Last : Natural := 0;
      Hits : Natural := 0;

      procedure Append (Piece : String) is
      begin
         for C of Piece loop
            exit when Last >= OutB'Last;
            Last := Last + 1;
            OutB (Last) := C;
         end loop;
      end Append;
   begin
      if not Ada.Directories.Exists (Path) or else Q'Length = 0 then
         return "";
      end if;
      Open (F, In_File, Path);
      while not End_Of_File (F) loop
         declare
            Line : constant String := Get_Line (F);
         begin
            if Contains (To_Lower (Line), Q) then
               Hits := Hits + 1;
               if Hits <= Max_Hits then
                  if Last > 0 then
                     Append (String'(1 => ASCII.LF));
                  end if;
                  Append ("LTM[");
                  Append (Natural'Image (Hits));
                  Append ("]: ");
                  --  truncate long lines
                  if Line'Length > 160 then
                     Append (Line (Line'First .. Line'First + 159));
                     Append ("…");
                  else
                     Append (Line);
                  end if;
               end if;
            end if;
         end;
      end loop;
      Close (F);
      if Last = 0 then
         return "";
      end if;
      return OutB (1 .. Last);
   end Recall;

   function Episode_Count return Natural is
   begin
      return Episodes;
   end Episode_Count;

   function Mull_Note
     (Map_Rate : Long_Float; Unresolved_N : Natural) return String
   is
   begin
      if Unresolved_N > 0 or else Map_Rate < 0.85 then
         return
           "Mull: thin knowledge — densify via inject/export; "
           & "law unchanged (SR-ITE observer densify policy).";
      end if;
      return "Mull: coverage dense; no densify plan.";
   end Mull_Note;

end PFLT_LTM;
