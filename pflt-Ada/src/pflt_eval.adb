with Ada.Text_IO; use Ada.Text_IO;
with PFLT_Morph;
with PFLT_Store;

package body PFLT_Eval
  with SPARK_Mode => Off
is

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

   function Soft_Match (Gold, Pred : String) return Boolean is
      G : constant String := To_Lower (Gold);
      P : constant String := To_Lower (Pred);
   begin
      if G'Length = 0 or else P'Length = 0 then
         return False;
      end if;
      if G = P or else Contains (P, G) or else Contains (G, P) then
         return True;
      end if;
      if G'Length >= 4 and then P'Length >= 4 then
         if G (G'First .. G'First + 3) = P (P'First .. P'First + 3) then
            return True;
         end if;
      end if;
      --  shared stem length >= 5
      if G'Length >= 5 and then P'Length >= 5 then
         if G (G'First .. G'First + 4) = P (P'First .. P'First + 4) then
            return True;
         end if;
      end if;
      return False;
   end Soft_Match;

   function Run_Sample (Path : String) return Eval_Report is
   begin
      return Run_Sample (Path, 8000, Open_Set);
   end Run_Sample;

   function Run_Sample (Path : String; Max_N : Natural) return Eval_Report is
   begin
      return Run_Sample (Path, Max_N, Open_Set);
   end Run_Sample;

   function Run_Sample
     (Path : String; Max_N : Natural; Mode : Eval_Mode) return Eval_Report
   is
      F       : File_Type;
      R       : Eval_Report;
      Cap     : constant Natural := (if Max_N = 0 then 8000 else Max_N);
      Train_N : Natural := 0;
      Densify_N, Gold_N : Natural := 0;
   begin
      R.Mode := Mode;
      if Mode = Product then
         --  Shipping path: densify + full gold_core (competitor-class inventory)
         PFLT_Store.Clear;
         PFLT_Store.Set_Data_Root
           ("C:\Users\damia\Desktop\pflt\pflt-Ada\data");
         PFLT_Store.Load_Default_Packs (Densify_N, Gold_N);
         Train_N := PFLT_Store.Count;
      else
         --  Honest open-set: train_mass only
         Train_N := PFLT_Store.Load_Open_Set_Train;
      end if;
      R.Train_N := Train_N;

      Open (F, In_File, Path);
      while not End_Of_File (F) loop
         declare
            Line : constant String := Get_Line (F);
            T1, T2 : Natural := 0;
            Tabs : Natural := 0;
         begin
            for I in Line'Range loop
               if Line (I) = ASCII.HT then
                  Tabs := Tabs + 1;
                  if Tabs = 1 then
                     T1 := I;
                  elsif Tabs = 2 then
                     T2 := I;
                     exit;
                  end if;
               end if;
            end loop;
            if T1 > Line'First and then T2 > T1 and then T2 < Line'Last then
               declare
                  Lang  : constant String := Line (Line'First .. T1 - 1);
                  Form  : constant String := Line (T1 + 1 .. T2 - 1);
                  Gold  : constant String := Line (T2 + 1 .. Line'Last);
                  Exact_G : constant String := PFLT_Store.Lookup (Form);
                  Morph   : constant PFLT_Morph.Morph_Hit :=
                    PFLT_Morph.Resolve (Form, Lang);
                  Pred    : String (1 .. 96) := (others => ' ');
                  Pred_L  : Natural := 0;
                  Gl      : constant String := To_Lower (Gold);
                  Pl      : String (1 .. 96) := (others => ' ');
                  Used_Morph : Boolean := False;
               begin
                  if Exact_G'Length > 0 then
                     Pred_L := Natural'Min (Exact_G'Length, 96);
                     Pred (1 .. Pred_L) :=
                       Exact_G (Exact_G'First .. Exact_G'First + Pred_L - 1);
                  elsif Morph.Found then
                     Pred_L := Morph.Gloss_Last;
                     Pred (1 .. Pred_L) := Morph.Gloss (1 .. Pred_L);
                     Used_Morph := True;
                  end if;
                  if Pred_L > 0 then
                     Pl (1 .. Pred_L) := To_Lower (Pred (1 .. Pred_L));
                  end if;
                  R.N := R.N + 1;
                  if Used_Morph then
                     R.Morph_Hits := R.Morph_Hits + 1;
                  end if;
                  if Pred_L > 0
                    and then
                      (Gl = Pl (1 .. Pred_L)
                       or else Contains (Pl (1 .. Pred_L), Gl)
                       or else Contains (Gl, Pl (1 .. Pred_L)))
                  then
                     R.Exact := R.Exact + 1;
                  elsif Pred_L > 0
                    and then Soft_Match (Gold, Pred (1 .. Pred_L))
                  then
                     R.Soft := R.Soft + 1;
                  else
                     R.Miss := R.Miss + 1;
                  end if;
               end;
            end if;
         end;
         exit when R.N >= Cap;
      end loop;
      Close (F);
      if R.N > 0 then
         R.Exact_Rate := Long_Float (R.Exact) / Long_Float (R.N);
         R.Partial_Rate :=
           Long_Float (R.Exact + R.Soft) / Long_Float (R.N);
      end if;
      return R;
   end Run_Sample;

   procedure Print_Report (R : Eval_Report) is
   begin
      if R.Mode = Product then
         Put_Line ("=== Ada PRODUCT eval (full gold+densify+morph) ===");
         Put_Line
           ("Track: SHIPPING path — competitor-class inventory accuracy.");
      else
         Put_Line ("=== Ada OPEN-SET eval (train_mass only) ===");
         Put_Line
           ("Track: morph stress — held-out forms never exact in train.");
      end if;
      Put_Line ("store_entries=" & Natural'Image (R.Train_N));
      Put_Line ("n=" & Natural'Image (R.N));
      Put_Line
        ("exact="
         & Natural'Image (R.Exact)
         & "  soft="
         & Natural'Image (R.Soft)
         & "  miss="
         & Natural'Image (R.Miss)
         & "  morph_resolve="
         & Natural'Image (R.Morph_Hits));
      Put_Line
        ("exact_rate="
         & Long_Float'Image (R.Exact_Rate)
         & "  partial_rate="
         & Long_Float'Image (R.Partial_Rate));
      if R.Mode = Product then
         Put_Line
           ("Goal PRODUCT: partial >= 0.90 (match/beat inventory-class systems).");
      else
         Put_Line
           ("Goal OPEN-SET: partial >= 0.55 then 0.70 (harder than BLEU reports).");
      end if;
   end Print_Report;

end PFLT_Eval;
