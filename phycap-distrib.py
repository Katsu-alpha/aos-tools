#
#   phycap-distrib.py
#
#   show ap association, show ap bss-table をパースし、以下を集計
#   - 2.4GHz/5GHz/6GHz STA数
#   - HT/VHT/HE STA数
#   - 1ss/2ss/3ss/4ss STA数
#   - OS別 STA数
#   - SSID別 AP数/STA数
#   - チャネル別 STA数
#   - SSID-VLANマッピング
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
    cmds = ["show ap association", "show ap bss-table", "show user-table", "show clients debug"]
    aos = AOSParser(args.infile, cmds, merge=True)
    assoc_table = aos.get_table(cmds[0], 'Name', 'bssid', 'mac', 'assoc', 'essid', 'vlan-id', 'phy_cap')
    bss_table   = aos.get_table(cmds[1])
    user_table  = aos.get_table(cmds[2], 'AP name', 'MAC', 'Type')
    cli_table   = aos.get_table(cmds[3], 'Access Point', 'MAC Address', 'OS')

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

    if user_table is not None:
        for r in user_table:
            apn, mac, os = r
            if not re.search(args.pattern, apn):
                continue

            apnctr[apn] += 1
            flrctr[floorname(apn)] += 1
            mac2os[mac] = os or 'unknown'

    if cli_table is not None:
        for r in cli_table:
            apn, mac, os = r
            if not re.search(args.pattern, apn):
                continue

            apnctr[apn] += 1
            flrctr[floorname(apn)] += 1
            mac2os[mac] = os or 'unknown'




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
    numsta_radio = [0, 0, 0]
    numht = 0
    numvht = 0
    numhe = 0
    numss = [0,0,0,0,0]
    os_numss = defaultdict(lambda: [0,0,0,0,0])
    essctr = defaultdict(lambda: 0)
    essctrphy = defaultdict(lambda: [0, 0, 0])
    chctr = defaultdict(lambda: 0)
    essvlan = defaultdict(lambda: set())
    for r in assoc_table:
        if not re.search(args.pattern, r[0]):
            continue

        name, bss, mac, assoc, essid, vlan, phycap = r
        if assoc != 'y':
            continue
        numsta += 1

        if '5GHz' in phycap:
            radio = 1
        elif '6GHz' in phycap:
            radio = 2
        else:
            radio = 0

        isht = True if "-HT-" in phycap else False
        isvht = True if "-VHT-" in phycap else False
        ishe = True if "-HE-" in phycap else False

        essctr[essid] += 1
        essvlan[essid].add(vlan)


        numsta_radio[radio] += 1
        essctrphy[essid][radio] += 1
        if isht: numht+=1
        if isvht: numvht+=1
        if ishe: numhe+=1

        r = re.search(r"-(\d)ss", phycap)
        if r:
            ss = int(r.group(1))
        else:
            ss = 0
        numss[ss]+=1

        os = mac2os.get(mac, 'unknown')
        os_numss[os][ss] += 1

        chctr[bss2ch[bss]] += 1

    print('--- Client capability distribution ---')
    print(f"2.4GHz:{numsta_radio[0]}, 5GHz:{numsta_radio[1]}, 6GHz:{numsta_radio[2]}, Total:{numsta}")
    print(f"non-HT:{numsta-numht-numvht-numhe}, HT:{numht}, VHT:{numvht}, HE:{numhe}")
    print(f"1ss:{numss[1]}, 2ss:{numss[2]}, 3ss:{numss[3]}, 4ss:{numss[4]}")

    print("\n--- OS/nss distribution ---")
    for os in sorted(os_numss.keys()):
        print(f"{os:10}: ", end="")
        for i in range(1, 4):
            print(f"{i}ss {os_numss[os][i]:>4}", end=", ")
        print()

    print("\n--- APs/Clients per SSID (2.4/5G/6G) ---")
    for ess in essapnset.keys():
        print(f"{ess:20}: {len(essapnset[ess])} APs/{essctr[ess]} STAs ({essctrphy[ess][0]}/{essctrphy[ess][1]}/{essctrphy[ess][2]})")

    # print("\nTop 20 populated APs (based on L3 user table)")
    # for apn in sorted(apnctr.keys(), key=lambda x:apnctr[x], reverse=True)[:20]:
    #     print(f"{apn:15}: {apnctr[apn]}")

    print("\n--- Clients per Floor (based on L3 user table) ---")
    for fl in sorted(flrctr.keys()):
        print(f"{fl}: {flrctr[fl]}")

    print("\n--- Clients per channel ---")
    for ch in sorted(chctr.keys()):
        print(f"{ch}: {chctr[ch]}  ", end="")
    print()

    print("\n--- VLANs per ESSID ---")
    for ess in sorted(essvlan.keys()):
        vlans = sorted(essvlan[ess], key=lambda x: int(x))
        print(f"{ess:20}: {', '.join(vlans)}")

    #
    #   draw pie chart
    #
    if DrawGraph:
        band = {'2.4GHz': numsta_radio[0], '5GHz': numsta_radio[1], '6GHz': numsta_radio[2]}
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
