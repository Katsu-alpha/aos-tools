#
#   radio-summary-toputil.py
#
#   show radio-summary をパースし、5GHz radio を channel util 順にソート
#   端末数の column は show ap active から取得
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict

# APpat = "^APKUDKS|^APSMFTM"
# APpat = "^APGTS"
APpat = ".*"

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show radio-summary and sort the 5GHz radios by channel utilization")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
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
    aos = AOSParser(args.infile, ["show ap radio-summary"], merge=False)
    radio_summary = aos.get_table("show ap radio-summary")
    if radio_summary is None:
        print("show ap radio-summary output not found.")
        sys.exit(-1)

    aos = AOSParser(args.infile, ["show ap active"], merge=True)
    ap_active_tbl = aos.get_table("show ap active")
    if ap_active_tbl is None:
        print("show ap active output not found.")
        sys.exit(-1)
    print("done.")

    #
    #   show ap active から 5GHz client 数取得
    #
    idx_r0 = ap_active_tbl[0].index("Radio 0 Band Ch/EIRP/MaxEIRP/Clients")
    apn_sta = {}
    apn_type = {}
    for row in ap_active_tbl[1:]:
        apn = row[0]
        r0 = row[idx_r0]
        r = re.match("(.+):([\dSE+\-]+)/([\d\.]+)/[\d\.]+/(\d+)$", r0)
        if r:
            r0_sta = r.group(4)
            apn_sta[apn] = r0_sta
        apn_type[apn] = row[3]

    #
    #   radio-summary の必要な column のみ取り出す
    #
    tbl = []
    ch_ctr = defaultdict(lambda: 0)
    util_sum = defaultdict(lambda: 0)
    for r in radio_summary:
        apn = r[0]
        if not re.search(APpat, apn):
            continue

        apg = r[1]
        band = r[4]
        if band != '5GHz':
            continue
        mode = r[5]     # AP:VHT:56
        if mode == 'AM': continue
        m = re.search(":(\d+)", mode)
        if m:
            ch = m.group(1)
        m = re.search("([0-9\.]+)/", r[6])   # EIRP/MaxEIRP
        if m:
            eirp = m.group(1)
        m = re.search("(-\d+)/(\d+)/\d+", r[7])     # NF/U/I
        if m:
            nf = m.group(1)
            util = int(m.group(2))

        ch_ctr[ch] += 1
        util_sum[ch] += util
        if apn in apn_sta:
            sta = apn_sta[apn]
        else:
            sta = "na"
        row = [ apn, apg, mode, eirp, sta, nf, util, apn_type[apn] ]
        tbl.append(row)

    tbl.sort(key=lambda x: x[6], reverse=True)

    print("Name                        Group                           Type  Mode          EIRP    Clients  NF    Util")
    print("----                        -----                           ----  ----          ----    -------  ---   ----")
    for r in tbl:
        print(f"{r[0]:28}{r[1]:32}{r[7]:6}{r[2]:14}{r[3]:>4}{r[4]:>7}  {r[5]:>7}{r[6]:>7}")

    for ch in sorted(ch_ctr.keys(), key=lambda x: int(x)):
        avg = util_sum[ch] / ch_ctr[ch]
        print(f"{ch} - {avg:.2f} ({ch_ctr[ch]} APs)")
