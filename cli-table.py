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
import pandas as pd
import matplotlib.pyplot as plt

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

# rate_buckets = [0, 30, 60, 100, 150, 220, 300]
# rate_buckets = [i*20 for i in range(16)]
rate_buckets = [0, 20, 40, 70, 100, 140, 180, 230, 300]
snr_buckets = [0, 10, 20, 30, 40, 50, 100]

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


def rate_idx(rate):
    global rate_buckets
    for i, r in enumerate(rate_buckets):
        if rate < r:
            return i-1
    return len(rate_buckets) - 1

def snr_idx(snr):
    global snr_buckets
    for i, r in enumerate(snr_buckets):
        if snr < r:
            return i-1
    return len(snr_buckets) - 1


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
    cols = ["MAC", "ESSID", "BSSID", "Tx_Pkts", "Tx_Retries", "Tx_Rate", "Rx_Rate", "Last_Rx_SNR", "TX_Chains"]


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
    print("MAC                ESSID                 BSSID              Retry(%)  Tx    Rx   SNR   TX_Chains")
    print("---                -----                 -----              --------  --    --   ---   ---------")

    tx_hist = [0] * len(rate_buckets)
    rx_hist = [0] * len(rate_buckets)
    snr_hist = [0] * len(snr_buckets)
    for row in sorted(tbl, key=lambda x: int(x[5]), reverse=True):
        mac,essid,bssid,tx_pkts,tx_retr,tx_rate,rx_rate,rx_snr,tx_chains = row

        # rate histogram (count only 2SS clients)
        if tx_chains.startswith('2'):
            tx_hist[rate_idx(int(tx_rate))+1] += 1
            rx_hist[rate_idx(int(rx_rate))+1] += 1

        snr_hist[snr_idx(int(rx_snr))+1] += 1

        # calculate retry rate
        tx_pkts = int(tx_pkts)
        tx_retr = int(tx_retr)
        if tx_pkts > 300:
            retr_rate = f"{tx_retr / tx_pkts * 100:.1f}%"
        else:
            retr_rate = 'n/a'

        # print row
        print(f'{mac}  {essid:20}  {bssid}  {retr_rate:>7}  {col_red(tx_rate,54)} {col_red(rx_rate,54)}  {col_yel_red(rx_snr,24,9)} {tx_chains}')



    #
    #   Tx/Rx rate histogram
    #
    max_hist = max(max(tx_hist), max(rx_hist))
    rate_label = []
    for r1, r2 in zip(rate_buckets[:-1], rate_buckets[1:]):
        rate_label.append(f"{r1} - {r2-1}")

    df = pd.DataFrame({'Tx': tx_hist[1:], 'Rx': rx_hist[1:]}, index=rate_label)
    print(df)

    fig, axs = plt.subplots(2, 1, figsize=(8,10))
    fig.suptitle('Rate Histograms', fontsize=24, fontweight='bold', font='Calibri')

    df.plot(ax=axs[0], title='Tx Rate (AP->STA, 2ss clients)', y='Tx', kind='bar', width=1,
            color='limegreen', edgecolor='black', ylim=[0, max_hist+5], legend=False, zorder=3)
    axs[0].grid(visible=True, axis='y', ls='--', zorder=0)
    axs[0].tick_params(rotation=0, labelsize=8)
    for i, v in enumerate(tx_hist[1:]):
        axs[0].text(i, v+1, str(v), ha='center', fontweight='bold')

    df.plot(ax=axs[1], title='Rx Rate (STA->AP, 2ss clients)', y='Rx', kind='bar', width=1,
            color='royalblue', edgecolor='black', ylim=[0, max_hist+5], legend=False, zorder=3)
    axs[1].grid(visible=True, axis='y', ls='--', zorder=0)
    axs[1].tick_params(rotation=0, labelsize=8)
    for i, v in enumerate(rx_hist[1:]):
        axs[1].text(i, v+1, str(v), ha='center', fontweight='bold')

    #
    #   SNR histogram
    #
    snr_label = []
    for i, r in enumerate(snr_buckets):
        if i==0: continue
        snr_label.append(f"{snr_buckets[i-1]} - {r-1}")

    df = pd.DataFrame({'SNR': snr_hist[1:]}, index=snr_label)
    ax = df.plot(title='SNR Histogram', y='SNR', kind='bar', width=1,
            color='orange', edgecolor='black', legend=False, zorder=3)
    ax.grid(visible=True, axis='y', ls='--', zorder=0)
    ax.tick_params(rotation=0, labelsize=8)
    for i, v in enumerate(snr_hist[1:]):
        ax.text(i, v+1, str(v), ha='center', fontweight='bold')

    #
    #   Draw bar charts
    #
    # plt.tight_layout()
    # plt.xticks(ha='center')
    plt.subplots_adjust(hspace=0.3)
    # plt.savefig('chart.png')

    plt.show()
