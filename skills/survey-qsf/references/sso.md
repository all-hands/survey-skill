# SSO authenticator: shape, placement, failure modes

Reached from `SKILL.md` §5. Observed on two surveys using the same
Shibboleth connection with an identical authenticator config: one worked
for every respondent tested, the other failed for some.

## Shape (Shibboleth)

"Shibboleth" is Qualtrics' label for SAML-based SSO ("Respondents
authenticate via SAML"), whatever SAML identity provider the organisation
runs. Other SSO types: Token, CAS, LDAP, Google OAuth 2.0, Facebook.

```json
{
  "Type": "Authenticator",
  "FlowID": "FL_3",
  "FilterDataFields": true,
  "SSOOptions": {
    "respondentMap": [
      { "key": "urn:oid:2.5.4.42",                  "value": "FirstName" },
      { "key": "urn:oid:2.5.4.4",                   "value": "LastName" },
      { "key": "urn:oid:0.9.2342.19200300.100.1.3", "value": "Email" },
      { "key": "urn:oid:0.9.2342.19200300.100.1.1", "value": "UserID" }
    ],
    "Type": "Shibboleth",
    "token": { "EncryptionMethod": "3DES", "MacMethod": "sha512",
               "Leeway": 300, "Key": "XXXXXXXXXXXXXXXX" },
    "ldap": { "Hostname": "ldap://", "Port": "389", "EmailField": "mail",
              "Filter": "(sAMAccountName=%1)", "FirstNameField": "givenname",
              "LastNameField": "sn", "ExternalDataReferenceField": "" },
    "UsePanel": "No", "CaptureRespondentInfo": "Yes", "UseSSO": "Yes",
    "SSOID": "ASC_XXXXXXXXXXXXXXX", "cas": []
  },
  "Options": {
    "maxAttempts": 3,
    "questionText":              { "SystemMessage": { "Section": "ErrorCodes", "Message": "EAUTH04" } },
    "authenticationError":       { "SystemMessage": { "Section": "ErrorCodes", "Message": "EAUTH02" } },
    "failedAuthenticationError": { "SystemMessage": { "Section": "ErrorCodes", "Message": "EAUTH05" } },
    "allowRetake": true, "loadExistingSession": false, "reauthenticateSession": false
  },
  "Flow": [ "...everything that needs a signed-in respondent..." ]
}
```

- `respondentMap` keys are SAML attribute OIDs (givenName, sn, mail, uid);
  values are embedded-data field names, which become response columns. The
  IdP decides which attributes it releases; a missing one arrives blank.
- `token` and `ldap` are carried even for Shibboleth (default-looking
  values). `token.Key` is real secret material in an export.
- `SSOID` (`ASC_…`) names the brand-level SSO connection. It is per brand:
  a file moved to another brand needs the connection re-picked in Survey
  flow. Wrong or disabled connection shows Qualtrics error
  `AUTHENTICATOR_SSO_CONFIG_DISABLED` / `…_NOT_FOUND` for **everyone**.
- `Autofill` is never on an authenticator item; only on Block/Standard.

## Placement

| Layout | Observed |
|---|---|
| Authenticator as very first flow element, all blocks inside | Worked for some respondents, failed for others |
| Welcome page first, authenticator inside a branch after a routing question | Worked for everyone tested |

Authenticator-first redirects to the IdP on the first page load, before any
Qualtrics page has set its session; embedded/in-app browsers and strict
cookie settings are likelier to lose the session on that immediate
redirect. Qualtrics' own advice is "move the authenticator to the beginning
of your survey flow", so authenticator-first is not a config *error*, just
the riskier layout. Default: a welcome block with **no** `${e://Field/…}`
piping (nothing is filled before login), then the authenticator.

## What failure looks like

- Login fails → after `maxAttempts`, Qualtrics **skips the authenticated
  section**. If every block is inside it, the respondent goes straight to
  the thank-you page. "SSO broken" is reported as "the survey ends at once".
