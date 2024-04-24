#/usr/bin/python3 -u
#
#   ap-monitor-list-sum.py
#
#   show ap monitor ap-list の結果をパースし、co-ch AP数、3rd party AP 数 (SNR>=10) のサマリ表示
#   複数ファイル指定可能
#   複数の monitor ap-list テーブルがある場合、同一 BSSID のうち SNR が最大のもののみ表示
#   AOS 8.10 対応
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

SNR_THRESHOLD = 10

chset = {
    '36+': {'36', '40'},
    '40-': {'36', '40'},
    '44+': {'44', '48'},
    '48-': {'44', '48'},
    '52+': {'52', '56'},
    '56-': {'52', '56'},
    '60+': {'60', '64'},
    '64-': {'60', '64'},
    '64+': set(),
    '100+': {'100', '104'},
    '104-': {'100', '104'},
    '108+': {'108', '112'},
    '108-': set(),
    '112-': {'108', '112'},
    '116+': {'116', '120'},
    '120-': {'116', '120'},
    '124+': {'124', '128'},
    '128-': {'124', '128'},
    '132+': {'132', '136'},
    '136-': {'132', '136'},
    '140+': {'140', '144'},
    '144-': {'140', '144'},
    '149+': {'149', '153'},
    '153-': {'149', '153'},
    '157+': {'157', '161'},
    '161-': {'157', '161'},
    '36E': {'36', '40', '44', '48'},
    '40E': {'36', '40', '44', '48'},
    '44E': {'36', '40', '44', '48'},
    '48E': {'36', '40', '44', '48'},
    '52E': {'52', '56', '60', '64'},
    '56E': {'52', '56', '60', '64'},
    '60E': {'52', '56', '60', '64'},
    '64E': {'52', '56', '60', '64'},
    '100E': {'100', '104', '108', '112'},
    '104E': {'100', '104', '108', '112'},
    '108E': {'100', '104', '108', '112'},
    '112E': {'100', '104', '108', '112'},
    '116E': {'116', '120', '124', '128'},
    '120E': {'116', '120', '124', '128'},
    '124E': {'116', '120', '124', '128'},
    '128E': {'116', '120', '124', '128'},
    '132E': {'132', '136', '140', '144'},
    '136E': {'132', '136', '140', '144'},
    '140E': {'132', '136', '140', '144'},
    '144E': {'132', '136', '140', '144'},
    '149E': {'149', '153', '157', '161'},
    '153E': {'149', '153', '157', '161'},
    '157E': {'149', '153', '157', '161'},
    '161E': {'149', '153', '157', '161'},
}

for i in [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165]:
    chset[str(i)] = {str(i)}


def isIntf(ch1, ch2):
    if chset[ch1]&chset[ch2]:
        return True
    return False


def parse_aplist(fn):
    #
    #   parse AP List
    #
    cmd = "show ap monitor ap-list .+"
    aos = AOSParser(fn, cmd)
    cols = ["bssid", "essid", "band/chan/ch-width/ht-type", "ap-type", "encr", "curr-snr", "curr-rssi"]
    ap_list_tbl = aos.get_table(cmd, *cols)
    if ap_list_tbl is None:
        print("show ap monitor ap-list output not found.")
        sys.exit(-1)

    #
    #   Process Monitor AP List
    #
    aplist = []
    mych = ''
    for row in ap_list_tbl:
        if not row[2].startswith('5GHz'):
            continue

        bss = row[0]
        try:
            row[5] = int(row[5])    # curr-snr
            row[6] = int(row[6])    # curr-rssi
            r = re.search(r"/(\d+[SE+-]?)/(\d+MHz)/(\w+)", row[2])   # "5GHz/36+/40MHz/VHT"
            if r:
                ch = r.group(1)     # ex. "52E"
                cbw = r.group(2)    # ex. "80MHz"
                phy = r.group(3)    # ex. "HE"
                pch = int(re.sub(r'[SE+-]', '', ch))
                if mych == '' and bss.endswith('(+)'):
                    mych = ch
            else:
                print(f"invalid phy column: {row[2]}")
                sys.exit(1)
        except ValueError:
            print(f"Can't parse row: {row}")
            # sys.exit(1)
            continue
        #                   essid                      type    encr    snr     rssi
        aplist.append([bss, row[1], ch, pch, cbw, phy, row[3], row[4], row[5], row[6]])

    #
    #   Count co-ch APs and intf APs
    #
    #   co-ch AP: BSSID 末尾が 0 で、ap-type が valid で同一チャネルにあり、SNR が 10 以上
    #   intf AP: ap-type が valid 以外で、SNR が 10 以上
    #
    coch = 0
    intf = 0
    intf_ap = []
    for r in aplist:
        bss, ch, ap_type, snr = r[0], r[2], r[6], r[8]
        if bss.endswith('0') and ap_type == 'valid' and isIntf(ch, mych) and snr >= SNR_THRESHOLD:
            coch += 1
        if ap_type != 'valid' and snr >= SNR_THRESHOLD:
            intf += 1
            intf_ap.append(r)

    return intf_ap, coch, intf

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Count co-channel APs and interfering APs")
    parser.add_argument('infile', help="Input file containing 'show ap monitor ap-list' output", type=str, nargs='+')
    #parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    coch_tot = 0
    intf_all = {}
    for fn in args.infile:
        print(f"Parsing file {fn} ... ", end="")
        intf_ap, coch, intf = parse_aplist(fn)
        print(f"done. co-ch APs: {coch}, 3rd party APs: {intf}")
        coch_tot += coch

        for r in intf_ap:
            bss, essid, ch, cbw, phy, encr, snr = r[0], r[1], r[2], r[4], r[5], r[7], int(r[8])
            if bss not in intf_all:
                intf_all[bss] = [essid, ch, cbw, phy, encr, snr]
            else:
                if snr > intf_all[bss][5]:
                    intf_all[bss] = [essid, ch, cbw, phy, encr, snr]


    print(f"\nTotal co-ch APs: {coch_tot}, Total 3rd party APs: {len(intf_all)}")
    print("\n****************** 3rd party APs ******************")
    print("BSSID               ESSID                        CHAN   CBW     PHY            Enc   SNR")
    for bss in sorted(intf_all.keys(), key=lambda x:intf_all[x][5], reverse=True):
        r = intf_all[bss]
        print(f"{bss:20}{r[0]:25}{r[1]:>8}{r[2]:>8}{r[3]:>6}{r[4]:>15}{r[5]:>6}")


    sys.exit(0)
