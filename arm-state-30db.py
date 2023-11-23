#
#   arm-state.py
#
#   show ap arm state をパースし、以下の条件の AP を表示
#       - SNR 25dB 以上
#

import sys
import re
import argparse
import fileinput
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict

def fln():
    return fileinput.filename() + ":" + str(fileinput.filelineno())

apn2model = {}
apn2group = {}
apgctr = defaultdict(lambda: 0)
apgcov = defaultdict(lambda: 0)
grp2flr = {'Pasaraya 2nd Floor': 2,
           'Pasaraya 3rd Floor': 3,
           'Pasaraya 4th Floor': 4,
           'Pasaraya 5th Floor': 5,
           'Pasaraya 6th Floor': 6,
           'Pasaraya 7th Floor': 7,
           'Go-Jek Lantai 4': 4,
           'Go-Jek Lantai 5': 5,
           'Go-Jek Lantai 6': 6,
           'Go-Jek Lantai 7': 7,
           }
flrctr = defaultdict(lambda: 0)
flrcov = defaultdict(lambda: 0)

def parse_nbr_data(out, myapn, mych):
    global apn2model, apn2group
    global apgctr, apgcov
    cmd = out[0].strip()
    aos = AOSParser("".join(out), [cmd])
    tbl = aos.get_table(cmd)
    if tbl is None or len(tbl) == 0:
        apg = apn2group[myapn]
        #m = re.search(r'Floor_(\d\d)', apg)
        m = re.search(r'GTS(\d\d)', apg)
        if m:
            fl = m.group(1)
        else:
            # log.err(f"can't get floor info from group name: {apg}")
            # sys.exit(-1)
            fl = 'n/a'
        # if len(apg) > 18:
        #     apg = apg[:18]
        # fl = grp2flr[apg]
        apgctr[apg] += 1
        flrctr[fl] += 1
        print(f"{myapn},{apg},{mych},0")
        return
    tbl2 = []
    for r in tbl[1:]:
        apn = r[0]
        if ':' in apn:
            continue

        snr = int(r[2])
        r = re.match(r'(\d+)/([\d\.]+)', r[5])
        if r:
            ch = r.group(1)
            pwr = r.group(2)
        else:
            print(f"Can't parse Ch/EIRP: {r[5]}")
            exit()

        if snr >= 25:
            tbl2.append([apn, snr, ch, pwr])

    # print(f'AP "{myapn}" Ch={mych}')
    # print("Name                     Model  SNR   Ch  EIRP")
    # print("-----                    -----  ---   --  ----")
    # for r in tbl2:
    #     print(f"{r[0]:25}{apn2model[r[0]]:5}{r[1]:>5}{r[2]:>5} {r[3]:>5}")
    # print(f"Number of APs (SNR>=25): {len(tbl2)}")
    # print()

    apg = apn2group[myapn]
    #m = re.search(r'Floor_(\d\d)', apg)
    m = re.search(r'GTS(\d\d)', apg)
    if m:
        fl = m.group(1)
    else:
        # log.err(f"can't get floor info from group name: {apg}")
        # sys.exit(-1)
        fl = 'n/a'
    # if len(apg) > 18:
    #     apg = apg[:18]
    # fl = grp2flr[apg]
    apgctr[apg] += 1
    apgcov[apg] += len(tbl2)
    flrctr[fl] += 1
    flrcov[fl] += len(tbl2)
    print(f"{myapn},{apg},{mych},{len(tbl2)}")

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show ap tech and display neighbor APs")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    #
    #   parse ap database and get apname -> ap model mapping
    #
    aos = AOSParser(args.infile, [AP_DATABASE_LONG_TABLE], merge=True)
    ap_database_tbl = aos.get_table(AP_DATABASE_LONG_TABLE)
    if ap_database_tbl is None:
        print("show ap database long output not found.")
        sys.exit(-1)

    for r in ap_database_tbl[1:]:
        apn2model[r[0]] = r[2]
        apn2group[r[0]] = r[1]

    #
    #   parse show ap arm state
    #

    f = fileinput.input(args.infile, encoding='utf-8')
    for l in f:
        if l.startswith('show ap arm state'):
            break

    out = []
    cont = 0
    for l in f:
        if cont != 0 and l.startswith('Legend: '):
            # if apn.startswith('APGTS23'):
            parse_nbr_data(out, apn, ch)
            cont = 0
            continue
        elif cont != 0:
            out.append(l)
            continue

        # cont == 0
        if not l.startswith('AP:'): continue

        r = re.match(r'AP:([\w-]+) MAC:[:\w]+ Band:5GHz Channel:(\d+)+', l)
        if r:
            apn = r.group(1)
            ch = r.group(2)
            cont = 1
            out = ["show ap arm state\n"]
            continue

        continue


    for apg in sorted(apgctr.keys()):
        avg = apgcov[apg] / apgctr[apg]
        print(f"{apg:20}: {avg:6.2f}")

    for fl in sorted(flrctr.keys()):
        avg = flrcov[fl] / flrctr[fl]
        print(f"{fl:5}: {avg:6.2f}")