- Failed authentications **are recorded as responses**: rows with no
  identity fields. Filter rows without the ID/email before analysis.
- Login works, attributes missing → identity card shows blank name/email.
  IdP attribute release for that account type; the IdP admins fix it.

## Diagnosis: "works for me, not for them"

Identical config cannot fail for one person only, so look at how they open
it:

| Symptom | Likely cause | Check |
|---|---|---|
| Never reaches the IdP login | Preview link, or browser | URL contains `/jfe/preview/` → send the live anonymous link `/jfe/form/SV_…` |
| Bounces between IdP and Qualtrics | Cookies lost across the redirect | Opened inside Teams/Outlook/mail app, private mode, strict tracking protection, ad-block → normal Chrome/Edge window, extensions off |
| IdP shows "not authorised for this service" | Account type not released to Qualtrics | Guest/external/staff vs regular account → IdP admins |
| Lands on thank-you page immediately | Login failed and was skipped | Combine with the rows above; look for an empty response at that time |
| Identity card blank | Attributes not released | IdP admins |
| "Error while determining which SSO connection to use for this survey. Please contact your brand administrator." plus a report tag | Imported file's `SSOID` is unknown in this brand (placeholder or another brand's ID). The editor *displays* a connection but has not stored it | Survey flow → authenticator: switch SSO Type to another value, save; switch back, re-select the connection, save, publish. If saving does not stick, publish/unpublish to force it. Confirmed fix on a sample import |
| Silent login as the wrong person | Already signed in to the IdP with another account | Sign out of the IdP or use a fresh browser profile |

Cross-check: have them open a survey whose SSO is known to work, in the
same browser. Fails there too → their account or browser. Works there →
try the welcome-block-first layout.

## Mixed SSO and non-SSO routes

To admit participants without an account while keeping one response schema:

1. Default block: welcome + routing question ("Sign in" / "Register without
   signing in").
2. Branch on choice 1 → authenticator → embedded `LoginMethod = SSO` →
   shared form block.
3. Branch on choice 2 → embedded `LoginMethod = Manual` and declare
   `FirstName`/`LastName`/`Email`/ID empty → same shared form block →
   embedded data copying `${q://QIDn/ChoiceTextEntryValue}` of the typed
   name/email into the same fields.
4. In the shared block, display logic per route: identity card (piped) for
   SSO, text-entry name/email (required, email `ContentType: ValidEmail`)
   for manual. Hidden required questions do not block the page.

Every row then has the same identity columns regardless of route; typed
addresses are less reliable than SSO ones (expect bounces).

## Other options

- `maxAttempts`: Qualtrics generally advises against it for SSO; it matters
  only with "associate respondent with panel" (`UsePanel: "Yes"`). Observed
  value 3 is harmless.
- `allowRetake: true` → repeat submissions; decide a rule (last per ID
  wins) or turn it off.
- `loadExistingSession` / `reauthenticateSession`: reload saved progress /
  force re-login on resume. Both `false` in every observed survey.
- Bot detection (`RecaptchaV3`) only adds a score; it never blocks
  respondents, so it is not an SSO suspect.

## Sources

- Qualtrics, [SSO Authenticator](https://www.qualtrics.com/support/survey-platform/survey-module/survey-flow/advanced-elements/authenticator/sso-authenticator/): Shibboleth section, preview limitation ("may not function properly with preview survey"), test via anonymous link, error codes, max-attempts advice.
- Qualtrics, [Authenticator Overview](https://www.qualtrics.com/support/survey-platform/survey-module/survey-flow/advanced-elements/authenticator/authenticator-overview/): placement, retake/reload options, failed authentications recorded as responses, skip-past behaviour.
- Qualtrics, [Fraud Detection](https://www.qualtrics.com/support/survey-platform/survey-module/survey-checker/fraud-detection/): bot detection never blocks respondents.
