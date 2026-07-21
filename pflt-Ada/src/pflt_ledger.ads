--  Append-only knowledge ledger (JSONL). Never rewrites FSOT law.

with PFLT_Scalar;
with PFLT_Domains;

package PFLT_Ledger
  with SPARK_Mode => Off
is

   procedure Set_Path (Path : String);

   procedure Append_Claim
     (Source_Text : String;
      Domain      : PFLT_Domains.Domain_Id;
      Gloss       : String;
      Panel       : PFLT_Scalar.Scalar_Panel;
      Authority_Ok : Boolean);

   function Claim_Count return Natural;

end PFLT_Ledger;
