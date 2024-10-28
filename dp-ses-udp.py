#!/usr/bin/python3
#
#   dp-ses-udp.py
#
#   show datapath session dpi をパースし、Bitrate (Bytes/TAge) でソート
#   Protocol, Port, AP Name でフィルタリング
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict

Proto = 17
# Ports = [22443]  # VDI
# Ports = [8801]    # Zoom
Ports = [3479, 3480, 3481]    # Teams
# Ports = [3481]    # Teams Screen Share
# Ports = [3479]    # Teams Audio
# Ports = [3480]    # Teams Video
APpat = r'SG-WA-F02|SG-WC-F02'

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
        description="Parse show datapath session dpi by the bitrate of each session")
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
    aos = AOSParser(args.infile, ["show user-table", "show datapath session dpi"], merge=True)
    dp_ses = aos.get_table("show datapath session dpi")
    if dp_ses is None:
        print("show datapath session dpi output not found.")
        sys.exit(-1)
    user_tbl = aos.get_table("show user-table")
    if user_tbl is None:
        print("show user-table output not found.")
        sys.exit(-1)
    print(f"done. {len(dp_ses)-1} session entries found.")


    #
    #   parse user-table and create IP to AP Name mapping
    #
    ip2apn = {}
    for r in user_tbl[1:]:
        ip = r[0]
        apn = r[7]
        ip2apn[ip] = apn

    #
    #   print session entries in descending order of bitrate
    #
    tbl = []
    tbl_m = []
    num_v = num_i = num_q = num_u = tot_br = 0
    uniq_ip = set()

    for r in dp_ses[1:]:
        tage = int(r[10], 16)
        proto = int(r[2])
        sp,dp = int(r[3]), int(r[4])
        if tage <= 5: continue          # ignore short-lived session
        if proto != Proto: continue
        if not (sp in Ports or dp in Ports): continue

        sap = ip2apn.get(r[0], '')
        dap = ip2apn.get(r[1], '')
        if 'APpat' in globals():
            if not (re.search(APpat, sap) or re.search(APpat, dap)): continue

        if sp in Ports:
            uniq_ip.add(r[1])   # add client IP

        bytes = int(r[12])
        flags = r[20]
        bitrate = bytes*8/tage
        tot_br += bitrate
        tbl.append([r[0], r[1], r[2], r[3], r[4], tage, bytes, bitrate, flags])

        m = re.match(r'(\d+)\.', r[1])
        if m:
            ip = int(m.group(1))
            if 224 <= ip <= 239:
                tbl_m.append([r[0], r[1], r[2], r[3], r[4], tage, bytes, bitrate, flags])

        if 'V' in flags: num_v += 1
        if 'I' in flags: num_i += 1
        if 'Q' in flags: num_q += 1
        if 'u' in flags: num_u += 1

    i = 1
    #print('Src,Dst,Proto,SPort,DPort,Bytes,Bitrate(Kbps),Flags')
    print("Src IP              Src AP              Dst IP              Dst AP              Proto  SPort  DPort       Bytes   Dur   BW(Kbps) Flags")
    print("------              ------              ------              ------              -----  -----  -----       -----   ---   -------- -----")
    for r in sorted(tbl, key=lambda x:x[7], reverse=True):
        src = r[0]
        dst = r[1]
        sap = ip2apn.get(r[0], '')
        dap = ip2apn.get(r[1], '')
        print(f'{src:20}{sap:20}{dst:20}{dap:20}{r[2]:7}{r[3]:7}{r[4]:7}{r[6]:>10}{r[5]:>6} {r[7]/1000:>10.2f} {r[8]} ')
        #print(f'{src},{dst},{r[2]},{r[3]},{r[4]},{r[6]},{r[7]/1000:>8.2f},{r[8]}')
        i+=1

    print(f"Total sessions: {len(tbl)}")
    print(f"Unique client IPs: {len(uniq_ip)}")
    print(f"Total bitrate: {tot_br/1000/1000:.2f} Mbps")
    #sys.exit(0)

    print("\n==== Multicast ====")
    for r in sorted(tbl_m, key=lambda x:x[7], reverse=True)[:100]:
        src = r[0]
        dst = r[1]
        print(f'{i:>3}: {src:20}{dst:20}{r[2]:5}{r[3]:6}{r[4]:6}{r[6]:>10} {r[7]/1000:>8.2f} Kbps')
        #print(f'{ip},{r[1]},{ip2name[ip]},{ip2apn[ip]},{ip2ssid[ip]},{r[2]}')
        i+=1

    print(f"V:{num_v}  I:{num_i}  Q:{num_q}  u:{num_u}")