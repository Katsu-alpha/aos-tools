#!/usr/bin/python3
#
#   dp-ses-zoom.py
#
#   show datapath session dpi をパースし、Zoom セッションのみ表示
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
    aos = AOSParser(args.infile, ["show datapath session dpi"], merge=True)
    dp_ses = aos.get_table("show datapath session dpi")
    if dp_ses is None:
        print("show datapath session dpi output not found.")
        sys.exit(-1)
    print(f"done. {len(dp_ses)-1} session entries found.")


    #
    #   get zoom session (src port==8801)
    #
    tbl = []
    tbl_m = []
    dip = set()
    num_v = num_i = num_q = num_u = tot_br = 0
    for r in dp_ses[1:]:
        tage = int(r[10], 16)
        if tage <= 5: continue          # ignore short-lived session
        if r[2] == '47': continue       # ignore GRE tunnel
        sp = int(r[3])
        if not (8801 <= sp <= 8810): continue       # ignore non-Zoom session

        bytes = int(r[12])
        flags = r[20]
        bitrate = bytes*8/tage
        tot_br += bitrate
        dip.add(r[1])       # Dest IP
        tbl.append([r[0], r[1], r[2], r[3], r[4], tage, bytes, bitrate, flags])

        m = re.match(r'(\d+)\.', r[1])
        if m:
            ip = int(m.group(1))
            if 224 <= ip <= 239:
                tbl_m.append([r[0], r[1], r[2], r[3], r[4], tage, bytes, bitrate, flags])


    i = 1
    #print('Src,Dst,Proto,SPort,DPort,Bytes,Bitrate(Kbps),Flags')
    print("Src IP              Dst IP              Proto  SPort  DPort  Bytes      Dur   BW(Kbps)   Flags")
    print("------              ------              -----  -----  -----  -----      ---   --------   -----")
    for r in sorted(tbl, key=lambda x:x[7], reverse=True):
        src = r[0]
        dst = r[1]
        print(f'{src:20}{dst:20}{r[2]:7}{r[3]:7}{r[4]:7}{r[6]:>10}{r[5]:>6} {r[7]/1000:>10.2f} {r[8]} ')
        #print(f'{src},{dst},{r[2]},{r[3]},{r[4]},{r[6]},{r[7]/1000:>8.2f},{r[8]}')
        i+=1

    print(f"Total sessions: {len(tbl)} sessions")
    print(f"Total unique receiver IP: {len(dip)} IPs")
    print(f"Total bitrate: {tot_br/1000/1000:.2f} Mbps")
    sys.exit(0)

    print("\n==== Multicast ====")
    for r in sorted(tbl_m, key=lambda x:x[7], reverse=True)[:100]:
        src = r[0]
        dst = r[1]
        print(f'{i:>3}: {src:20}{dst:20}{r[2]:5}{r[3]:6}{r[4]:6}{r[6]:>10} {r[7]/1000:>8.2f} Kbps')
        #print(f'{ip},{r[1]},{ip2name[ip]},{ip2apn[ip]},{ip2ssid[ip]},{r[2]}')
        i+=1

    print(f"V:{num_v}  I:{num_i}  Q:{num_q}  u:{num_u}")