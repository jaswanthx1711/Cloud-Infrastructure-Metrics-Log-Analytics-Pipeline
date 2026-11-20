This folder contains a minimal dbt project to run the repo's Silver + Gold SQL transforms using the existing SQLite `data/analytics.db`.

Quick start (local):

1. Install dbt core and the sqlite adapter (in a venv):

```bash
pip install dbt-core dbt-sqlite
```

2. Copy the profiles example to your home dbt profiles location:

```bash
mkdir -p ~/.dbt
cp dbt/profiles.yml.example ~/.dbt/profiles.yml
```

3. From the repo root, run dbt:

```bash
cd /path/to/repo
dbt deps
dbt seed   # none by default
dbt run
dbt test
```

Notes:
- Models under `dbt/models/staging` read from the raw Bronze tables via `source()`.
- Models under `dbt/models/marts` build the Gold tables via `ref()`.
- The project is intentionally minimal so it does not change your pipeline target; it writes models into the same SQLite DB (`data/analytics.db`) used by the existing pipeline.
