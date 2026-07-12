#/usr/bin/python3 -u
#
#   ap-monitor-list.py
#
#   show ap monitor ap-list の結果をパースし、valid/interfering に分け、curr_snr でソートして出力
#   show ap bss-table を含むファイルまたは --bssdic オプションを指定すると、AP名を解決して表示
#   AOS 8.10 対応版
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict
from colorama import Fore, Style

Color = True


if Color:
   GREEN = Fore.GREEN
   CYAN = Fore.CYAN
   RED = Fore.RED
   MAGENTA = Fore.MAGENTA
   BLUE = Fore.BLUE
   YELLOW = Fore.YELLOW
   RESET = Style.RESET_ALL
else:
    GREEN = ""
    CYAN = ""
    RED = ""
    MAGENTA = ""
    BLUE = ""
    YELLOW = ""
    RESET = ""

chlist = ['36', '40', '44', '48', '52', '56', '60', '64', '100', '104', '108', '112', '116', '120', '124', '128', '132', '136', '140', '144', '149', '153', '157', '161', '165']
chlist40 = ['36', '44', '52', '60', '100', '108', '116', '124', '132', '140', '149', '157']
chlist80 = ['36', '52', '100', '116', '132','149']
chlist160 = ['36', '100', '149']

chsets = {}

for ch in chlist:
    chsets[ch] = {ch}
for ch in chlist40:
    ch2 = str(int(ch)+4)
    chsets[ch  + '+'] = {ch, ch2}
    chsets[ch2 + '-'] = {ch, ch2}
for ch in chlist80:
    ch2 = str(int(ch)+4)
    ch3 = str(int(ch)+8)
    ch4 = str(int(ch)+12)
    chsets[ch  + 'E'] = {ch, ch2, ch3, ch4}
    chsets[ch2 + 'E'] = {ch, ch2, ch3, ch4}
    chsets[ch3 + 'E'] = {ch, ch2, ch3, ch4}
    chsets[ch4 + 'E'] = {ch, ch2, ch3, ch4}
for ch in chlist160:
    ch2 = str(int(ch)+4)
    ch3 = str(int(ch)+8)
    ch4 = str(int(ch)+12)
    ch5 = str(int(ch)+16)
    ch6 = str(int(ch)+20)
    ch7 = str(int(ch)+24)
    ch8 = str(int(ch)+28)
    chsets[ch  + 'S'] = {ch, ch2, ch3, ch4, ch5, ch6, ch7, ch8}
    chsets[ch2 + 'S'] = {ch, ch2, ch3, ch4, ch5, ch6, ch7, ch8}
    chsets[ch3 + 'S'] = {ch, ch2, ch3, ch4, ch5, ch6, ch7, ch8}
    chsets[ch4 + 'S'] = {ch, ch2, ch3, ch4, ch5, ch6, ch7, ch8}
    chsets[ch5 + 'S'] = {ch, ch2, ch3, ch4, ch5, ch6, ch7, ch8}
    chsets[ch6 + 'S'] = {ch, ch2, ch3, ch4, ch5, ch6, ch7, ch8}
    chsets[ch7 + 'S'] = {ch, ch2, ch3, ch4, ch5, ch6, ch7, ch8}
    chsets[ch8 + 'S'] = {ch, ch2, ch3, ch4, ch5, ch6, ch7, ch8}


chlist2G = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14']
for i in range(14):
    chsets[chlist2G[i]] = set(chlist2G[max(i-2, 0):min(i+3, len(chlist2G))])

for i in range(10):
    chsets[chlist2G[i]+'+'] = set(chlist2G[max(i-2, 0):min(i+8, len(chlist2G))])

for i in range(5,14):
    chsets[chlist2G[i]+'-'] = set(chlist2G[max(i-7, 0):min(i+3, len(chlist2G))])

def isIntf(ch1, ch2):
    global chsets
    if ch1 not in chsets:
        print(f"Warning: unknown channel: {ch1}")
        return False
    if ch2 not in chsets:
        print(f"Warning: unknown channel: {ch2}")
        return False
    if chsets[ch1] & chsets[ch2]:
        return True
    
    return False
