#!/usr/bin/python3
#
#   dp-ses-topuser.py
#
#   show datapath user table をパースし、session 数でソート
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict


def uniq(tbl, col=0):
    ret = []
    k = set()
    for r in tbl:
        if r[col] in k: continue
        k.add(r[col])
        ret.append(r)
    return ret


#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show datapath user table sort by the number of sessions")
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
    aos = AOSParser(args.infile, ["show datapath user table", "show user-table"], merge=True)
    dp_user = aos.get_table("show datapath user table")
    l3_user = aos.get_table("show user-table")
    if dp_user is None:
        print("show datapath user table output not found.")
        sys.exit(-1)
    if l3_user is None:
        print("show user-table output not found.")
        sys.exit(-1)
    print("done.")

    dp_user_uniq = uniq(dp_user)
    l3_user = uniq(l3_user)

    print(f'Got total {len(l3_user)-1} L3 users, {len(dp_user_uniq)-1} L2 users.')


    #
    #   create IP -> AP Name/SSID map
    #
    ip2apn = defaultdict(lambda: "")
    ip2ssid = defaultdict(lambda: "")
    ip2name = defaultdict(lambda: "")
    for r in l3_user[1:]:
        ip = r[0]
        name = r[2]
        apn = r[7]
        m = re.match(r'([\w-]+)/', r[9])
        if m:
            ssid = m.group(1)
        else:
            ssid = "n/a"
        ip2apn[ip] = apn
        ip2ssid[ip] = ssid
        ip2name[ip] = name


    #
    #   get top 200 session consumer
    #
    tbl = []
    for r in dp_user[1:]:
        if '2700/' in r[2]:
            continue
        m = re.search(r'(\d+)/(\d+)', r[7])
        if m:
            numses = int(m.group(1))
            tbl.append([r[0], r[1], numses])

    i = 1
    for r in sorted(tbl, key=lambda x:x[2], reverse=True)[:200]:
        ip = r[0]
        print(f'{i:>3}: {ip:20}{r[1]:24}{ip2name[ip]:40}{ip2apn[ip]:25}{ip2ssid[ip]:20}{r[2]:>5}')
        #print(f'{ip},{r[1]},{ip2name[ip]},{ip2apn[ip]},{ip2ssid[ip]},{r[2]}')
        i+=1
