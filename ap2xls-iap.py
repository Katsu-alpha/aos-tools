#
#   ap2xls-iap.py
#
#   show tech-support をパースし、以下の情報を Excel に書き出し
#       AP Name, Model, IP
#       各Radioについて、Channel, Clients, Util, Noise, Intf
#

import re
import argparse
import sys
import mylogger as log
import pandas as pd
from aos_parser import AOSParser
from collections import defaultdict
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


def avg(it):
    s = 0
    n = 0
    for v in it:
        s += v
        n += 1
    return s//n if n > 0 else 0

parser = argparse.ArgumentParser(
    description="Parse IAP tech-support and generate Excel file")
parser.add_argument('infiles', help="Input file(s) containing 'show tech-support' output", type=str, nargs='+')
parser.add_argument('--debug', help='Enable debug log', action='store_true')
args = parser.parse_args()

xlsfile = 'aplist.xlsx'

if args.debug:
    log.setloglevel(log.LOG_DEBUG)
else:
    log.setloglevel(log.LOG_INFO)

cmds = ['show ap association', 'show ap bss-table']


aps = set()

numsta = defaultdict(lambda: defaultdict(int))
htmode = defaultdict(lambda: defaultdict(str))

channel = defaultdict(lambda: defaultdict(str))
eirp = defaultdict(lambda: defaultdict(str))

uptime = defaultdict(str)
ibss = defaultdict(lambda: defaultdict(int))
obss = defaultdict(lambda: defaultdict(int))
intf = defaultdict(lambda: defaultdict(int))

nf = defaultdict(lambda: defaultdict(int))
busy = defaultdict(lambda: defaultdict(int))

model = defaultdict(str)
for fn in args.infiles:
    print(f"Processing {fn}")

    aos = AOSParser(fn, cmds)

    assoc_tbl = aos.get_table(cmds[0], 'assoc', 'phy')
    if assoc_tbl is None:
        assoc_tbl = []
    bss_tbl = aos.get_table(cmds[1], 'band/ht-mode/bandwidth', 'ch/EIRP/max-EIRP', 'ap name')
    if bss_tbl is None:
        print("show ap bss-table output not found.")
        continue

    #   parse bss-table and get AP Name, HT mode, Ch, EIRP
    maxbw = defaultdict(lambda: defaultdict(int))
    for r in bss_tbl:
        band_cbw, ch_eirp, apn = r
        m = re.match(r'([\d.]+)GHz/(\w+)/(\d+)MHz', band_cbw)
        if not m:
            print(f"Invalid band/ht-mode/bandwidth: {band_cbw}")
            sys.exit(1)
        cbw = int(m.group(3))
        band = m.group(1)[0]   # "5GHz" -> '5'
        if cbw <= maxbw[band][apn]:
            continue
        maxbw[band][apn] = cbw
        htmode[band][apn] = m.group(2)
        channel[band][apn], eirp[band][apn] = ch_eirp.split('/')[:2]

    if apn in aps:
        print(f"Duplicate AP Name found: {apn}")
        sys.exit(1)

    aps.add(apn)
    for r in assoc_tbl:
        assoc, phy = r
        if assoc != 'y':
            continue
        if phy[0] in ('2', '5', '6'):
            numsta[phy[0]][apn] += 1


    pat = re.compile(r"(^AP Uptime$|^CCA stats history:|show ap debug radio-stats|show version)")
    #
    #   parse file line by line
    #
    f = open(fn, 'r', encoding='macroman')
    while (l := f.readline()):
        if not pat.search(l):
            continue

        if l.startswith("AP Uptime"):
            _ = f.readline()   # skip next line
            uptime[apn] = f.readline().strip()
            continue

        if l.startswith("CCA stats history:"):
            if "wifi0" in l:
                radio = '5'
            elif "wifi1" in l:
                radio = '2'
            else:
                continue
            while True:
                l = f.readline()
                if l.startswith("ibss: "):
                    ibss[radio][apn] = avg(map(int, l[5:].strip().split()))     # max -> avg
                    continue
                if l.startswith("obss: "):
                    obss[radio][apn] = avg(map(int, l[5:].strip().split()))     # max -> avg
                    continue
                if l.startswith("intf: "):
                    intf[radio][apn] = avg(map(int, l[5:].strip().split()))     # max -> avg
                    break
            continue

        if "show ap debug radio-stats" in l:
            if "radio-stats 0" in l:
                radio = '5'
            elif "radio-stats 1" in l:
                radio = '2'
            else:
                continue
            while True:
                l = f.readline()
                if l.startswith("Current Noise Floor"):
                    nf[radio][apn] = -int(l.split()[-1])
                    continue
                if l.startswith("Channel Busy 64s"):
                    busy[radio][apn] = int(l.split()[-1])
                    break
            continue

        if "show version" in l:
            for _ in range(3):
                l = f.readline()
                if m:=re.search(r"MODEL: ([\w\d]+)", l):
                    model[apn] = m.group(1).strip()
                    break
            continue


#
#   Create a dataframe
#

tbl = []
for apn in sorted(aps):
    row = [apn, model[apn], uptime[apn], 
            htmode['5'][apn], eirp['5'][apn], channel['5'][apn], numsta['5'][apn], busy['5'][apn], obss['5'][apn], intf['5'][apn], nf['5'][apn],
            htmode['2'][apn], eirp['2'][apn], channel['2'][apn], numsta['2'][apn], busy['2'][apn], obss['2'][apn], intf['2'][apn], nf['2'][apn],
            ]
    tbl.append(row)

df = pd.DataFrame(tbl, columns=['AP Name', 'Model', 'Uptime',
                                # '5GHz Mode', '5GHz EIRP(dBm)', '5GHz Ch', '5GHz Clients', '5GHz Util%', '5GHz OBSS%', '5GHz Intf%', '5GHz NF(dBm)',
                                # '2GHz Mode', '2GHz EIRP(dBm)', '2GHz Ch', '2GHz Clients', '2GHz Util%', '2GHz OBSS%', '2GHz Intf%', '2GHz NF(dBm)',
                                'Mode', 'EIRP(dBm)', 'Channel', 'Clients', 'Util(%)', '他BSS(%)', '干渉(%)', 'ノイズ(dBm)',
                                'Mode', 'EIRP(dBm)', 'Channel', 'Clients', 'Util(%)', '他BSS(%)', '干渉(%)', 'ノイズ(dBm)',
                                ])


#
#   Write to Excel
#
wb = Workbook()
ws = wb.active
for r in dataframe_to_rows(df, index=False, header=True):
    ws.append(r)

f = Font(name='Consolas')
for row in ws.iter_rows(min_row=1):
    for cell in row:
        cell.font = f

widths = [25, 10, 30,   10, 10, 10,    10, 10, 10, 10,   10, 10, 10,   10, 10, 10, 10]
for i,w in enumerate(widths):
    ws.column_dimensions[chr(65+i)].width = w

f = Font(name='Arial', bold=True, size=9)
Ses = PatternFill(fgColor="BDD7EE", fill_type="solid")
for cell in ws['A1':'S1'][0]:
    cell.fill = Ses
    cell.font = f

ws.auto_filter.ref = "A:S"
ws.freeze_panes = "A2"


#
#   output to file
#
print(f"Writing to {xlsfile} ... ", end="")
wb.save(xlsfile)
print("done.")

sys.exit(0)
