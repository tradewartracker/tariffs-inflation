"""
download_detail_data.py — One-time download of BEA 402-commodity detail IO tables.

Downloads and caches the following files into data/io_detail/:
    Supply_2017_DET.xlsx          — import shares per commodity
    CxC_TR_2017_PRO_DET.xlsx      — pre-computed Leontief inverse (402×402)
    PCEBridge_Detail.xlsx         — detail PCE bridge (commodity → PCE category)

Run once before using pipeline_detail.py.  Skips files that already exist.
"""

import io
import os
import zipfile

import requests

DEST_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "data", "io_detail")

SUP_ZIP_URL = (
    "https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesSUP.zip"
)
PCE_BRIDGE_URL = (
    "https://apps.bea.gov/industry/release/xlsx/PCEBridge_Detail.xlsx"
)

# Files to extract from the SUP zip
ZIP_EXTRACT = [
    "Supply_2017_DET.xlsx",
    "CxC_TR_2017_PRO_DET.xlsx",
]


def download_detail_data(dest_dir: str = DEST_DIR) -> None:
    os.makedirs(dest_dir, exist_ok=True)

    # ── Files from AllTablesSUP.zip ──────────────────────────────────────────
    needed_from_zip = [
        f for f in ZIP_EXTRACT
        if not os.path.exists(os.path.join(dest_dir, f))
    ]
    if needed_from_zip:
        print(f"Downloading AllTablesSUP.zip ({len(needed_from_zip)} files needed)...")
        r = requests.get(SUP_ZIP_URL)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            for name in needed_from_zip:
                print(f"  Extracting {name}")
                data = zf.read(name)
                with open(os.path.join(dest_dir, name), "wb") as f:
                    f.write(data)
    else:
        print("Supply-Use zip files already present, skipping download.")

    # ── PCE Bridge Detail ────────────────────────────────────────────────────
    pce_path = os.path.join(dest_dir, "PCEBridge_Detail.xlsx")
    if not os.path.exists(pce_path):
        print("Downloading PCEBridge_Detail.xlsx...")
        r = requests.get(PCE_BRIDGE_URL)
        r.raise_for_status()
        with open(pce_path, "wb") as f:
            f.write(r.content)
    else:
        print("PCEBridge_Detail.xlsx already present, skipping download.")

    print(f"\nAll detail data files cached in {dest_dir}/")
    for name in ZIP_EXTRACT + ["PCEBridge_Detail.xlsx"]:
        path = os.path.join(dest_dir, name)
        size = os.path.getsize(path) / 1024 / 1024
        print(f"  {name:40s}  {size:.1f} MB")


if __name__ == "__main__":
    download_detail_data()
