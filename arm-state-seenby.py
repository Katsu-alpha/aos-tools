#
#   arm-state-seenby.py
#
#   show ap arm state をパースし、指定された AP が他のどの AP からどれぐらいの SNR で見えているかを表示
#

import sys
import re
import argparse
import fileinput
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
import pandas as pd


#
#   parse neighbor data and find if target AP is seen by this AP
#
def parse_nbr_data(out, myapn, mych):
    global apn2model, apn2group
    global allctr, allitf
    global COV_SNR
    global enc

    if not re.search(args.pattern, myapn):
        return

    if myapn not in apn2group:
        log.warn(f"AP {myapn} not found in AP database")
        return

    cmd = out[0].strip()
    aos = AOSParser("".join(out), [cmd], encoding=enc)
    tbl = aos.get_table(cmd)
    if tbl is None or len(tbl) == 0:
        return

    for r in tbl[1:]:
        apn = r[0]
        if apn != args.apname:
            continue
        snr = int(r[2])
        pl = int(r[3])
        return (myapn, snr, pl)

    return None


#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show ap tech and display neighbor APs")
    parser.add_argument('infile', help="Input file(s)", type=str)
    parser.add_argument('apname', help="AP name", type=str)
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    parser.add_argument('--band', '-b', help='Radio band', type=str, default='5')
    parser.add_argument('--pattern', '-p', help='regex for AP name', type=str, default='.*')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    #
    #   parse ap database and get apname -> ap model mapping
    #   identiry the encoding - utf-8, shift-jis, mac-roman
    #
    enc = ""
    for enc in ('utf-8', 'shift-jis', 'mac-roman'):
        try:
            aos = AOSParser(args.infile, [AP_DATABASE_LONG_TABLE], merge=True, encoding=enc)
        except UnicodeDecodeError as e:
            continue
        break   # encode success
    else:
        print("unknown encoding, abort.")
        sys.exit(-1)

    ap_database_tbl = aos.get_table(AP_DATABASE_LONG_TABLE)
    if ap_database_tbl is None:
        print("show ap database long output not found.")
        sys.exit(-1)

    for r in ap_database_tbl[1:]:
        apn2model[r[0]] = r[2]
        apn2group[r[0]] = r[1]

    #
    #   parse show ap arm state
    #

    f = fileinput.input(args.infile, encoding=enc)
    for l in f:
        if l.startswith('show ap arm state'):
            break

    out = []
    seenby = []
    apn = ch = ""
    cont = False
    for l in f:
        if cont and l.startswith('Legend: '):
            r = parse_nbr_data(out, apn, ch)
            if r:
                seenby.append(r)
            cont = False
            continue
        elif cont and l.startswith('AP:'):
            r = parse_nbr_data(out, apn, ch)
            if r:
                seenby.append(r)
            cont = False
            # fall through
        elif cont:
            out.append(l)
            continue

        # cont == False
        if not l.startswith('AP:'): continue

        m = re.match(r'AP:([\w-]+) MAC:[0-9a-f:]+ Band:(\w+) Channel:(\d+[SE+-]?)+', l)
        if m:
            apn = m.group(1)
            band = m.group(2)
            if band[0] != args.band:
                continue
            ch = m.group(3)
            cont = True
            out = ["show ap arm state\n"]
            continue

        continue

    seenby.sort(key=lambda x: x[2])   # sort by PathLoss

    print(f'AP "{args.apname}" is seen by:')
    for r in seenby:
        print(f"{r[0]:20} SNR: {r[1]:>3}, PathLoss: {r[2]:>3} dB")


    sys.exit(0)
