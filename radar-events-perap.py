#
#
#   show airmatch event radar をパースして各APの一日ごとの検出回数を CSV 出力
#

import sys
import re
import argparse
import fileinput
import mylogger as log
from collections import defaultdict
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE

# APpat = "^APKUD|^APSMFTM"
# APpat = r" (APGTS(\d\d)\d\d)$"
# APpat = r"(APGTS3805|APGTS3815|APGTS3817|APGTS3825|APGTS3829|APGTS3831|APGTS3835|APGTS3840)"
# APpat = r"(APGTS2805|APGTS2815|APGTS2817|APGTS2825|APGTS2829|APGTS2831|APGTS2835|APGTS2840)"
# APpat = r"(APGTS28\d\d)"
APpat = r" (APGTS\d\d\d\d$|APGTS\d\d\d\d-2$)"

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse airmatch radar events")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    parser.add_argument('-d', '--apdb', help='show ap database long output', type=str)
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    #
    #   parse AP tables
    #
    apn2model = None
    if args.apdb is not None:
        apn2model = {}
        print(f"Parsing file {args.apdb} ... ", end="")
        aos = AOSParser(args.apdb, [AP_DATABASE_LONG_TABLE], merge=True)
        ap_db_tbl = aos.get_table(AP_DATABASE_LONG_TABLE)
        if ap_db_tbl is None:
            print("show ap database long output not found.")
            sys.exit(-1)
        print("done.")

        for r in ap_db_tbl[1:]:
            apn2model[r[0]] = r[2]



    apnctr = defaultdict(lambda: 0)
    flrctr = defaultdict(lambda: 0)
    chctr = defaultdict(lambda: 0)
    hourctr = defaultdict(lambda: 0)
    dayctr = defaultdict(lambda: defaultdict(lambda: 0))
    days = set()
    total = 0

    f = fileinput.input(args.infile, encoding='utf-8')
    for l in f:
        m = re.search(APpat, l)
        if not m:
            continue
        apn = m.group(1)
        # fl = m.group(2)
        fl = apn[5:7]
        fli = int(fl)
        # if fli < 34 or fli > 38:    # 34F-38F AP のみ集計
        #     continue

        m = re.search(r'(\d\d\d\d-\d\d-\d\d)_\d\d:\d\d:\d\d +(\d+)', l)
        if not m:
            continue
        day = m.group(1)
        ch = m.group(2)

        flrctr[fl] += 1
        apnctr[apn] += 1
        chctr[int(ch)] += 1
        dayctr[apn][day] += 1
        days.add(day)
        total += 1

    print(f"Total radar events: {total}")

    # print("Hourly counts")
    # for hour in sorted(hourctr.keys()):
    #     print(f'{hour}: {hourctr[hour]}')

    print("\nChannel counts")
    for ch in sorted(chctr.keys()):
        print(f'{ch}: {chctr[ch]}')

    print("\nFloor counts")
    for fl in sorted(flrctr.keys()):
        print(f'{fl}: {flrctr[fl]}')

    print("Per-AP daily counts")
    ds = sorted(list(days))
    if apn2model is None:
        print("AP Name," + ",".join(ds))
    else:
        print("AP Name,Model," + ",".join(ds))
    for apn in sorted(dayctr.keys()):
        if apn2model is None:
            print(f'{apn},', end="")
        else:
            print(f'{apn},{apn2model[apn]},', end="")

        for day in ds:
            print(f'{dayctr[apn][day]},', end="")
        print()
