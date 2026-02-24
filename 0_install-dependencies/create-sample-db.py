from langchain_community.utilities import SQLDatabase

import sqlite3
import csv
import os

def load_csv_into_sqlite(db_name, csv_file_path, table_name):
  conn = None
  try:
      conn = sqlite3.connect(db_name)
      cursor = conn.cursor()

      with open(csv_file_path, 'r', encoding='utf-8') as file:
          csv_reader = csv.reader(file)
          header = next(csv_reader)  # Read the header row

          # Construct the INSERT statement dynamically
          columns = ", ".join(header)
          placeholders = ", ".join("?" * len(header))
          insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

          # Prepare data for insertion
          data_to_insert = []
          for row in csv_reader:
              # Basic validation: ensure row has the same number of columns as header
              if len(row) == len(header):
                  data_to_insert.append(row)
              else:
                  print(f"Skipping malformed row: {row} (Column count mismatch)")

          # Use executemany for efficient bulk insertion
          cursor.executemany(insert_sql, data_to_insert)
          conn.commit()
          print(f"Successfully loaded data from '{csv_file_path}' into table '{table_name}'.")

  except FileNotFoundError:
      print(f"Error: CSV file not found at '{csv_file_path}'.")
  except sqlite3.OperationalError as e:
      print(f"SQLite Operational Error (e.g., table not found, column mismatch): {e}")
      print(f"Attempted SQL: {insert_sql}")
  except Exception as e:
      print(f"An unexpected error occurred during data loading: {e}")
  finally:
      if conn:
          conn.close()


