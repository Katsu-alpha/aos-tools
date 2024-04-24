#
#   arm-state.py
#
#   show ap arm state をパースし、以下の条件の AP を表示
#       - 5GHz の同じチャネル
#       - SNR >= 10
#

import sys
import re
import argparse
import fileinput
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict


# APpat = "^APKUDKS|^APSMFTM"
# APpat = "^APGTS38"
# APpat = "^idjktpsy"
# APpat = "^APG7"
# APpat = r"^APUMEDA"
# APpat = r"^APHIBFS"

def fln():
    return fileinput.filename() + ":" + str(fileinput.filelineno())

apn2model = {}
apn2group = {}

grp2flr = {'Pasaraya 2nd Fl': 2,
           'Pasaraya 3rd Fl': 3,
           'Pasaraya 4th Fl': 4,
           'Pasaraya 5th Fl': 5,
           'Pasaraya 6th Fl': 6,
           'Pasaraya 7th Fl': 7,
           'Go-Jek Lantai 4': 4,
           'Go-Jek Lantai 5': 5,
           'Go-Jek Lantai 6': 6,
           'Go-Jek Lantai 7': 7,
           }
flrctr = defaultdict(lambda: 0)
flritf = defaultdict(lambda: 0)
grpctr = defaultdict(lambda: 0)
grpitf = defaultdict(lambda: 0)
allctr = 0
allitf = 0


intf_ch = {
    '36': {'36', '36+', '40-'},
    '40': {'40', '36+', '40-'},
    '44': {'44',  '44+', '48-'},
    '48': {'48',  '44+', '48-'},
    '52': {'52',  '52+', '56-'},
    '56': {'56',  '52+', '56-'},
    '60': {'60',  '60+', '64-'},
    '64': {'64',  '60+', '64-'},
    '100': {'100', '100+', '104-'},
    '104': {'104', '100+', '104-'},
    '108': {'108', '108+', '112-'},
    '112': {'112', '108+', '112-'},
    '116': {'116', '116+', '120-'},
    '120': {'120', '116+', '120-'},
    '124': {'124', '124+', '128-'},
    '128': {'128', '124+', '128-'},
    '132': {'132', '132+', '136-'},
    '136': {'136', '132+', '136-'},
    '140': {'140', '140+', '144-'},
    '149': {'149', '149+', '153-'},
    '153': {'153', '149+', '153-'},
    '157': {'157', '157+', '161-'},
    '161': {'161', '157+', '161-'},
    '165': {'165'},
    '36+': {'36', '40', '36+', '40-'},
    '40-': {'36', '40', '36+', '40-'},
    '44+': {'44', '48', '44+', '48-'},
    '48-': {'44', '48', '44+', '48-'},
    '52+': {'52', '56', '52+', '56-'},
    '56-': {'52', '56', '52+', '56-'},
    '60+': {'60', '64', '60+', '64-'},
    '64-': {'60', '64', '60+', '64-'},
    '100+': {'100', '104', '100+', '104-'},
    '104-': {'100', '104', '100+', '104-'},
    '108+': {'108', '112', '108+', '112-'},
    '112-': {'108', '112', '108+', '112-'},
    '116+': {'116', '120', '116+', '120-'},
    '120-': {'116', '120', '116+', '120-'},
    '124+': {'124', '128', '124+', '128-'},
    '128-': {'124', '128', '124+', '128-'},
    '132+': {'132', '136', '132+', '136-'},
    '136-': {'132', '136', '132+', '136-'},
    '149+': {'149', '153', '149+', '153-'},
    '153-': {'149', '153', '149+', '153-'},
    '157+': {'157', '161', '157+', '161-'},
    '161-': {'157', '161', '157+', '161-'},
}


