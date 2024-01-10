#
#
#   show airmatch event radar をパースして時間単位に集計
#

import sys
import re
import argparse
import fileinput
import mylogger as log
import datetime
from collections import defaultdict

#APpat = "^APKUD|^APSMFTM"
APpat = r" (APGTS(\d\d)\d\d)$"

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse airmatch radar events")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    apnctr = defaultdict(lambda: 0)
    flrctr = defaultdict(lambda: 0)
    chctr = defaultdict(lambda: 0)
    hourctr = defaultdict(lambda: 0)
    total = 0

    f = fileinput.input(args.infile, encoding='utf-8')
    for l in f:
        m = re.search(APpat, l)
        if not m:
            continue
        apn = m.group(1)
        fl = m.group(2)
        fli = int(fl)
        if fli < 34 or fli > 38:    # 34F-38F AP のみ集計
            continue

        m = re.search(r'(\d\d\d\d-\d\d-\d\d_\d\d):\d\d:\d\d +(\d+)', l)
        if not m:
            continue
        hour = m.group(1)
        ch = m.group(2)

        flrctr[fl] += 1
        apnctr[apn] += 1
        chctr[int(ch)] += 1
        hourctr[hour] += 1
        total += 1

    print(f"Total radar events: {total}")

    print("Hourly counts")
    for hour in sorted(hourctr.keys()):
        print(f'{hour}: {hourctr[hour]}')

    print("\nChannel counts")
    for ch in sorted(chctr.keys()):
        print(f'{ch}: {chctr[ch]}')

    print("\nFloor counts")
    for fl in sorted(flrctr.keys()):
        print(f'{fl}: {flrctr[fl]}')
