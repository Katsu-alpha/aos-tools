#!/usr/bin/python3 -u
#
#   show airmatch event radar パース
#

import sys
import argparse
import re
import mylogger as log
from aos_parser import AOSParser
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="parse tech-support and display client stats")
    parser.add_argument('files', type=str, nargs='*')
    parser.add_argument('--debug', help='debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    #
    #   parse datapath session table
    #
    #radar_cmd = "show airmatch event radar all-aps"
    radar_cmd = "show airmatch event radar .+"
    aos = AOSParser(args.files, radar_cmd, merge=True)

    #
    #   collect stats
    #
    radar_num = {}
    radar_ch = {}
    for r in aos.get_table(radar_cmd, "APName", "Chan"):
        apn, ch = r
        ch = int(ch)
        try:
            radar_num[apn] += 1
        except KeyError:
            radar_num[apn] = 1
            radar_ch[apn] = {}

        try:
            radar_ch[apn][ch] += 1
        except KeyError:
            radar_ch[apn][ch] = 1

    #
    #   create Excel
    #
    wb = Workbook()
    ws = wb.active

    dfs_ch = [52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140]
    ws.append(["AP Name"] + dfs_ch + ["Total"])

    for apn in sorted(radar_num.keys(), key=lambda x:radar_num[x], reverse=True):
        #print(f"{apn:28}{radar_num[apn]} : ")
        if radar_num[apn] <= 4:
            break
        nums = [radar_ch[apn][ch] if ch in radar_ch[apn] else 0 for ch in dfs_ch]
        ws.append([apn] + nums)

    #
    #   apply styles
    #
    ws.column_dimensions['A'].width = 21
    for col in "BCDEFGHIJKLMNOP":
        ws.column_dimensions[col].width = 5

    f = Font(name='Calibri')
    for row in ws.iter_rows():
        for cell in row:
            cell.font = f

    f = Font(name='Calibri', bold=True)
    Ses = PatternFill(fgColor="BDD7EE", fill_type="solid")
    for cell in ws[1]:
        cell.font = f
        cell.fill = Ses

    f1 = PatternFill(fgColor="FFE5E8", fill_type="solid")
    f2 = PatternFill(fgColor="FFC7CE", fill_type="solid")
    f3 = PatternFill(fgColor="FDB58D", fill_type="solid")
    f4 = PatternFill(fgColor="FF6600", fill_type="solid")
    for row in ws.iter_rows(min_row=2, min_col=2, max_col=16):
        for cell in row:
            if cell.value >= 20:
                cell.fill = f4
            elif cell.value >= 10:
                cell.fill = f3
            elif cell.value >= 5:
                cell.fill = f2
            elif cell.value > 0:
                cell.fill = f1

    print(f"max_row={ws.max_row}")

    for row in range(2,ws.max_row+1):
        rs = str(row)
        sum = f"=SUM(B{rs}:P{rs})"
        ws["Q" + rs] = sum

    rs1 = str(ws.max_row)
    rs2 = str(ws.max_row+1)
    f = Font(name='Calibri')
    for col in "BCDEFGHIJKLMNOP":
        sum = f"=SUM({col}2:{col}{rs1})"
        ws[col+rs2] = sum
        ws[col+rs2].font = f


    wb.save("radar-stats.xlsx")

    sys.exit(0)

