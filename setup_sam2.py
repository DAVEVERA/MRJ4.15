#!/usr/bin/env python3
"""
setup_sam2.py — SAM2 Model & Dependencies Setup

Downloads and configures SAM2 (Segment Anything Model 2) for MRJ4.15.
Run this once before starting the app: python setup_sam2.py
"""

import os
import sys
import subprocess
from pathlib import Path
import urllib.request
import shutil


def run_cmd(cmd, description=""):
    """Execute a shell command and report status."""
    if description:
        print(f"\n{'='*60}")
        print(f"  {description}")
        print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        return False


def check_python_deps():
    """Check if required Python packages are installed."""
    print("\n🔍 Checking Python dependencies...")
    required = ["torch", "torchvision", "flask", "pillow"]
    missing = []

    for pkg in required:
        try:
            __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} missing")
            missing.append(pkg)

    if missing:
        print(f"\n⚠️  Installing missing packages: {', '.join(missing)}")
        return run_cmd(f"pip install {' '.join(missing)}", "Installing Python packages")
    return True


def install_sam2():
    """Install SAM2 from GitHub."""
    print("\n🔍 Checking SAM2 installation...")
    try:
        import sam2
        print("  ✅ SAM2 already installed")
        return True
    except ImportError:
        print("  ❌ SAM2 not found, installing...")
        cmd = "pip install -e 'git+https://github.com/facebookresearch/sam2.git@main#egg=sam2'"
        return run_cmd(cmd, "Installing SAM2 from GitHub")


def download_model():
    """Download the SAM2 Hiera Large checkpoint."""
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    model_path = models_dir / "sam2_hiera_large.pt"

    if model_path.exists():
        print(f"\n✅ Model already exists: {model_path}")
        return True

    print(f"\n⬇️  Downloading SAM2 Hiera Large model (~2.5 GB)...")
    print(f"   This may take several minutes...")

    url = "https://dl.fbaipublicfiles.com/segment_anything_2/sam2_hiera_large.pt"

    try:
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            pct = min(100, (downloaded / total_size) * 100)
            bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
            print(f"\r   [{bar}] {pct:.1f}%", end="", flush=True)

        urllib.request.urlretrieve(url, model_path, progress_hook)
        print("\n  ✅ Model downloaded successfully")
        return True
    except Exception as e:
        print(f"\n  ❌ Download failed: {e}")
        return False


def verify_setup():
    """Verify that SAM2 is properly set up."""
    print("\n" + "="*60)
    print("  Verifying SAM2 Setup")
    print("="*60)

    models_dir = Path(__file__).parent / "models"
    model_path = models_dir / "sam2_hiera_large.pt"

    checks = [
        ("PyTorch", lambda: __import__("torch") or True),
        ("Torchvision", lambda: __import__("torchvision") or True),
        ("SAM2 package", lambda: __import__("sam2") or True),
        (f"SAM2 model checkpoint", lambda: model_path.exists()),
    ]

    all_good = True
    for name, check_fn in checks:
        try:
            result = check_fn()
            status = "✅" if result else "❌"
            print(f"  {status} {name}")
            if not result:
                all_good = False
        except Exception as e:
            print(f"  ❌ {name} — {e}")
            all_good = False

    return all_good


def main():
    print("\n" + "="*60)
    print("  SAM2 Setup for MRJ4.15")
    print("="*60)
    print("\nThis script will:")
    print("  1. Install Python dependencies (torch, torchvision, etc.)")
    print("  2. Install SAM2 from GitHub")
    print("  3. Download the SAM2 Hiera Large model (~2.5 GB)")

    # Step 1: Check and install Python deps
    if not check_python_deps():
        print("\n⚠️  Some Python packages failed to install.")
        sys.exit(1)

    # Step 2: Install SAM2
    if not install_sam2():
        print("\n⚠️  SAM2 installation failed. Try:")
        print("   pip install -e 'git+https://github.com/facebookresearch/sam2.git@main#egg=sam2'")
        sys.exit(1)

    # Step 3: Download model
    if not download_model():
        print("\n⚠️  Model download failed. You can manually download from:")
        print("   https://dl.fbaipublicfiles.com/segment_anything_2/sam2_hiera_large.pt")
        print("   and place it in: ./models/sam2_hiera_large.pt")
        sys.exit(1)

    # Step 4: Verify
    if verify_setup():
        print("\n" + "="*60)
        print("  ✅ SAM2 Setup Complete!")
        print("="*60)
        print("\nYou can now start the MRJ4.15 app:")
        print("  python app.py")
        print()
        return 0
    else:
        print("\n" + "="*60)
        print("  ❌ Setup verification failed")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
