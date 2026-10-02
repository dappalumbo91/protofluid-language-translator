(* FSOT PFLT Math Microscope — master loader *)
(* Open in Mathematica / Wolfram Engine and evaluate *)
pfltDir = If[$InputFileName =!= "", DirectoryName[$InputFileName], NotebookDirectory[]];
Get[FileNameJoin[{pfltDir, "FSOT_Symbolic_Microscope.wl"}]];
Print["=== Symbolic pathway ==="];
FSOTPrintPathway[];
Get[FileNameJoin[{pfltDir, "trace_linguistic.wl"}]];
Print["=== Numeric domain trace (linguistic) ==="];
Print["FSOTTrace: ", FSOTTrace[]];
Print["Diff vs Python panel: ", FSOTDiff[]];
(* Other domains: Get["…/trace_historical.wl"] etc. *)
(* Formal: compare N[FSOTDerived[]["K"]] to formal/golden_fsot_pflt.json constants.K *)
