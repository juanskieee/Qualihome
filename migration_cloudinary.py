"""
One-off migration script: push legacy local upload files to Cloudinary.

What it does
------------
1. Scans `properties`, `subdivisions`, and `projects` rows.
2. For every image reference that is a local filename (not an http(s) URL),
   uploads the file from instance/uploads/ to Cloudinary.
3. Rewrites the row's images column with the returned secure_url(s).
4. Prints a summary: migrated vs skipped (already URLs) vs missing files vs errors.

Notes
-----
- Safe to re-run: references that are already URLs are skipped, so an
  interrupted run can simply be executed again.
- Local files are NOT deleted after upload (kept as backup).
- Requires CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET
  in the environment or .env before running.

Usage
-----
    python migration_cloudinary.py            # run migration
    python migration_cloudinary.py --dry-run  # report only, no uploads/DB writes
"""

import os
import sys

from app import create_app
from app.models import db, Project, Subdivision, Property


MIGRATED = "migrated"
SKIPPED = "skipped"
MISSING = "missing"
ERROR = "error"


def new_stats():
    return {MIGRATED: 0, SKIPPED: 0, MISSING: 0, ERROR: 0}


def migrate(dry_run=False):
    app = create_app()
    with app.app_context():
        cloud_name = app.config.get("CLOUDINARY_CLOUD_NAME")
        api_key = app.config.get("CLOUDINARY_API_KEY")
        api_secret = app.config.get("CLOUDINARY_API_SECRET")
        if not (cloud_name and api_key and api_secret):
            print(
                "ERROR: Cloudinary credentials are not configured.\n"
                "Set CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET "
                "in your .env (or environment) and try again."
            )
            sys.exit(1)

        import cloudinary.uploader

        folder = app.config.get("CLOUDINARY_FOLDER", "qualihome")
        upload_dir = app.config["UPLOAD_FOLDER"]

        print(f"Cloudinary cloud : {cloud_name}")
        print(f"Upload folder    : {upload_dir}")
        print(f"Folder on Cloud. : {folder}")
        print(f"Dry run          : {'YES' if dry_run else 'no'}")
        print("-" * 60)

        cache = {}  # filename -> secure_url (avoid uploading duplicates twice)

        def migrate_ref(ref):
            """Return (new_ref, status) for one image reference."""
            ref = (ref or "").strip()
            if not ref:
                return None, SKIPPED
            if ref.startswith(("http://", "https://")):
                return ref, SKIPPED
            if ref in cache:
                return cache[ref], MIGRATED

            fpath = os.path.join(upload_dir, os.path.basename(ref))
            if not os.path.exists(fpath):
                return ref, MISSING

            if dry_run:
                return f"[cloudinary]/{folder}/{ref}", MIGRATED
            try:
                with open(fpath, "rb") as fh:
                    result = cloudinary.uploader.upload(fh, folder=folder)
                url = result["secure_url"]
                cache[ref] = url
                return url, MIGRATED
            except Exception as exc:
                print(f"  ! upload failed for {ref}: {exc}")
                return ref, ERROR

        def process_row(images_list):
            """Migrate a list of refs; returns (new_list, stats, changed)."""
            row_stats = new_stats()
            new_refs = []
            changed = False
            for ref in images_list:
                new_ref, status = migrate_ref(ref)
                if new_ref is None:
                    continue
                if status == MIGRATED and new_ref != ref:
                    changed = True
                new_refs.append(new_ref)
                row_stats[status] += 1
            return new_refs, row_stats, changed

        # ── Properties (images column = comma-separated TEXT) ──────────
        prop_stats = new_stats()
        prop_rows_changed = 0
        props = Property.query.all()
        print(f"\nproperties: {len(props)} row(s)")
        for prop in props:
            refs = [x.strip() for x in (prop.images or "").split(",") if x.strip()]
            new_refs, row_stats, changed = process_row(refs)
            for k in prop_stats:
                prop_stats[k] += row_stats[k]
            if changed and not dry_run:
                prop.images = ",".join(new_refs)
                db.session.commit()
                prop_rows_changed += 1
                print(f"  updated property #{prop.id} ({prop.name}): {row_stats[MIGRATED]} file(s) migrated")

        # ── Projects & Subdivisions (.images list property over CSV) ────
        proj_stats = new_stats()
        proj_rows_changed = 0
        projects = Project.query.all()
        print(f"\nprojects: {len(projects)} row(s)")
        for project in projects:
            refs = list(project.images or [])
            new_refs, row_stats, changed = process_row(refs)
            for k in proj_stats:
                proj_stats[k] += row_stats[k]
            if changed and not dry_run:
                project.images = new_refs
                db.session.commit()
                proj_rows_changed += 1
                print(f"  updated project #{project.id} ({project.name}): {row_stats[MIGRATED]} file(s) migrated")

        sub_stats = new_stats()
        sub_rows_changed = 0
        subdivisions = Subdivision.query.all()
        print(f"\nsubdivisions: {len(subdivisions)} row(s)")
        for sub in subdivisions:
            refs = _sub_images(sub)
            new_refs, row_stats, changed = process_row(refs)
            for k in sub_stats:
                sub_stats[k] += row_stats[k]
            if changed and not dry_run:
                sub.images = new_refs
                db.session.commit()
                sub_rows_changed += 1
                print(f"  updated subdivision #{sub.id} ({sub.name}): {row_stats[MIGRATED]} file(s) migrated")

        def report(label, stats, rows_changed, total_rows):
            print(f"\n{label} ({total_rows} rows scanned, {rows_changed} updated)")
            print(f"  migrated              : {stats[MIGRATED]}")
            print(f"  skipped (already URL) : {stats[SKIPPED]}")
            print(f"  missing local file    : {stats[MISSING]}")
            print(f"  errors                : {stats[ERROR]}")

        print("\n" + "=" * 60)
        verb = "WOULD UPDATE" if dry_run else "UPDATED"
        report("PROPERTIES", prop_stats, prop_rows_changed, len(props))
        report("PROJECTS", proj_stats, proj_rows_changed, len(projects))
        report("SUBDIVISIONS", sub_stats, sub_rows_changed, len(subdivisions))

        totals = {k: prop_stats[k] + proj_stats[k] + sub_stats[k] for k in new_stats()}
        print("-" * 60)
        print(f"TOTAL migrated: {totals[MIGRATED]} | skipped: {totals[SKIPPED]} | "
              f"missing: {totals[MISSING]} | errors: {totals[ERROR]}")
        if dry_run:
            print("\nDry run only - nothing was uploaded or written.")
        else:
            print(f"\n{verb}. Local files were kept in instance/uploads/ as backup.")
        print("=" * 60)


def _sub_images(sub):
    """Subdivision.images getter already returns a list."""
    return list(sub.images or [])


if __name__ == "__main__":
    migrate(dry_run="--dry-run" in sys.argv)
