import subprocess
import sys
from pathlib import Path


def download_taco_images():
    
    print("=" * 70)
    print("TACO Images Downloader")
    print("=" * 70)
    
    taco_path = Path("taco_dataset/TACO-master")
    
    if not taco_path.exists():
        print("Error: TACO repository not found!")
        print("Please run: python download_taco.py first")
        return
    
    # Install required package for TACO download script
    print("\nInstalling TACO requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "imagesize"], check=True)
    
    # Run TACO download script
    print("\nDownloading TACO images...")
    print("This will download ~15GB of images")
    print("-" * 70)
    
    download_script = taco_path / "download.py"
    
    if download_script.exists():
        # Run the download script from TACO directory
        import os
        os.chdir(str(taco_path))
        subprocess.run(
            [sys.executable, "download.py"],
            check=True
        )
        
        print("\n" + "=" * 70)
        print("TACO images downloaded!")
        print("=" * 70)
        print("\nNow run: python download_taco.py")
        print("This will convert the dataset to YOLO format")
        
    else:
        print(f"Error: Download script not found at {download_script}")


if __name__ == "__main__":
    download_taco_images()
