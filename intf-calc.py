#
#   intf-calc.py
#
#   AP-535 の show ap debug radio-info をパースし、co-ch intf(%) を表示
#

import sys
import re
import argparse
import fileinput
import datetime
import pandas as pd
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


def list2str(l):
    s = ""
    for i in l:
        s += f"{i:>5}"
    return s

def past10sec(s):
    ti = datetime.datetime.fromisoformat("2023-01-01 " + s)
    ti -= datetime.timedelta(seconds=10)
    return ti.strftime('%H:%M:%S')

parser = argparse.ArgumentParser(
    description="Parse 'show ap debug radio-info' and calculate co-channel CCA(%)")
parser.add_argument('infile', help="Input file containing 'show ap debug radio-info output", type=str, nargs='+')
#parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
parser.add_argument('--debug', help='Enable debug log', action='store_true')
args = parser.parse_args()


f = fileinput.input(args.infile, encoding='utf-8')
f_it = iter(f)
apn = ""

while True:
    try:
        l = next(f_it)
    except StopIteration:
        break

    if l.startswith('show ap debug radio-info ap-name'):
        r = re.search(r'ap-name "(.*)"', l)
        if r:
            apn = r.group(1)
        continue

    if l.startswith('aruba_dbg_radio_info_0 Start time:'):
        st = l[35:].rstrip()
        r = re.search('\w+ (\w+ \d+) (\d\d:\d\d:\d\d)', st)
        if r:
            date = r.group(1)
            time = r.group(2)
        continue

    if l.startswith('wifi0     phy_stats:0'):
        _ = next(f_it)

        tx = next(f_it)
        tx = list(map(int, re.split(r' +', tx[40:].strip())))

        rx = next(f_it)
        rx = list(map(int, re.split(r' +', rx[40:].strip())))

        rx_tome = next(f_it)
        rx_tome = list(map(int, re.split(r' +', rx_tome[40:].strip())))

        ch_busy = next(f_it)
        ch_busy = list(map(int, re.split(r' +', ch_busy[40:].strip())))

        _ = next(f_it)
        intf = next(f_it)
        intf = list(map(int, re.split(r' +', intf[40:].strip())))

        coch = []
        for a, b in zip(rx, rx_tome):
            coch.append(a-b)

        tot_intf = []
        for a, b in zip(intf, coch):
            tot_intf.append(a+b)

        continue

    if l.startswith('Noise Floor History at Home Channel:') and tx is not None:
        ch = l[37:].strip()
        print(f"File: {fileinput.filename()}")
        # print(f"AP: {apn} Ch: {ch}  Time: {date} {past10sec(time)} - {time}")
        print(f"AP Name: {apn}")
        print(f"Channel: {ch}")
        print(f"Time:    {date} {past10sec(time)} - {time}")
        print("------------------")
        print("Tx                              " + list2str(tx))
#        print("Rx                       " + list2str(rx))
        print("Rx to me                        " + list2str(rx_tome))
        print("Ch Busy                         " + list2str(ch_busy))
        print("Intf (non-wifi + adj. ch wifi)  " + list2str(intf))
        print("Co-ch Wi-Fi Intf                " + list2str(coch))
        print("Total interference              " + list2str(tot_intf))
        print()
        tx = None