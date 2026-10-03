# Credital landing page

Short, institutional landing page for Credital, a lending marketplace. One self-contained file, `index.html`
(Tailwind + vanilla JS, no framework). Sections: hero with an example loan, how it works, waitlist, talk to us, risk disclaimer.

## Working on it

- **Edit and preview:** open `index.html` in a browser. It loads Tailwind from the Play CDN, so it needs a network connection.
- **Production build:** `npm ci && npm run build` writes `dist/index.html` with Tailwind precompiled and inlined (no CDN). CI runs this on every PR.
- **Share image:** `og.png` (1200x630) is rendered from `assets/og.html`.
- **Phone number:** the "Talk to us" section uses `+39 320 818 9855` (one `tel:` link plus the visible text).

## Before it goes public

1. **Waitlist:** set `WAITLIST_ENDPOINT` in the script at the bottom of `index.html` to a URL that accepts a JSON POST
   `{ email, source, ts }` (Formspree, Loops, a Google Apps Script web app, your own API). Until you do, the form shows a demo
   success only on `localhost`/`file://`; on a public host it says the waitlist isn't open yet.
2. **Legal review:** the page advertises interest to retail investors. Have the disclaimer and claims checked, and fill in the
   legal entity / regulator placeholder in the footer.
3. **Example loan:** the hero numbers ($500, 12 months, 12.0%, $44.42 a month, $33.04 interest) are illustrative. Confirm the rating scale and rates before publishing.

## Deploying (GitHub Pages)

`.github/workflows/pages.yml` builds on every PR and push and deploys `dist/` from `main` once you opt in:

1. Repo **Settings > Pages > Build and deployment > Source: GitHub Actions**.
2. Repo **Settings > Secrets and variables > Actions > Variables**: add `PAGES_ENABLED` = `true`.
3. Optional: add `SITE_URL` (for example `https://credital.com`) for a custom domain. It sets the absolute URL of the share image.

Any static host works too: publish the contents of `dist/`.
