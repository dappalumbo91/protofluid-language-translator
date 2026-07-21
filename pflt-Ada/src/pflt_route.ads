--  Lightweight domain routing from text (mirrors Python route keywords).

with PFLT_Domains;

package PFLT_Route
  with SPARK_Mode => Off
is

   function Route_Domain (Text : String) return PFLT_Domains.Domain_Id;

end PFLT_Route;
