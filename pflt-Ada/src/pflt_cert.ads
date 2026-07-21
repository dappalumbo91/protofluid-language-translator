--  Certified numeric gate (archive certified-agent culture).
--  Law numbers from pinned scalar; linguistics from archive anchors.
--  Refuses vibes math as FSOT law.

with PFLT_Scalar;

package PFLT_Cert
  with SPARK_Mode => Off
is

   type Cert_Report is record
      Ok            : Boolean := True;
      Block         : String (1 .. 1024) := (others => ' ');
      Block_Last    : Natural := 0;
      Certified_N   : Natural := 0;
      Refused_N     : Natural := 0;
   end record;

   --  Scan user text; emit certified panel / anchor lines or refuse.
   function Certify_Turn
     (Text  : String;
      Panel : PFLT_Scalar.Scalar_Panel) return Cert_Report;

   function Block_Slice (R : Cert_Report) return String;

end PFLT_Cert;
