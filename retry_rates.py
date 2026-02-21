#
#   show ap debug client-table の Tx Retry 率を計算
#   同じ AP に対して複数回取得された場合は、AP 全体のリトライ率を計算
#

import sys
import argparse
import mylogger as log
from aos_parser import AOSParser

TX_PKTS_THRESHOLD = 4000      # Tx 4,000パケット未満の端末は除外

#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="calculate Tx retry rate for show ap debug client-table outputs")
    parser.add_argument('files', type=str, nargs='+')
    parser.add_argument('--debug', help='debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    # cmd = "show ap debug client-table ap-name .*"
    cmd = "show ap debug client-table.*"
    #
    #   parse AP tables
    #
    aos = AOSParser(args.files, cmds=[cmd])
    tbls = aos.get_tables(cmd)

    log.info(f"Got {len(tbls)} tables.")
    max_tx_pkts = {}
    rows = {}
    retry_rate = {}
    sta_txpkts_st = {}
    sta_txretr_st = {}
    sta_txpkts_ed = {}
    sta_txretr_ed = {}

    for tbl in tbls:
        idx_tx_pkts = tbl[0].index("Tx_Pkts")
        idx_tx_retr = tbl[0].index("Tx_Retries")
        idx_snr = tbl[0].index("Last_Rx_SNR")
        idx_txrate = tbl[0].index("Tx_Rate")

        for row in tbl[1:]:
            mac = row[0]
            tx_pkts = int(row[idx_tx_pkts])
            tx_retr = int(row[idx_tx_retr])

            # per-STA Tx/Retr values
            sta_txpkts_ed[mac] = tx_pkts
            sta_txretr_ed[mac] = tx_retr
            if mac not in max_tx_pkts:
                sta_txpkts_st[mac] = tx_pkts
                sta_txretr_st[mac] = tx_retr

            if tx_pkts < TX_PKTS_THRESHOLD:
                continue
            try:
                if tx_pkts < max_tx_pkts[mac]:
                    continue
            except KeyError:
                pass
            max_tx_pkts[mac] = tx_pkts
            rows[mac] = row
            retry_rate[mac] = tx_retr / tx_pkts * 100

    #
    #   sort
    #
        clients = list(rows.keys())
        clients.sort(key=lambda x: retry_rate[x], reverse=True)

        print("MAC                 Tx Pkts   Tx Retries  Tx Rate  SNR  Retry(%)")
        print("---                 -------   ----------  -------  ---  --------")
        for mac in clients:
            tx_pkts = rows[mac][idx_tx_pkts]
            tx_retr = rows[mac][idx_tx_retr]
            retr_rate = retry_rate[mac]
            snr = rows[mac][idx_snr]
            txrate = rows[mac][idx_txrate]
            print(f"{mac:20}{tx_pkts:10}{tx_retr:10}  {txrate:6}   {snr:5}{retr_rate:4.2f}")

        print("")

    #   per-STA retry rate
    tot_pkts = 0
    tot_retr = 0
    for mac in sta_txpkts_ed.keys():
        tx_pkts_st = sta_txpkts_st[mac]
        tx_retr_st = sta_txretr_st[mac]
        tx_pkts_ed = sta_txpkts_ed[mac]
        tx_retr_ed = sta_txretr_ed[mac]
        delta_pkts = tx_pkts_ed - tx_pkts_st
        delta_retr = tx_retr_ed - tx_retr_st
        tot_pkts += delta_pkts
        tot_retr += delta_retr
        retr_rate = delta_retr / delta_pkts * 100 if delta_pkts > 0 else 0.0
        print(f"{mac}: st: {tx_retr_st}/{tx_pkts_st}, ed: {tx_retr_ed}/{tx_pkts_ed}, delta: {delta_retr}/{delta_pkts}, Retry%: {retr_rate:.2f}%")

    #   overall retry rate
    if tot_pkts > 0:
        rr = tot_retr / tot_pkts * 100
        print(f"Retry rate on AP: {rr:.2f}% ( {tot_retr} / {tot_pkts} )")

    sys.exit(0)
