#!/usr/bin/env python3
"""Structural validator for Qualtrics .qsf files.

Default mode accepts genuine tenant exports (keyed-map BL, free-form block
IDs, FlowID gaps, trashed questions). --fresh adds the rules for files you
generate yourself (array BL, 15-char IDs, neutral brand, no PL, no
message-library refs).

    python3 validate_qsf.py survey.qsf [more.qsf ...] [--fresh]

Prints ERROR / WARN lines; exit 1 if any ERROR.
Stdlib only.
"""
import json
import re
import sys

ID15 = r"[A-Za-z0-9]{15}"
STRING_BOOL_SO_KEYS = ("BackButton", "SaveAndContinue", "BallotBoxStuffingPrevention", "SecureResponseFiles",
                       "RecaptchaV3")
REAL_BOOL_SO_KEYS = ("ProtectSelectionIds", "ConfirmStart", "AutoConfirmStart", "AutoCloseSurvey")
MESSAGE_PAIRS = (("EOSMessage", "EOSMessageLibrary"), ("InactiveMessage", "InactiveMessageLibrary"),
                 ("ThankYouEmailMessage", "ThankYouEmailMessageLibrary"),
                 ("ValidationMessage", "ValidationMessageLibrary"))
PLACEHOLDER = re.compile(r"^(ASC_)?X+$")


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def walk_strings(node, path=""):
    """Yield (path, string) for every string value in a JSON tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def walk_flow(item, depth=0, inside_auth=False):
    """Yield (flow_item, depth, inside_authenticator) depth-first, in display order."""
    yield item, depth, inside_auth
    child_auth = inside_auth or item.get("Type") == "Authenticator"
    for child in item.get("Flow", []) or []:
        yield from walk_flow(child, depth + 1, child_auth)


def blocks_of(bl_payload, rep, fresh):
    if isinstance(bl_payload, list):
        return list(bl_payload)
    if isinstance(bl_payload, dict):
        if fresh:
            rep.error("BL.Payload is a keyed map; generate the array form for fresh files")
        return [bl_payload[k] for k in sorted(bl_payload, key=lambda k: int(k) if k.isdigit() else 0)]
    rep.error("BL.Payload is neither an array nor a keyed map")
    return []


def choice_keys(payload):
    choices = payload.get("Choices")
    if isinstance(choices, dict):
        return set(choices)
    return set()


def max_int(keys):
    nums = [int(k) for k in keys if str(k).isdigit()]
    return max(nums) if nums else 0


def validate(doc, fresh=False):
    rep = Report()
    if not isinstance(doc, dict) or "SurveyEntry" not in doc or "SurveyElements" not in doc:
        rep.error("top level must hold SurveyEntry and SurveyElements")
        return rep
    entry, elements = doc["SurveyEntry"], doc["SurveyElements"]

    # --- SurveyEntry -----------------------------------------------------
    sv = entry.get("SurveyID", "")
    if not re.fullmatch(f"SV_{ID15}", sv or ""):
        rep.error(f"SurveyEntry.SurveyID {sv!r} is not SV_ + 15 alphanumerics")
    for key in ("SurveyOwnerID", "CreatorID"):
        if not re.fullmatch(f"UR_{ID15}", entry.get(key) or ""):
            rep.error(f"SurveyEntry.{key} must be UR_ + 15 alphanumerics, never blank")
    if fresh and entry.get("SurveyBrandID") != "qualtrics":
        rep.error("fresh file: SurveyBrandID should be the neutral 'qualtrics'")

    by_type = {}
    for el in elements:
        by_type.setdefault(el.get("Element"), []).append(el)
        if el.get("SurveyID") != sv:
            rep.error(f"element {el.get('Element')} {el.get('PrimaryAttribute')} carries SurveyID "
                      f"{el.get('SurveyID')!r}, expected {sv!r}")
    for need in ("BL", "FL", "QC", "RS", "SO", "STAT"):
        if len(by_type.get(need, [])) != 1:
            rep.error(f"need exactly one {need} element, found {len(by_type.get(need, []))}")
    for soft in ("PROJ", "SCO"):
        if soft not in by_type:
            rep.warn(f"no {soft} element (real exports always carry one)")
    if fresh and "PL" in by_type:
        rep.error("fresh file: omit PL; Qualtrics mints the preview link on import")
    if rep.errors:
        return rep

    rs = by_type["RS"][0]
    if entry.get("SurveyActiveResponseSet") != rs.get("PrimaryAttribute"):
        rep.error("SurveyActiveResponseSet does not match the RS element's PrimaryAttribute")

    # --- SQ ----------------------------------------------------------------
    questions = {}
    tags = {}
    for el in by_type.get("SQ", []):
        p = el.get("Payload") or {}
        qid = el.get("PrimaryAttribute")
        if qid in questions:
            rep.error(f"duplicate SQ {qid}")
        if p.get("QuestionID") != qid:
            rep.error(f"SQ {qid}: Payload.QuestionID is {p.get('QuestionID')!r}")
        questions[qid] = p
        tag = p.get("DataExportTag")
        if tag in tags:
            rep.warn(f"DataExportTag {tag!r} used by {tags[tag]} and {qid}")
        tags[tag] = qid

    qc = by_type["QC"][0].get("SecondaryAttribute")
    if qc != str(len(questions)):
        rep.error(f"QC.SecondaryAttribute is {qc!r}; SQ count (trashed included) is {len(questions)}")

    # --- BL ----------------------------------------------------------------
    blocks = blocks_of(by_type["BL"][0].get("Payload"), rep, fresh)
    block_ids, trash_ids = {}, set()
    placed = {}
    defaults = 0
    for b in blocks:
        bid = b.get("ID", "")
        pattern = f"BL_{ID15}" if fresh else r"BL_[A-Za-z0-9]+"
        if not re.fullmatch(pattern, bid):
            rep.error(f"block ID {bid!r} does not match {pattern}")
        if bid in block_ids:
            rep.error(f"duplicate block ID {bid}")
        block_ids[bid] = b
        if b.get("Type") == "Trash":
            trash_ids.add(bid)
        if b.get("Type") == "Default":
            defaults += 1
        for be in b.get("BlockElements", []) or []:
            if be.get("Type") != "Question":
                continue
            q = be.get("QuestionID")
            if q not in questions:
                rep.error(f"block {bid} references missing question {q}")
            if q in placed:
                rep.error(f"{q} sits in two blocks ({placed[q]} and {bid})")
            placed[q] = bid
    if defaults != 1:
        rep.warn(f"expected one Default block, found {defaults}")
    if len(trash_ids) > 1:
        rep.error("more than one Trash block")
    for q in questions:
        if q not in placed:
            rep.error(f"{q} is orphaned: in no block (not even Trash)")

    # --- FL ----------------------------------------------------------------
    root = by_type["FL"][0].get("Payload") or {}
    if root.get("Type") != "Root" or root.get("FlowID") != "FL_1":
        rep.error("FL root must be Type Root with FlowID FL_1")
    seen_fids = {}
    flow_blocks = []
    auth_items = []
    for item, depth, inside_auth in walk_flow(root):
        fid = item.get("FlowID", "")
        if not re.fullmatch(r"FL_\d+", fid):
            rep.error(f"bad FlowID {fid!r}")
            continue
        if fid in seen_fids:
            rep.error(f"duplicate FlowID {fid}")
        seen_fids[fid] = item
        t = item.get("Type")
        if t in ("Block", "Standard"):
            bid = item.get("ID")
            flow_blocks.append(bid)
            if bid not in block_ids:
                rep.error(f"flow {fid} points at missing block {bid}")
            elif bid in trash_ids:
                rep.error(f"flow {fid} points at the Trash block")
            else:
                want = "Standard" if "SubType" in block_ids[bid] else "Block"
                if t != want:
                    rep.warn(f"flow {fid} is Type {t!r}; block {bid} "
                             f"{'has' if want == 'Standard' else 'lacks'} SubType, exports spell it {want!r}")
        if t == "Authenticator":
            auth_items.append((item, depth))
    if root.get("Type") == "Root":
        count = (root.get("Properties") or {}).get("Count")
        top = max(int(f[3:]) for f in seen_fids) if seen_fids else 0
        if count != top:
            rep.error(f"FL Properties.Count is {count!r}; max FlowID is {top}")
    for bid in block_ids:
        if bid not in trash_ids and bid not in flow_blocks:
            rep.warn(f"block {bid} ({block_ids[bid].get('Description')!r}) is not in the flow; "
                     "its questions never show")

    # question display order, for carry-forward checks
    order = []
    for bid in flow_blocks:
        for be in (block_ids.get(bid) or {}).get("BlockElements", []) or []:
            if be.get("QuestionID") not in order:
                order.append(be.get("QuestionID"))

    # --- per-question payload checks ---------------------------------------
    for qid, p in questions.items():
        keys = choice_keys(p)
        dyn = p.get("DynamicChoices")
        co = p.get("ChoiceOrder")
        if isinstance(co, list):
            stray = [str(c) for c in co if str(c) not in keys]
            if stray and not dyn:
                rep.error(f"{qid}: ChoiceOrder lists unknown choice IDs {stray}")
        nci = p.get("NextChoiceId")
        if keys and isinstance(nci, int) and nci <= max_int(keys):
            rep.error(f"{qid}: NextChoiceId {nci} must exceed max choice ID {max_int(keys)}")
        answers = p.get("Answers")
        if isinstance(answers, dict):
            nai = p.get("NextAnswerId")
            if isinstance(nai, int) and nai <= max_int(answers):
                rep.error(f"{qid}: NextAnswerId {nai} must exceed max answer ID {max_int(answers)}")
            ao = p.get("AnswerOrder") or []
            stray = [str(a) for a in ao if str(a) not in answers]
            if stray:
                rep.error(f"{qid}: AnswerOrder lists unknown answer IDs {stray}")
        if dyn:
            m = re.match(r"q://(QID\d+)/", dyn.get("Locator", ""))
            src = m.group(1) if m else None
            if src not in questions:
                rep.error(f"{qid}: DynamicChoices source {src!r} does not exist")
            else:
                if src in order and qid in order and order.index(src) > order.index(qid):
                    rep.error(f"{qid}: carry-forward source {src} shows after it")
                src_keys = {f"x{k}" for k in choice_keys(questions[src])}
                for field in ("RecodeValues", "VariableNaming"):
                    extra = set(p.get(field) or {}) - src_keys
                    if extra:
                        rep.error(f"{qid}: {field} keys {sorted(extra)} are not x + a {src} choice ID")
        else:
            labels = keys if p.get("QuestionType") != "Matrix" else set(answers or {})
            for field in ("RecodeValues", "VariableNaming"):
                extra = set(p.get(field) or {}) - labels
                if extra and labels:
                    rep.error(f"{qid}: {field} keys {sorted(extra)} match no choice/answer")
        fr = ((p.get("Validation") or {}).get("Settings") or {}).get("ForceResponse")
        if fr is not None and fr not in ("ON", "OFF"):
            rep.error(f"{qid}: ForceResponse must be the string 'ON' or 'OFF'")
        if fresh and "QuestionJS" in p and not p["QuestionJS"].lstrip().startswith("Qualtrics.SurveyEngine"):
            rep.warn(f"{qid}: QuestionJS does not start with a Qualtrics.SurveyEngine hook")

    # --- references anywhere in the file -----------------------------------
    for path, s in walk_strings(doc):
        for qid, rest in re.findall(r"q:(?:\\?/){2}(QID\d+)((?:\\?/)[A-Za-z]+(?:\\?/)?\d*)?", s):
            if qid not in questions:
                rep.error(f"{path}: reference to missing {qid}")
                continue
            m = re.search(r"SelectableChoice(?:\\?/)(\d+)", rest or "")
            if m and questions[qid].get("Choices") and m.group(1) not in choice_keys(questions[qid]):
                rep.error(f"{path}: {qid} has no choice {m.group(1)}")
        if fresh and re.search(r"\bMS_[A-Za-z0-9]{15}\b", s):
            rep.error(f"{path}: message-library ID in a fresh file; it will dangle in another account")

    # --- SO ----------------------------------------------------------------
    so = by_type["SO"][0].get("Payload") or {}
    for key in STRING_BOOL_SO_KEYS:
        if key in so and not isinstance(so[key], str):
            rep.error(f"SO.{key} must be a string ('true'/'false'), got {type(so[key]).__name__}")
    for key in REAL_BOOL_SO_KEYS:
        if key in so and not isinstance(so[key], bool):
            rep.error(f"SO.{key} must be a JSON boolean, got {type(so[key]).__name__}")
    for msg, lib in MESSAGE_PAIRS:
        if so.get(msg) and str(so[msg]).startswith("MS_") and not so.get(lib):
            rep.error(f"SO.{msg} names a library message but SO.{lib} is empty")
    footer = so.get("Footer") or ""
    if footer.count("<script") > footer.count("</script>"):
        rep.warn(f"SO.Footer has an unclosed <script> ({len(footer)} chars); exports have been seen "
                 "cut mid-script, so check it on the live survey")
    if fresh:
        skin = so.get("Skin") or {}
        if so.get("SkinLibrary") != "qualtrics" or skin.get("brandingId") is not None:
            rep.error("fresh file: use SkinLibrary 'qualtrics' and Skin.brandingId null")

    # --- SSO authenticators ------------------------------------------------
    first = (root.get("Flow") or [{}])[0] if root.get("Flow") else {}
    for item, depth in auth_items:
        sso = item.get("SSOOptions") or {}
        fid = item.get("FlowID")
        if PLACEHOLDER.match(sso.get("SSOID") or ""):
            rep.warn(f"{fid}: SSOID is a placeholder; after import, Survey flow -> authenticator: switch SSO Type "
                     "to another value, save, switch back, select your connection, save, publish")
        key = (sso.get("token") or {}).get("Key")
        if key and not PLACEHOLDER.match(key):
            rep.warn(f"{fid}: SSO token key present; treat this file as a secret")
        if item is first:
            rep.warn(f"{fid}: authenticator is the very first flow element; respondents bounce to the IdP "
                     "before any page renders (fragile in in-app browsers). Put a welcome block first")
        if not item.get("Flow"):
            rep.error(f"{fid}: authenticator has an empty Flow; nothing is protected")
    return rep


def main(argv):
    fresh = "--fresh" in argv
    files = [a for a in argv if a != "--fresh"]
    if not files:
        print(__doc__.strip())
        return 2
    failed = False
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"{path}: ERROR cannot load JSON: {exc}")
            failed = True
            continue
        rep = validate(doc, fresh=fresh)
        for e in rep.errors:
            print(f"{path}: ERROR {e}")
        for w in rep.warnings:
            print(f"{path}: WARN {w}")
        print(f"{path}: {'FAIL' if rep.errors else 'OK'} ({len(rep.errors)} errors, {len(rep.warnings)} warnings)")
        failed = failed or bool(rep.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
