#!/usr/bin/python3
#
#   silent-sta.py
#
#   Assoc table にあるが、L3 user table に載っていない端末をリストアップ
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict

APpat = r'SG-WA-F02|SG-WC-F02'

def mac2vendor(mac):
    mac3 = mac[0:2]+mac[3:5]+mac[6:8]
    mac3 = mac3.upper()
    return oui.get(mac3, 'unkown')


#
#   main
#
if __name__ == '__main__':

    # read OUI-Vendor mapping DB
    with open("ouidb.txt") as f:
        oui = {}
        for l in f:
            m = re.match(r"([0-9A-F]{6})\s+\(base 16\)\s+(.*)", l)
            if m:
                oui[m.group(1)] = m.group(2)

    parser = argparse.ArgumentParser(
        description="Identiry silent STA")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    #
    #   parse tables
    #
    print("Parsing files ... ", end="")
    cmds = ["show user-table", "show ap association"]
    aos = AOSParser(args.infile, cmds, merge=True)
    l3_tbl = aos.get_table(cmds[0])
    if l3_tbl is None:
        print(f"{cmds[0]} output not found.")
        sys.exit(-1)
    assoc_tbl = aos.get_table(cmds[1])
    if assoc_tbl is None:
        print(f"{cmds[1]} output not found.")
        sys.exit(-1)
    print("done.\n")


    #
    #   parse L3 user-table and create IP to AP Name mapping
    #
    l3mac = set()
    for r in l3_tbl[1:]:
        l3mac.add(r[1])

    #
    #   parse assoc table and find silent device
    #
    ven = defaultdict(lambda: 0)

    print("MAC Address (Vendor)                                  AP Name              ESSID                VLAN  Duration     PHY Capabilities")
    print("--------------------                                  -------              -----                ----  --------     ----------------")
    for r in assoc_tbl[1:]:
        apn, mac, essid, vlan, dur, phy_cap = r[0], r[2], r[7], r[8], r[11], r[15]
        if 'APpat' in globals():
            if not re.search(APpat, apn): continue

        ven[mac2vendor(mac)] += 1

        if mac in l3mac: continue

        # print the info of silent STA
        v = f"({mac2vendor(mac)})"
        print(f"{mac:18}{v:35} {apn:20} {essid:20} {vlan:5} {dur:12} {phy_cap}")

    print("\n=== Device Vendors ===")
    for k in sorted(ven.keys(), key=lambda x: ven[x], reverse=True):
        print(f"{k:50} {ven[k]}")