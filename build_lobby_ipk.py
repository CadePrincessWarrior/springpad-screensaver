import os
import io
import json
import tarfile
import time

# Lobby build — packages lobby.html as its OWN webOS app so it can be installed
# alongside com.springpad.screensaver (they don't collide). Mirrors the structure
# of build_webos_ipk.py; the lobby appinfo.json is generated inline here so it
# doesn't overwrite the screensaver's appinfo.json on disk.

APP_ID = "com.springpad.lobby"
APP_VERSION = "1.0.0"
IPK_FILENAME = f"{APP_ID}_{APP_VERSION}_all.ipk"

APPINFO = {
    "id": APP_ID,
    "version": APP_VERSION,
    "type": "web",
    "main": "lobby.html",
    "title": "SpringPad Lobby",
    "icon": "icon.png",
    "largeIcon": "largeIcon.png",
    "vendor": "SpringPad",
    "resolution": "1920x1080",
    "disableBackHistoryAPI": True,
    "handlesBackKey": True,
}


def make_ar_header(name, size):
    """Creates a 60-byte ar archive header for debian ipk files."""
    name_field = name.ljust(16)[:16]
    mtime_field = str(int(time.time())).ljust(12)[:12]
    owner_field = "0".ljust(6)[:6]
    group_field = "0".ljust(6)[:6]
    mode_field = "100644".ljust(8)[:8]
    size_field = str(size).ljust(10)[:10]
    magic_field = "`\n"

    header_str = f"{name_field}{mtime_field}{owner_field}{group_field}{mode_field}{size_field}{magic_field}"
    return header_str.encode('ascii')


def create_control_tar_gz():
    """Generates control.tar.gz containing package metadata."""
    control_content = f"""Package: {APP_ID}
Version: {APP_VERSION}
Section: misc
Priority: optional
Architecture: all
Maintainer: SpringPad
Description: SpringPad lobby welcome + live Lincoln weather display for LG webOS TV
""".encode('utf-8')

    out_buf = io.BytesIO()
    with tarfile.open(fileobj=out_buf, mode='w:gz') as tar:
        ti = tarfile.TarInfo(name='./control')
        ti.size = len(control_content)
        ti.mtime = int(time.time())
        ti.mode = 0o644
        tar.addfile(ti, io.BytesIO(control_content))

    return out_buf.getvalue()


def create_data_tar_gz(base_dir):
    """Generates data.tar.gz with the app files under /usr/palm/applications/<APP_ID>/."""
    out_buf = io.BytesIO()
    app_rel_path = f"./usr/palm/applications/{APP_ID}"

    with tarfile.open(fileobj=out_buf, mode='w:gz') as tar:
        # appinfo.json — generated inline (lobby-specific, main=lobby.html)
        appinfo_bytes = (json.dumps(APPINFO, indent=2) + "\n").encode('utf-8')
        ti = tarfile.TarInfo(name=f"{app_rel_path}/appinfo.json")
        ti.size = len(appinfo_bytes)
        ti.mtime = int(time.time())
        ti.mode = 0o644
        tar.addfile(ti, io.BytesIO(appinfo_bytes))
        print(f"  + Generated appinfo.json (main=lobby.html) -> {app_rel_path}/appinfo.json")

        # App files from disk
        files_to_include = ['lobby.html', 'icon.png', 'largeIcon.png']
        for file in files_to_include:
            filepath = os.path.join(base_dir, file)
            if os.path.exists(filepath):
                arcname = f"{app_rel_path}/{file}"
                tar.add(filepath, arcname=arcname)
                print(f"  + Added {file} -> {arcname}")
            else:
                print(f"  ! MISSING {file} (skipped)")

    return out_buf.getvalue()


def build_ipk(base_dir):
    print(f"Building LG webOS App Package ({IPK_FILENAME})...")

    debian_binary = b"2.0\n"
    control_tar_gz = create_control_tar_gz()
    data_tar_gz = create_data_tar_gz(base_dir)

    ar_magic = b"!<arch>\n"
    out_ipk_path = os.path.join(base_dir, IPK_FILENAME)
    with open(out_ipk_path, 'wb') as f:
        f.write(ar_magic)

        f.write(make_ar_header('debian-binary', len(debian_binary)))
        f.write(debian_binary)
        if len(debian_binary) % 2 != 0:
            f.write(b"\n")

        f.write(make_ar_header('control.tar.gz', len(control_tar_gz)))
        f.write(control_tar_gz)
        if len(control_tar_gz) % 2 != 0:
            f.write(b"\n")

        f.write(make_ar_header('data.tar.gz', len(data_tar_gz)))
        f.write(data_tar_gz)
        if len(data_tar_gz) % 2 != 0:
            f.write(b"\n")

    print(f"\nSuccessfully created LG webOS app package:")
    print(f"Location: {out_ipk_path}")
    print(f"Package Size: {os.path.getsize(out_ipk_path):,} bytes")
    return out_ipk_path


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    build_ipk(current_dir)
