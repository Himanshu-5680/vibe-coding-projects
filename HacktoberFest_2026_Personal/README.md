# Himanshu Pathak — Hacktoberfest 2026 Portfolio

An upload-ready static portfolio adapted from the Hacktoberfest 2026 visual
template. Original owner-specific names, social links, contributor lists, and
promotional links have been removed.

## Included

- Responsive single-page portfolio in `index.html` and `styles.css`
- Five featured repositories from `Himanshu-5680` (TwitchBatch and WildWalk were intentionally removed)
- Local Hacktoberfest 2026 milestone images and certificates
- A combined `assets/Hacktoberfest-2026-achievements.pdf`
- Neo-brutalist responsive design with no build step or package installation required
- Contribution guide, code of conduct, PR template, contributor registry, and PR validation workflow

## Upload to the second GitHub account

1. Copy the contents of this folder into a new repository, for example
   `HacktoberFest_2026`.
2. Create a repository on the second GitHub account.
3. Commit and push the files:

   ```bash
   git init
   git add .
   git commit -m "Create personal Hacktoberfest 2026 portfolio"
   git branch -M main
   git remote add origin https://github.com/YOUR-SECOND-ACCOUNT/HacktoberFest_2026.git
   git push -u origin main
   ```

4. To publish it, open **Settings → Pages**, choose **Deploy from a branch**,
   select `main` and `/ (root)`, then save.

The repository cards intentionally point to the source repositories under
`Himanshu-5680`; change those URLs in `index.html` if the second account will
own renamed or forked copies.

## Contributions

Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) before opening a pull request.
Pull requests are checked automatically for the required contributor entry,
valid Markdown, and restricted changes. The repository can enable GitHub
auto-merge after branch protection and required checks are configured.
