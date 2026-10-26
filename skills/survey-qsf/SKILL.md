---
name: survey-qsf
description: >-
  Quirks of Qualtrics .qsf survey files. Use when editing a real Qualtrics
  export, generating a .qsf to import, adding an SSO authenticator, branches,
  embedded data, carry-forward ranking, custom validation, JS or CSS, or when
  an import fails or SSO login breaks for some respondents.
---

# Qualtrics QSF: the quirks layer

You already know QSF basics (SurveyEntry, SurveyElements, BL/FL/SQ/SO, QIDs,
choices). This skill is the layer above: what real tenant exports actually
contain, what breaks silently, and how SSO behaves. Every quirk below was
observed in working exports, not inferred from docs, unless marked
*unverified*.

## 1. Pick the mode first

| Mode | When | Rule |
|---|---|---|
| **Fresh** | No export involved; you write the file | Portable defaults (§3), `validate_qsf.py --fresh` |
| **Edit in place** | User hands you a real export and wants a change | Keep every tenant field as found; recompute list (§4) |
| **Rebuild** | Export is broken beyond patching | Extract content, rebuild fresh, re-add tenant features from `references/feature-shapes.md` |

Mixing modes is the fatal habit: patching an export with fresh defaults
(blanket `SurveyBrandID: "qualtrics"`, stripping `PL`, renumbering QIDs)
destroys tenant configuration the user wanted kept. State the mode to the
user before the first write, and back the file up.

## 2. Export reality

Facts a genuine export holds that a hand-written file would not:

- **`BL.Payload` may be a keyed map**, `{"0": {...}, "1": {...}, "4": {...}}`,
  with gaps where blocks were deleted. The array form imports too. Edit in
  place: keep the form you found.
- **Block IDs are free-form**: readable IDs shaped like `BL_Intro01`
  occur in real exports. Read
  with `BL_[A-Za-z0-9]+`; mint `BL_` + 15 alphanumerics. `SV_`/`UR_`/`RS_`
  were always 15.
- **Trash** can hold questions (each keeps its full `SQ`), need not be the
  last block, and never appears in the flow. `QC.SecondaryAttribute` counts
  **all** SQ elements, trashed included.
- **Flow item `Type` follows `SubType`, not the block's `Type`**: a BL block
  with a `SubType` key (even `""`) appears in flow as `"Type": "Standard"`;
  without it, `"Type": "Block"`.
- **FlowIDs are creation-ordered**: a branch can contain lower FlowIDs than
  itself, deleted items leave holes, and `Properties.Count` = max numeric
  FlowID, holes included. Inserting: mint `FL_<Count+1>`, bump `Count`, never
  renumber.
- **One block can sit in several branches** (one shared form reached by an
  SSO route and a manual route). Only the branch that fires shows it.
- **`/` is serialized as `\/`** inside strings (`q:\/\/QID2\/SelectableChoice\/1`).
  Same value after `json.load`; plain `/` imports fine. Never treat the two
  spellings as different values.
- **Type discipline per key**: SO `BackButton`, `SaveAndContinue`,
  `BallotBoxStuffingPrevention`, `SecureResponseFiles`, `RecaptchaV3` are
  strings `"true"`/`"false"`; `ProtectSelectionIds`, `ConfirmStart`,
  `AutoConfirmStart`, `AutoCloseSurvey` are JSON booleans; `ForceResponse` is
  `"ON"`/`"OFF"`; `RightOperand`, `MinChoices`, recode values are strings.
  Copy the observed type, never normalize.
- **Placeholder text** (`"Click to write Choice 1"`) marks an untouched
  editor question: template debris, usually trashed.
- **`SecondaryAttribute` of an SQ** is a ~100-char plain-text echo of the
  question, ending in `...`. Cosmetic; keep it roughly in sync.
- **"Copy survey" provenance**: a copy keeps owner `UR_`, every `BL_` and
  `QID`; mints new `SV_`, `RS_`, `PreviewID`; appends " - Copy"; resets
  `SurveyStatus` to `Inactive`. Same lineage, not a new design.
- **IDs hard-coded inside JS do not follow a copy**: an exported copy still
  used a `sessionStorage` key naming the *original* survey's `SV_` ID. Grep
  `QuestionJS` and `SO.Footer` for `SV_` after copying.
- **`SO.Footer` arrived cut mid-script** (a few thousand chars, unclosed
  `<script>`, IIFE never closed) in one export. Cause unknown; the
  validator warns on it. Move long JS into `QuestionJS` instead.
- **Message-library references travel as IDs only**: `EOSMessage`,
  `ValidationMessage`, and custom validation `Message.messageID` name a
  message in the owner's library (`MS_…` + `UR_…` library). In another
  account they dangle. Fresh files: `SurveyTermination: "DefaultMessage"`,
  no `MS_` IDs, re-pick custom messages in the editor after import. Keep
  each message ID with its library ID as a pair.
- **`PL` (preview link)** sits after `FL` in exports. Edit in place: leave
  it. Fresh: omit it; Qualtrics mints one.

## 3. Fresh-file defaults

`SurveyBrandID: "qualtrics"`, `SkinLibrary: "qualtrics"`,
`Skin.brandingId: null`, `SurveyStatus: "Inactive"`, synthetic `UR_` used for
both owner and creator (the importer replaces it), no `PL`, no `MS_` IDs,
array-form `BL` with an empty Trash block last. Never invent a tenant brand,
skin ID, SSO connection ID or library ID.

## 4. Recompute list

After any edit, recompute each of these. Every one has broken an import or a
survey when left stale:

