#
#   phycap-distrib.py
#
#   show ap association で、各端末の phy_cap をカウント
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict


def uniq(tbl, col=0):
    ret = []
    k = set()
    for r in tbl:
        if r[col] in k: continue
        k.add(r[col])
        ret.append(r)
    return ret


#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show ap association and display phy_cap breakdown")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    else:
        log.setloglevel(log.LOG_INFO)

    #
    #   parse AP tables
    #
    print("Parsing files ... ", end="")
    aos = AOSParser(args.infile, ["show ap association", "show user-table", "show ap bss-table"], merge=True)
    user_table  = aos.get_table("show user-table")
    assoc_table = aos.get_table("show ap association")
    bss_table   = aos.get_table("show ap bss-table")
    if user_table is None:
        print("show user-table output not found.")
        sys.exit(-1)
    if assoc_table is None:
        print("show ap association output not found.")
        sys.exit(-1)
    if bss_table is None:
        print("show ap bss-table output not found.")
        sys.exit(-1)

    assoc_table = uniq(assoc_table, 2)
    bss_table = uniq(bss_table)
    print(f"done. {len(assoc_table)-1} STAs found.")

    #
    #   create MAC -> OS Type map
    #
    mac2os = {}
    apnctr = defaultdict(lambda: 0)
    flrctr = defaultdict(lambda: 0)
    for r in user_table[1:]:
        mac = r[1]
        apn = r[7]
        apnctr[apn] += 1

        # m = re.match(r'idjktpsy0(\d)', apn)
        # if m:
        #     fl = int(m.group(1))
        #     flrctr[fl] += 1
        m = re.search(r'Floor_(\d\d)', apn)
        if m:
            fl = int(m.group(1))
            flrctr[fl] += 1

        os = r[12]
        if os != "":
            mac2os[mac] = os

    #
    #   create BSS -> channel map
    #
    bss2ch = {}
    for r in bss_table[1:]:
        if r[6] in ('am', 'Spectrum'): continue
        bss = r[0]
        m = re.match(r'(\d+[SE+-]?)/', r[5])
        if not m:
            print(f"Invalid channel: {r}")
            sys.exit(-1)
        bss2ch[bss] = m.group(1)

    #
    #   phy_cap カウント
    #
    n = len(assoc_table)-1
    num5G = 0
    num2G = 0
    numht = 0
    numvht = 0
    numhe = 0
    numss = [0,0,0,0,0]
    os_numss = defaultdict(lambda: [0,0,0,0,0])
    essctr = defaultdict(lambda: 0)
    essctrphy = defaultdict(lambda: [0, 0])
    chctr = defaultdict(lambda: 0)
    for r in assoc_table[1:]:
        bss = r[1]
        mac = r[2]
        essid = r[7]
        phycap = r[15]


        is5G = True if "5GHz" in phycap else False
        isht = True if "-HT-" in phycap else False
        isvht = True if "-VHT-" in phycap else False
        ishe = True if "-HE-" in phycap else False

        essctr[essid] += 1

        if is5G:
            num5G+=1
            essctrphy[essid][1] += 1
        else:
            num2G+=1
            essctrphy[essid][0] += 1
        if isht: numht+=1
        if isvht: numvht+=1
        if ishe: numhe+=1

        r = re.search("-(\d)ss", phycap)
        if r:
            ss = int(r.group(1))
        else:
            ss = 0
        numss[ss]+=1

        if mac in mac2os:
            os = mac2os[mac]
        else:
            os = "unknown"
        os_numss[os][ss] += 1

        chctr[bss2ch[bss]] += 1

    print(f"2.4GHz:{num2G}, 5GHz:{num5G}")
    print(f"non-HT:{n-numht-numvht-numhe}, HT:{numht}, VHT:{numvht}, HE:{numhe}")
    print(f"1ss:{numss[1]}, 2ss:{numss[2]}, 3ss:{numss[3]}, 4ss:{numss[4]}")

    print()
    for os in sorted(os_numss.keys()):
        print(f"{os:10}: ", end="")
        for i in range(1, 4):
            print(f"{i}ss {os_numss[os][i]:>4}", end=", ")
        print()

    print("\nClients per SSID")
    for ess, n in essctr.items():
        print(f"{ess:20}: {n} ({essctrphy[ess][0]}/{essctrphy[ess][1]})")

    print("\nTop 20 populated APs (based on L3 user table)")
    for apn in sorted(apnctr.keys(), key=lambda x:apnctr[x], reverse=True)[:20]:
        print(f"{apn:15}: {apnctr[apn]}")

    print("\nClients per Floor (based on L3 user table)")
    for fl in sorted(flrctr.keys()):
        print(f"{fl}: {flrctr[fl]}")

    print("\nClients per channel")
    for ch in sorted(chctr.keys()):
        print(f"{ch}: {chctr[ch]}  ", end="")
    print()
