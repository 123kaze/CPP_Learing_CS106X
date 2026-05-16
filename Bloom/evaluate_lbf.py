import argparse
import math
import random
from typing import Dict, List, Sequence, Tuple

from Bloom import PiecewiseLinearLBF


GIB_BITS = 1024 * 1024 * 1024 * 8
SEGMENT_BITS = 4 * 64


def bloom_fpr(bit_count: int, item_count: int) -> Tuple[int, float]:
    if item_count <= 0:
        return 1, 0.0
    k = max(1, round((bit_count / item_count) * math.log(2)))
    fpr = (1.0 - math.exp(-k * item_count / bit_count)) ** k
    return k, fpr


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> Tuple[float, float]:
    if trials == 0:
        return 0.0, 0.0

    p = successes / trials
    denom = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denom
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * trials)) / trials) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def clustered_positives(n: int, universe: int, clusters: int, width_ratio: float) -> List[int]:
    width = max(1, int(universe * width_ratio / clusters))
    result = set()
    centers = [int((i + 0.5) * universe / clusters) for i in range(clusters)]

    while len(result) < n:
        center = random.choice(centers)
        key = random.randint(center - width // 2, center + width // 2)
        if 0 <= key < universe:
            result.add(key)

    return sorted(result)


def uniform_positives(n: int, universe: int) -> List[int]:
    return sorted(random.sample(range(universe), n))


def make_negatives(count: int, universe: int, positives: Sequence[int]) -> List[int]:
    positives_set = set(positives)
    result = []
    while len(result) < count:
        key = random.randrange(universe)
        if key not in positives_set:
            result.append(key)
    return result


def empirical_rates(
    positives: Sequence[int],
    train_negatives: Sequence[int],
    test_negatives: Sequence[int],
    segment_count: int,
    threshold: float,
) -> Tuple[float, float, Tuple[float, float]]:
    model = PiecewiseLinearLBF(
        hashNum=1,
        maxSize=1,
        segmentNum=segment_count,
        threshold=threshold,
    )
    model.train(positives, train_negatives)

    backup_items = sum(1 for key in positives if model.predict_score(key) < threshold)
    model_false_accepts = sum(1 for key in test_negatives if model.predict_score(key) >= threshold)
    alpha = model_false_accepts / len(test_negatives)
    alpha_ci = wilson_interval(model_false_accepts, len(test_negatives))
    backup_ratio = backup_items / len(positives)
    return alpha, backup_ratio, alpha_ci


def auto_tuned_report(
    positives: Sequence[int],
    train_negatives: Sequence[int],
    validation_negatives: Sequence[int],
    test_negatives: Sequence[int],
    total_bits: int,
    projected_items: int,
    segment_count: int,
) -> Tuple[Dict[str, float], Tuple[float, float]]:
    model = PiecewiseLinearLBF(
        hashNum=1,
        maxSize=1,
        segmentNum=segment_count,
        threshold=0.5,
    )
    model.train_auto(
        positives,
        train_negatives,
        validation_negatives,
        total_bits,
        projected_items,
        SEGMENT_BITS,
    )

    report = model.estimate_projected_fpr(
        positives,
        test_negatives,
        total_bits,
        projected_items,
        model.threshold,
        SEGMENT_BITS,
    )
    false_accepts = sum(1 for key in test_negatives if model.predict_score(key) >= model.threshold)
    alpha_ci = wilson_interval(false_accepts, len(test_negatives))
    return report, alpha_ci


def run_case(
    name: str,
    positives: Sequence[int],
    train_negatives: Sequence[int],
    test_negatives: Sequence[int],
    total_bits: int,
    projected_items: int,
    segment_count: int,
    threshold: float,
    auto_tune: bool,
):
    alpha, backup_ratio, alpha_ci = empirical_rates(
        positives,
        train_negatives,
        test_negatives,
        segment_count,
        threshold,
    )

    model_bits = segment_count * SEGMENT_BITS
    backup_bits = total_bits - model_bits
    projected_backup_items = max(0, round(projected_items * backup_ratio))

    baseline_k, baseline_fpr = bloom_fpr(total_bits, projected_items)
    backup_k, backup_fpr = bloom_fpr(backup_bits, projected_backup_items)
    lbf_fpr = alpha + (1.0 - alpha) * backup_fpr
    improvement = baseline_fpr / lbf_fpr if lbf_fpr > 0 else math.inf

    print(f"case={name}")
    print(f"  projected_items={projected_items:,}")
    print(f"  total_memory_bits={total_bits:,}")
    print(f"  total_memory_gib={total_bits / GIB_BITS:.3f}")
    print(f"  segments={segment_count}, threshold={threshold}")
    print(f"  model_bits={model_bits:,}, backup_bits={backup_bits:,}")
    print(f"  model_false_accept_alpha={alpha:.8g}")
    print(f"  alpha_95ci=[{alpha_ci[0]:.8g}, {alpha_ci[1]:.8g}]")
    print(f"  backup_positive_ratio={backup_ratio:.8g}")
    print(f"  baseline_k={baseline_k}, baseline_fpr={baseline_fpr:.8g}")
    print(f"  backup_k={backup_k}, backup_fpr={backup_fpr:.8g}")
    print(f"  projected_lbf_fpr={lbf_fpr:.8g}")
    print(f"  improvement_baseline_over_lbf={improvement:.8g}")

    if auto_tune:
        validation_negatives, heldout_negatives = split_half(test_negatives)
        report, tuned_alpha_ci = auto_tuned_report(
            positives,
            train_negatives,
            validation_negatives,
            heldout_negatives,
            total_bits,
            projected_items,
            segment_count,
        )
        print("  auto_tuned:")
        print(f"    threshold={report['threshold']:.8g}")
        print(f"    model_false_accept_alpha={report['alpha']:.8g}")
        print(f"    alpha_95ci=[{tuned_alpha_ci[0]:.8g}, {tuned_alpha_ci[1]:.8g}]")
        print(f"    backup_positive_ratio={report['backup_positive_ratio']:.8g}")
        print(f"    backup_fpr={report['backup_fpr']:.8g}")
        print(f"    projected_lbf_fpr={report['lbf_fpr']:.8g}")
        print(f"    improvement_baseline_over_lbf={report['improvement']:.8g}")
    print()


def split_half(items: Sequence[int]) -> Tuple[List[int], List[int]]:
    midpoint = len(items) // 2
    return list(items[:midpoint]), list(items[midpoint:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--sample-items", type=int, default=100_000)
    parser.add_argument("--test-negatives", type=int, default=200_000)
    parser.add_argument("--projected-items", type=int, default=1_000_000_000)
    parser.add_argument("--memory-gib", type=float, default=4.0)
    parser.add_argument("--segments", type=int, default=256)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--auto-tune", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    universe = args.sample_items * 200
    total_bits = int(args.memory_gib * GIB_BITS)

    cases = [
        (
            "clustered_5pct",
            clustered_positives(args.sample_items, universe, clusters=32, width_ratio=0.05),
        ),
        (
            "clustered_20pct",
            clustered_positives(args.sample_items, universe, clusters=32, width_ratio=0.20),
        ),
        (
            "uniform_random",
            uniform_positives(args.sample_items, universe),
        ),
    ]

    for name, positives in cases:
        train_negatives = make_negatives(args.sample_items, universe, positives)
        test_negatives = make_negatives(args.test_negatives, universe, positives)
        run_case(
            name,
            positives,
            train_negatives,
            test_negatives,
            total_bits,
            args.projected_items,
            args.segments,
            args.threshold,
            args.auto_tune,
        )


if __name__ == "__main__":
    main()
