# Releasing

HACS uses a published GitHub Release as the remote version source. A Git tag by
itself is not sufficient.

## Prepare a release

1. Start from an up-to-date `main` branch with a clean working tree.
2. Choose a semantic version such as `0.1.0`.
3. Set the same version in `pyproject.toml` and
   `custom_components/weather_underground_uploader/manifest.json`.
4. Move the relevant entries from the `Unreleased` section of `CHANGELOG.md`
   into a versioned section with the release date.
5. Replace the previous content of `RELEASE_NOTES.md` with a concise summary of
   the release using the convention below.
6. Run the complete validation suite documented in `CONTRIBUTING.md`.
7. Merge the release-preparation pull request and verify CI, hassfest, and HACS
   validation on `main`.

## Write release notes

`RELEASE_NOTES.md` contains only the curated introduction for the next release.
The release workflow prepends it to GitHub's generated contributor and pull
request changelog, so do not duplicate the complete PR list manually.

Use this structure and omit an optional section only when it has no useful
content:

```markdown
## 🌦️ Summary

One short paragraph describing why the release matters to users.

## ✨ Highlights

- The most important user-visible changes.

## ⚠️ Breaking changes

None.

## ⬆️ Installation and upgrade notes

Only steps that differ from the normal HACS update process.
```

Always retain the breaking-changes heading and write `None.` when the release
is backward compatible. Add installation or upgrade notes only when users need
to take action.

GitHub categorizes the generated changelog through `.github/release.yml`.
Apply the most relevant standard label to each pull request:

- `enhancement` for new features and user-visible improvements;
- `bug` for fixes;
- `documentation` for documentation-only changes.

Unlabeled pull requests and maintenance work appear in the catch-all
**Maintenance and other changes** category. Labels affect presentation only;
they do not replace the curated summary or the explicit breaking-change note.

## Publish

Create an annotated semantic-version tag on the validated release commit and
push that explicit tag:

```bash
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

The `Release` workflow verifies that the tag matches both project version
files, reruns the quality, test, hassfest, and HACS checks, and then creates a
full GitHub Release with generated release notes. The workflow does not publish
an integration archive because HACS installs the integration from GitHub's
release source archive. The curated `RELEASE_NOTES.md` content appears first,
followed by the categorized GitHub-generated changelog and full comparison
link.

## Verify

1. Confirm that the GitHub Release is published and marked as the latest stable
   release.
2. Add the repository to HACS as a custom integration repository.
3. Install the release into a non-production Home Assistant 2026.7+ instance.
4. Restart Home Assistant, complete a setup flow with synthetic test
   credentials, and confirm the integration loads.
5. For subsequent releases, verify both a fresh installation and an upgrade
   from the previous release.

Do not move, recreate, or overwrite a published release tag. Publish a new
patch version if a release needs correction.
