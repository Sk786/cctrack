# Website deployment

The site is a static HTML/CSS landing page in this directory. GitHub Pages serves it
for free; there is no server, build step, JavaScript framework, or analytics.

## One-time GitHub setup

1. In the repository, open **Settings → Pages**.
2. Set the build and deployment source to **GitHub Actions**.
3. Merge the site to `master`; `.github/workflows/website.yml` will deploy it.
4. Confirm the workflow's Pages environment reports a successful deployment.

The custom domain is stored in `CNAME` as `cctrack.sandeepk.dev`. At the DNS provider
for `sandeepk.dev` (Squarespace Domains), add a CNAME record:

| Host | Type | Data |
| --- | --- | --- |
| `cctrack` | `CNAME` | `sk786.github.io` |

Remove any conflicting record for the `cctrack` host. Once DNS resolves and Pages
shows the custom domain as verified, enable **Enforce HTTPS** in Settings → Pages.
DNS propagation and certificate issuance can take some time.

## Deployment status

Live at <https://cctrack.sandeepk.dev> from `master` via GitHub Actions. GitHub Pages for
this repository requires the repo to be public; it was made public for that reason.

Custom domain and HTTPS are configured in **Settings → Pages**. DNS is managed at
Squarespace Domains and points `cctrack` at `sk786.github.io`.
