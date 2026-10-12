# Credital landing page

Short, institutional landing page for Credital, a lending marketplace. One self-contained file, `index.html`
(Tailwind + vanilla JS, no framework). Sections: hero with a "Cool or stupid?" switch, how it works, talk to us, risk disclaimer.
Sliding to cool reveals the waitlist sign-up (email or phone); sliding to stupid shows a thank-you message.

## Working on it

- **Edit and preview:** open `index.html` in a browser. It loads Tailwind from the Play CDN, so it needs a network connection.
- **Production build:** `npm ci && npm run build` writes `dist/index.html` with Tailwind precompiled and inlined (no CDN). CI runs this on every PR.
- **Share image:** `og.png` (1200x630) is rendered from `assets/og.html`.
- **Phone number:** the "Talk to us" section uses `+39 320 818 9855` (one `tel:` link plus the visible text).

## Before it goes public

1. **Votes and sign-ups:** set `WAITLIST_ENDPOINT` in the script at the bottom of `index.html` to a URL that accepts a JSON POST
   (Formspree, Loops, a Google Apps Script web app, your own API). It receives `{ type: 'vote', vote: 'cool' | 'stupid', ... }`
   for every slider vote and `{ type: 'signup', method: 'email' | 'phone', contact, ... }` for every sign-up. The cool/stupid ratio is
   the count of each `vote` value. One vote per browser (stored in localStorage, so it can be cleared). While the endpoint is empty,
   votes are not recorded, and on a public host sign-up says the waitlist isn't open yet.
2. **Legal review:** the page advertises interest to retail investors. Have the disclaimer and claims checked, and fill in the
   legal entity / regulator placeholder in the footer.
3. **Example loan:** the hero numbers ($500, 12 months, 12.0%, $44.42 a month, $33.04 interest) are illustrative. Confirm the rating scale and rates before publishing.

## Deploying (GitHub Pages)

`.github/workflows/pages.yml` builds on every PR and push and deploys `dist/` from `main` once you opt in:

1. Repo **Settings > Pages > Build and deployment > Source: GitHub Actions**.
2. Repo **Settings > Secrets and variables > Actions > Variables**: add `PAGES_ENABLED` = `true`.
3. Optional: add `SITE_URL` (for example `https://credital.com`) for a custom domain. It sets the absolute URL of the share image.

Any static host works too: publish the contents of `dist/`.
