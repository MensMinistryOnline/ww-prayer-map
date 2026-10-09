# Weekend Warriors · Pray for Your Leaders

Public data for the MensMinistry.online Weekend Warriors prayer map.

- `docs/data/index.json` and `docs/data/states/XX.json` are rebuilt every day by `.github/workflows/refresh.yml`.
- GitHub Pages serves `docs/` at `https://mensministryonline.github.io/ww-prayer-map/`.
- `widget/ww-prayer-map.html` is the Squarespace Code block. Set `data-base` to your Pages `data/` URL.
- Supreme Court names live in `scripts/national_static.json`. Update them by hand if a Justice changes.

Sources: unitedstates/congress-legislators, Plural Open States (openstates/people and data.openstates.org), U.S. Census Geocoder.
