# Frequently asked questions

Common questions about surveys with sign-in (SSO). For the step-by-step
guide, see [the plain guide](guide.md).

Menu names in Qualtrics differ a little between accounts and change over
time. If a step doesn't match what you see, search the
[Qualtrics support site](https://www.qualtrics.com/support/) for the
setting's name.

## Sign-in (SSO)

### Sign-in works for me but not for a participant. What's wrong?

If the survey works for you, the setup is usually fine. Check these, in
this order:

1. **Preview link.** Did they open a preview link? Sign-in through
   preview is unreliable. Send them the anonymous link.
2. **Browser.** Links opened inside the Teams or Outlook app, private
   windows, strict privacy settings and ad blockers can break the
   sign-in. Ask them to paste the link into a normal browser window.
3. **Account type.** Guest or some staff accounts may not pass their
   name and email to Qualtrics. Only the team that runs your
   organisation's login can fix that.

A failed sign-in sends participants straight to the end of the survey, so they
will say "it ended at once". Qualtrics still saves an almost empty
response. Remove rows without an email or ID before you count results.

### Where does Qualtrics say preview doesn't work with SSO?

On the
[SSO Authenticator](https://www.qualtrics.com/support/survey-platform/survey-module/survey-flow/advanced-elements/authenticator/sso-authenticator/)
support page, which warns that this SSO type "may not function properly
with Preview Survey" and suggests testing with the anonymous link.

### Could bot detection (reCAPTCHA) be blocking participants?

Unlikely. Qualtrics' support pages describe bot detection as adding a
score to each response; it doesn't stop any participant taking the survey. To
switch it off anyway: **Survey options › Security › Bot detection**,
then **Publish**. The live link keeps the old setting until you publish.

### After importing a sample, the link says "Error while determining which SSO connection to use". How do I fix it? ([Shibboleth](#Shibboleth))

The sample file only holds a placeholder connection, and the editor can
show your connection without actually saving it. This fix worked:

1. In **Survey flow**, open the authenticator.
2. Change **SSO Type** to another method and save. If saving doesn't
   stick, publish and then unpublish.
3. Switch **SSO Type** back and select your connection again.
4. Save and publish. If saving doesn't stick, publish once more.
5. Test with a fresh anonymous link in a normal browser window.

The number in brackets after the message is only a reference for
reports. If no connection is listed at all, your Qualtrics brand
administrator has to switch SSO on for survey authenticators.

## Questions and answers

### How do I ask that I want something else?
Ask directly opening an [issue](https://github.com/all-hands/survey-skill/issues). You can also contribute directly with a [pull request](https://github.com/all-hands/survey-skill/pulls).

### Participants pick 3 options and then rank them. Do they have to move anything, or can they just click Next?

With a drag-and-drop ranking and **Force response** on, an untouched
ranking counts as unanswered, so Next shows "Please answer this
question". Participants have to drag at least one item (they can drop it back
in place). Without Force response, an untouched ranking is saved as
blank, not as 1 to 3.

The easier option is to show the ranking as radio buttons: one row per
option, one column per rank, each rank used once. It is also easier to
use with a keyboard or screen reader.

### Can I make participants pick exactly 3 options, without JavaScript?

Yes. On the question, go to **Response requirements › Add validation ›
Answers range** and set both minimum and maximum to 3. Also turn on
**Force response**, so picking nothing doesn't pass. Test in preview with
0, 2, 3 and 4 options ticked.

"Minimum choices" on its own only checks the lower limit, so participants
could still pick 4 or more.

### How do I change the "Please answer this question." message?

Under **Survey options › Responses › Custom error messages**, create a
new message for "Require response", enter your text, save it and
publish. This changes the message for the whole survey, so keep the
wording general. For one question only, give that question its own
custom validation with its own message. You can change the text, not the
style.

### What else is worth setting before the survey goes live?

- Stop participants from taking the survey twice with the same login, or plan
  to keep only their newest response.
- Set a closing date.
- Write your own thank-you message for the end of the survey.
- Delete questions you no longer use, including those in the Trash
  block.
- Give questions readable export names (`preferred_session`, not `Q7`). That
  makes the results file much easier to work with.

## Emails after a response

### How do I email participants a copy of their answers?

With a workflow that sends an email after each response, with their
answers attached. The steps are in the guide:
[Email participants a copy of their answers](guide.md#email-participants-a-copy-of-their-answers).

### I set up a workflow that sends an email after each response, but nothing is sent. Why?

First open **Workflows › Run history**:

- **No run at all**: the trigger never fired.
- **Stopped at the condition**: the condition didn't match.
- **Email task failed**: the error is shown there.
- **Succeeded, but nothing arrived**: a delivery problem (spam folder,
  mail filters).

With sign-in surveys, the usual cause is the **To** field. "Recipient
Email" refers to a contact list, and is empty when participants sign in. Their
address comes from the sign-in as embedded data instead, so use the
`Email` embedded data field as the recipient. Also check that the
workflow is switched on and fires for new responses only. Unfinished
responses don't trigger it: the email goes out only after the last page.

## Look and feel

### I imported a sample and my organisation's logo appears. Is it in the file?

No. The samples don't name a theme, so Qualtrics uses your account's
default theme, which can include a logo. Change it per survey under
**Look & feel**.

### How do I make a theme the default?

Only a brand administrator can. In the admin pages, under **Themes**,
the theme at the top of the list becomes the default for new projects.
Existing surveys don't change. Everyone else can only pick a theme per
survey.

## For the technical colleague or AI assistant

### What surprised us in real `.qsf` exports?

- Messages (end of survey, error texts) are stored as references to the
  account's message library, so they break when the file is imported
  into another account. Set them again after import.
- A ranking fed by an earlier question keys its recodes as `x` plus the
  source choice ID.
- A copied survey's JavaScript can still contain the original survey's
  ID.
- A footer script can arrive cut off mid-code.
- A real export with sign-in contains the SSO connection's secret key.
  Treat it like a password and keep it out of the repo.

The skill (`skills/survey-qsf/SKILL.md`) covers these in detail.
