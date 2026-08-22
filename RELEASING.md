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
5. Run the complete validation suite documented in `CONTRIBUTING.md`.
6. Merge the release-preparation pull request and verify CI, hassfest, and HACS
   validation on `main`.

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
release source archive.

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
