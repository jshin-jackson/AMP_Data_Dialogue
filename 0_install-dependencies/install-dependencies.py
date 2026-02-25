
print("############ Installing python modules")
!pip install --upgrade pip
!pip install --no-cache-dir --log /home/cdsw/0_install-dependencies/pip-req.log -r /home/cdsw/0_install-dependencies/requirements.txt

print("############ Creating sample SQLite database")
!python3 /home/cdsw/0_install-dependencies/create-sample-db.py
