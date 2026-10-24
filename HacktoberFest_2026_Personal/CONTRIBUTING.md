# Contributing to Himanshu's Hacktoberfest Portfolio

Thanks for contributing. This repository is intentionally beginner-friendly,
but every pull request must make a useful, respectful improvement.

## Contribution rules

1. Fork the repository and create a focused branch.
2. Add your entry at the bottom of `contributors/contributorsList.js` when you
   contribute.
3. Use the next available numeric `id` and a valid
   `https://github.com/username` URL.
4. Do not delete or rewrite another contributor's work.
5. Keep changes focused: documentation, accessibility, responsive styling,
   bug fixes, or small static-site improvements are welcome.
6. Do not add secrets, generated dependency folders, build output, or
   unrelated binaries.
7. Test the changed page locally by opening `index.html` before submitting.
8. Explain what changed in the pull request and confirm the checklist.

## Local workflow

```bash
git clone https://github.com/YOUR-SECOND-ACCOUNT/HacktoberFest_2026.git
cd HacktoberFest_2026/HacktoberFest_2026_Personal
git checkout -b my-contribution
```

After editing, open `index.html` in a browser and verify the links, layout,
images, and mobile view. Then commit and push your branch:

```bash
git add .
git commit -m "Describe the contribution"
git push origin my-contribution
```

Open a pull request against `main`. The automated workflow will check the
contributor registry, repository hygiene, and changed files. Maintainers can
enable GitHub's native auto-merge once required checks and branch protection
are configured; no workflow can bypass repository permissions or failed checks.
