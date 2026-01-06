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



# Print iterations progress
def printProgressBar (iteration, total, prefix = 'Progress:', suffix = 'Complete', decimals = 0, length = 50, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


#
#   parse neighbor data and find if target AP is seen by this AP
#
def parse_nbr_data(out, myapn, mych):
    if not re.search(args.pattern, myapn):
        return

    cmd = out[0].strip()
    aos = AOSParser("".join(out), [cmd])
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
    for enc in ('utf-8', 'shift-jis', 'mac-roman'):
        try:
            aos = AOSParser(args.infile, [AP_DATABASE_LONG_TABLE], merge=True, encoding=enc)
        except UnicodeDecodeError as e:
            continue
        break   # encode success
    else:
        print("unknown encoding, abort.")
        sys.exit(-1)


    #
    #   parse show ap arm state
    #
    f = fileinput.input(args.infile, encoding=enc)
    for l in f:
        if l.startswith('show ap arm state'):
            break
    arm_state = []
    for l in f:
        if l.startswith('show '):
            break
        arm_state.append(l)

    total = len(arm_state)
    out = []
    seenby = []
    apn = ch = ""
    cont = False
    for i, l in enumerate(arm_state, 1):
        if cont and l.startswith('Legend: '):
            r = parse_nbr_data(out, apn, ch)
            printProgressBar(i, total)
            if r:
                seenby.append(r)
            cont = False
            continue
        elif cont and l.startswith('AP:'):
            r = parse_nbr_data(out, apn, ch)
            printProgressBar(i, total)
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

    printProgressBar(i, total)  # 100% Complete

    seenby.sort(key=lambda x: x[2])   # sort by PathLoss

    print(f'AP "{args.apname}" is seen by:')
    for r in seenby:
        print(f"{r[0]:20} SNR: {r[1]:>3}, PathLoss: {r[2]:>3} dB")


    sys.exit(0)
