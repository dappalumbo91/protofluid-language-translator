#!/usr/bin/env python3
"""Force high-quality converse demo senses into densify + train cache."""
from __future__ import annotations

import pickle
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

SEEDS = [
    ("hola", "hello"),
    ("mundo", "world"),
    ("bonjour", "hello"),
    ("monde", "world"),
    ("hallo", "hello"),
    ("welt", "world"),
    ("ciao", "hello"),
    ("mondo", "world"),
    ("ola", "hello"),
    ("olá", "hello"),
    ("wereld", "world"),
    ("aqua", "water"),
    ("agua", "water"),
    ("lingua", "language"),
    ("water", "water"),
    ("jambo", "hello"),
    ("merhaba", "hello"),
    ("dünya", "world"),
    ("dunya", "world"),
    ("namaste", "hello"),
    ("नमस्ते", "hello"),
    ("cześć", "hello"),
    ("swiecie", "world"),
    ("świecie", "world"),
    ("안녕", "hello"),
    ("שלום", "peace"),
    ("γεια", "hi"),
    ("saluton", "hello"),
    ("привет", "hello"),
    ("мир", "world"),
    ("水", "water"),
    ("hello", "hello"),
    ("world", "world"),
    ("peace", "peace"),
    ("thanks", "thanks"),
    ("gracias", "thanks"),
    ("merci", "thanks"),
    ("danke", "thanks"),
]


def main() -> None:
    dens = DATA / "densify.tsv"
    with dens.open("a", encoding="utf-8") as w:
        for k, v in SEEDS:
            w.write(f"{k}\t{v}\n")
    # Append train_mass first, then refresh cache so mtime order stays correct
    with (DATA / "train_mass.tsv").open("a", encoding="utf-8") as w:
        for k, v in SEEDS:
            w.write(f"{k.lower()}\t{v}\n")
    cache = DATA / "train_cache.pkl"
    store: dict = {}
    if cache.exists():
        with cache.open("rb") as f:
            store = pickle.load(f)
    for k, v in SEEDS:
        store[k.lower()] = v
    with cache.open("wb") as f:
        pickle.dump(store, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"injected {len(SEEDS)} converse seeds", flush=True)


if __name__ == "__main__":
    main()
