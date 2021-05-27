#/usr/bin/python3 -u
#
#   ap2xls.py
#
#   Join 'show ap database' and 'show ap active' tables and write the result to an MS Excel file
#

import sys
import argparse
import pandas as pd
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Join 'show ap database' and 'show ap active' tables and write the result to an MS Excel file")
    parser.add_argument('infile', help="Input file containing 'show ap database long' and 'show ap active' output", type=str, nargs=1)
    parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    if args.outfile == '':
        xlsfile = 'ap-table.xlsx'
    else:
        xlsfile = args.outfile

    #
    #   parse AP tables
    #
    print("Parsing files ... ", end="")
    aos = AOSParser(args.infile, [AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE])
    ap_database_tbl = aos.get_table(AP_DATABASE_LONG_TABLE)
    ap_active_tbl   = aos.get_table(AP_ACTIVE_TABLE)
    if ap_database_tbl is None:
        print("show ap database long output not found.")
        sys.exit(-1)
    if ap_active_tbl is None:
        print("show ap active output not found.")
        sys.exit(-1)
    print("done.")

    #
    #   table join & sort
    #
    df_ap_database = pd.DataFrame(ap_database_tbl[1:], columns=ap_database_tbl[0])
    df_ap_act      = pd.DataFrame(ap_active_tbl[1:], columns=ap_active_tbl[0])

    df1 = df_ap_database.merge(df_ap_act[[
        'Name', 'Radio 0 Band Ch/EIRP/MaxEIRP/Clients', 'Radio 1 Band Ch/EIRP/MaxEIRP/Clients',
        'Radio 2 Band Ch/EIRP/MaxEIRP/Clients',
    ]], how="left", left_on="Name", right_on="Name")
    df2 = df1[[
        'Name', 'Group', 'AP Type', 'IP Address', 'Switch IP', 'Serial #',
        'Radio 0 Band Ch/EIRP/MaxEIRP/Clients', 'Radio 1 Band Ch/EIRP/MaxEIRP/Clients',
        'Radio 2 Band Ch/EIRP/MaxEIRP/Clients',
    ]]
    df = df2.sort_values(['Group', 'Name'])


    #
    #   Create Excel
    #
    wb = Workbook()
    ws = wb.active
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    f = Font(name='Consolas')
    for row in ws.iter_rows(min_row=1):
        for cell in row:
            cell.font = f

    widths = [25, 20, 10, 20, 20, 13, 35, 35, 35]
    for i,w in enumerate(widths):
        ws.column_dimensions[chr(65+i)].width = w

    f = Font(name='Arial', bold=True, size=9)
    s = PatternFill(fgColor="BDD7EE", fill_type="solid")
    for cell in ws['A1':'I1'][0]:
        cell.fill = s
        cell.font = f

    ws.auto_filter.ref = "A:I"
    ws.freeze_panes = "A2"


    #
    #   output to file
    #
    print(f"Writing to {xlsfile} ... ", end="")
    wb.save(xlsfile)
    print("done.")

    sys.exit(0)
