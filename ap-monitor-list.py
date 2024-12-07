#/usr/bin/python3 -u
#
#   ap2-monitor-list.py
#
#   show ap monitor ap-list の結果をパースし、valid/interfering に分け、curr_snr でソートして出力
#   show ap bss-table を含むファイルを追加で指定すると、AP名を解決して表示
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
    '36S': {'36', '40', '44', '48', '52', '56', '60', '64'},
    '48S': {'36', '40', '44', '48', '52', '56', '60', '64'},
    '60S': {'36', '40', '44', '48', '52', '56', '60', '64'},
    '64S': {'36', '40', '44', '48', '52', '56', '60', '64'},
    '100S': {'100', '104', '108', '112', '116', '120', '124', '128'},
    '149S': {'149', '153', '157', '161', '165'},
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
        description="Parse 'show ap monitor ap-list' and sort valid/intf APs with SNR descending order")
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
    #   parse AP List
    #
    # print("Parsing files ... ", end="")
    cmd = ["show ap monitor ap-list .+","show ap bss-table"]
    cols = ["bssid", "essid", "band/chan/ch-width/ht-type", "ap-type", "encr", "curr-snr", "curr-rssi"]
    aos = AOSParser(args.infile, cmd, merge=True)
    ap_list_tbl = aos.get_table(cmd[0], *cols)
    ap_bss_tbl = aos.get_table(cmd[1])
    if ap_list_tbl is None:
        print("show ap monitor ap-list output not found.")
        sys.exit(-1)

    # BSSID -> AP Name の辞書を作成
    bss2apn = defaultdict(lambda: "")
    if ap_bss_tbl is not None:
        for r in ap_bss_tbl:
            bss2apn[r[0]] = r[8]

    # print("done.")

    #
    #   Process ap-list table
    #
    aplist = []
    mych = ''       # 5GHz channel
    for row in ap_list_tbl:
        bss = row[0]
        try:
            row[5] = int(row[5])    # curr-snr
            row[6] = int(row[6])    # curr-rssi
            r = re.search("/(\d+[SE+-]?)/(\d+MHz)/(\w+)", row[2])   # "5GHz/36+/40MHz/VHT"
            if r:
                ch = r.group(1)
                cbw = r.group(2)
                phy = r.group(3)
                pch = int(re.sub(r'[SE+-]', '', ch))
            else:
                print(f"invalid phy column: {row[2]}")
                sys.exit(1)
        except ValueError:
            print(f"Can't parse row: {row}")
            # sys.exit(1)
            continue

        #              bssid   essid                      type    encr    snr     rssi
        aplist.append([row[0], row[1], ch, pch, cbw, phy, row[3], row[4], row[5], row[6]])
        if mych=='' and bss.endswith('(+)') and pch >= 36:
            mych = ch
            myapn = bss2apn[bss[:17]]


    #
    #   結果表示
    #
    aplist.sort(key=lambda x: x[8], reverse=True)
    rslt = [
        "****************** Valid APs (base BSS only) ******************",
        "",
        "                    BSSID               ESSID    Chan     CBW/PHY      Type               Enc   SNR  RSSI  AP Name",
        "                    -----               -----    ----     -------      ----               ---   ---  ----  -------",
        ]

    valid_tot = 0
    valid_coch_snr10 = 0
    for r in aplist:
        bss, ap_type, pch = r[0], r[6], r[3]
        if (bss.endswith('0') or bss.endswith('0(+)')) and ap_type == "valid" and pch >= 36:
            cbw_phy = r[4] + '/' + r[5]
            apn = bss2apn[bss[:17]]
            ch = r[2]
            snr = r[8]
            valid_tot += 1
            l = f"{valid_tot:>3}{bss:>22}{r[1]:>20}{r[2]:>8}{cbw_phy:>12}{r[6]:>10}{r[7]:>18}{r[8]:>6}{-r[9]:>6}  {apn}"

            if bss.endswith('(+)'):
                rslt.append(GREEN + l + RESET)
            elif isIntf(ch, mych):
                if snr >= 10:
                    rslt.append(RED + l + RESET)
                    valid_coch_snr10 += 1
                else:
                    rslt.append(YELLOW + l + RESET)
            else:
                rslt.append(l)

    if not args.summary:
        print("\n".join(rslt))
        print(f"\nTotal Valid APs: {valid_tot}, Co-ch APs with SNR>=10: {valid_coch_snr10}\n")


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
        if ap_type != "valid" and pch >= 36:
            cbw_phy = r[4] + '/' + r[5]
            apn = bss2apn[bss]
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

    if args.summary:
        print(f"{myapn}: {valid_tot} / {valid_coch_snr10} / {intf_coch_snr10}")
    sys.exit(0)





    #
    #   Create Excel
    #
    wb = Workbook()
    ws = wb.active
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    f = Font(name='Consolas')
    for row in ws.iter_rows(min_row=1):
        for cell in row:
            cell.font = f

    widths = [25, 30, 10, 20, 20, 13, 15, 10, 10, 15, 10, 10]
    for i,w in enumerate(widths):
        ws.column_dimensions[chr(65+i)].width = w

    f = Font(name='Arial', bold=True, size=9)
    Ses = PatternFill(fgColor="BDD7EE", fill_type="solid")
    for cell in ws['A1':'L1'][0]:
        cell.fill = Ses
        cell.font = f

    ws.auto_filter.ref = "A:L"
    ws.freeze_panes = "A2"


    #
    #   output to file
    #
    print(f"Writing to {xlsfile} ... ", end="")
    wb.save(xlsfile)
    print("done.")

    sys.exit(0)
