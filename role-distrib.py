#
#   role-distrib.py
#
#   show user-table で、各 ESSID/Role/OS Type のユーザ数ヒストグラム
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
        description="Parse show user-table and display role histogram")
    parser.add_argument('infile', help="Input file", type=str, nargs='+')
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
    aos = AOSParser(args.infile, ["show user-table"], merge=True)
    user_table = aos.get_table("show user-table")
    if user_table is None:
        print("show user-table output not found.")
        sys.exit(-1)
    print(f"done. {len(user_table)-1} users found.")

    #
    #   必要な column のみ取り出す
    #
    roles = defaultdict(lambda: [0, 0])
    ssids = defaultdict(lambda: [0, 0])
    types = defaultdict(lambda: 0)
    for r in user_table[1:]:
        role = r[3]
        m = re.match("([\w-]+)/", r[9])
        if m:
            ssid = m.group(1)
        else:
            print(f"can't parse SSID: {r[9]}")
            exit()
        m = re.search("/5GHz", r[9])
        band = 0 if m else 1    # 0:5G 1:2.4G
        type = r[12]
        if type == "":
            type = "unknown"
        if type.startswith("Win"):
            type = "Windows"

        roles[role][band] += 1
        ssids[ssid][band] += 1
        types[type] += 1

    print("=== Roles ===")
    for r in sorted(roles.keys(), key=lambda x:roles[x][0]+roles[x][1], reverse=True):
        print(f"{r:20} {roles[r][0]+roles[r][1]} ({roles[r][0]}/{roles[r][1]})")

    print("\n=== SSIDs ===")
    for r in sorted(ssids.keys(), key=lambda x:ssids[x][0]+ssids[x][1], reverse=True):
        print(f"{r:20} {ssids[r][0]+ssids[r][1]} ({ssids[r][0]}/{ssids[r][1]})")

    print("\n=== OS Type ===")
    for r in sorted(types.keys(), key=lambda x:types[x], reverse=True):
        print(f"{r:20} {types[r]}")
