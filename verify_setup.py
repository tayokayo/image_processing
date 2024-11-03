import subprocess
import sys
import importlib

def verify_installation():
    required_packages = [
        'flask',
        'torch',
        'cv2',
        'numpy',
        'segment_anything'
    ]
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package} installed successfully")
        except ImportError:
            print(f"❌ {package} not installed properly")
            sys.exit(1)
    
    # Verify SAM model file
    import os
    if os.path.exists('models/sam/sam_vit_h_4b8939.pth'):
        print("✅ SAM model file exists")
    else:
        print("❌ SAM model file missing")
        sys.exit(1)

    print("\n🎉 All dependencies installed successfully!")

if __name__ == "__main__":
    verify_installation()