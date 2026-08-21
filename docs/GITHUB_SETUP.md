# GitHub repository setup

Recommended repository name:

```text
dpr360
```

Recommended GitHub About description:

> Free open-source tool that turns RAW/DNG sets captured with supported drone Panorama Modes into full-resolution 360° equirectangular panoramas.

Recommended topics:

```text
drone photography panorama 360 raw dng equirectangular hugin rawtherapee open-source aerial-photography
```

Recommended settings:

- Default branch: `main`.
- Enable Issues and Discussions if community support is desired.
- Enable Private vulnerability reporting.
- Require CI checks on pull requests once the initial repository is stable.
- Actions workflow permissions: read by default; allow `release.yml` its declared `contents: write` permission.
- Keep branch deletion protection and force-push restrictions for `main` if desired.

## Important local file

`TODO_LOCAL.md` is intentionally present in the handoff ZIP but listed in `.gitignore`. A normal `git add .` will therefore keep the private/local roadmap out of the public repository.
