package body PFLT_Domains
  with SPARK_Mode => On
is

   function Domain_Name (D : Domain_Id) return String is
   begin
      case D is
         when Linguistic    => return "linguistic";
         when Historical    => return "historical";
         when Mythological  => return "mythological";
         when Quantum       => return "quantum";
         when Cosmological  => return "cosmological";
         when Biological    => return "biological";
         when Hieroglyphic  => return "hieroglyphic";
         when Consciousness => return "consciousness";
         when English       => return "english";
      end case;
   end Domain_Name;

   function Default_Input (D : Domain_Id) return PFLT_Scalar.Scalar_Input is
      I : PFLT_Scalar.Scalar_Input;
   begin
      I.N := 1.0;
      I.P := 1.0;
      I.Recent_Hits := 0.0;
      I.Rho := 1.0;
      I.Scale := 1.0;
      I.Amplitude := 1.0;
      I.Trend_Bias := 0.0;
      case D is
         when Linguistic =>
            I.D_Eff := 12.0;
            I.Observed := True;
            I.Delta_Psi := 0.8;
            I.Delta_Theta := 1.0;
         when Historical =>
            I.D_Eff := 21.0;
            I.Observed := True;
            I.Delta_Psi := 0.8;
            I.Delta_Theta := 1.0;
         when Mythological =>
            I.D_Eff := 21.0;
            I.Observed := True;
            I.Delta_Psi := 0.8;
            I.Delta_Theta := 1.0;
         when Quantum =>
            I.D_Eff := 6.0;
            I.Observed := True;
            I.Delta_Psi := 1.0;
            I.Delta_Theta := 1.0;
         when Cosmological =>
            I.D_Eff := 25.0;
            I.Observed := False;
            I.Delta_Psi := 1.0;
            I.Delta_Theta := 1.0;
         when Biological =>
            I.D_Eff := 12.0;
            I.Observed := False;
            I.Delta_Psi := 0.05;
            I.Delta_Theta := 1.0;
         when Hieroglyphic =>
            I.D_Eff := 18.0;
            I.Observed := True;
            I.Delta_Psi := 0.9;
            I.Delta_Theta := 1.0;
         when Consciousness =>
            I.D_Eff := 14.0;
            I.Observed := True;
            I.Delta_Psi := 0.1;
            I.Delta_Theta := 1.0;
         when English =>
            I.D_Eff := 12.0;
            I.Observed := True;
            I.Delta_Psi := 0.8;
            I.Delta_Theta := 1.0;
      end case;
      return I;
   end Default_Input;

end PFLT_Domains;
