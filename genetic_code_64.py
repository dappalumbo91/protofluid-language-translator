#!/usr/bin/env python3
"""Standard genetic code (64 codons) → FSOT-process meanings for PFLT genomic domain."""
from __future__ import annotations

# DNA codon → amino acid / signal (IUPAC standard table)
DNA_TO_AA = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

AA_PROCESS = {
    "M": "start",  # ATG initiator (also Met)
    "*": "stop",
    "F": "aromatic_ring",
    "L": "hydrophobic_chain",
    "S": "hydroxyl_link",
    "Y": "signal_tyrosine",
    "C": "disulfide_bridge",
    "W": "aromatic_core",
    "P": "kink_proline",
    "H": "charge_histidine",
    "Q": "amide_link",
    "R": "charge_arginine",
    "I": "hydrophobic_branch",
    "T": "hydroxyl_threonine",
    "N": "amide_asparagine",
    "K": "charge_lysine",
    "V": "hydrophobic_valine",
    "A": "compact_alanine",
    "D": "charge_aspartate",
    "E": "charge_glutamate",
    "G": "flex_glycine",
}

# Preserve PFLT legacy process words for key codons
LEGACY = {
    "ATG": "start",
    "GTG": "transfer",
    "CAC": "energy",
    "CTG": "structure",
    "ACT": "action",
    "TAA": "stop",
    "TAG": "stop",
    "TGA": "stop",
    "CAA": "energy_link",
    "GCG": "core_structure",
}


def codon_lexicon() -> dict:
    """DNA + RNA forms for all 64 codons."""
    lex = {}
    for dna, aa in DNA_TO_AA.items():
        meaning = LEGACY.get(dna) or AA_PROCESS.get(aa, f"aa_{aa}")
        if dna == "ATG":
            meaning = "start"
        lex[dna.lower()] = meaning
        lex[dna.upper()] = meaning
        # RNA only when T→U actually changes the string
        rna = dna.replace("T", "U")
        if rna == dna:
            continue
        if dna == "ATG":
            lex["aug"] = "start_rna"
            lex["AUG"] = "start_rna"
        elif dna in ("TAA", "TAG", "TGA"):
            lex[rna.lower()] = "stop_rna"
            lex[rna.upper()] = "stop_rna"
        else:
            rm = meaning if meaning.endswith("_rna") else meaning + "_rna"
            lex[rna.lower()] = rm
            lex[rna.upper()] = rm
    return lex


if __name__ == "__main__":
    lex = codon_lexicon()
    print("entries", len(lex), "unique dna", len(DNA_TO_AA))
    for c in ["ATG", "TTT", "TAA", "AUG", "GAA"]:
        print(c, lex.get(c.lower()), lex.get(c))
