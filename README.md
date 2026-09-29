# Credital landing page

Landing page for Credital, a global peer-to-peer lending marketplace. One self-contained file, `index.html`
(Tailwind + vanilla JS, no framework).

## Working on it

- **Edit and preview:** open `index.html` in a browser. It loads Tailwind from the Play CDN, so it needs a network connection.
- **Production build:** `npm ci && npm run build` writes `dist/index.html`, with Tailwind precompiled and inlined (no CDN).
  CI runs this on every PR.
- **Share image:** `og.png` (1200x630) is rendered from `assets/og.html`.

## Before it goes public

1. **Waitlist:** set `WAITLIST_ENDPOINT` in the script at the bottom of `index.html` to a URL that accepts a JSON POST
   `{ email, role, country, source, ts }` (Formspree, Loops, a Google Apps Script web app, your own API).
   Until you do, the form shows a demo success only on `localhost`/`file://`. On any public host it tells visitors
   the waitlist isn't open yet.
2. **Legal review:** the page advertises yields to retail investors. Have the disclaimers and claims checked, and fill in
   the legal entity / regulator placeholder in the footer. Replace the Terms, Privacy, Risk and Cookie links (currently `#`).
3. **Product assumptions:** fees, minimums, the 48-hour funding target, the provision fund, segregated accounts, rating
   base rates and default rates are illustrative and were invented for the page. Make them true or remove them.
4. **Placeholders:** the testimonials, stats and press logos are labelled placeholders. Replace them with real, verified
   content, or delete the section.

## Changing the pricing model

The model lives in the `RATINGS`, `FEE_LENDER`, `LGD` and `FEE_ORIG` constants in the script. The static rating table and the
comparison table in the HTML are hard-coded copies, so update them when you change the constants.

- APR = base rate for the rating (quoted at 12 months) x term factor, where term factor = 1 + 0.008 x (months - 12)
- Lender net yield = APR - servicing fee - (annual default rate x loss given default)
- Borrower cost = interest + origination fee (deducted at payout); all-in APR is the IRR of the cash flows

## Deploying (GitHub Pages)

`.github/workflows/pages.yml` builds on every PR and push and deploys `dist/` from `main` once you opt in:

1. Repo **Settings > Pages > Build and deployment > Source: GitHub Actions**.
2. Repo **Settings > Secrets and variables > Actions > Variables**: add `PAGES_ENABLED` = `true`.
3. Optional: add `SITE_URL` (for example `https://credital.com`) if you use a custom domain. It sets the absolute URL of the share image.

Any static host works too: publish the contents of `dist/`.
