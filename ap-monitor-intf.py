#/usr/bin/python3 -u
#
#   ap2-monitor-intf.py
#
#   show ap monitor ap-list の結果をパースし、特定 SSID がどれぐらいの SNR で見えているかを表示
#   AOS 8.10 対応版
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser
from collections import defaultdict

SSIDnames = ["RHC", "RHC_GUEST"]

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description=f"Parse 'show ap monitor ap-list' and search for SSID '{SSIDnames}'")
    parser.add_argument('infile', help="Input files(s) containing 'show ap monitor ap-list' output", type=str, nargs='+')
    #parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)


    apn2ch = {}
    bss2ch = defaultdict(lambda: set())
    aplist = []
    snr_dic = defaultdict(lambda: defaultdict(lambda: 0))
    bss_set = set()

    cmd = "show ap monitor ap-list .+"
    cols = ["bssid", "essid", "band/chan/ch-width/ht-type", "ap-type", "curr-snr"]

    #
    #   parse AP List
    #
    for fn in args.infile:
        print(f"Parsing file {fn} ... ", end="")
        aos = AOSParser(fn, cmd)
        apn = fn[:9]
        aplist.append(apn)

        ap_list_tbl = aos.get_table(cmd, *cols)
        if ap_list_tbl is None:
            print("ap-list table not found.")
            sys.exit(-1)

        for row in ap_list_tbl:
            # check 5GHz APs only
            if not row[2].startswith('5GHz'):
                continue

            try:
                snr = int(row[4])  # curr-snr
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
                sys.exit(1)


            if snr == 0:
                continue

            bss = row[0]
            if bss.endswith('(+)'):
                apn2ch[apn] = ch
                continue

            if row[1] not in SSIDnames:
                continue

            bss = bss[:-1] + 'X'
            snr_dic[apn][bss] = snr
            bss_set.add(bss)
            bss2ch[bss].add(ch)

        print("Done.")

    bss_list = sorted(bss_set)
    print(",," + ",".join(bss_list))
    ch_list = [ "/".join(sorted(list(bss2ch[bss]), key=lambda x:int(x))) for bss in bss_list]
    print(",,"+ ",".join(ch_list))

    aplist.sort()
    for apn in aplist:
        snrlist = []
        for bss in bss_list:
            snrlist.append(str(snr_dic[apn][bss]))
        print(apn + "," + apn2ch[apn] + "," + ",".join(snrlist))


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
