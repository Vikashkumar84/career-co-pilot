# Career Copilot — privacy, accessibility, marketing audit (2026-10-18)

## Implemented in this demo
- Privacy, terms, refund, and cookie policy routes linked globally. Terms state this is an educational demo, not a legal sign-off.
- Consent banner: equal accept/reject; preference stored locally; footer settings reopen it; no nonessential tracking currently installed.
- Registration: removed unnecessary name, education and goal inputs; separate required terms acknowledgment and unchecked optional marketing checkbox. No actual account creation.
- Removed unsupported homepage user totals and accuracy percentage, and softened unsupported AI promises. Any other demo numbers are illustrative only.
- Added keyboard skip link, focus indicators, visible form labels, browser-friendly font stack, reduced motion support and accessible cookie controls.
- Added data deletion page allowing removal of the site's locally saved cookie preference; optional configured contact email for deletion requests.
- Business contact/name displayed only if configured via BUSINESS_NAME / CONTACT_EMAIL; missing info explicitly disclosed.
- No checkout, hidden fees, payment SDK, reviews or email-sending system exists in this repository. Refund policy states no payments.

## Actions needed BEFORE production launch
1. Configure and verify business identity and privacy/support contact; secure a legal review for applicable jurisdictions.
2. Replace stub login and sample career outputs with secure authenticated server logic before claiming functionality. Implement authenticated deletion of *all* backend data, backups, and processor-held data if added.
3. Introduce verified age assurance and legally appropriate parent/guardian consent **only if** collecting children's personal data. Avoid collecting it otherwise.
4. If mailing is implemented, add unique working unsubscribe links, opt-in records, preference management, and email provider suppression list. No email is sent now.
5. Audit and ideally self-host Bootstrap 5.3.3 / Font Awesome 6.5.2; confirm library licenses and vendor policies; current CDNs can receive IP information prior to banner choice. System fonts eliminate remote Google Fonts. Inline SVG is authored in code; inspect any future image assets for rights and meaningful alt text.
6. Perform manual WCAG 2.2 AA testing with keyboard, screen reader, color contrast tool, real mobile browsers; style changes alone do not certify WCAG conformance.
7. Audit every new SDK, cookie, network request, review, advertising claim and fee at release. Ensure no manipulative opt-in flows.
8. Replace example score/match fields with verified calculations or label as simulated.

Run: `pip install flask && python app.py`. Set FLASK_DEBUG only for local development.
