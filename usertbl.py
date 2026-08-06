#
#   usertbl.py
#
#   show user-table verbose を集計
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict
import matplotlib.pyplot as plt

DrawGraph = True



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


def int2(s):
    if m:=re.match(r'(\d+)', s):
        return int(m.group(1))
    return 0


def print_dict(d, title):
    print(f"\n{title}")
    print('-' * len(title))
    maxlen = max(len(k) for k in d.keys())
    for k in sorted(d.keys()):
        print(f"{k:<{maxlen+2}} {d[k]}")

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show user-table verbose and display summary")
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
    cmds = ["show user-table verbose", "show ap active"]
    aos = AOSParser(args.infile, cmds, merge=True)
    user_table  = aos.get_table(cmds[0], "IP", "MAC", "Role", "AP name", "Roaming", "Essid/Bssid/Phy", "Forward mode", "Type", "User Type", "Vlan")
    if user_table is None:
        print("show user-table verbose output not found.")
        sys.exit(-1)
    ap_table = aos.get_table(cmds[1], "Name", "AP Type", "Radio 0 Band Ch/EIRP/MaxEIRP/Clients", "Radio 1 Band Ch/EIRP/MaxEIRP/Clients", "Radio 2 Band Ch/EIRP/MaxEIRP/Clients")


    #
    #   Get stats for L3 table
    #
    print('parsing show user-table...')

    tot_sta = 0
    uniq_sta = 0
    osctr = defaultdict(int)
    essctr = defaultdict(int)
    vlanctr = defaultdict(int)
    essctrphy = defaultdict(lambda: defaultdict(int))
    essvlan = defaultdict(lambda: set())
    bandctr = defaultdict(int)
    genctr = defaultdict(int)
    macset = set()

    for r in user_table:
        ip, mac, role, apn, roam, ebp, fwdmode, ostype, utype, vlan = r
        if mac == '00:00:00:00:00:00':      # VPN or AP
            continue
        if not re.search(args.pattern, apn):
            continue
        if utype != 'WIRELESS':             # ignore wired client
            continue

        tot_sta += 1
        if mac in macset:                    # ignore duplicate MAC
            continue
        macset.add(mac)

        uniq_sta += 1

        ess, bss, phy = ebp.split('/')

        # Band
        if '5' in phy:
            band = '5'
            bandctr['5GHz'] += 1
        elif '6' in phy:
            band = '6'
            bandctr['6GHz'] += 1
        elif '2' in phy:
            band = '2'
            bandctr['2.4GHz'] += 1

        # 802.11 generation
        if 'EHT' in phy:
            genctr['EHT(11be)'] += 1
        elif 'VHT' in phy:
            genctr['VHT(11ac)'] += 1
        elif 'HE' in phy:
            genctr['HE(11ax)'] += 1
        elif 'HT' in phy:
            genctr['HT(11n)'] += 1
        else:
            genctr['Legacy'] += 1


        vlanid = str(int2(vlan))
        if vlanid == '0':
            vlanid = 'unknown'

        essctr[ess] += 1
        essvlan[ess].add(vlanid)
        essctrphy[ess][band] += 1
        vlanctr[vlanid] += 1

        if ostype == '':
            ostype = 'unknown'
        osctr[ostype] += 1


    print(f"Total {tot_sta} wireless clients found.")
    print(f"Unique wireless clients found: {uniq_sta}") 
    print_dict(osctr, "OS Type distribution")
    print_dict(bandctr, "Band distribution")
    print_dict(genctr, "Generation distribution")

    essctr2 = {}
    for ess in essctr.keys():
        r = f'{essctr[ess]} ({essctrphy[ess]['2']}/{essctrphy[ess]['5']}/{essctrphy[ess]['6']})'
        essctr2[ess] = r
    print_dict(essctr2, "Clients per SSID (2/5/6GHz)")
    print_dict(vlanctr, "Clients per VLAN")

    essvlan2 = {k: ",".join(sorted(v)) for k, v in essvlan.items()}
    print_dict(essvlan2, "VLANs per SSID")


    #
    #   Get stats for AP table
    #
    print('\n\nparsing show ap active...')

    aptypectr = defaultdict(int)
    bandctr = defaultdict(int)
    apnset = set()
    numaps = 0
    for r in ap_table:
        apn, aptype, r0, r1, r2 = r
        if not re.search(args.pattern, apn):
            continue
        if apn in apnset:
            continue
        apnset.add(apn)
        numaps += 1

        for i, r in enumerate([r0, r1, r2]):
            if r == '':
                continue
            m = re.search(r':([\d.]+)GHz', r)
            if m:
                band = m.group(1)[0]
                clients = int2(r.split('/')[-1])
                bandctr[band] += clients

        aptypectr[aptype] += 1
    

    print(f"Total {numaps} APs found.")
    print_dict(aptypectr, "AP Type distribution")
    print_dict(bandctr, "Band distribution")

    #
    #   draw pie chart
    #
    # if DrawGraph:
    #     band = {'2.4GHz': num2G, '5GHz': num5G}
    #     gen = {'HT(11n)': numht, 'VHT(11ac)': numvht, 'HE(11ax)': numhe}
    #     ss = {f"{i}ss": numss[i] for i in range(1, 4)}
    #     # colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    #     # colors2 = ['#ff9999', '#99ff99', '#66b3ff']
    #     colors = ['tomato', 'deepskyblue', 'springgreen', '#99ff99', '#ffcc99']
    #     colors2 = ['tomato', 'limegreen', 'deepskyblue']

    #     fig, axs = plt.subplots(3, 1, figsize=(6, 12))
    #     drawpie(axs[0], band, colors)
    #     # axs[0].set_title('Band distribution')

    #     drawpie(axs[1], gen, colors2)
    #     # axs[1].set_title('Generation distribution')

    #     drawpie(axs[2], ss, colors)
    #     # axs[2].set_title('Spatial Stream distribution')
    #     plt.tight_layout()
    #     plt.show()
