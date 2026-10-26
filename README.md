# survey-skill

An agent skill for Qualtrics® `.qsf` survey files, focused on the quirks:
what real exports contain, what breaks silently, how SSO behaves. It
assumes a frontier model that already knows the QSF basics.

New to this? Start with the plain-language guide in
[`instructions/`](instructions/guide.md): what the sample
surveys do, how to import them and how to switch on sign-in. Common questions
are answered in the [FAQ](instructions/FAQ.md). Indicative screenshots in [`screenshots/`](screenshots/).

## Quick start
1. Use or upload the distribution file [dist/survey-skill-bundle.txt](dist/survey-skill-bundle.txt) to your AI web service or harness and describe what survey you want
2. Import the survey into Qualtrics
3. If SSO is needed, reselect the SSO type to Shibboleth as described in [FAQ](instructions/FAQ.md#Shibboleth)

## Layout

```
Makefile                       shortcuts: make validate | test | bundle | clean
skills/survey-qsf/
  SKILL.md                     the skill: modes, export quirks, recompute list, SSO essentials
  references/sso.md            authenticator shape, placement, failure modes, diagnosis
  references/feature-shapes.md copy-ready JSON for branches, embedded data, ranking, validation, JS/CSS
  scripts/validate_qsf.py      structural validator (stdlib); --fresh for generated files
  samples/                     three anonymized sample surveys, each with an SSO authenticator
tests/test_validate_qsf.py     validator + sample tests
scripts/
  make_bundle.sh              one-file bundle of all docs + validator + samples (for AI web uploads)
instructions/                  plain-language guide: import the samples, set up sign-in
  guide.md                     the guide
  FAQ.md                       common questions
screenshots/                   screenshots of the steps in the guide
```

## Samples

| File | What it is |
|---|---|
| `session-availability-sso.qsf` | Sign in, then mark each of 8 one-hour slots as no / remote / on site / either |
| `ranked-preferences-sso.qsf` | Sign in, opt in, pick exactly 3 of 10 options, drag them into rank order, comment |
| `event-attendance-sso.qsf` | Sign up via SSO or manually, RSVP yes / no, add the event to a calendar (Google/Outlook links, `.ics` download) |

All three show a Qualtrics page before the authenticator and carry placeholder
SSO values (`ASC_XXXXXXXXXXXXXXX`, key `XXXXXXXXXXXXXXXX`). After import
(new project → Survey → *Import a QSF file*), open Survey flow, select your
brand's SSO connection in the authenticator, publish, and test on the
anonymous link (SSO is unreliable in preview). If the link says "Error
while determining which SSO connection to use", the selection was not
stored: switch SSO Type to another value, save, switch back, re-select
the connection, save and publish.

## Install the skill

Clone the repo, then copy or symlink `skills/survey-qsf/` into your agent's
skills folder, e.g. for [pi](https://pi.dev/):

```sh
git clone https://github.com/all-hands/survey-skill.git
cd survey-skill
ln -s "$PWD/skills/survey-qsf" ~/.pi/agent/skills/survey-qsf
```

## Validate and test

```sh
python3 skills/survey-qsf/scripts/validate_qsf.py skills/survey-qsf/samples/*.qsf --fresh
python3 -m unittest discover -s tests
```

With `make`: `make validate`, `make test`, `make bundle` (one-file bundle for
AI services that accept a single upload), `make clean` — wrappers for the
commands above.

One test scans every tracked text file for the words in
`tests/forbidden_terms.txt` (one regex per line, git-ignored, so it is not
in a fresh clone). Without that file the test fails. To run the tests
without it, set `SURVEY_SKILL_NO_TERMS=1`. Images are not scanned: check
screenshots by eye.

## Real exports are secrets

A `.qsf` exported from a survey with an SSO authenticator embeds the SSO
connection's token key. Keep real exports out of this repo: `exports/` and
`*.private.qsf` are git-ignored for that.

## Made with AI

The initial skill, validator, tests, sample surveys and guide in this repo were
created with open-weight AI models. Final polishing was made with a mix of open- and closed-weight models.

## License and trademarks

MIT, see `LICENSE`. Qualtrics is a registered trademark of Qualtrics, LLC.
This project is not affiliated with or endorsed by Qualtrics and was made to facilitate survey design.
