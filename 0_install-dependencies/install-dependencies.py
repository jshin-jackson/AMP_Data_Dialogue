import subprocess
import sys

print("############ Installing python modules")
subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
subprocess.run([
    sys.executable, "-m", "pip", "install",
    "--no-cache-dir",
    "--log", "/home/cdsw/AMP_Data_Dialogue/0_install-dependencies/pip-req.log",
    "-r", "/home/cdsw/AMP_Data_Dialogue/0_install-dependencies/requirements.txt"
], check=True)

print("############ Creating sample SQLite database")
subprocess.run([sys.executable, "/home/cdsw/AMP_Data_Dialogue/0_install-dependencies/create-sample-db.py"], check=True)
