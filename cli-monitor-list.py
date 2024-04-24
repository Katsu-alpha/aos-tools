#/usr/bin/python3 -u
#
#   cli-monitor-list.py
#
#   show ap monitor client-list の結果をパースし、AP に接続していないものを、curr_snr でソートして出力
#   show ap bss-table ap-name の結果から、自分自身の BSSID を読み込み、自分自身に接続している STA は除外する
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

chset = {
    '36+': {'36', '40'},
    '40-': {'36', '40'},
    '44+': {'44', '48'},
    '48-': {'44', '48'},
    '52+': {'52', '56'},
    '56-': {'52', '56'},
    '60+': {'60', '64'},
    '64+': {'60', '64'},
    '64-': {'60', '64'},
    '100+': {'100', '104'},
    '104-': {'100', '104'},
    '108-': {'104', '108'},
    '108+': {'108', '112'},
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
    '60S': {'36', '40', '44', '48', '52', '56', '60', '64'},
}

for i in [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 144, 149, 153, 157, 161, 165]:
    chset[str(i)] = {str(i)}


def isIntf(ch1, ch2):
    if chset[ch1]&chset[ch2]:
        return True
    return False

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Join 'show ap database' and 'show ap active' tables and write the result to an MS Excel file")
    parser.add_argument('infile', help="Input file containing 'show ap monitor ap-list' output", type=str, nargs='+')
    #parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    parser.add_argument('--summary', help='Summary only', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    #
    #   parse Client List/BSS table
    #
    # print("Parsing files ... ", end="")
    cmd = ["show ap monitor client-list .+","show ap bss-table ap-name .+"]
    cols = ["mac", "bssid", "essid", "band/chan/ch-width/ht-type", "sta-type", "snr", "rssi"]
    aos = AOSParser(args.infile, cmd, merge=True)
    sta_list_tbl = aos.get_table(cmd[0], *cols)
    ap_bss_tbl = aos.get_table(cmd[1])
    if sta_list_tbl is None:
        print("show ap monitor client-list output not found.")
        sys.exit(-1)

    # 自身の BSSID 一覧
    mybss = set()
    if ap_bss_tbl is not None:
        for r in ap_bss_tbl:
            mybss.add(r[0])

    # print("done.")

    #
    #   Process client-list table
    #
    stalist = []
    mych = ''       # 5GHz channel
    for row in sta_list_tbl:
        bss = row[1]
        try:
            snr  = int(row[5])    # snr
            rssi = int(row[6])    # rssi
            r = re.search("/(\d+[SE+-]?)/(\d+MHz)/([\w-]+)", row[3])   # "5GHz/36+/40MHz/VHT"
            if r:
                ch  = r.group(1)
                cbw = r.group(2)
                phy = r.group(3)
                pch = int(re.sub(r'[SE+-]', '', ch))
            else:
                print(f"invalid phy column: {row[3]}")
                sys.exit(1)
        except ValueError:
            print(f"Can't parse row: {row}")
            # sys.exit(1)
            continue

        #               mac          essid                      type
        stalist.append([row[0], bss, row[2], ch, pch, cbw, phy, row[4], snr, rssi])
        if mych=='' and bss in mybss and pch >= 36:
            mych = ch


    #
    #   結果表示
    #
    stalist.sort(key=lambda x: x[8], reverse=True)
    rslt = [
        "****************** Connected STAs ******************",
        "",
        "                      MAC                 BSSID               ESSID    Chan     CBW/PHY      Type   SNR  RSSI",
        "                      ---                 -----               -----    ----     -------      ----   ---  ----",
        ]

    idx = 0
    for r in stalist:
        bss, sta_type, pch = r[1], r[7], r[4]
        if bss in mybss and pch >= 36:
            cbw_phy = r[5] + '/' + r[6]
            ch = r[3]
            snr = r[8]
            idx += 1
            l = f"{idx:>3}{r[0]:>22}{bss:>22}{r[2]:>20}{r[3]:>8}{cbw_phy:>12}{sta_type:>10}{r[8]:>6}{-r[9]:>6}"

            rslt.append(l)

    if not args.summary:
        print("\n".join(rslt))
        print("\n")


    rslt = [
        "****************** Non-connected Valid STAs ******************",
        "",
        "                      MAC                 BSSID               ESSID    Chan     CBW/PHY      Type   SNR  RSSI",
        "                      ---                 -----               -----    ----     -------      ----   ---  ----",
        ]

    idx = 0
    for r in stalist:
        bss, sta_type, pch = r[1], r[7], r[4]
        if bss in mybss or sta_type != 'valid' or pch < 36:
            continue
        ch = r[3]
        snr = r[8]
        cbw_phy = r[5] + '/' + r[6]
        idx += 1
        l = f"{idx:>3}{r[0]:>22}{bss:>22}{r[2]:>20}{ch:>8}{cbw_phy:>12}{sta_type:>10}{r[8]:>6}{-r[9]:>6}"

        if isIntf(ch, mych):
            if snr >= 10:
                rslt.append(RED + l + RESET)
            else:
                rslt.append(YELLOW + l + RESET)
        else:
            rslt.append(l)

    if not args.summary:
        print("\n".join(rslt))
        print("\n")



    rslt = [
        "****************** Non-valid STAs ******************",
        "",
        "                      MAC                 BSSID                    ESSID    Chan     CBW/PHY         Type   SNR  RSSI",
        "                      ---                 -----                    -----    ----     -------         ----   ---  ----",
        ]

    idx = 0
    for r in stalist:
        bss, sta_type, pch = r[1], r[7], r[4]
        if sta_type == 'valid' or pch < 36:
            continue
        ch = r[3]
        snr = r[8]
        cbw_phy = r[5] + '/' + r[6]
        idx += 1
        l = f"{idx:>3}{r[0]:>22}{bss:>22}{r[2]:>25}{ch:>8}{cbw_phy:>12}{sta_type:>13}{r[8]:>6}{-r[9]:>6}"

        if isIntf(ch, mych):
            if snr >= 10:
                rslt.append(RED + l + RESET)
            else:
                rslt.append(YELLOW + l + RESET)
        else:
            rslt.append(l)

    if not args.summary:
        print("\n".join(rslt))
    sys.exit(0)

