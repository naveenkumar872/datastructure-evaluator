"""
Script to update ONLY the email column in the database
from an Excel file - no other data will be modified
"""

import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')

def update_emails_from_excel(excel_file='name_list_E.xlsx'):
    # Read Excel file - skip the first row (empty) and use row 1 as header
    print(f"Reading {excel_file}...")
    df = pd.read_excel(excel_file, header=1)
    
    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]
    
    print(f"Columns found: {df.columns.tolist()}")
    print(f"Total rows: {len(df)}\n")
    
    # Find register number column
    reg_col = None
    for col in df.columns:
        col_lower = str(col).lower()
        if 'register' in col_lower or 'reg' in col_lower:
            reg_col = col
            break
    
    # Find email column
    email_col = None
    for col in df.columns:
        col_lower = str(col).lower()
        if 'email' in col_lower or 'mail' in col_lower:
            email_col = col
            break
    
    if not reg_col or not email_col:
        print("Could not auto-detect columns. Available columns:")
        for i, col in enumerate(df.columns):
            print(f"  {i}: {col}")
        return
    
    print(f"Using columns:")
    print(f"  Register Number: {reg_col}")
    print(f"  Email: {email_col}\n")
    
    # Connect to database
    print("Connecting to PostgreSQL database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Update emails
    updated = 0
    not_found = 0
    skipped = 0
    
    for _, row in df.iterrows():
        username = str(row[reg_col]).strip()
        email = row[email_col]
        
        # Skip if email is empty/NaN
        if pd.isna(email) or str(email).strip() == '':
            skipped += 1
            continue
        
        email = str(email).strip()
        
        # Update only the email column for this username
        cursor.execute(
            "UPDATE users SET email = %s WHERE username = %s",
            (email, username)
        )
        
        if cursor.rowcount > 0:
            updated += 1
            print(f"  ✓ {username}: {email}")
        else:
            not_found += 1
            print(f"  ✗ {username}: not found in database")
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  ✓ Updated: {updated}")
    print(f"  ✗ Not found: {not_found}")
    print(f"  - Skipped (no email): {skipped}")
    print(f"{'='*50}")

if __name__ == '__main__':
    update_emails_from_excel()
