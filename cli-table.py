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


    print("MAC                ESSID                 BSSID              Tx    Rx    SNR   TX_Chains")
    print("---                -----                 -----              --    --    ---   ---------")
    #
    #   parse Client Table
    #
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

        for row in cli_tbl:
            mac,essid,bssid,tx_rate,rx_rate,rx_snr,tx_chains = row
            print(f'{mac}  {essid:20}  {bssid}  {tx_rate:5} {rx_rate:5} {rx_snr:5} {tx_chains}')

    sys.exit(0)
