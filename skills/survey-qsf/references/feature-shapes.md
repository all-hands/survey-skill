# Feature shapes

Copy-ready shapes from working exports, reached from `SKILL.md` §6. QIDs and
FlowIDs are examples: renumber to your file and run the recompute list
afterwards. Each shape is used in at least one file in `../samples/`.

## Embedded data: declare, then set per branch

Declare once (empty `Value`) before branching, set inside each branch.
`Value` takes a literal or a pipe.

```json
{ "Type": "EmbeddedData", "FlowID": "FL_4",
  "EmbeddedData": [
    { "Description": "OptIn", "Type": "Custom", "Field": "OptIn",
      "VariableType": "Nominal", "DataVisibility": [], "Value": "" } ],
  "Options": { "VarTypes": "Yes" } }
```

```json
{ "Type": "Custom", "Description": "Email", "Field": "Email",
  "Value": "${q://QID6/ChoiceTextEntryValue}", "VariableType": "Nominal" }
```

`DataVisibility: []` appears on some field rows and not others in exports;
both import. Flow items of type EmbeddedData, Branch and Authenticator carry
no `Autofill`; Block/Standard items carry `"Autofill": []`.

Use embedded fields as the **stable contract** for downstream code (exports,
mail merges): set a route or status field per branch instead of making
scripts decode choice IDs.

## Branch

```json
{ "Type": "Branch", "FlowID": "FL_6", "Description": "Yes — choose 3, rank, comment",
  "BranchLogic": { "0": { "0": {
      "LogicType": "Question", "QuestionID": "QID3", "QuestionIsInLoop": "no",
      "ChoiceLocator": "q://QID3/SelectableChoice/1", "Operator": "Selected",
      "QuestionIDFromLocator": "QID3", "LeftOperand": "q://QID3/SelectableChoice/1",
      "Type": "Expression", "Description": "If QID3 choice 1 is selected" },
    "Type": "If" }, "Type": "BooleanExpression" },
  "Flow": [ ... ] }
```

