"""Tests for skills/survey-qsf/scripts/validate_qsf.py and the bundled samples.

    python3 -m unittest discover -s tests
"""
import contextlib
import copy
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "survey-qsf"
sys.path.insert(0, str(SKILL / "scripts"))
import validate_qsf  # noqa: E402

SAMPLES = sorted((SKILL / "samples").glob("*.qsf"))

# Local blocklist (your own organisation's names, etc.) in a git-ignored
# file, one regex per line. Without it the repo-wide anonymity test fails;
# set SURVEY_SKILL_NO_TERMS=1 to skip it on a clone that lacks the list.
TERMS_FILE = Path(__file__).with_name("forbidden_terms.txt")
TERMS = [t.strip() for t in TERMS_FILE.read_text(encoding="utf-8").splitlines()
         if t.strip() and not t.startswith("#")] if TERMS_FILE.exists() else []
FORBIDDEN = re.compile(r"\b(" + "|".join(TERMS) + r")\b", re.IGNORECASE) if TERMS else None


def text_files():
    """Tracked files that read as UTF-8 text; images need checking by eye."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
        paths = [ROOT / p for p in out.decode().split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        paths = [p for p in ROOT.rglob("*")
                 if p.is_file() and not {".git", "__pycache__"} & set(p.parts)]
    for path in paths:
        if path == TERMS_FILE:
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError):
            continue


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def element(doc, name):
    return next(e for e in doc["SurveyElements"] if e["Element"] == name)


def question(doc, qid):
    return next(e for e in doc["SurveyElements"] if e["Element"] == "SQ" and e["PrimaryAttribute"] == qid)


def flow_items(node):
    yield node
    for child in node.get("Flow", []) or []:
        yield from flow_items(child)


class SampleTests(unittest.TestCase):
    def test_three_samples_exist(self):
        self.assertEqual([p.stem for p in SAMPLES],
                         ["event-attendance-sso", "ranked-preferences-sso", "session-availability-sso"])

    def test_samples_pass_fresh_validation(self):
        for path in SAMPLES:
            with self.subTest(path.name):
                rep = validate_qsf.validate(load(path), fresh=True)
                self.assertEqual(rep.errors, [])

    def test_every_sample_has_sso(self):
        for path in SAMPLES:
            with self.subTest(path.name):
                root = element(load(path), "FL")["Payload"]
                auths = [i for i in flow_items(root) if i.get("Type") == "Authenticator"]
                self.assertEqual(len(auths), 1)
                self.assertEqual(auths[0]["SSOOptions"]["SSOID"], "ASC_XXXXXXXXXXXXXXX")
                self.assertEqual(auths[0]["SSOOptions"]["token"]["Key"], "XXXXXXXXXXXXXXXX")

    def test_authenticator_is_never_first(self):
        for path in SAMPLES:
            with self.subTest(path.name):
                first = element(load(path), "FL")["Payload"]["Flow"][0]
                self.assertNotEqual(first["Type"], "Authenticator")

    def test_samples_are_anonymous(self):
        for path in SAMPLES:
            with self.subTest(path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("MS_", text)
                self.assertIsNone(re.search(r"ASC_(?!X{15})", text))
                self.assertNotIn('"PL"', text)

    def test_samples_are_inactive_and_neutral(self):
        for path in SAMPLES:
            with self.subTest(path.name):
                doc = load(path)
                self.assertEqual(doc["SurveyEntry"]["SurveyStatus"], "Inactive")
                self.assertEqual(doc["SurveyEntry"]["SurveyBrandID"], "qualtrics")

    def test_ids_are_unique_across_samples(self):
        ids = [load(p)["SurveyEntry"]["SurveyID"] for p in SAMPLES]
        self.assertEqual(len(ids), len(set(ids)))


class RepoIsAnonymous(unittest.TestCase):
    def test_terms_list_present(self):
        if os.environ.get("SURVEY_SKILL_NO_TERMS") == "1":
            self.skipTest("SURVEY_SKILL_NO_TERMS=1: forbidden-terms check switched off")
        self.assertTrue(TERMS, f"{TERMS_FILE} is missing or empty; add it, or set SURVEY_SKILL_NO_TERMS=1")

    def test_no_forbidden_terms_in_any_file(self):
        if not FORBIDDEN:
            self.skipTest("no forbidden-terms list (see test_terms_list_present)")
        for path, text in text_files():
            with self.subTest(str(path.relative_to(ROOT))):
                m = FORBIDDEN.search(text)
                self.assertIsNone(m, m and f"line {text.count(chr(10), 0, m.start()) + 1}: {m.group(0)!r}")


class AcceptsExportShapes(unittest.TestCase):
    def setUp(self):
        self.doc = load(SKILL / "samples" / "ranked-preferences-sso.qsf")

    def test_keyed_map_bl_with_gap(self):
        bl = element(self.doc, "BL")
        bl["Payload"] = {str(i if i < 3 else i + 1): b for i, b in enumerate(bl["Payload"])}
        self.assertEqual(validate_qsf.validate(self.doc).errors, [])
        self.assertTrue(any("keyed map" in e for e in validate_qsf.validate(self.doc, fresh=True).errors))

    def test_free_form_block_id(self):
        bl = element(self.doc, "BL")["Payload"]
        old = bl[1]["ID"]
        bl[1]["ID"] = "BL_IdentityOptIn"
        raw = json.dumps(self.doc).replace(old, "BL_IdentityOptIn")
        doc = json.loads(raw)
        self.assertEqual(validate_qsf.validate(doc).errors, [])
        self.assertTrue(validate_qsf.validate(doc, fresh=True).errors)

    def test_trashed_question_counts_in_qc(self):
        bl = element(self.doc, "BL")["Payload"]
        moved = bl[-2]["BlockElements"].pop()  # last real block -> trash
        bl[-1]["BlockElements"] = [moved]
        self.assertEqual(validate_qsf.validate(self.doc).errors, [])

    def test_flowid_gap(self):
        root = element(self.doc, "FL")["Payload"]
        root["Flow"][0]["FlowID"] = "FL_99"
        root["Properties"]["Count"] = 99
        self.assertEqual(validate_qsf.validate(self.doc).errors, [])


class CatchesBreakage(unittest.TestCase):
    def setUp(self):
        self.doc = load(SKILL / "samples" / "event-attendance-sso.qsf")

    def assertError(self, fragment, fresh=False):
        errors = validate_qsf.validate(self.doc, fresh=fresh).errors
        self.assertTrue(any(fragment in e for e in errors), errors)

    def test_stale_qc(self):
        element(self.doc, "QC")["SecondaryAttribute"] = "3"
        self.assertError("QC.SecondaryAttribute")

    def test_wrong_flow_count(self):
        element(self.doc, "FL")["Payload"]["Properties"]["Count"] = 2
        self.assertError("Properties.Count")

    def test_duplicate_flowid(self):
        element(self.doc, "FL")["Payload"]["Flow"][1]["FlowID"] = "FL_2"
        self.assertError("duplicate FlowID")

    def test_stale_next_choice_id(self):
        question(self.doc, "QID7")["Payload"]["NextChoiceId"] = 2
        self.assertError("NextChoiceId")

    def test_choice_order_unknown_id(self):
        question(self.doc, "QID7")["Payload"]["ChoiceOrder"].append("9")
        self.assertError("ChoiceOrder")

    def test_dangling_locator(self):
        question(self.doc, "QID3")["Payload"]["DisplayLogic"]["0"]["0"]["LeftOperand"] = \
            "q://QID42/SelectableChoice/1"
        self.assertError("missing QID42")

    def test_locator_to_missing_choice(self):
        flow = element(self.doc, "FL")["Payload"]["Flow"]
        flow[1]["BranchLogic"]["0"]["0"]["ChoiceLocator"] = "q://QID2/SelectableChoice/7"
        self.assertError("has no choice 7")

    def test_dangling_pipe(self):
        question(self.doc, "QID1")["Payload"]["QuestionText"] += "${q://QID77/ChoiceTextEntryValue}"
        self.assertError("missing QID77")

    def test_orphaned_question(self):
        element(self.doc, "BL")["Payload"][1]["BlockElements"].pop()
        self.assertError("orphaned")

    def test_flow_points_at_trash(self):
        trash = element(self.doc, "BL")["Payload"][-1]["ID"]
        element(self.doc, "FL")["Payload"]["Flow"][0]["ID"] = trash
        self.assertError("Trash block")

    def test_qid_mismatch(self):
        question(self.doc, "QID8")["Payload"]["QuestionID"] = "QID80"
        self.assertError("Payload.QuestionID")

    def test_json_boolean_in_string_bool_key(self):
        element(self.doc, "SO")["Payload"]["BackButton"] = False
        self.assertError("SO.BackButton")

    def test_string_in_real_bool_key(self):
        element(self.doc, "SO")["Payload"]["ProtectSelectionIds"] = "true"
        self.assertError("SO.ProtectSelectionIds")

    def test_missing_rs(self):
        self.doc["SurveyElements"] = [e for e in self.doc["SurveyElements"] if e["Element"] != "RS"]
        self.assertError("exactly one RS")

    def test_blank_owner(self):
        self.doc["SurveyEntry"]["SurveyOwnerID"] = ""
        self.assertError("SurveyOwnerID")

    def test_surveyid_mismatch(self):
        element(self.doc, "SO")["SurveyID"] = "SV_000000000000000"
        self.assertError("carries SurveyID")

    def test_dangling_library_message(self):
        so = element(self.doc, "SO")["Payload"]
        so["EOSMessage"], so["EOSMessageLibrary"] = "MS_abcdefghijklmno", None
        self.assertError("EOSMessageLibrary")

    def test_fresh_rejects_tenant_brand(self):
        self.doc["SurveyEntry"]["SurveyBrandID"] = "somecompany"
        self.assertError("SurveyBrandID", fresh=True)

    def test_fresh_rejects_preview_link(self):
        pl = copy.deepcopy(element(self.doc, "PROJ"))
        pl.update({"Element": "PL", "PrimaryAttribute": "Preview Link",
                   "Payload": {"PreviewType": "Brand", "PreviewID": "00000000-0000-0000-0000-000000000000"}})
        self.doc["SurveyElements"].insert(2, pl)
        self.assertError("omit PL", fresh=True)

    def test_empty_authenticator(self):
        auth = element(self.doc, "FL")["Payload"]["Flow"][1]["Flow"][0]
        auth["Flow"] = []
        errors = validate_qsf.validate(self.doc).errors
        self.assertTrue(any("empty Flow" in e for e in errors), errors)


class CarryForward(unittest.TestCase):
    def setUp(self):
        self.doc = load(SKILL / "samples" / "ranked-preferences-sso.qsf")

    def test_ranking_keys_must_be_x_prefixed(self):
        rank = question(self.doc, "QID5")["Payload"]
        rank["RecodeValues"]["1"] = rank["RecodeValues"].pop("x1")
        errors = validate_qsf.validate(self.doc).errors
        self.assertTrue(any("not x + a QID4 choice ID" in e for e in errors), errors)

    def test_source_must_precede(self):
        bl = element(self.doc, "BL")["Payload"]
        flow = element(self.doc, "FL")["Payload"]["Flow"][1]["Flow"][2]["Flow"]
        flow[1], flow[2] = flow[2], flow[1]  # rank block before choose block
        errors = validate_qsf.validate(self.doc).errors
        self.assertTrue(any("shows after it" in e for e in errors), (errors, bl))


class Warnings(unittest.TestCase):
    def test_authenticator_first_warns(self):
        doc = load(SKILL / "samples" / "session-availability-sso.qsf")
        root = element(doc, "FL")["Payload"]
        root["Flow"] = root["Flow"][1:]  # drop the welcome block
        warnings = validate_qsf.validate(doc).warnings
        self.assertTrue(any("very first flow element" in w for w in warnings), warnings)

    def test_real_key_warns(self):
        doc = load(SKILL / "samples" / "session-availability-sso.qsf")
        element(doc, "FL")["Payload"]["Flow"][1]["SSOOptions"]["token"]["Key"] = "a1b2c3d4e5f6g7h8"
        warnings = validate_qsf.validate(doc).warnings
        self.assertTrue(any("treat this file as a secret" in w for w in warnings), warnings)

    def test_unclosed_footer_script_warns(self):
        doc = load(SKILL / "samples" / "session-availability-sso.qsf")
        element(doc, "SO")["Payload"]["Footer"] = "<script>(function(){var x=1;"
        warnings = validate_qsf.validate(doc).warnings
        self.assertTrue(any("unclosed <script>" in w for w in warnings), warnings)

    def test_subtype_flow_spelling_warns(self):
        doc = load(SKILL / "samples" / "ranked-preferences-sso.qsf")
        yes = element(doc, "FL")["Payload"]["Flow"][1]["Flow"][2]["Flow"]
        comment = next(i for i in yes if i["Type"] == "Standard")
        comment["Type"] = "Block"
        warnings = validate_qsf.validate(doc).warnings
        self.assertTrue(any("exports spell it 'Standard'" in w for w in warnings), warnings)


class Cli(unittest.TestCase):
    def test_exit_codes(self):
        good = str(SAMPLES[0])
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            bad = Path(tmp) / "broken.qsf"
            bad.write_text("{not json", encoding="utf-8")
            self.assertEqual(validate_qsf.main([good, "--fresh"]), 0)
            self.assertEqual(validate_qsf.main([]), 2)
            self.assertEqual(validate_qsf.main([str(bad)]), 1)


if __name__ == "__main__":
    unittest.main()
