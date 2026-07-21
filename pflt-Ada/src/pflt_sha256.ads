--  Pure Ada SHA-256 (FIPS 180-4) for live archive pin verify.
--  Not SPARK (byte streams); law packages stay pure.

package PFLT_SHA256
  with SPARK_Mode => Off
is

   --  Hex uppercase digest of file bytes; "" if missing/unreadable.
   function File_Hex (Path : String) return String;

   --  Hex uppercase digest of raw string bytes.
   function Digest_Hex (Data : String) return String;

end PFLT_SHA256;
