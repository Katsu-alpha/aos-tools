#
#   radio-summary-toputil.py
#
#   show radio-summary をパースし、AP group/channel ごとに AP数、avg util を集計
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show radio-summary and ze per-group summary")
    parser.add_argument('infile', help="Input file", type=str, nargs=1)
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    #
    #   parse AP tables
    #
    print("Parsing files ... ", end="")
    aos = AOSParser(args.infile, ["show ap radio-summary", "show ap active"])
    radio_summary = aos.get_table("show ap radio-summary")
    if radio_summary is None:
        print("show ap radio-summary output not found.")
        sys.exit(-1)
    print("done.")

    #
    #   AP group ごとに ch/util 集計
    #
    grpchctr = defaultdict(lambda: defaultdict(lambda: 0))
    grpchutil = defaultdict(lambda: defaultdict(lambda: 0))
    for r in radio_summary[1:]:
        apg = r[1]
        if len(apg) > 18:
            apg = apg[:18]
        band = r[4]
        if band != '5GHz':
            continue

        m = re.search(":(\d+)", r[5])
        if m:
            ch = m.group(1)
        else:
            print(f"invalid channel: {r[5]}")
            exit()

        m = re.search("(-\d+)/(\d+)/\d+", r[7])     # NF/U/I
        if m:
            util = int(m.group(2))
        else:
            print(f"invalid util: {r[7]}")
            exit()

        grpchctr[apg][ch] += 1
        grpchutil[apg][ch] += util


    chset = ['52', '56', '60', '64', '149', '153', '157', '161']

    print("Channel distribution")
    print("                      ", end="")
    for ch in chset:
        print(f"{ch:>6}", end="")
    print()
    for apg in sorted(grpchctr.keys()):
        print(f"{apg:20}: ", end="")
        for ch in chset:
            print(f"{grpchctr[apg][ch]:>6}", end="")
        print()

    print("Channel Utilization")
    print("                      ", end="")
    for ch in chset:
        print(f"{ch:>6}", end="")
    print()
    for apg in sorted(grpchutil.keys()):
        print(f"{apg:20}: ", end="")
        for ch in chset:
            if grpchctr[apg][ch] > 0:
                avg = grpchutil[apg][ch] / grpchctr[apg][ch]
                print(f"{avg:>6.2f}", end="")
            else:
                print(f"  n/a ", end="")
        print()
