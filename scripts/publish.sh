#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"

usage() {
  cat <<'USAGE'
Usage: scripts/publish.sh <command>

Commands:
  deps          Install build tools (build, twine)
  build         Build sdist/wheel into dist/
  check         Validate dist/ metadata with twine
  testpypi      Upload dist/* to TestPyPI (creates project on first upload)
  pypi          Upload dist/* to PyPI
  release-test  Clean, build, check, upload to TestPyPI
  release       Clean, build, check, upload to PyPI
  clean         Remove dist/ and build/
USAGE
}

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing file: $1" >&2
    exit 1
  fi
}

require_dist() {
  shopt -s nullglob
  local files=("$ROOT_DIR"/dist/*)
  shopt -u nullglob
  if [ ${#files[@]} -eq 0 ]; then
    echo "dist/ is empty. Run 'scripts/publish.sh build' first." >&2
    exit 1
  fi
}

cmd_deps() {
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install --upgrade build twine
}

cmd_build() {
  require_file "$ROOT_DIR/pyproject.toml"
  rm -rf "$ROOT_DIR/dist" "$ROOT_DIR/build"
  "$PYTHON" -m build
}

cmd_check() {
  require_dist
  "$PYTHON" -m twine check "$ROOT_DIR"/dist/*
}

cmd_testpypi() {
  require_dist
  if [ -z "${TESTPYPI_TOKEN:-}" ]; then
    echo "TESTPYPI_TOKEN is not set." >&2
    echo "Create a token at https://test.pypi.org/manage/account/token/ and export it." >&2
    exit 1
  fi
  echo "Uploading to TestPyPI. First upload creates the project."
  TWINE_USERNAME="__token__" TWINE_PASSWORD="$TESTPYPI_TOKEN" \
    "$PYTHON" -m twine upload --repository-url https://test.pypi.org/legacy/ "$ROOT_DIR"/dist/*
}

cmd_pypi() {
  require_dist
  if [ -z "${PYPI_TOKEN:-}" ]; then
    echo "PYPI_TOKEN is not set." >&2
    echo "Create a token at https://pypi.org/manage/account/token/ and export it." >&2
    exit 1
  fi
  TWINE_USERNAME="__token__" TWINE_PASSWORD="$PYPI_TOKEN" \
    "$PYTHON" -m twine upload "$ROOT_DIR"/dist/*
}

cmd_clean() {
  rm -rf "$ROOT_DIR/dist" "$ROOT_DIR/build"
}

main() {
  cd "$ROOT_DIR"
  case "${1:-}" in
    deps) cmd_deps ;;
    build) cmd_build ;;
    check) cmd_check ;;
    testpypi) cmd_testpypi ;;
    pypi) cmd_pypi ;;
    release-test) cmd_clean; cmd_build; cmd_check; cmd_testpypi ;;
    release) cmd_clean; cmd_build; cmd_check; cmd_pypi ;;
    -h|--help|help|"") usage ;;
    *)
      echo "Unknown command: $1" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
