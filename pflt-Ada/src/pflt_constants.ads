--  Protofluid Language Translator (Ada/SPARK)
--  FSOT 2.1 seed constants — frozen f64 panel matching formal/golden_fsot_pflt.json
--
--  Formula: S = K * (T1 + T2 + T3)
--  Authority culture: zero free fit knobs; seeds π,e,φ,γ,G_Catalan lineage.

package PFLT_Constants
  with SPARK_Mode => On
is

   --  Fundamental seeds (IEEE f64 snapshots of golden fixtures)
   Pi      : constant Long_Float := 3.141_592_653_589_793;
   E_Const : constant Long_Float := 2.718_281_828_459_045;
   Phi     : constant Long_Float := 1.618_033_988_749_895;
   Gamma_E : constant Long_Float := 0.577_215_664_901_532_9;
   G_Cat   : constant Long_Float := 0.915_965_594_177_219_0;

   --  Layer-1 / Layer-2 derived constants (golden_fsot_pflt.json)
   Alpha    : constant Long_Float := 0.000_808_293_741_414_040_5;
   Psi_Con  : constant Long_Float := 0.632_120_558_828_557_7;
   Eta_Eff  : constant Long_Float := 0.466_942_206_924_259_86;
   Beta     : constant Long_Float := 2.620_866_911_333_223e-17;
   Gamma_C  : constant Long_Float := -0.428_388_516_792_206_6;
   Omega    : constant Long_Float := 1.294_130_578_055_966_2;
   Theta_S  : constant Long_Float := 0.290_896_540_545_173_05;
   Poof     : constant Long_Float := 0.153_482_214_894_450_8;
   C_Eff    : constant Long_Float := 0.957_702_202_620_561_3;
   A_Bleed  : constant Long_Float := 1.046_973_630_587_551;
   P_Var    : constant Long_Float := 0.957_987_122_672_275_7;
   B_In     : constant Long_Float := 0.787_940_792_276_443_5;
   A_In     : constant Long_Float := 1.666_853_845_004_573_1;
   Suction  : constant Long_Float := 0.147_033_985_428_102_84;
   Chaos    : constant Long_Float := -0.331_024_182_610_481_83;
   P_Base   : constant Long_Float := 0.212_345_776_239_378_42;
   P_New    : constant Long_Float := 0.300_302_276_670_371_46;
   C_Factor : constant Long_Float := 0.287_600_151_819_183_97;
   K        : constant Long_Float := 0.420_221_664_160_696_7;

   Formula : constant String := "S = K*(T1+T2+T3)";

end PFLT_Constants;
