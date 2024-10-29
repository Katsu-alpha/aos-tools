#
#   cli-table.py
#   show ap debug client-table をパース
#

import sys
import re
import mylogger as log
import argparse
from aos_parser import AOSParser
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


def col_red(s, thresh, col=5):
    if int(s) <= thresh:
        return RED + f"{s:{col}}" + RESET
    return f"{s:{col}}"

def col_yel_red(s, thresh1, thresh2, col=5):
    if int(s) <= thresh2:
        return RED + f"{s:{col}}" + RESET
    if int(s) <= thresh1:
        return YELLOW + f"{s:{col}}" + RESET
    return f"{s:{col}}"

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description=f"Parse 'show ap debug client-table'")
    parser.add_argument('infile', help="Input files(s) containing 'show ap monitor ap-list' output", type=str, nargs='+')
    #parser.add_argument('outfile', help='Output Excel file', type=str, nargs='?', default='')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)



    cmd = "show ap debug client-table .+"
    cols = ["MAC", "ESSID", "BSSID", "Tx_Rate", "Rx_Rate", "Last_Rx_SNR", "TX_Chains"]


    #
    #   parse Client Table
    #
    tbl = []
    for fn in args.infile:
        #print(f"Parsing file {fn} ... ", end="")
        try:
            aos = AOSParser(fn, cmd)
        except UnicodeDecodeError as e:
            aos = AOSParser(fn, cmd, encoding='shift-jis')

        cli_tbl = aos.get_table(cmd, *cols)
        if cli_tbl is None:
            print(f"Client Table not found in {fn}.")
            continue

        tbl.extend(cli_tbl)


    #
    #   print results
    #
    print("MAC                ESSID                 BSSID              Tx    Rx    SNR   TX_Chains")
    print("---                -----                 -----              --    --    ---   ---------")

    for row in tbl:
        mac,essid,bssid,tx_rate,rx_rate,rx_snr,tx_chains = row
        print(f'{mac}  {essid:20}  {bssid}  {col_red(tx_rate,54)} {col_red(rx_rate,54)} {col_yel_red(rx_snr,24,9)} {tx_chains}')

    sys.exit(0)
