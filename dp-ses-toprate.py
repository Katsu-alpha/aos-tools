#!/usr/bin/python3
#
#   dp-ses-toprate.py
#
#   show datapath session dpi をパースし、Bitrate (Bytes/TAge) でソート
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict

#
#   重複するキーを削除
#
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
    aos = AOSParser(args.infile, ["show user-table", "show datapath session dpi", "show datapath session internal"], merge=True)
    dp_ses = aos.get_table("show datapath session dpi")
    if dp_ses is None:
        dp_ses = aos.get_table("show datapath session internal")
        if dp_ses is None:
            print("show datapath session dpi|internal output not found.")
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
    #   get top 200 high-bandwidth session
    #
    tbl = []
    tbl_m = []
    num_v = num_i = num_q = num_u = tot_br = 0
    idx_tos   = dp_ses[0].index('ToS')
    idx_tage  = dp_ses[0].index('TAge')
    idx_bytes = dp_ses[0].index('Bytes')
    idx_flags = dp_ses[0].index('Flags')
    idx_appid = dp_ses[0].index('AppID')

    for r in dp_ses[1:]:
        tage = int(r[idx_tage], 16)
        if tage <= 5: continue          # ignore short-lived session
        if r[2] == '47': continue       # ignore GRE tunnel
        bytes = int(r[idx_bytes])
        flags = r[idx_flags]
        bitrate = bytes*8/tage
        tot_br += bitrate
        tbl.append([r[0], r[1], r[2], r[3], r[4], r[idx_tos], tage, bytes, bitrate, flags, r[idx_appid][:16].rstrip()])

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
    print("Src IP              Src AP              Dst IP              Dst AP              Proto  SPort  DPort  ToS  Bytes        Dur   BW(Kbps)  Flags  AppID")
    print("------              ------              ------              ------              -----  -----  -----  ---  -----        ---   --------  -----  -----")
    for r in sorted(tbl, key=lambda x:x[8], reverse=True)[:200]:
        src = r[0]
        dst = r[1]
        sap = ip2apn.get(src, '')
        dap = ip2apn.get(dst, '')
        print(f'{src:20}{sap:20}{dst:20}{dap:20}{r[2]:7}{r[3]:7}{r[4]:7}{r[5]:3}  {r[7]:>10}{r[6]:>6} {r[8]/1000:>10.2f}  {r[9]:5}  {r[10]}')
        #print(f'{src},{dst},{r[2]},{r[3]},{r[4]},{r[6]},{r[7]/1000:>8.2f},{r[8]}')
        i+=1

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