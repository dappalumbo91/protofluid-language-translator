--  Law authority pin (matches Python fsot_law_bridge.AUTHORITY_SHA256).
--  Full SHA-256 of archive vendor/fsot_compute.py — D1D38A… prefix for status.

package PFLT_Authority
  with SPARK_Mode => On
is

   --  Full expected pin (uppercase hex)
   Expected_SHA256 : constant String :=
     "D1D38A185487B452E470AC68ECE2EB45AEB1CA9CE25FC9BF9564C19633FFBE70";

   Expected_Prefix : constant String := "D1D38A";

   type Authority_Status is record
      Ok      : Boolean;
      Prefix  : String (1 .. 6);
      Note    : String (1 .. 48);
   end record;

   --  Runtime check of an observed digest string (may be empty if archive absent).
   function Verify_Pin (Observed_SHA256 : String) return Authority_Status
     with
       Global => null,
       Post   =>
         (if Observed_SHA256'Length = Expected_SHA256'Length
            and then Observed_SHA256 = Expected_SHA256
          then Verify_Pin'Result.Ok
          else not Verify_Pin'Result.Ok
             or else Observed_SHA256'Length = 0);

   --  Built-in status: Ada kernel ships the pin; archive file check is optional.
   function Kernel_Pin_Status return Authority_Status
     with Global => null;

end PFLT_Authority;
