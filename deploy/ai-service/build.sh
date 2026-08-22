#!/usr/bin/env bash
# Build the Lambda deployment package for the optional AI service.
# Output: deploy/ai-service/build/ (tree) and deploy/ai-service/package.zip.
# Requires uv. Targets the arm64 python3.12 Lambda runtime; boto3/botocore
# come from the runtime and are excluded.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
build="$here/build"
rm -rf "$build" "$here/package.zip"
mkdir -p "$build/repo/data/rules" "$build/repo/data/jurisdictions" "$build/repo/corpus"

# Third-party dependencies for the Lambda platform, without boto3/botocore.
uv export --frozen --no-dev --extra ai --no-emit-project --format requirements-txt \
  --no-hashes --output-file "$build/requirements.txt" >/dev/null
grep -v -E '^(boto3|botocore|s3transfer|jmespath)==' "$build/requirements.txt" > "$build/requirements.lambda.txt"
uv pip install --quiet --target "$build" --python-platform aarch64-manylinux2014 \
  --python-version 3.12 --only-binary :all: --no-deps -r "$build/requirements.lambda.txt"
rm -f "$build/requirements.txt" "$build/requirements.lambda.txt"

# This project's source and the committed inputs the service reads.
cp -R "$root/src/permit_pathways" "$build/permit_pathways"
cp "$here/lambda_handler.py" "$build/lambda_handler.py"
cp "$root"/data/rules/*.json "$build/repo/data/rules/"
cp "$root/data/sources.json" "$build/repo/data/sources.json"
cp "$root/data/jurisdictions/registry.json" "$build/repo/data/jurisdictions/registry.json"
# Only the text documents the corpus index reads (see data/sources.json).
python3 - "$root" "$build/repo" <<'PY'
import json, pathlib, shutil, sys
root, dest = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
for entry in json.loads((root / "data/sources.json").read_text()).values():
    local = entry.get("local_copy")
    if local and pathlib.Path(local).suffix in {".html", ".htm", ".txt", ".pdf"}:
        target = dest / local
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / local, target)
PY
find "$build" -name '__pycache__' -type d -prune -exec rm -rf {} +
(cd "$build" && zip -qr -X "$here/package.zip" .)
echo "package: $(du -h "$here/package.zip" | cut -f1) at $here/package.zip"
