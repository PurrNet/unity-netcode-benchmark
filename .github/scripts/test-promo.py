#!/usr/bin/env python3
"""Regression checks for chart claims and bundle publication; drawing is mocked."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1]
SPEC = importlib.util.spec_from_file_location("promo", SCRIPTS / "render-promo.py")
promo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(promo)

STATE = "01-state-bandwidth"
CPU = "02-messaging-cpu"
GC = "03-general-gc"
SCALING = "04-connection-scaling"
SLUGS = {STATE, CPU, GC, SCALING}
TESTS = ("MoveY", "MoveWander", "SyncVars", "SendRPC", "ClientInput", "SpawnChurn")
STATE_TESTS = TESTS[:3]
RPC_TESTS = ("SendRPC", "ClientInput")
NETCODES = ("purrnet", "fishnet", "mirror", "ngo", "fusion")
BASE = json.loads((ROOT / "docs/latest.json").read_text(encoding="utf-8"))


def fixture():
    """Retain the real schema, but give the compared sessions stable test inputs."""
    # Published data may be a custom subset on the next CI run. Use it for shape,
    # while explicitly constructing the coverage these behavior tests require.
    data = []
    for netcode in NETCODES:
        template = next((r for r in BASE if r["netcode"] == netcode), BASE[0] if BASE else {})
        for connections in (10, 100):
            run = copy.deepcopy(template)
            run.update(netcode=netcode, size=connections, connections=connections,
                       tick=20, tag=f"c{connections}t20")
            run.setdefault("meta", {})
            run.setdefault("server", {})
            run.setdefault("clients", {})
            for name in (*TESTS, "Idle", "Static"):
                run["server"].setdefault(name, {})
            for name in TESTS:
                run["clients"][name] = dict(n=10, truncated=0,
                    rpcDeliveryChecked=10 if name == "SendRPC" else 0,
                    rpcDeliveryMatched=10 if name == "SendRPC" else 0,
                    syncStateChecked=10 if name == "SyncVars" else 0,
                    syncStateMatched=10 if name == "SyncVars" else 0)
            data.append(run)
    cpu = dict(zip(NETCODES, (5, 8, 12, 40, 15)))
    alloc = dict(zip(NETCODES, (100, 400, 900, 50, 450)))
    wire = dict(zip(NETCODES, (10, 20, 30, 40, 25)))
    for run in data:
        n, connections = run["netcode"], run["size"]
        run["connections"] = connections
        run["meta"].update(cpuModel="AMD Ryzen 5 3600 6-Core Processor", cpuCount=6,
                           unityVersion="6000.5.4f1", devBuild=False, targetFps=60,
                           tickRate=20, requestedTickRate=20, connectedAtStart=connections,
                           expectedClients=connections, measuredClients=10, serverError=None)
        run["meta"]["process"] = {"status": "exited", "exitCode": 0}
        for name in TESTS:
            run["server"][name].update(
                name=name, objects=1 if name == "ClientInput" else 100, connections=connections,
                windowSeconds=10.0, truncated=False, deliveryComplete=True,
                p99FrameMs=16.7, avgFps=60.0, cpuPercent=cpu[n],
                txBytesPerSec=wire[n] * connections * 1024,
                gcAllocBytesPerSec=alloc[n] * 1024, gcAllocEstimated=True)
    return data


def reference(data, netcode="purrnet", connections=100):
    return next(r for r in data if r["netcode"] == netcode and r["size"] == connections)


def set_metric(data, netcode, metric, value, tests=TESTS):
    for name in tests:
        reference(data, netcode)["server"][name][metric] = value


class PromoChecks(unittest.TestCase):
    def setUp(self):
        self.data = fixture()

    def card(self, slug, data=None):
        cards = promo.build_cards(self.data if data is None else data, selected=slug)
        self.assertEqual([c["slug"] for c in cards], [slug])
        return cards[0]

    def assert_skips_only(self, data, expected):
        skipped = {}
        cards = promo.build_cards(data, ci=True, skipped=skipped)
        self.assertEqual(set(skipped), set(expected))
        self.assertEqual({c["slug"] for c in cards}, SLUGS - set(expected))
        for reason in skipped.values():
            self.assertTrue(reason)

    def test_each_selection_uses_only_its_own_metrics_tests_and_sessions(self):
        cases = ((STATE, STATE_TESTS, "txBytesPerSec", (100,)),
                 (CPU, RPC_TESTS, "cpuPercent", (100,)),
                 (GC, TESTS, "gcAllocBytesPerSec", (100,)),
                 (SCALING, TESTS, "txBytesPerSec", (10, 100)))
        for slug, tests, metric, sessions in cases:
            with self.subTest(chart=slug):
                data = [r for r in fixture() if r["size"] in sessions]
                for run in data:
                    run["server"] = {t: run["server"][t] for t in tests}
                    for sample in run["server"].values():
                        for unused in ("txBytesPerSec", "cpuPercent", "gcAllocBytesPerSec"):
                            if unused != metric:
                                sample.pop(unused, None)
                        if slug != GC:
                            sample.pop("gcAllocEstimated", None)
                self.assertEqual(len(self.card(slug, data)["rows"]), 5)

    def test_gc_weights_each_of_six_tests_equally(self):
        run = reference(self.data)
        for name, kib in zip(TESTS, (6, 12, 18, 24, 30, 36)):
            run["server"][name]["gcAllocBytesPerSec"] = kib * 1024
        run["server"]["Idle"]["gcAllocBytesPerSec"] = 10**12
        run["server"]["Static"]["gcAllocBytesPerSec"] = 10**12
        card = self.card(GC)
        purrnet = next(r for r in card["rows"] if r["netcode"] == "purrnet")
        self.assertEqual(purrnet["value"], 21)
        self.assertAlmostEqual(card["reduction_percent"], 94.75)
        self.assertEqual(card["reduction_percent_rounded"], 95)

    def test_missing_scaling_session_skips_scaling_only(self):
        data = [r for r in self.data if r["size"] == 100]
        self.assert_skips_only(data, {SCALING})
        with self.assertRaises(promo.ChartUnavailable):
            promo.build_cards(data, selected=SCALING)

    def test_incomplete_rpc_delivery_leaves_state_chart_available(self):
        reference(self.data)["server"]["SendRPC"]["deliveryComplete"] = False
        self.assert_skips_only(self.data, {CPU, GC, SCALING})

    def test_regression_uses_higher_wording_without_negative_less_claim(self):
        set_metric(self.data, "purrnet", "gcAllocBytesPerSec", 800 * 1024)
        card = self.card(GC)
        self.assertIn("higher", card["takeaway"].lower())
        self.assertNotRegex(card["takeaway"], r"-\s*\d+(?:\.\d+)?\s*%.*(?:less|lower)")

    def test_cpu_secondary_can_regress_independently_of_primary(self):
        set_metric(self.data, "fishnet", "cpuPercent", 2, RPC_TESTS)
        takeaway = self.card(CPU)["takeaway"]
        self.assertNotRegex(takeaway, r"-\s*\d+(?:\.\d+)?\s*%")
        if "FishNet" in takeaway:
            self.assertIn("higher", takeaway.lower())

    def test_exact_tie_does_not_claim_a_reduction(self):
        set_metric(self.data, "purrnet", "gcAllocBytesPerSec", 400 * 1024)
        card = self.card(GC)
        self.assertNotRegex(card["takeaway"].lower(), r"\b(?:less|lower|higher)\b")
        self.assertIn(card["reduction_percent"], (None, 0))

    def test_zero_baseline_has_no_percentage_ratio(self):
        set_metric(self.data, "fishnet", "gcAllocBytesPerSec", 0)
        card = self.card(GC)
        self.assertIsNone(card["reduction_percent"])
        self.assertIsNone(card["reduction_percent_rounded"])
        self.assertNotIn("%", card["takeaway"])
        self.assertTrue(math.isfinite(card["axis_max"]))

    def test_overload_retains_bars_and_suppresses_named_comparison(self):
        for netcode in ("purrnet", "fishnet"):
            with self.subTest(netcode=netcode):
                data = fixture()
                reference(data, netcode)["server"]["MoveY"]["p99FrameMs"] = 50
                card = self.card(GC, data)
                row = next(r for r in card["rows"] if r["netcode"] == netcode)
                self.assertEqual(row["overloaded"], 1)
                self.assertEqual(len(card["rows"]), 5)
                self.assertIsNone(card["reduction_percent"])
                self.assertNotIn("%", card["takeaway"])
                self.assertIn({"purrnet": "PurrNet", "fishnet": "FishNet"}[netcode], card["chart_note"])

    def test_unrelated_overloaded_competitor_is_named_in_note(self):
        reference(self.data, "mirror")["server"]["MoveY"]["p99FrameMs"] = 50
        card = self.card(GC)
        self.assertIn("Mirror", card["chart_note"])
        self.assertIsNotNone(card["reduction_percent"])

    def test_profiler_counter_switches_allocation_label(self):
        for run in self.data:
            run["meta"]["devBuild"] = True
            for name in TESTS:
                run["server"][name]["gcAllocEstimated"] = False
        card = self.card(GC)
        self.assertIs(card["allocation_estimated"], False)
        self.assertNotIn("estimated", card["chart_subtitle"].lower())
        self.assertNotIn("estimated", card["takeaway"].lower())
        self.assertRegex(card["footer"].lower(), r"development|profil")

    def test_mixed_allocation_sources_skip_gc_only(self):
        reference(self.data)["server"]["MoveY"]["gcAllocEstimated"] = False
        self.assert_skips_only(self.data, {GC})
        with self.assertRaises(promo.ChartUnavailable):
            self.card(GC)

    def test_invalid_allocation_values_cannot_enter_otherwise_valid_chart(self):
        for invalid in (float("nan"), float("inf"), -float("inf"), None, -1, "100", True):
            with self.subTest(value=repr(invalid)):
                data = fixture()
                reference(data)["server"]["MoveY"]["gcAllocBytesPerSec"] = invalid
                self.assert_skips_only(data, {GC})
                with self.assertRaises(promo.ChartUnavailable):
                    self.card(GC, data)

    def test_larger_valid_values_expand_the_axis(self):
        set_metric(self.data, "mirror", "gcAllocBytesPerSec", 20000 * 1024)
        card = self.card(GC)
        self.assertTrue(math.isfinite(card["axis_max"]))
        self.assertGreaterEqual(card["axis_max"], 20000)
        self.assertTrue(all(0 <= r["value"] <= card["axis_max"] for r in card["rows"]))

    def test_changed_window_object_count_and_hardware_are_not_hardcoded(self):
        for run in self.data:
            run["meta"].update(cpuModel="Test Processor 9000", unityVersion="6000.9.1f1")
            for name in TESTS:
                run["server"][name]["windowSeconds"] = 5.0
                if name != "ClientInput":
                    run["server"][name]["objects"] = 200
        card = self.card(STATE)
        self.assertIn("Test Processor 9000", card["footer"])
        self.assertIn("6000.9.1f1", card["footer"])
        self.assertIn("200", card["figure_method"])
        self.assertRegex(card["figure_method"], r"\b5(?:\.0)?\s*s\b")
        self.assertNotIn("Ryzen", card["footer"])
        self.assertNotIn("10 s", card["figure_method"])

    def test_mixed_cpu_models_disable_cpu_comparison_only(self):
        reference(self.data, "fishnet")["meta"]["cpuModel"] = "Different Processor"
        self.assert_skips_only(self.data, {CPU})

    def test_missing_cpu_model_does_not_invent_a_comparable_server(self):
        reference(self.data, "fishnet")["meta"].pop("cpuModel")
        with self.assertRaises(promo.ChartUnavailable):
            self.card(CPU)

    def test_missing_or_mixed_build_modes_do_not_make_comparative_cards(self):
        for mode in (None, True):
            with self.subTest(mode=mode):
                data = fixture()
                reference(data, "fishnet")["meta"]["devBuild"] = mode
                self.assert_skips_only(data, SLUGS)

    def test_build_mode_requires_a_boolean_not_a_truthy_value(self):
        for mode in (0, 1, "false"):
            with self.subTest(mode=mode):
                data = fixture()
                for run in data:
                    run["meta"]["devBuild"] = mode
                self.assert_skips_only(data, SLUGS)
                with self.assertRaises(promo.ChartUnavailable):
                    self.card(GC, data)

    def test_actual_connection_and_tick_mismatches_are_not_nominal_comparisons(self):
        for field, value in (("connectedAtStart", 99), ("tickRate", 19)):
            with self.subTest(field=field):
                data = fixture()
                reference(data, "fusion")["meta"][field] = value
                with self.assertRaises(promo.ChartUnavailable):
                    self.card(GC, data)

    def test_missing_optional_frame_cap_is_supported(self):
        for run in self.data:
            run["meta"].pop("targetFps", None)
        self.assertEqual(len(self.card(GC)["rows"]), 5)

    def test_nonstandard_or_mixed_explicit_frame_caps_are_unavailable(self):
        for mixed in (False, True):
            with self.subTest(mixed=mixed):
                data = fixture()
                if mixed:
                    reference(data, "fishnet")["meta"]["targetFps"] = 120
                else:
                    for run in data:
                        run["meta"]["targetFps"] = 30
                self.assert_skips_only(data, SLUGS)
                with self.assertRaises(promo.ChartUnavailable):
                    self.card(GC, data)


class BundleChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="promo-bundle-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "latest"
        self.output.mkdir()
        self.data = fixture()
        # Nondefault indentation and CRLF make a reserialized source distinguishable.
        self.raw = json.dumps(self.data, indent=3, ensure_ascii=False).encode("utf-8") + b"\r\n"
        self.markdown = (
            "_Last run 2026-09-09: PurrNet test · FishNet test · Mirror test · NGO test · "
            "Fusion test · Unity 6000.5.4f1 · 100 objects per test · 10 s windows._\n\n"
            "[workflow run](https://github.com/PurrNet/unity-netcode-benchmark/actions/runs/123)\n"
        )
        self.metadata = promo.parse_metadata(self.raw, self.markdown, "fixture-code-revision")

    @staticmethod
    def draw_stub(card, metadata, staging):
        for suffix in (".png", ".svg"):
            (staging / (card["slug"] + suffix)).write_bytes(("new " + card["slug"] + suffix).encode())

    @staticmethod
    def snapshot(directory):
        return {p.relative_to(directory).as_posix(): p.read_bytes()
                for p in directory.rglob("*") if p.is_file()}

    def seed_previous_output(self):
        for slug in SLUGS:
            for suffix in (".png", ".svg"):
                (self.output / (slug + suffix)).write_bytes(b"previous chart")
        for name in ("README.md", "chart-data.json", "source-data.json", "source-summary.md"):
            (self.output / name).write_bytes(b"previous bundle metadata")
        (self.output / "custom.png").write_bytes(b"user image")
        (self.output / "notes.txt").write_bytes(b"user notes")
        (self.output / "assets").mkdir(exist_ok=True)
        (self.output / "assets" / "logo.svg").write_bytes(b"user logo")
        (self.root / "archive").mkdir(exist_ok=True)
        (self.root / "archive" / "previous.png").write_bytes(b"historical chart")

    def test_skipped_and_unselected_charts_remove_only_stale_managed_exports(self):
        for mode in ("skipped", "selected"):
            with self.subTest(mode=mode):
                self.seed_previous_output()
                data = fixture()
                skipped = {}
                if mode == "skipped":
                    reference(data)["server"]["MoveY"]["gcAllocEstimated"] = False
                    cards = promo.build_cards(data, ci=True, skipped=skipped)
                    expected = SLUGS - {GC}
                    self.assertEqual(set(skipped), {GC})
                else:
                    cards = promo.build_cards(data, selected=GC)
                    expected = {GC}
                raw = json.dumps(data, indent=3, ensure_ascii=False).encode("utf-8") + b"\r\n"
                metadata = promo.parse_metadata(raw, self.markdown, "fixture-code-revision")
                with mock.patch.object(promo, "draw_card", side_effect=self.draw_stub):
                    promo.write_bundle(cards, metadata, skipped, raw, self.markdown, self.output)
                for slug in SLUGS:
                    for suffix in (".png", ".svg"):
                        path = self.output / (slug + suffix)
                        self.assertEqual(path.is_file(), slug in expected)
                        if slug in expected:
                            self.assertTrue(path.read_bytes().startswith(b"new "))
                manifest = json.loads((self.output / "chart-data.json").read_text(encoding="utf-8"))
                self.assertEqual({c["slug"] for c in manifest["charts"]}, expected)
                self.assertEqual(manifest["skipped"], skipped)
                self.assertEqual((self.output / "custom.png").read_bytes(), b"user image")
                self.assertEqual((self.output / "notes.txt").read_bytes(), b"user notes")
                self.assertEqual((self.output / "assets" / "logo.svg").read_bytes(), b"user logo")
                self.assertEqual((self.root / "archive" / "previous.png").read_bytes(), b"historical chart")

    def test_staging_render_failure_preserves_the_entire_previous_bundle(self):
        self.seed_previous_output()
        before = self.snapshot(self.root)
        cards = promo.build_cards(self.data)
        calls = []

        def fail_after_rendering(card, metadata, staging):
            calls.append(card["slug"])
            self.draw_stub(card, metadata, staging)
            if len(calls) == 2:
                raise RuntimeError("simulated renderer failure")

        with mock.patch.object(promo, "draw_card", side_effect=fail_after_rendering):
            with self.assertRaisesRegex(RuntimeError, "simulated renderer failure"):
                promo.write_bundle(cards, self.metadata, {}, self.raw, self.markdown, self.output)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.snapshot(self.root), before)
        self.assertFalse(list(self.root.glob(".promo-*")))

    def test_bundle_keeps_exact_raw_snapshot_and_matching_checksum(self):
        cards = promo.build_cards(self.data, selected=GC)
        with mock.patch.object(promo, "draw_card", side_effect=self.draw_stub):
            promo.write_bundle(cards, self.metadata, {}, self.raw, self.markdown, self.output)
        source = (self.output / "source-data.json").read_bytes()
        self.assertEqual(source, self.raw)
        manifest = json.loads((self.output / "chart-data.json").read_text(encoding="utf-8"))
        metadata = manifest["metadata"]
        self.assertEqual(metadata["source_sha256"], hashlib.sha256(source).hexdigest())
        self.assertEqual(metadata["source_data"], "source-data.json")
        self.assertEqual(metadata["source_summary"], "source-summary.md")
        self.assertEqual((self.output / "source-summary.md").read_text(encoding="utf-8"), self.markdown)
        readme = (self.output / "README.md").read_text(encoding="utf-8")
        self.assertIn(metadata["source_sha256"], readme)
        self.assertIn("(source-data.json)", readme)


if __name__ == "__main__":
    unittest.main()
