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
import matplotlib.pyplot as plt

DrawGraph = True

#
#   get floor name
#
def floorname(apn):
    # m = re.search(r'Floor_(\d\d)', apn)
    # m = re.search(r'hvnap([0-9b]+)fap', apn, re.IGNORECASE)
    m = re.search(r'(\d+|[GM])F', apn)
    if m:
        return m.group(1)
    else:
        return 'n/a'


def uniq(tbl, col=0):
    ret = []
    k = set()
    for r in tbl:
        if r[col] in k: continue
        k.add(r[col])
        ret.append(r)
    return ret


wedgep = {'edgecolor': 'white', 'linewidth': 0.5}
textp = {'fontsize': 20, 'fontweight': 'bold'}

def drawpie(ax, data, colors):
    global wedgep, textp
    patches, texts, pcts = ax.pie(
        data.values(), labels=data.keys(), autopct='%1.1f%%', colors=colors, wedgeprops=wedgep, textprops=textp)
    for i, p in enumerate(patches):
        texts[i].set_color(p.get_facecolor())


#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show ap association and display phy_cap breakdown")
    parser.add_argument('infile', help="Input file(s)", type=str, nargs='+')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    parser.add_argument('--pattern', '-p', help='reged for AP name', type=str, default='.*')
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
    print(f"done.")

    #
    #   create MAC -> OS Type map
    #
    mac2os = {}
    apnctr = defaultdict(lambda: 0)
    flrctr = defaultdict(lambda: 0)
    for r in user_table[1:]:
        apn = r[7]
        if not re.search(args.pattern, apn):
            continue

        mac = r[1]
        apnctr[apn] += 1
        flrctr[floorname(apn)] += 1

        os = r[12] or 'unknown'
        mac2os[mac] = os

    #
    #   create BSS -> channel map
    #
    bss2ch = {}
    essapnset = defaultdict(lambda: set())
    for r in bss_table[1:]:
        if r[6] in ('am', 'Spectrum'):
            continue
        apn = r[8]
        if not re.search(args.pattern, apn):
            continue

        bss = r[0]
        ess = r[1]
        m = re.match(r'(\d+[SE+-]?)/', r[5])
        if not m:
            print(f"Invalid channel: {r}")
            sys.exit(-1)
        bss2ch[bss] = m.group(1)
        essapnset[ess].add(apn)

    #
    #   phy_cap カウント
    #
    numsta = 0
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
    essvlan = defaultdict(lambda: set())
    for r in assoc_table[1:]:
        if not re.search(args.pattern, r[0]):
            continue

        numsta += 1
        bss = r[1]
        mac = r[2]
        essid = r[7]
        vlan = r[8]
        phycap = r[15]

        is5G = True if "5GHz" in phycap else False
        isht = True if "-HT-" in phycap else False
        isvht = True if "-VHT-" in phycap else False
        ishe = True if "-HE-" in phycap else False

        essctr[essid] += 1
        essvlan[essid].add(vlan)

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

        os = mac2os.get(mac, 'unknown')
        os_numss[os][ss] += 1

        chctr[bss2ch[bss]] += 1

    print(f"2.4GHz:{num2G}, 5GHz:{num5G}, Total:{numsta}")
    print(f"non-HT:{numsta-numht-numvht-numhe}, HT:{numht}, VHT:{numvht}, HE:{numhe}")
    print(f"1ss:{numss[1]}, 2ss:{numss[2]}, 3ss:{numss[3]}, 4ss:{numss[4]}")

    print()
    for os in sorted(os_numss.keys()):
        print(f"{os:10}: ", end="")
        for i in range(1, 4):
            print(f"{i}ss {os_numss[os][i]:>4}", end=", ")
        print()

    print("\nAPs/Clients per SSID (5G/2.4G)")
    for ess in essapnset.keys():
        print(f"{ess:20}: {len(essapnset[ess])} APs/{essctr[ess]} STAs ({essctrphy[ess][1]}/{essctrphy[ess][0]})")

    # print("\nTop 20 populated APs (based on L3 user table)")
    # for apn in sorted(apnctr.keys(), key=lambda x:apnctr[x], reverse=True)[:20]:
    #     print(f"{apn:15}: {apnctr[apn]}")

    print("\nClients per Floor (based on L3 user table)")
    for fl in sorted(flrctr.keys()):
        print(f"{fl}: {flrctr[fl]}")

    print("\nClients per channel")
    for ch in sorted(chctr.keys()):
        print(f"{ch}: {chctr[ch]}  ", end="")
    print()

    print("\nVLANs per ESSID")
    for ess in sorted(essvlan.keys()):
        vlans = sorted(essvlan[ess], key=lambda x: int(x))
        print(f"{ess:20}: {', '.join(vlans)}")

    #
    #   draw pie chart
    #
    if DrawGraph:
        band = {'2.4GHz': num2G, '5GHz': num5G}
        gen = {'HT(11n)': numht, 'VHT(11ac)': numvht, 'HE(11ax)': numhe}
        ss = {f"{i}ss": numss[i] for i in range(1, 4)}
        # colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
        # colors2 = ['#ff9999', '#99ff99', '#66b3ff']
        colors = ['tomato', 'deepskyblue', 'springgreen', '#99ff99', '#ffcc99']
        colors2 = ['tomato', 'limegreen', 'deepskyblue']

        fig, axs = plt.subplots(3, 1, figsize=(6, 12))
        drawpie(axs[0], band, colors)
        # axs[0].set_title('Band distribution')

        drawpie(axs[1], gen, colors2)
        # axs[1].set_title('Generation distribution')

        drawpie(axs[2], ss, colors)
        # axs[2].set_title('Spatial Stream distribution')
        plt.tight_layout()
        plt.show()