#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse 'show ap monitor ap-list' and sort valid/intf APs with SNR descending order")
    parser.add_argument('infiles', help="Input file containing 'show ap monitor ap-list' output", type=str, nargs='+')
    #parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    parser.add_argument('--band', '-b', help='Radio band', type=str, default='5')
    parser.add_argument('--summary', help='Summary only', action='store_true')
    parser.add_argument('--bssdic', '-d', help='Specify BSSID dictionary', type=str)
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    # BSSID -> AP Name の辞書を作成
    bss2apn = {}
    if args.bssdic:
        if args.bssdic.endswith('.py'):
            args.bssdic = args.bssdic[:-3]
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("bssdict", args.bssdic+".py")
            bssdict = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bssdict)
            # bssdict = __import__(args.bssdic)
            bss2apn = bssdict.bss2apn
        except Exception as e:
            print(f"Error: can't import {args.bssdic}.py: {e}")
            sys.exit(1)

    #
    #   parse files
    #
    cmd = ["show ap monitor ap-list.*","show ap bss-table"]
    cols = ["bssid", "essid", "band/chan/ch-width/ht-type", "ap-type", "encr", "curr-snr", "curr-rssi"]
    for fn in args.infiles:
        aos = AOSParser(fn, cmd, merge=True)
        ap_list_tbl = aos.get_table(cmd[0], *cols)
        ap_bss_tbl = aos.get_table(cmd[1])
        if ap_bss_tbl is not None:
            for r in ap_bss_tbl[1:]:
                bss2apn[r[0]] = r[8]
        if ap_list_tbl is None:
            print(f"show ap monitor ap-list output not found in {fn}.")
            continue

        #
        #   Process ap-list table
        #
        aplist = []
        mych = ''       # own channel
        for row in ap_list_tbl:
            bss = row[0]
            try:
                row[5] = int(row[5])    # curr-snr
                row[6] = int(row[6])    # curr-rssi
                r = re.search(r"([2456.]+)GHz/(\d+)([SE+-]?)/(\d+MHz)/(\w+)", row[2])   # "5GHz/36+/40MHz/VHT"
                if r:
                    band = r.group(1)
                    pch = r.group(2)
                    ch = pch + r.group(3)
                    pch = int(pch)
                    cbw = r.group(4)
                    phy = r.group(5)
                else:
                    print(f"invalid phy column: {row[2]}")
                    sys.exit(1)
            except ValueError:
                print(f"Can't parse row: {row}")
                # sys.exit(1)
                continue

            if band[0] != args.band:
                continue

            #              bssid   essid                      type    encr    snr     rssi
            aplist.append([row[0], row[1], ch, pch, cbw, phy, row[3], row[4], row[5], row[6]])
            if mych=='' and bss.endswith('(+)'):
                mych = ch
                myapn = bss2apn.get(bss[:17], row[0])


        if len(aplist) == 0:
            print("No APs found.")
            sys.exit(0)

        #
        #   結果表示
        #
        bss_dedup = set()
        aplist.sort(key=lambda x: x[8], reverse=True)
        rslt = [
            "****************** Valid APs ******************",
            "",
            "                    BSSID               ESSID    Chan     CBW/PHY      Type               Enc   SNR  RSSI  AP Name",
            "                    -----               -----    ----     -------      ----               ---   ---  ----  -------",
            ]

        valid_tot = 0
        valid_coch_snr10 = 0
        cov_ap = 0      # Valid APs with SNR >= 30
        for r in aplist:
            bss, ap_type, pch = r[0], r[6], r[3]
            if ap_type == "valid":
                if bss[:16] in bss_dedup:
                    continue
                bss_dedup.add(bss[:16])
                cbw_phy = r[4] + '/' + r[5]
                apn = bss2apn.get(bss[:17], '')
                ch = r[2]
                snr = r[8]
                valid_tot += 1
                l = f"{valid_tot:>3}{bss:>22}{r[1]:>20}{r[2]:>8}{cbw_phy:>12}{r[6]:>10}{r[7]:>18}{r[8]:>6}{-r[9]:>6}  {apn}"

                if bss.endswith('(+)'):
                    rslt.append(GREEN + l + RESET)
                else:
                    if snr >= 30:
                        cov_ap += 1
                    if isIntf(ch, mych):
                        if snr >= 10:
                            rslt.append(RED + l + RESET)
                            valid_coch_snr10 += 1
                        else:
                            rslt.append(YELLOW + l + RESET)
                    else:
                        rslt.append(l)

        if not args.summary:
            print("\n".join(rslt))
            print(f"\nTotal Valid APs: {valid_tot}, Coverage APs with SNR>=30: {cov_ap}, Co-ch APs with SNR>=10: {valid_coch_snr10}\n")

        if args.summary:
            # print(f"{myapn}: Channel:{mych}  Coverage APs:{cov_ap}  Co-ch APs:{valid_coch_snr10}")
            print(f'"{myapn}","{mych}",{cov_ap},{valid_coch_snr10}')
            continue

        rslt = [
            f"****************** Interfering APs seen by {myapn} ******************",
            "",
            "                    BSSID                    ESSID    Chan     CBW/PHY                  Type               Enc   SNR  RSSI",
            "                    -----                    -----    ----     -------                  ----               ---   ---  ----",
            ]

        intf_tot = 0
        intf_coch_snr10 = 0
        for r in aplist:
            bss, ap_type, pch = r[0], r[6], r[3]
            if ap_type != "valid":
                cbw_phy = r[4] + '/' + r[5]
                apn = bss2apn.get(bss[:17], '')
                ch  = r[2]
                snr = r[8]
                intf_tot += 1
                l = f"{intf_tot:>3}{r[0]:>22}{r[1]:>25}{r[2]:>8}{cbw_phy:>12}{r[6]:>22}{r[7]:>18}{r[8]:>6}{-r[9]:>6}  {apn}"

                if isIntf(ch, mych):
                    if snr >= 10:
                        rslt.append(RED + l + RESET)
                        intf_coch_snr10 += 1
                    else:
                        rslt.append(YELLOW + l + RESET)
                else:
                    rslt.append(l)

        if not args.summary:
            print("\n".join(rslt))
            print(f"\nTotal Interfering APs: {intf_tot}, Co-ch APs with SNR>=10: {intf_coch_snr10}\n")





