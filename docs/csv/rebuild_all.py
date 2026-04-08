"""Rebuild all 3 Excel files after running the individual build scripts with updated tiers."""
import subprocess, sys, os

PY = r"c:\Users\nicho\AppData\Local\Programs\Python\Python3127\python.exe"
DIR = r"c:\Users\nicho\OneDrive\Documents\GitHub\data-acq-functional-SophistryDude\Securities_prediction_model\docs\csv"

scripts = [
    "build_competitive_matrix.py",
    "build_bifurcation_matrix.py",
    "build_vs_all_competitors.py",
]

for script in scripts:
    path = os.path.join(DIR, script)
    print(f"\n{'='*60}")
    print(f"Running {script}...")
    print(f"{'='*60}")
    result = subprocess.run([PY, path], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
    else:
        print("OK")
