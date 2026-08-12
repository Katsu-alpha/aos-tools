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
from utils import isintf

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



def print_table(tbl):
    maxlen = [0] * (len(tbl[0])-1)
    for r in tbl:
        for i, c in enumerate(r[1:]):
            if len(str(c)) > maxlen[i]:
                maxlen[i] = len(str(c))

    sep = [None]
    for c in tbl[0][1:]:
        sep.append('-' * len(c))
    tbl.insert(1, sep)


    for r in tbl:
        l = ""
        for i, c in enumerate(r[1:]):
            l += f"{c:<{maxlen[i]+2}}"
        if r[0]:
            l = r[0] + l + RESET
        print(l)




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
    parser.add_argument('--extend-valid', help='Assume the AP type as valid if the BSSID is in the dictionary', action='store_true')
    parser.add_argument('--coch', help='Co-channel APs only', action='store_true')
    parser.add_argument('--group', help='Group adjacent BSSIDs for interfering APs', action='store_true')
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

    if args.summary:
        print('"AP Name","Channel","Coverage APs","Co-ch APs"')


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
            if not args.summary:
                print("No APs found.")
            continue


        if args.extend_valid:
            for r in aplist:
                bss = r[0][:17]
                if bss in bss2apn:
                    r[6] = "valid"

        valid_aps = [r for r in aplist if r[6] == "valid"]              # Valid AP list
        intf_aps = [r for r in aplist if r[6] != "valid" and r[8]!=0]   # non-Valid and SNR!=0 AP list

        #
        #   Display Valid APs
        #
        bss_dedup = set()
        valid_aps.sort(key=lambda x: x[8], reverse=True)    # sort by curr-snr
        rslt = [[None, "BSSID", "ESSID", "Chan", "CBW/PHY", "Type", "Enc", "SNR", "RSSI", "AP Name"]]
        rslt_coch = [[None, "BSSID", "AP Name", "Chan", "SNR"]]

        valid_tot = 0
        valid_coch_snr10 = 0
        cov_ap = 0      # Valid APs with SNR >= 30
        for r in valid_aps:
            bss, ap_type, pch = r[0], r[6], r[3]
            if bss[:16] in bss_dedup:
                continue
            bss_dedup.add(bss[:16])
            cbw_phy = r[4] + '/' + r[5]
            apn = bss2apn.get(bss[:17], '')
            ch = r[2]
            snr = r[8]
            valid_tot += 1
            rr = [None, bss, r[1], r[2], cbw_phy, r[6], r[7], r[8], -r[9], apn]

            if bss.endswith('(+)'):
                rr[0] = GREEN
            else:
                if snr >= 30:
                    cov_ap += 1
                if isintf(args.band, ch, mych):
                    if snr >= 10:
                        rr[0] = RED
                        rslt_coch.append([None, bss, apn, ch, snr])
                        valid_coch_snr10 += 1
                    else:
                        rr[0] = YELLOW
            rslt.append(rr)

        if args.summary:
            # print(f"{myapn}: Channel:{mych}  Coverage APs:{cov_ap}  Co-ch APs:{valid_coch_snr10}")
            print(f'"{myapn}","{mych}",{cov_ap},{valid_coch_snr10}')
            continue
        elif args.coch:
            print("****************** Valid Co-channel APs ******************\n")
            print_table(rslt_coch)
        else:
            print("****************** Valid APs ******************\n")
            print_table(rslt)
            print(f"\nTotal Valid APs: {valid_tot}, Coverage APs with SNR>=30: {cov_ap}, Co-ch APs with SNR>=10: {valid_coch_snr10}\n")


        #
        #   Display Interfering APs
        #
        rslt = [[None, "BSSID", "ESSID", "Chan", "CBW/PHY", "Type", "Enc", "SNR", "RSSI", "AP Name"]]
        rslt_coch = [[None, "BSSID", "ESSID", "Chan", "Type", "SNR"]]

        if args.group:
            ap_snr = {}
            for r in intf_aps:
                bss, snr = r[0], r[8]
                if bss[:16] not in ap_snr:
                    ap_snr[bss[:16]] = snr
            intf_aps.sort(key=lambda x: (-ap_snr[x[0][:16]], x[0]))    # sort by curr-snr, bssid
        else:
            intf_aps.sort(key=lambda x: x[8], reverse=True)    # sort by curr-snr

        intf_tot = 0
        intf_coch_snr10 = 0
        for r in intf_aps:
            bss, ess, ch, ap_type, enc, snr, rssi = r[0], r[1], r[2], r[6], r[7], r[8], r[9]
            cbw_phy = r[4] + '/' + r[5]
            apn = bss2apn.get(bss[:17], '')
            intf_tot += 1
            rr = [None, bss, ess, ch, cbw_phy, ap_type, enc, snr, -rssi, apn]

            if isintf(args.band, ch, mych):
                if snr >= 10:
                    rr[0] = RED
                    rslt_coch.append([None, bss, ess, ch, ap_type, snr])
                    intf_coch_snr10 += 1
                else:
                    rr[0] = YELLOW
            rslt.append(rr)


        if args.coch:
            print(f"\n****************** Interfering Co-channel APs seen by {myapn} on ch{mych} ******************\n")
            print_table(rslt_coch)
        elif not args.summary:
            print(f"\n****************** Interfering APs seen by {myapn} on ch{mych} ******************\n")
            print_table(rslt)
            print(f"\nTotal Interfering APs: {intf_tot}, Co-ch APs with SNR>=10: {intf_coch_snr10}\n")
            