def parse_nbr_data(out, myapn, mych):
    global apn2model, apn2group
    global allctr, allitf

    if 'APpat' in globals() and not re.search(APpat, myapn):
        return

    cmd = out[0].strip()
    aos = AOSParser("".join(out), [cmd])
    tbl = aos.get_table(cmd)
    if tbl is None or len(tbl) == 0:
        log.warn(fln() + f": No Neighbor Data found for AP {myapn}")
        print(f'{myapn},{apn2group[myapn]},{apn2model[myapn]},"{mych}",0')
        return
    tbl2 = []
    ncov = 0        # neighbor AP with SNR >= 25
    for r in tbl[1:]:
        apn = r[0]
        if ':' in apn:
            # log.warn(f"skipping non-AP entry: {apn}")
            continue
        snr = int(r[2])
        if snr >= 25: ncov += 1

        m = re.match(r'(\d+)[+-]?/([\d\.]+)', r[5])
        if not m:
            m = re.match(r'(\d+)[+-]?/([\d\.]+)', r[4])
        if m:
            ch = m.group(1)
            pwr = m.group(2)
        else:
            print(f"Can't parse Ch/EIRP: {fileinput.filelineno()}: {r[5]}")
            exit()

        if ch in intf_ch[mych]:
            tbl2.append([apn, snr, ch, pwr])


    # print(f'AP "{myapn}" Ch={mych}')
    # print("Name                     Model  SNR   Ch  EIRP")
    # print("-----                    -----  ---   --  ----")
    nintf = 0
    for r in tbl2:
        # print(f"{r[0]:25}{apn2model[r[0]]:5}{r[1]:>5}{r[2]:>5} {r[3]:>5}")
        if int(r[1]) >= 10:
            nintf += 1
    # print(f"Number of co-channel AP (SNR>=10): {nintf}")
    # print(f"Number of coverage AP (SNR>=25): {ncov}")
    # print()

    print(f'{myapn},{apn2group[myapn]},{apn2model[myapn]},"{mych}",{nintf}')

    apg = apn2group[myapn]

    # フロア名取得
    # fl = grp2flr[apg[:15]]
    # fl = apg[5:7]
    fl = myapn[3:5]
    # m = re.search(r'KUDKS(\d+)', apg)
    # if m:
    #     fl = m.group(1)
    # else:
    #     m = re.search(r'SMFTM(\d+)', apg)
    #     if m:
    #         fl = m.group(1)
    #     else:
    #         # log.err(f"can't get floor info from group name: {apg}")
    #         # sys.exit(-1)
    #         fl = "n/a"

    # m = re.match(r'GTS(\d+)', apg)
    # if m:
    #     fl = m.group(1)
    # else:
    #     fl = "n/a"

    flrctr[fl] += 1
    flritf[fl] += nintf
    allctr += 1
    allitf += nintf
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

    print("AP Name,Group,Type,Channel,Co-ch AP")
    out = []
    cont = 0
    for l in f:
        if cont != 0 and l.startswith('Legend: '):
            parse_nbr_data(out, apn, ch)
            cont = 0
            continue
        elif cont != 0:
            out.append(l)
            continue

        # cont == 0
        if not l.startswith('AP:'): continue

        r = re.match(r'AP:([\w-]+) MAC:[:\w]+.* Channel:(\d+[SE+-]?)+', l)
        if r:
            apn = r.group(1)
            ch = r.group(2)
            if int(re.sub(r'[SE+-]', '', ch)) < 36:
                continue
            cont = 1
            out = ["show ap arm state\n"]
            continue

        continue

    # for apg in sorted(grpctr.keys()):
    #     avg = grpitf[apg] / grpctr[apg]
    #     print(f"{apg:5}: {avg:6.2f}")

    #
    #   Average number of co-channel AP per floor
    #

    for fl in sorted(flrctr.keys()):
        avg = flritf[fl] / flrctr[fl]
        print(f"{fl:5}: {avg:6.2f} ({flrctr[fl]} APs)")

    print(f"Total avg intf APs: {allitf/allctr:.2f}")