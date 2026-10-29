# External dependencies and rights audit

As inspected on 2026-10-18:

| Dependency | Where | Role | Licensing / privacy action |
|---|---|---|---|
| Bootstrap v5.3.3 | jsDelivr CSS and JS in base.html | UI components | MIT licensed; retain notices on self-hosting; CDN gets browser request information. |
| Font Awesome Free 6.5.2 | cdnjs CSS in base.html | Icons | Mixed licenses (icons CC BY 4.0, fonts SIL OFL 1.1, code MIT); verify attribution and redistribution terms. CDN gets request metadata. |
| System font stack | style.css | Typography | Uses operating system fonts; no external font vendor request. |
| Custom inline SVG | index.html | Example illustration | Included as project source; confirm ownership of source code before commercial reuse. |
| Gemini | Mentions only; no API integration | Future AI | No SDK or external Gemini calls currently enabled. Review DPA, disclosure and consent before implementing. |

No testimonial or payment vendor found. No user-supplied image files found. This is a code inspection, not a browser network audit or legal license verification.
