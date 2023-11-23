#/usr/bin/python3 -u
#
#   ap-mgmt-frame.py
#
#   show ap remote debug mgmt-frames の結果をパースし、deauth reason を集計
#

import sys
import re
import argparse
import pandas as pd
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show ap remote debug mgmt-frames and count deauths")
    parser.add_argument('infiles', help="Input file containing 'show ap monitor ap-list' output", type=str, nargs='+')
    #parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    #
    #   parse AP List
    #
    print("Parsing files ... ", end="")
    cmd = "show ap remote debug mgmt-frames .+"
    aos = AOSParser(args.infiles, cmd, merge=True)
    mgmt_frames_tbl = aos.get_table(cmd)
    if mgmt_frames_tbl is None:
        print("show ap remoet debug mgmt-frames output not found.")
        sys.exit(-1)
    print("done.")

    #
    #   Process columns in active AP table
    #
    cols = ["stype", "SA", "BSS", "Misc"]
    mgmt_frames_tbl_2 = aos.get_table(cmd, *cols)
    deauth_reason = {}
    assoc_resp = {}
    auth_resp = {}

    for row in mgmt_frames_tbl_2:
        if row[0] == "deauth":
            rsn = re.sub(' \(seq num \d+\)', '', row[3])
            if rsn in deauth_reason:
                deauth_reason[rsn] += 1
            else:
                deauth_reason[rsn] = 1
        if row[0] in ("assoc-resp", "reassoc-resp"):
            rsn = re.sub(' \(seq num \d+\)', '', row[3])
            if rsn in assoc_resp:
                assoc_resp[rsn] += 1
            else:
                assoc_resp[rsn] = 1
        if row[0] == "auth" and row[1] == row[2]:
            rsn = re.sub(' \(seq num \d+\)', '', row[3])
            if rsn in auth_resp:
                auth_resp[rsn] += 1
            else:
                auth_resp[rsn] = 1

    print("\n*** deauth reasons ***")
    for rsn in sorted(deauth_reason.keys(), key=lambda x: deauth_reason[x], reverse=True):
        print(f"{deauth_reason[rsn]:5}  {rsn}")
    print("\n*** auth responses ***")
    for rsn in sorted(auth_resp.keys(), key=lambda x: auth_resp[x], reverse=True):
        print(f"{auth_resp[rsn]:5}  {rsn}")
    print("\n*** assoc responses ***")
    for rsn in sorted(assoc_resp.keys(), key=lambda x: assoc_resp[x], reverse=True):
        print(f"{assoc_resp[rsn]:5}  {rsn}")
    #for rsn,ctr in deauth_reason.items():
    #    print(f"{ctr:5}  {rsn}")



    sys.exit(0)
