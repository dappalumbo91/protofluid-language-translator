with Ada.Directories;
with Ada.Streams; use Ada.Streams;
with Ada.Streams.Stream_IO;
with Interfaces; use Interfaces;

package body PFLT_SHA256
  with SPARK_Mode => Off
is

   type U32 is mod 2 ** 32;
   type U64 is mod 2 ** 64;
   type Word_Array is array (Natural range <>) of U32;
   type Byte_Array is array (Natural range <>) of Unsigned_8;

   function RR (X : U32; N : Natural) return U32 is
   begin
      return U32 (Rotate_Right (Unsigned_32 (X), N));
   end RR;

   function Ch (X, Y, Z : U32) return U32 is
   begin
      return (X and Y) xor ((not X) and Z);
   end Ch;

   function Maj (X, Y, Z : U32) return U32 is
   begin
      return (X and Y) xor (X and Z) xor (Y and Z);
   end Maj;

   function Big_S0 (X : U32) return U32 is
   begin
      return RR (X, 2) xor RR (X, 13) xor RR (X, 22);
   end Big_S0;

   function Big_S1 (X : U32) return U32 is
   begin
      return RR (X, 6) xor RR (X, 11) xor RR (X, 25);
   end Big_S1;

   function Sigma0 (X : U32) return U32 is
   begin
      return RR (X, 7) xor RR (X, 18) xor (X / 8);
   end Sigma0;

   function Sigma1 (X : U32) return U32 is
   begin
      return RR (X, 17) xor RR (X, 19) xor (X / 1024);
   end Sigma1;

   K : constant Word_Array (0 .. 63) :=
     (16#428a2f98#, 16#71374491#, 16#b5c0fbcf#, 16#e9b5dba5#,
      16#3956c25b#, 16#59f111f1#, 16#923f82a4#, 16#ab1c5ed5#,
      16#d807aa98#, 16#12835b01#, 16#243185be#, 16#550c7dc3#,
      16#72be5d74#, 16#80deb1fe#, 16#9bdc06a7#, 16#c19bf174#,
      16#e49b69c1#, 16#efbe4786#, 16#0fc19dc6#, 16#240ca1cc#,
      16#2de92c6f#, 16#4a7484aa#, 16#5cb0a9dc#, 16#76f988da#,
      16#983e5152#, 16#a831c66d#, 16#b00327c8#, 16#bf597fc7#,
      16#c6e00bf3#, 16#d5a79147#, 16#06ca6351#, 16#14292967#,
      16#27b70a85#, 16#2e1b2138#, 16#4d2c6dfc#, 16#53380d13#,
      16#650a7354#, 16#766a0abb#, 16#81c2c92e#, 16#92722c85#,
      16#a2bfe8a1#, 16#a81a664b#, 16#c24b8b70#, 16#c76c51a3#,
      16#d192e819#, 16#d6990624#, 16#f40e3585#, 16#106aa070#,
      16#19a4c116#, 16#1e376c08#, 16#2748774c#, 16#34b0bcb5#,
      16#391c0cb3#, 16#4ed8aa4a#, 16#5b9cca4f#, 16#682e6ff3#,
      16#748f82ee#, 16#78a5636f#, 16#84c87814#, 16#8cc70208#,
      16#90befffa#, 16#a4506ceb#, 16#bef9a3f7#, 16#c67178f2#);

   type State is array (0 .. 7) of U32;

   procedure Process_Block (H : in out State; Block : Byte_Array) is
      W : Word_Array (0 .. 63) := (others => 0);
      A, B, C, D, E, F, G, HH : U32;
      T1, T2 : U32;
      Base : constant Natural := Block'First;
   begin
      for I in 0 .. 15 loop
         W (I) :=
           U32 (Block (Base + I * 4)) * 16#1000000#
           + U32 (Block (Base + I * 4 + 1)) * 16#10000#
           + U32 (Block (Base + I * 4 + 2)) * 16#100#
           + U32 (Block (Base + I * 4 + 3));
      end loop;
      for I in 16 .. 63 loop
         W (I) :=
           Sigma1 (W (I - 2))
           + W (I - 7)
           + Sigma0 (W (I - 15))
           + W (I - 16);
      end loop;
      A := H (0);
      B := H (1);
      C := H (2);
      D := H (3);
      E := H (4);
      F := H (5);
      G := H (6);
      HH := H (7);
      for I in 0 .. 63 loop
         T1 := HH + Big_S1 (E) + Ch (E, F, G) + K (I) + W (I);
         T2 := Big_S0 (A) + Maj (A, B, C);
         HH := G;
         G := F;
         F := E;
         E := D + T1;
         D := C;
         C := B;
         B := A;
         A := T1 + T2;
      end loop;
      H (0) := H (0) + A;
      H (1) := H (1) + B;
      H (2) := H (2) + C;
      H (3) := H (3) + D;
      H (4) := H (4) + E;
      H (5) := H (5) + F;
      H (6) := H (6) + G;
      H (7) := H (7) + HH;
   end Process_Block;

   function Hex_Nibble (N : Natural) return Character is
   begin
      if N < 10 then
         return Character'Val (Character'Pos ('0') + N);
      else
         return Character'Val (Character'Pos ('A') + (N - 10));
      end if;
   end Hex_Nibble;

   function State_To_Hex (H : State) return String is
      R : String (1 .. 64);
      P : Natural := 1;
   begin
      for I in H'Range loop
         declare
            V : constant U32 := H (I);
            Bytes : array (0 .. 3) of Natural;
         begin
            Bytes (0) := Natural ((V / 16#1000000#) mod 256);
            Bytes (1) := Natural ((V / 16#10000#) mod 256);
            Bytes (2) := Natural ((V / 16#100#) mod 256);
            Bytes (3) := Natural (V mod 256);
            for J in 0 .. 3 loop
               R (P) := Hex_Nibble (Bytes (J) / 16);
               R (P + 1) := Hex_Nibble (Bytes (J) mod 16);
               P := P + 2;
            end loop;
         end;
      end loop;
      return R;
   end State_To_Hex;

   function Digest_Bytes (Data : Byte_Array) return String is
      H : State :=
        (16#6a09e667#, 16#bb67ae85#, 16#3c6ef372#, 16#a54ff53a#,
         16#510e527f#, 16#9b05688c#, 16#1f83d9ab#, 16#5be0cd19#);
      Len : constant Natural := Data'Length;
      Bit_Len : constant U64 := U64 (Len) * 8;
      Pad_Len : Natural;
      Total : Natural;
   begin
      Pad_Len := (55 - (Len mod 64)) mod 64;
      Total := Len + 1 + Pad_Len + 8;
      declare
         Buf : Byte_Array (0 .. Total - 1) := (others => 0);
      begin
         for I in 0 .. Len - 1 loop
            Buf (I) := Data (Data'First + I);
         end loop;
         if Len = 0 then
            null; -- nothing to copy
         end if;
         Buf (Len) := 16#80#;
         for I in 0 .. 7 loop
            Buf (Total - 1 - I) :=
              Unsigned_8 ((Bit_Len / (2 ** (8 * I))) mod 256);
         end loop;
         declare
            Off : Natural := 0;
         begin
            while Off < Total loop
               Process_Block (H, Buf (Off .. Off + 63));
               Off := Off + 64;
            end loop;
         end;
      end;
      return State_To_Hex (H);
   end Digest_Bytes;

   function Digest_Hex (Data : String) return String is
      B : Byte_Array (1 .. Data'Length);
   begin
      for I in Data'Range loop
         B (I - Data'First + 1) := Unsigned_8 (Character'Pos (Data (I)));
      end loop;
      return Digest_Bytes (B);
   end Digest_Hex;

   function File_Hex (Path : String) return String is
      use Ada.Streams.Stream_IO;
      use type Ada.Directories.File_Size;
      F : File_Type;
      Size : Ada.Directories.File_Size;
   begin
      if not Ada.Directories.Exists (Path) then
         return "";
      end if;
      Size := Ada.Directories.Size (Path);
      if Size = 0 then
         declare
            Empty : Byte_Array (1 .. 0);
         begin
            return Digest_Bytes (Empty);
         end;
      end if;
      if Size > Ada.Directories.File_Size (64_000_000) then
         return "";
      end if;
      declare
         N : constant Stream_Element_Offset :=
           Stream_Element_Offset (Size);
         SEA : Stream_Element_Array (1 .. N);
         Last : Stream_Element_Offset;
         B : Byte_Array (1 .. Natural (N));
      begin
         Open (F, In_File, Path);
         Read (F, SEA, Last);
         Close (F);
         if Last < N then
            return "";
         end if;
         for I in 1 .. Natural (N) loop
            B (I) := Unsigned_8 (SEA (Stream_Element_Offset (I)));
         end loop;
         return Digest_Bytes (B);
      exception
         when others =>
            if Is_Open (F) then
               Close (F);
            end if;
            return "";
      end;
   end File_Hex;

end PFLT_SHA256;
