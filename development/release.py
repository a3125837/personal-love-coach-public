"""Package only Skill resources and optionally install a new local copy without overwriting anything."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import zipfile

WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "personal-love-coach"


def release(install=False):
    files = sorted(p for p in SOURCE.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    manifest = {p.relative_to(SOURCE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    output = WORKSPACE / "dist"
    output.mkdir(exist_ok=True)
    metadata = (SOURCE / "SKILL.md").read_text(encoding="utf-8")
    version = re.search(r'^\s+version:\s*"([0-9.]+)"', metadata, flags=re.MULTILINE).group(1)
    package = output / f"personal-love-coach-{version}.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "personal-love-coach/" + path.relative_to(SOURCE).as_posix())
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(files)
        for entry in archive.namelist():
            key = entry.removeprefix("personal-love-coach/")
            assert hashlib.sha256(archive.read(entry)).hexdigest() == manifest[key]
            assert not any(token in entry for token in ("conversation.txt", "personal-love-coach-data", "__pycache__"))
    report = {"version": version, "files": len(files), "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
              "zip": str(package), "manifest": manifest}
    if install:
        codex_dir = Path(os.environ.get("CODEX_HOME", "") or Path.home() / ".codex")
        target = codex_dir / "skills/personal-love-coach"
        if target.exists():
            target_manifest = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in target.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
            if target_manifest != manifest:
                raise RuntimeError("An existing different Skill was found; it was not overwritten")
        else:
            shutil.copytree(SOURCE, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for key, digest in manifest.items():
            assert hashlib.sha256((target / key).read_bytes()).hexdigest() == digest
        report["installed"] = str(target)
    (output / "release-manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "manifest"}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true")
    release(parser.parse_args().install)
