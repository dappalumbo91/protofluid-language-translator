#!/usr/bin/env python3
from dual_track_eval import split_90_10
from held_out_classical import score
from name_gazetteer import NameGazetteer
from PFLT_FSOT_2_1_aligned import PFLT
from promote_and_train_classical import inject, load_all_gold, partition_core_name


def main() -> None:
    gold = load_all_gold()
    core, _ = partition_core_name(gold)
    train, test = split_90_10(core)
    p = PFLT(
        load_historical=True,
        load_classical=False,
        load_hieroglyphs=False,
        load_domain_lexica=False,
        enable_gapfill=True,
    )
    inject(p, train, expand_paradigms=False)
    p._name_gaz = NameGazetteer(load=False)
    for w, ctx in (
        ("Κρής", "mythological"),
        ("αἰτία", "mythological"),
        ("βωμός", "mythological"),
        ("ζωή", "mythological"),
        ("Ναζωραῖος", "mythological"),
        ("Γαλάτης", "mythological"),
        ("manibus", "historical"),
        ("aqua", "historical"),
    ):
        m, e = p.map_token(w, ctx)
        print(f"{w:20s} exact={e} -> {m}")

    sample = test[:: max(1, len(test) // 1500)][:1500]
    s = score(p, sample, miss_cap=20)
    print(
        f"sample n={s['n']} exact={s['exact_rate']*100:.1f}% "
        f"partial={s['exact_or_partial_rate']*100:.1f}%"
    )


if __name__ == "__main__":
    main()
