#
#   arm-state-dump.py
#
#   show ap arm state で 38F AP の内容のみ表示
#

import sys
import re
import argparse
import fileinput
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict

def fln():
    return fileinput.filename() + ":" + str(fileinput.filelineno())

apn2model = {}
apn2group = {}

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show ap tech and display neighbor APs")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    #
    #   parse ap database and get apname -> ap model mapping
    #
    aos = AOSParser(args.infile, [AP_DATABASE_LONG_TABLE], merge=True)
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

    arm_state = {}
    nbrctr = {}

    f = fileinput.input(args.infile, encoding='utf-8')
    for l in f:
        if l.startswith('show ap arm state'):
            break

    out = []
    cont = 0
    for l in f:
        if cont != 0 and l.startswith('Legend: '):
            out.append(l)
            if apn.startswith('APGTS38'):
                arm_state[apn] = "".join(out)
                nbrctr[apn] = len(out)-8
            cont = 0
            continue
        elif cont != 0:
            out.append(l)
            continue

        # cont == 0
        if not l.startswith('AP:'): continue

        r = re.match(r'AP:([\w-]+) MAC:[:\w]+.* Channel:(\d+[SE+-]?)+', l)
        if r:
            apn = r.group(1)
            ch = r.group(2)
            #if int(re.sub(r'[SE+-]', '', ch)) < 36:
            if int(re.sub(r'[SE+-]', '', ch)) >= 36:
                continue
            cont = 1
            out = [l]
            continue

        continue

    for apn in sorted(arm_state.keys()):
        print(arm_state[apn])
        print()

    for apn in sorted(arm_state.keys()):
        print(f"{apn}: {nbrctr[apn]}")
