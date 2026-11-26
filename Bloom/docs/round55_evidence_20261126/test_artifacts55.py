"""Pure aggregation fixtures; these are not new experimental observations."""
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('artifacts55', HERE / 'artifacts55.py')
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


def fixture(seed, workload, count, oracle=None):
    c = dict(dataset='synthetic_fixture', budget_kib=1, workload=workload, seed=seed, cohort='main')
    return dict(case=c, members=100, hindsight_h_fp=oracle,
                R={m: dict(fp=count, trees=1) for m in P.A.METHODS},
                ablations=[dict(variant=v, fp=count) for v in P.A.ABLS])


class ArtifactTests(unittest.TestCase):
    def test_main_sum_of_seed_means(self):
        # Not a raw sum and not a mean over all workloads.
        items = [fixture(0, 'uniform-全部', 10), fixture(1, 'uniform-全部', 20),
                 fixture(0, '每key一次', 2), fixture(1, '每key一次', 4), fixture(0, P.A.PROBE, 100000)]
        result = P.main_tables(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['RA6'], 18)
        self.assertEqual(result[0]['cases'], 4)

    def test_hindsight_reference_not_replay(self):
        item = fixture(0, 'uniform-全部', 100, oracle=0)
        self.assertEqual(P.cohorts(item), ('all_nonprobe', 'low_reference_nonprobe'))
        item['hindsight_h_fp'] = None
        self.assertIn('eligible30_nonprobe', P.cohorts(item))

    def test_prediction_threshold_uses_all_ten(self):
        top = [dict(stage1=i + 10, stage2=i + 5, fp=i + 50) for i in range(10)]
        top[-1]['fp'] = 0
        r = P.ranking_metrics(top)
        self.assertFalse(r['best10_ge30'])
        self.assertFalse(r['best10_in_top5'])

    def test_constant_rank_is_undefined(self):
        r = P.ranking_metrics([dict(stage1=1, stage2=2, fp=0) for _ in range(10)])
        self.assertIsNone(r['stage1_rho'])
        self.assertIsNone(r['stage2_rho'])
        self.assertEqual(r['stage1_relative_errors'], [])
        self.assertEqual(r['stage1_zero_measured_excluded_from_relative_error'], 5)
        self.assertTrue(r['stage1_picks_best'])

    def test_stage2_rank_and_error(self):
        top = [dict(stage1=i + 1, stage2=5 - i, fp=5 - i) for i in range(5)]
        top += [dict(stage1=i + 6, stage2=i + 6, fp=i + 6) for i in range(5)]
        r = P.ranking_metrics(top)
        self.assertAlmostEqual(r['stage1_rho'], -1)
        self.assertAlmostEqual(r['stage2_rho'], 1)
        self.assertFalse(r['stage1_picks_best'])
        self.assertTrue(r['stage2_picks_best'])
        self.assertEqual(r['stage2_relative_errors'], [0] * 5)

    def test_ablation_mean_before_ratio_and_probe_separate(self):
        a, b = fixture(0, 'uniform-全部', 0), fixture(1, 'uniform-全部', 10)
        a['ablations'][0]['fp'] = 6
        variant = a['ablations'][0]['variant']
        probe = fixture(0, P.A.PROBE, 100)
        detail, summary = P.ablation_tables([a, b, probe])
        row = next(r for r in detail if r['variant'] == variant and r['workload'] != P.A.PROBE)
        self.assertEqual(row['ratio'], (8 + 1) / (5 + 1))
        main = next(r for r in summary if r['variant'] == variant and r['scope'] == 'main_nonprobe')
        all_ = next(r for r in summary if r['variant'] == variant and r['scope'] == 'original_main_including_probe')
        self.assertEqual(main['setting_workloads'], 1)
        self.assertEqual(all_['setting_workloads'], 2)

    def test_motivation_and_mawi_render_in_memory(self):
        # Only disposable, synthetic fixtures; no fake experimental file is retained.
        fracs = [0, .001, .002, .005, .01, .015, .02, .05, .1, .2, .3, .4, .6]
        cases = []
        for ds, workloads in (
            ('shalla', ['每key一次', 'uniform-全部', 'zipf1.0-全部', 'zipf1.0-10万', 'zipf1.2-1万']),
            ('caida_flow', ['真实轨迹']), ('mawi2021_flow', ['真实轨迹'])):
            for budget in (256, 1024, 2048, 4096):
                for workload in workloads:
                    item = fixture(0, workload, 10)
                    item['case'].update(dataset=ds, budget_kib=budget)
                    item['weighted_full'] = [dict(frac=frac, fp=100 + j) for j, frac in enumerate(fracs)]
                    cases.append(item)
        mawi = []
        for budget in (16, 24, 32, 128):
            item = fixture(0, '真实轨迹', 10)
            item['case'].update(dataset='mawi2024_flow', budget_kib=budget, cohort='previously_used_MAWI24')
            item['weighted_full'] = [dict(trees=1, frac=frac, fp=j + 10, stage1=j + 11, stage2=j + 12, cache_bytes=0) for j, frac in enumerate(fracs)]
            for row in item['R'].values():
                row.update({p: 32 for p in P.A.PARTS})
                row.update(total_bytes=160, frac=0)
            mawi.append(item)
        captured = []
        oldsave = P.savefigure
        def capture(fig, out, name):
            fig.canvas.draw()
            captured.append(name)
            P.plt.close(fig)
        P.savefigure = capture
        try:
            with tempfile.TemporaryDirectory() as path:
                P.chart_style()
                P.motivation(cases, Path(path))
                P.mawi_figures(mawi, Path(path))
        finally:
            P.savefigure = oldsave
        self.assertEqual(len(captured), 4)

    def test_case_plot_all_points_no_fixed_clipping(self):
        # Render in memory only; the synthetic fixture never becomes a result file.
        items = [fixture(0, 'uniform-1万', 1), fixture(1, 'uniform-1万', 10**6)]
        items[1]['R']['Replay']['fp'] = 1
        captured = []
        oldsave = P.savefigure
        def capture(fig, out, name):
            fig.canvas.draw()
            lo, hi = fig.axes[0].get_xlim()
            captured.append((lo, hi))
            P.plt.close(fig)
        P.savefigure = capture
        try:
            with tempfile.TemporaryDirectory() as path:
                P.chart_style()
                P.case_plot(items, Path(path), 'all_nonprobe')
        finally:
            P.savefigure = oldsave
        self.assertLess(captured[0][0], 1)
        self.assertGreater(captured[0][1], 500000)


if __name__ == '__main__':
    unittest.main(verbosity=2)
