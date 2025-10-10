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
    parser.add_argument('--pattern', '-p', help='regex for AP name', type=str, default='.*')
    parser.add_argument('--top', '-t', help='Top N sessions', type=int, default=100)
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
    user_ip = set()
    ip2apn = {}
    maxlen = 0
    for r in user_tbl[1:]:
        ip = r[0]
        apn = r[7]
        user_ip.add(ip)
        ip2apn[ip] = apn
        maxlen = max(maxlen, len(apn))

    #
    #   get top 100 high-bandwidth session
    #
    tbl = []
    tbl_m = []
    num_v = num_i = num_q = num_u = tot_br = 0
    idx_tos   = dp_ses[0].index('ToS')
    idx_tage  = dp_ses[0].index('TAge')
    idx_bytes = dp_ses[0].index('Bytes')
    idx_flags = dp_ses[0].index('Flags')
    idx_appid = dp_ses[0].index('AppID')
    rate_ap = defaultdict(lambda: 0)
    rate_ip = defaultdict(lambda: 0)
    num_ses = defaultdict(lambda: 0)

    for r in dp_ses[1:]:
        tage = int(r[idx_tage], 16)
        if tage <= 5: continue          # ignore short-lived session
        if r[2] == '47': continue       # ignore GRE tunnel
        sip = r[0]
        dip = r[1]
        sap = ip2apn.get(sip, '')
        dap = ip2apn.get(dip, '')
        if (not re.search(args.pattern, sap)) and (not re.search(args.pattern, dap)):
            continue        # AP name does not match

        bytes = int(r[idx_bytes])
        flags = r[idx_flags]
        bitrate = bytes*8/tage
        tot_br += bitrate
        # SIP, SAP, DIP, DAP, Proto, SPort, DPort, ToS, TAge, Bytes, Bitrate, Flags, AppID
        tbl.append([sip, sap, dip, dap, r[2], r[3], r[4], r[idx_tos], tage, bytes, bitrate, flags, r[idx_appid][:16].rstrip()])

        m = re.match(r'(\d+)\.', dip)
        if m:
            ip = int(m.group(1))
            if 224 <= ip <= 239:
                tbl_m.append([sip, sap, dip, r[2], r[3], r[4], tage, bytes, bitrate, flags])

        if 'V' in flags: num_v += 1
        if 'I' in flags: num_i += 1
        if 'Q' in flags: num_q += 1
        if 'u' in flags: num_u += 1

        #   traffic summary
        if sap:
            rate_ap[sap] += bitrate
        if dap:
            rate_ap[dap] += bitrate
        if sip in user_ip:
            rate_ip[sip] += bitrate    # Source IP
            num_ses[sip] += 1
        if dip in user_ip:
            rate_ip[dip] += bitrate    # Dest IP
            num_ses[dip] += 1


    #
    #   show results
    #

    print(f'Listing top {args.top} sessions:')
    spc = " " * (maxlen-4)
    print(f"Src IP              Src AP{spc}Dst IP              Dst AP{spc}Proto  SPort  DPort  ToS  Bytes        Dur   BW(Kbps)  Flags  AppID")
    print(f"------              ------{spc}------              ------{spc}-----  -----  -----  ---  -----        ---   --------  -----  -----")

    # Sorty by BW
    for r in sorted(tbl, key=lambda x:x[10], reverse=True)[:args.top]:
        print(f'{r[0]:20}{r[1]:{maxlen+2}}{r[2]:20}{r[3]:{maxlen+2}}{r[4]:7}{r[5]:7}{r[6]:7}{r[7]:3}  {r[9]:>10}{r[8]:>6} {r[10]/1000:>10.2f}  {r[11]:5}  {r[12]}')

    print(f"Total bitrate: {tot_br/1000/1000:.2f} Mbps")
    #sys.exit(0)

    print("\n==== Multicast ====")
    i = 1
    for r in sorted(tbl_m, key=lambda x:x[8], reverse=True)[:100]:
        print(f'{i:>3}: {r[0]:20}{r[1]:20}{r[2]:20}{r[3]:5}{r[4]:6}{r[5]:6}{r[7]:>10} {r[8]/1000:>8.2f} Kbps')
        #print(f'{ip},{r[1]},{ip2name[ip]},{ip2apn[ip]},{ip2ssid[ip]},{r[2]}')
        i+=1

    print("\n==== Flagged sessions ====")
    print(f"V:{num_v}  I(Deep Instpect):{num_i}  Q(Real-Time Quality analysis):{num_q}  u(Upstream Real-Time Quality analysis):{num_u}")

    print("\n==== Top APs ====")
    for ap, br in sorted(rate_ap.items(), key=lambda x:x[1], reverse=True)[:20]:
        print(f'{ap:{maxlen}}  {br/1000/1000:>8.2f} Mbps')

    print("\n==== Top Users ====")
    for ip, br in sorted(rate_ip.items(), key=lambda x:x[1], reverse=True)[:20]:
        print(f'{ip:15}  {br/1000/1000:>8.2f} Mbps')

    print("\n==== Top Users by # of sessions ====")
    for ip, ns in sorted(num_ses.items(), key=lambda x:x[1], reverse=True)[:20]:
        print(f'{ip:15}  {ns:>5} sessions')