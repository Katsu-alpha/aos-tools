#
#
#   WIRELESS.log をパースして Radar event を集計
#

import sys
import re
import argparse
import fileinput
import mylogger as log
import datetime
from collections import defaultdict

# APpat = "^APKUD|^APSMFTM"
# APpat = "^APGTS"
# APpat = "^APG7"
# APpat = "^APHIBFS"

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse WIRELESS.log and count radar events")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    f = fileinput.input(args.infile, encoding='utf-8')
    # st = datetime.datetime(2023, 9, 18)
    apnctr = defaultdict(lambda: 0)
    flrctr = defaultdict(lambda: 0)
    chctr = defaultdict(lambda: 0)
    total = 0
    for l in f:
        if len(l) < 20: continue

        # dt = datetime.datetime.strptime(l[:20], '%b %d %H:%M:%S %Y')
        # if dt < st: continue

        m = re.search(r'\|AP ([\w-]+)@[0-9\.]+ sapd\|.*: ARM Radar Detected Trigger Current Channel (\d+)', l)
        if not m:
            m = re.search(r'\|AP ([\w-]+)@[0-9\.]+ sapd\|.*: Radar detected on interface wifi[012], channel (\d+)', l)
            if not m:
                continue

        apn = m.group(1)

        if 'APpat' in globals() and not re.search(APpat, apn):
            continue

        ch = m.group(2)
        fl = apn[5:7]
        apnctr[apn] += 1
        flrctr[fl] += 1
        chctr[int(ch)] += 1
        total += 1

        #print(f"Radar detected at {l[:15]} AP:{apn} Ch:{ch}")

    print("=== per AP ===")
    for apn in sorted(apnctr.keys(), key=lambda x:apnctr[x], reverse=True):
        print(f'{apn}: {apnctr[apn]}')

    print("=== per Channel ===")
    for ch in sorted(chctr.keys(), key=lambda x:chctr[x], reverse=True):
        print(f'{ch}: {chctr[ch]}')

    print("=== per Floor ===")
    for fl in sorted(flrctr.keys()):
        print(f'{fl}: {flrctr[fl]}')

    print(f"Total: {total}")
