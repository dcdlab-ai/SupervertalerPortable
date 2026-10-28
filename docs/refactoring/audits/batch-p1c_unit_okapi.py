"""
BATCH P1-C probe 3 (unit): Okapi sidecar paths inside the build (P1.5).

With the SUPERVERTALER_DATA_ROOT seam pointed at an isolated dir:
  * _user_data_sidecar_dir() == <data_root>/okapi-sidecar (lazy-download
    target; never an OS user-config directory);
  * candidate order: a bundled/source-tree JAR (build candidates) wins over
    a downloaded JAR in <data_root>; with no build JAR, the data-root copy
    is found on the next construction ("restart");
  * download_install() with a MOCKED requests (no network) installs the
    fake bundle under <data_root>/okapi-sidecar, writes the
    okapi-sidecar.version stamp next to it, and the instance reports
    is_user_downloaded()/needs_update() correctly;
  * nothing is written to the (isolated) LOCALAPPDATA Supervertaler dir —
    the old Windows candidate is gone.

Prints P1C-OKAPI-OK / P1C-OKAPI-FAIL. Exit code 0/1.
"""
import io
import os
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
# iso dir: argv[1] (the runner passes the stage dir) or the documented stage
ISO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else \
    Path(r"E:\Dev\Work_temp\SupervertalerPortable\refactoring\batch-p1c\iso-okapi")
PROFILE = ISO / "profile"
os.environ["SUPERVERTALER_DATA_ROOT"] = str(ISO)
os.environ["USERPROFILE"] = str(PROFILE)
os.environ["HOME"] = str(PROFILE)
os.environ["APPDATA"] = str(PROFILE / "AppData" / "Roaming")
os.environ["LOCALAPPDATA"] = str(PROFILE / "AppData" / "Local")

sys.path.insert(0, str(REPO))

from modules import okapi_sidecar as mod                          # noqa: E402
from modules.okapi_sidecar import OkapiSidecar                     # noqa: E402
from modules.portable_paths import data_root                       # noqa: E402

FAILURES = []
BUILD_CAND = REPO / "okapi-sidecar"      # source-tree candidate
BUILD_JAR = BUILD_CAND / "okapi-sidecar.jar"


def check(name, cond, detail=""):
    tag = "OK " if cond else "FAIL"
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


class FakeResp:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.headers = {"Content-Length": str(len(payload))}
        self.status_code = 200

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=64 * 1024):
        yield self.payload

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def install_mock_requests():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("okapi-sidecar/okapi-sidecar.jar", "FAKE-JAR-BYTES")
        zf.writestr("okapi-sidecar/jre/bin/java.exe", "FAKE-JRE")
    payload = buf.getvalue()

    class FakeRequests:
        def get(self, url, stream=False, timeout=None):
            return FakeResp(payload)

    mod.requests = FakeRequests()


def main():
    dr = data_root()
    target = dr / "okapi-sidecar"

    check("data_root == iso/Supervertaler (seam)",
          dr == ISO / "Supervertaler", str(dr))
    check("_user_data_sidecar_dir == <data_root>/okapi-sidecar",
          OkapiSidecar()._user_data_sidecar_dir() == target, str(target))

    # --- candidate order: build JAR wins over data-root copy ---
    created_build = False
    try:
        target.mkdir(parents=True, exist_ok=True)
        (target / "okapi-sidecar.jar").write_bytes(b"downloaded")
        BUILD_CAND.mkdir(exist_ok=True)
        if not BUILD_JAR.exists():
            BUILD_JAR.write_bytes(b"build")
            created_build = True
        sc = OkapiSidecar()
        check("build/source-tree JAR wins while it exists",
              sc.sidecar_dir == BUILD_CAND, str(sc.sidecar_dir))
        if created_build:
            BUILD_JAR.unlink()
        sc2 = OkapiSidecar()
        check("data-root copy found once the build JAR is gone",
              sc2.sidecar_dir == target, str(sc2.sidecar_dir))
    finally:
        if created_build and BUILD_JAR.exists():
            BUILD_JAR.unlink()
        if created_build and BUILD_CAND.exists() and not any(BUILD_CAND.iterdir()):
            BUILD_CAND.rmdir()
        if (target / "okapi-sidecar.jar").exists():
            (target / "okapi-sidecar.jar").unlink()

    # --- download_install with mocked requests (no network) ---
    install_mock_requests()
    sc3 = OkapiSidecar()
    check("not installed before download", not sc3.is_installed())
    ok = sc3.download_install()
    check("download_install returned True", ok is True)
    jar = target / "okapi-sidecar.jar"
    check("JAR installed under <data_root>/okapi-sidecar",
          jar.exists() and jar.read_bytes() == b"FAKE-JAR-BYTES", str(jar))
    stamp = target / "okapi-sidecar.version"
    check("version stamp written next to the JAR",
          stamp.exists()
          and stamp.read_text(encoding="utf-8") == OkapiSidecar.EXPECTED_VERSION,
          stamp.read_text(encoding="utf-8") if stamp.exists() else "missing")
    check("sidecar_dir updated to the install target",
          sc3.sidecar_dir == target, str(sc3.sidecar_dir))
    check("is_installed() True after download", sc3.is_installed())
    check("is_user_downloaded() True after download",
          sc3.is_user_downloaded() is True)
    check("needs_update() False right after download",
          sc3.needs_update() is False)
    check("installed_version_hint() == EXPECTED_VERSION",
          sc3.installed_version_hint() == OkapiSidecar.EXPECTED_VERSION)

    # --- "restart": a fresh instance finds the downloaded copy ---
    sc4 = OkapiSidecar()
    check("fresh instance resolves the downloaded copy",
          sc4.sidecar_dir == target and sc4.is_installed(), str(sc4.sidecar_dir))

    # --- old Windows candidate is gone: LOCALAPPDATA untouched ---
    old_win = PROFILE / "AppData" / "Local" / "Supervertaler"
    check("nothing written to <LOCALAPPDATA>/Supervertaler",
          not old_win.exists(), str(old_win))

    print()
    if FAILURES:
        print("P1C-OKAPI-FAIL:", len(FAILURES), "failed —", "; ".join(FAILURES))
        return 1
    print("P1C-OKAPI-OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