`Description` is the label in the flow editor and survives export: write
route names. A second condition in the same group is key `"1"` with
`"Conjuction": "Or"` (Qualtrics' spelling, one *n*).

## Display logic on a question

Same expression object, wrapped with `inPage`:

```json
"DisplayLogic": { "0": { "0": {
    "ChoiceLocator": "q://QID2/SelectableChoice/2",
    "Description": "<span class=\"ConjDesc\">If</span> <span class=\"QuestionDesc\">How would you like to register?</span> <span class=\"LeftOpDesc\">Register without signing in</span> <span class=\"OpDesc\">Is Selected</span> ",
    "LeftOperand": "q://QID2/SelectableChoice/2", "LogicType": "Question",
    "Operator": "Selected", "QuestionID": "QID2", "QuestionIDFromLocator": "QID2",
    "QuestionIsInLoop": "no", "Type": "Expression" },
  "Type": "If" }, "Type": "BooleanExpression", "inPage": false }
```

`Description` is HTML the editor renders; exports may hold stray newlines
inside it. Content is cosmetic, the locators are what run.

## Perma-hide (park a question without trashing it)

```json
"DisplayLogic": { "0": { "0": {
    "LogicType": "BooleanValue", "Value": "False", "Type": "Expression",
    "Description": "<span class=\"ConjDesc\">If</span><span> False</span>" },
  "Type": "If" }, "Type": "BooleanExpression", "inPage": false }
```

The other way: move its BlockElements entry into the Trash block and keep
its SQ.

## Select exactly N (custom validation)

```json
"Validation": { "Settings": {
  "ForceResponse": "OFF", "ForceResponseType": "ON", "Type": "CustomValidation",
  "MinChoices": "3", "MaxChoices": "3",
  "CustomValidation": {
    "Logic": { "0": { "0": {
        "ChoiceLocator": "q://QID4/SelectedChoicesCount",
        "LeftOperand": "q://QID4/SelectedChoicesCount",
        "Operator": "EqualTo", "RightOperand": "3",
        "LogicType": "Question", "QuestionID": "QID4", "QuestionIDFromLocator": "QID4",
        "QuestionIsInLoop": "no", "Type": "Expression", "Description": "..." },
      "Type": "If" }, "Type": "BooleanExpression" },
    "Message": { "description": "Please select exactly 3 options.",
                 "subMessageID": "VE_CUSTOM_VALIDATION_0" } } } }
```

`ForceResponse: "OFF"` with the custom validation doing the enforcing is
normal. In exports `Message` also carries `messageID` + `libraryID` (owner's
library); drop both in fresh files. Pair with a JS limiter that disables
further boxes at N (see `ranked-preferences-sso.qsf`, QID4) so the error
rarely fires.

Exports also use `CustomValidation` as a disguised force-response (OR of
"choice 1 selected", "choice 2 selected", `subMessageID:
"VE_FORCE_RESPONSE"`). Plain `"ForceResponse": "ON"` does the same job.

## Multi-select in columns

```json
"QuestionType": "MC", "Selector": "MACOL", "SubSelector": "TX",
"Configuration": { "QuestionDescriptionOption": "UseText", "NumColumns": 2 }
```

Column count lives in `Configuration`, not in the choices.

## Drag-and-drop ranking of carried-forward choices

```json
{ "QuestionType": "RO", "Selector": "DND", "SubSelector": "TX",
  "Choices": [], "ChoiceOrder": [], "NextChoiceId": 1,
  "DynamicChoices": { "DynamicType": "ChoiceGroup",
                      "Locator": "q://QID4/ChoiceGroup/SelectedChoices", "Type": "Dynamic" },
  "DynamicChoicesData": [],
  "Validation": { "Settings": { "ForceResponse": "ON", "ForceResponseType": "ON", "Type": "None" } },
  "RecodeValues":   { "x1": "1", "x2": "2" },
  "VariableNaming": { "x1": "P01 — Customer onboarding redesign", "x2": "P02 — ..." } }
```

- `Choices` is an **empty array**, not `{}`.
- Carried-forward choices are keyed **`x` + source choice ID**. Keys without
  the `x` match nothing.
- The source question must show earlier in flow order.
- With `ForceResponse: "ON"`, a respondent who likes the default order must
  still drag one item (anywhere, even back in place) before the page
  submits. Say so in the question text.
- Piping `${q://QID4/ChoiceGroup/SelectedChoices}` on a review page shows the
  picks in **choice order, not rank order**. One export had such a review
  page, parked in Trash.

## Matrix grid (one answer per row)

```json
{ "QuestionType": "Matrix", "Selector": "Likert", "SubSelector": "SingleAnswer",
  "Configuration": { "QuestionDescriptionOption": "UseText", "TextPosition": "inline",
                     "ChoiceColumnWidth": 45, "RepeatHeaders": "none",
                     "WhiteSpace": "OFF", "MobileFirst": true },
  "Choices": { "1": { "Display": "Monday 1 March 2027, 09:00-11:00" } },
  "ChoiceOrder": ["1"],
  "Answers": { "1": { "Display": "No" }, "2": { "Display": "Remote" } },
  "AnswerOrder": ["1", "2"],
  "RecodeValues":   { "1": "1", "2": "2" },
  "VariableNaming": { "1": "NO", "2": "REMOTE" },
  "NextChoiceId": 2, "NextAnswerId": 3,
  "DefaultChoices": false, "ChoiceDataExportTags": false, "GradingData": [] }
```

Rows are `Choices`, columns are `Answers`; on a matrix, `RecodeValues` and
`VariableNaming` key on **answers**. Both `Next…Id` counters apply.

## Text entry

```json
"QuestionType": "TE", "Selector": "SL",
"Validation": { "Settings": { "ForceResponse": "ON", "ForceResponseType": "ON",
                              "Type": "ContentType", "ContentType": "ValidEmail" } },
"SearchSource": { "AllowFreeResponse": "false" }
```

`Selector` `SL` single line, `ML` multi-line (box size in
`Configuration.InputWidth`/`InputHeight`). `SearchSource` rides along on TE
exports.

## Recodes and labels

- `RecodeValues` may be non-monotonic: yes/no as `{"1": "1",
  "2": "0"}` makes the column a 0/1 flag.
- `VariableNaming` gives choices short analysis labels (`"1": "P01"`).
- Both are string→string maps at payload level.
- `DataExportTag` is the response column name: make it semantic
  (`rsvp`) and treat it as contract between survey waves.

## Custom code

- `QuestionJS`: one string of JS using
  `Qualtrics.SurveyEngine.addOnReady` / `addOnPageSubmit`; several hooks
  may sit in one string. Observed uses: change the Next button label,
  limit checkbox count, build an `.ics` blob URL, write to `sessionStorage`.
- `SO.CustomStyles.customCSS`: raw CSS for the whole survey. `:has()` works
  for styling selected choices.
- `SO.Footer`: HTML including `<script>`; see the truncation quirk in
  `SKILL.md` §2. Prefer `QuestionJS`.
- Inline-styled HTML in `QuestionText` (cards, buttons) survives round
  trips. Edit in place: preserve all of the above byte for byte.