def create_sqlite_database(db_name="sample_sqlite.db"):
  conn = None
  try:
      conn = sqlite3.connect(db_name)
      cursor = conn.cursor()

      # DDL statements adjusted for SQLite compatibility
      # ENUM types are converted to VARCHAR with CHECK constraints

      # Table: district
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS district (
              district_id INTEGER NOT NULL PRIMARY KEY,
              city VARCHAR(50) NOT NULL,
              state_name VARCHAR(50) NOT NULL,
              state_abbrev VARCHAR(50) NOT NULL,
              region VARCHAR(50) NOT NULL,
              division VARCHAR(50) NOT NULL              
          );
      """)

      # Table: account
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS account (
              account_id VARCHAR NOT NULL,
              district_id INTEGER NOT NULL,
              frequency VARCHAR NOT NULL CHECK(frequency IN ('Issuance After Transaction', 'Monthly Issuance', 'Weekly Issuance')),
              date TEXT NOT NULL
          );
      """)

      # Table: client
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS client (
              client_id VARCHAR NOT NULL PRIMARY KEY,
              sex VARCHAR NOT NULL,
              fulldate TEXT NOT NULL,
              day INTEGER NOT NULL,
              month INTEGER NOT NULL,
              year INTEGER NOT NULL,
              age INTEGER NOT NULL,
              social VARCHAR NOT NULL,
              first VARCHAR NOT NULL,
              middle VARCHAR NULL,
              last VARCHAR NOT NULL,
              phone INTEGER NOT NULL,
              email VARCHAR NOT NULL,
              address_1 VARCHAR NOT NULL,
              address_2 VARCHAR NULL,
              city VARCHAR NOT NULL,
              state VARCHAR NOT NULL,
              zipcode VARCHAR NOT NULL,
              district_id INTEGER NOT NULL
              );
      """)


      # Table: disposition
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS disposition (
              disp_id VARCHAR(10) NOT NULL PRIMARY KEY,
              client_id VARCHAR(10) NOT NULL,
              account_id VARCHAR(10) NULL,
              disp_type VARCHAR(50) NULL
          );
      """)

      # Table: card
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS card (
              card_id VARCHAR(50) NOT NULL PRIMARY KEY,
              disp_id VARCHAR(50) NOT NULL,
              card_type VARCHAR NOT NULL CHECK(card_type IN ('VISA Signature', 'VISA Standard', 'VISA Infinite')),
              year INTEGER NOT NULL,
              month INTEGER NOT NULL,
              day INTEGER NOT NULL,
              fulldate TEXT NOT NULL 
          );
      """)

      # Table: loan
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS loan (
              loan_id VARCHAR(50) NOT NULL,
              account_id VARCHAR(50) NOT NULL,
              amount INTEGER NOT NULL,
              duration INTEGER NOT NULL,
              payments INTEGER NOT NULL,
              status VARCHAR(50) NOT NULL,
              year INTEGER NOT NULL,
              month INTEGER NOT NULL,
              day INTEGER NOT NULL,
              fulldate TEXT NOT NULL,
              location INTEGER NOT NULL,
              purpose VARCHAR(50) NOT NULL
          );
      """)

      # Table: CRMCallCenterLogs
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS CRMCallCenterLogs (
              Date_received VARCHAR(50) NOT NULL,
              Complaint_ID VARCHAR(50) NOT NULL,
              rand_client VARCHAR(50) NULL,
              phonefinal VARCHAR(50) NULL,
              vru_line VARCHAR(50) NULL,
              call_id INTEGER NULL,
              priority INTEGER NULL,
              complaint_type VARCHAR(50) NULL,
              outcome VARCHAR(50) NULL,
              server VARCHAR(50) NULL,
              ser_start VARCHAR(50) NOT NULL,
              ser_exit VARCHAR(50) NOT NULL,
              ser_time VARCHAR(50) NOT NULL
          );
      """)

      # Table: order (still quoted as "order" is also a reserved keyword)
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS "order" (
              order_id INTEGER NOT NULL PRIMARY KEY,
              account_id VARCHAR(50) NOT NULL,
              bank_to VARCHAR(50) NOT NULL,
              account_to INTEGER NOT NULL,
              amount INTEGER NOT NULL,
              k_symbol VARCHAR(50) NULL,
              FOREIGN KEY (account_id) REFERENCES account(account_id) ON DELETE CASCADE
          );
      """)

      # Table: CRMEvents
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS CRMEvents (
              Date_received TEXT NOT NULL,
              Product VARCHAR(50) NOT NULL,
              Sub_product VARCHAR(50) NULL,
              Issue VARCHAR(50) NOT NULL,
              Sub_issue VARCHAR(50) NOT NULL,
              Consumer_complaint_narrative VARCHAR(20000) NULL,
              Tags VARCHAR(50) NULL,
              Consumer_consent_provided VARCHAR(50) NULL,
              Submitted_via VARCHAR(50) NULL,
              Date_sent_to_company VARCHAR(50) NULL,
              Company_response_to_consumer VARCHAR(50) NULL,
              Timely_response VARCHAR(50) NULL,
              Consumer_disputed VARCHAR(50) NULL,
              Complaint_ID VARCHAR(50) NOT NULL PRIMARY KEY,
              Client_ID VARCHAR(50) NULL,
              createdAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
          );
      """)


      # Table: CRMReviews
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS CRMReviews (
              reviewId INTEGER PRIMARY KEY AUTOINCREMENT,
              Date TEXT NOT NULL,
              Stars INTEGER NOT NULL,
              Reviews VARCHAR NULL,
              Product VARCHAR(50) NOT NULL,
              district_id INTEGER NOT NULL
          );
      """)

      # Table: bank_transactions (renamed from 'transaction')
      cursor.execute("""
          CREATE TABLE IF NOT EXISTS bank_transactions (
              trans_id VARCHAR(50) NOT NULL PRIMARY KEY,
              account_id VARCHAR(50) NOT NULL,
              transaction_type VARCHAR(50) NOT NULL,
              operation VARCHAR(50) NULL,
              amount INTEGER NOT NULL,
              balance INTEGER NOT NULL,
              k_symbol VARCHAR(50) NULL,
              bank VARCHAR(50) NULL,
              account VARCHAR(50) NULL,
              date TEXT NULL,
              fulldatewithtime VARCHAR(50) NULL
          );
      """)

      conn.commit()
      print(f"Database '{db_name}' and tables created successfully with updated naming conventions.")

  except sqlite3.Error as e:
      print(f"An error occurred during database creation: {e}")
  finally:
      if conn:
          conn.close()

db = "/home/cdsw/sample_sqlite.db"

if os.path.exists(db):
    os.remove(db)

create_sqlite_database(db)
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/01_account.csv", "account")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/02_district.csv", "district")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/03_account.csv", "account")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/04_card.csv", "card")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/05_client.csv", "client")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/06_crmcallcentrelog.csv", "CRMCallCenterLogs")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/07_crmevents.csv", "CRMEvents")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/08_crmreviews.csv", "CRMReviews")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/09_disposition.csv", "disposition")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/10_loan.csv", "loan")
load_csv_into_sqlite(db, "/home/cdsw/0_install-dependencies/sample_data_csv/11_transaction.csv", "bank_transactions")