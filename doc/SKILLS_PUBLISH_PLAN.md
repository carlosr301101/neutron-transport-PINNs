# Publishing `nts-pinns-autopilot` to skills.sh

Step-by-step plan to make the project skill installable through the open
agent skills ecosystem (skills.sh / `npx skills`).

Source: `skills/nts-pinns-autopilot/` in the public repo
**carlosr301101/neutron-transport-PINNs**.

---

## 1. Sanity-check the skill

- [ ] `skills/nts-pinns-autopilot/SKILL.md` has valid YAML frontmatter with
      `name` and `description` (description decides triggering — keep it
      pushy/complete, body stays under ~500 lines).
- [ ] Directory name matches frontmatter `name` (`nts-pinns-autopilot`).
- [ ] Relative pointers inside SKILL.md (`scripts/`, `evals/`) resolve from
      the skill folder itself, not the repo root. Optionally adjust the
      bundled-script usage example to the installed location.

## 2. Commit and push

```bash
git add skills/
git commit -m "feat: add nts-pinns-autopilot skill (SKILL.md + KPI script)"
git push origin main
```

## 3. Verify skills.sh indexes it

Public repos are indexed automatically. Confirm with:

```bash
npx skills find nts --owner carlosr301101
npx skills find pinns
```

Or open `https://skills.sh/carlosr301101/neutron-transport-PINNs/nts-pinns-autopilot`.

## 4. One-line installation for anyone

```bash
# project scope (current repo)
npx skills add carlosr301101/neutron-transport-PINNs@nts-pinns-autopilot

# user scope
npx skills add carlosr301101/neutron-transport-PINNs@nts-pinns-autopilot -g
```

## 5. Local self-check (before sharing)

Install it and check that agents pick it up:

```bash
npx skills add carlosr301101/neutron-transport-PINNs@nts-pinns-autopilot -g -y
npx skills ls -g          # should list nts-pinns-autopilot
```

## 6. Update flow (SKILL.md changes)

skills.sh tracks the GitHub repo, so publishing an update is just:

```bash
git add skills/ && git commit -m "docs(skill): ..." && git push origin main
npx skills update nts-pinns-autopilot   # consumers update to latest
```

Keep a small changelog note in `CHANGELOG.md` whenever the skill body or
frontmatter changes, using the project version.

## 7. Maintenance notes

- If the skill grows (more scripts, references), prefer `references/*.md`
  loaded on demand over bloating SKILL.md.
- Going forward, keep the description synchronized with repo reality — the
  description is what makes agents trigger the skill or ignore it.
