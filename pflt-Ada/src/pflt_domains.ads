--  Domain routing params aligned with Python DOMAIN_PARAMS (subset).

with PFLT_Scalar;

package PFLT_Domains
  with SPARK_Mode => On
is

   type Domain_Id is
     (Linguistic,
      Historical,
      Mythological,
      Quantum,
      Cosmological,
      Biological,
      Hieroglyphic,
      Consciousness,
      English);

   function Domain_Name (D : Domain_Id) return String;

   function Default_Input (D : Domain_Id) return PFLT_Scalar.Scalar_Input
     with Global => null;

end PFLT_Domains;
