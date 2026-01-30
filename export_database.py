"""
Database Export Script
Exports all tables from the connected PostgreSQL database to CSV or Excel
"""

import os
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL')

def export_database(format='excel'):
    """
    Export database tables to CSV or Excel
    format: 'excel' or 'csv'
    """
    print("Connecting to PostgreSQL database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = [t[0] for t in cursor.fetchall()]
    print(f"Tables found: {tables}\n")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    exported_files = []

    if format == 'excel':
        # Export all tables to a single Excel file with multiple sheets
        output_file = f'database_export_{timestamp}.xlsx'
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for table in tables:
                cursor.execute(f'SELECT * FROM {table}')
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                df = pd.DataFrame(rows, columns=columns)
                df.to_excel(writer, sheet_name=table, index=False)
                print(f"  ✓ {table}: {len(df)} rows, {len(columns)} columns")
        
        exported_files.append(output_file)
        print(f"\n✅ Database exported to: {output_file}")
    
    elif format == 'csv':
        # Export each table to a separate CSV file
        for table in tables:
            cursor.execute(f'SELECT * FROM {table}')
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            df = pd.DataFrame(rows, columns=columns)
            output_file = f'{table}_{timestamp}.csv'
            df.to_csv(output_file, index=False, encoding='utf-8')
            exported_files.append(output_file)
            print(f"  ✓ {table}: {len(df)} rows → {output_file}")
        
        print(f"\n✅ Exported {len(tables)} CSV files")

    conn.close()
    return exported_files

if __name__ == '__main__':
    import sys
    
    # Default to Excel, or use command line argument
    fmt = 'excel'
    if len(sys.argv) > 1:
        fmt = sys.argv[1].lower()
        if fmt not in ['excel', 'csv']:
            print("Usage: python export_database.py [excel|csv]")
            print("  excel - Export all tables to a single .xlsx file (default)")
            print("  csv   - Export each table to separate .csv files")
            sys.exit(1)
    
    export_database(format=fmt)
