From Stdlib Require Import QArith.
Definition golden_K : Q := 420221664161 # 1000000000000.
Compute (Qcompare (0 # 1) golden_K).