1. `QC.SecondaryAttribute`: string of the SQ count, trashed included.
2. `FL.Payload.Properties.Count`: max FlowID.
3. `NextChoiceId` / `NextAnswerId`: strictly greater than the max ID in use.
4. `ChoiceOrder`: it is **both filter and order**. IDs need not be
   contiguous or sorted (`[..."7", "12", "8"...]` happens); a choice absent
   from `ChoiceOrder` is not displayed.
5. Every `QIDn` reference: SQ envelope, `Payload.QuestionID`, BlockElements,
   logic (`QuestionID`, `QuestionIDFromLocator`, `ChoiceLocator`,
   `LeftOperand`), `DynamicChoices.Locator`, `${q://…}` pipes in text, JS and
   embedded-data values.
6. Carry-forward keys: `RecodeValues`/`VariableNaming` on a carried-forward
   question are keyed `x` + source choice ID (`"x3"`), not plain IDs.
7. Branch coverage: every choice of a routing question still has a branch.

**Done when** `python3 scripts/validate_qsf.py <file>` (add `--fresh` in
fresh mode) reports 0 errors and you have read every warning; in edit mode,
a diff against the backup shows only the intended change.

The validator (stdlib, in this skill's `scripts/`) checks 1–6 plus IDs,
element set, SurveyID consistency, orphaned questions, flow→trash refs, SO
boolean types, dangling library pairs, footer scripts and SSO placement.
Branch coverage (7) is yours to check.

## 5. SSO in one screen

- Everything the respondent should answer **only after login** goes
  **inside** the authenticator's `Flow`. `respondentMap` writes IdP
  attributes into embedded data (`FirstName`, `LastName`, `Email`, an ID).
- **Put a welcome block before the authenticator.** Authenticator-first
  redirects to the IdP before any Qualtrics page renders; that layout failed
  for some respondents, while intro-then-authenticator worked.
- A failed login **skips the whole authenticated section**: respondent lands
  on the thank-you page, and an almost-empty response is recorded.
- SSO through `/jfe/preview/` links is unreliable by Qualtrics' own docs:
  test with the live anonymous link in a normal browser window.
- `SSOOptions.SSOID` and `token.Key` belong to a brand's SSO connection.
  Exports embed the key: **treat any export with an authenticator as a
  secret**. Samples here carry `X` placeholders; after import, open Survey
  flow → authenticator and pick your connection. The editor may *display*
  a connection while the flow still stores the placeholder; respondents
  then get "Error while determining which SSO connection to use for this
  survey". Fix: switch SSO Type to another value, save, switch back,
  re-select the connection, save, publish.
- `allowRetake: true` means one person can produce several rows: dedupe on
  the ID field, last submission wins.

Read `references/sso.md` when wiring a new authenticator, mixing SSO with a
non-SSO route, or diagnosing "SSO works for me, not for them".

## 6. Feature shapes

`references/feature-shapes.md` holds copy-ready JSON, from working exports,
for: embedded data (declare, then set per branch), branches with
descriptions, select-exactly-N with custom validation, multi-column
multi-select, drag-and-drop ranking with carry-forward, display logic,
perma-hide, matrix grid, email validation, QuestionJS/CSS, and recodes.
Read it before adding any of those to a file.

## 7. Samples

Three importable, anonymized samples in `samples/`. Each has an SSO
authenticator, never as the first flow element: a welcome page (or, in the
event sample, event details plus a route question) comes first. The event
sample also offers a manual route around SSO. Pick the nearest, copy it,
change text, keep the shapes.

| File | Shows |
|---|---|
| `session-availability-sso.qsf` | Welcome → authenticator → identity card (`${e://Field/…}` piping) + matrix grid (session × attendance mode) with `VariableNaming` |
| `ranked-preferences-sso.qsf` | Opt-in branch with embedded data per route; pick exactly 3 of 10 (custom validation + JS limiter, 2 columns); drag-rank the picks (carry-forward, `x`-keyed recodes); `SubType: ""` block spelled `Standard` in flow |
| `event-attendance-sso.qsf` | SSO route **or** manual route into one shared block; display logic per route; manual answers copied into the same embedded fields; RSVP yes/no recoded `1`/`0` and mirrored to `RsvpStatus`; static Outlook/Google calendar links plus an `.ics` download built as a blob URL in `QuestionJS` |

Import: new project → Survey → *Import a QSF file*. Then: set the SSO
connection in Survey flow, publish, test on the anonymous link. The samples
are structurally validated, not import-tested in every account; *unverified*:
whether a custom validation `Message` without library IDs keeps its
description text on import.

## 8. Postflight

- [ ] Mode stated; backup taken (edit mode)
- [ ] Recompute list done; validator 0 errors, warnings read
- [ ] No tenant field baseline-ified (edit) / no tenant field invented (fresh)
- [ ] Authenticator after a welcome block; SSO placeholders or real values handled per §5
- [ ] File with a real SSO key kept out of public repos, chats and open shares
- [ ] Hand-off reminder (§9) in your reply

## 9. Hand-off reminder

Whenever your reply delivers or changes a `.qsf` that contains an
authenticator, end the reply with this reminder, adapted to the user's
SSO type:

> **After import, register the SSO connection, or respondents get "Error
> while determining which SSO connection to use for this survey":**
> 1. Survey flow → click the authenticator.
> 2. SSO Type: select another type, save the flow.
> 3. SSO Type: back to Shibboleth (or your type), select your connection,
>    save the flow.
> 4. Publish. If saving does not stick, publish and unpublish, then
>    publish again.
> 5. Test with the anonymous link in a normal browser window, not preview.

The editor shows a connection even when the flow still stores a
placeholder or another brand's `SSOID`; only the switch-and-save makes it
stick. Confirmed on a sample import.
