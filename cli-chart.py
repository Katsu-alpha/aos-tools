#
#   cli-chart.py
#   以下のコマンドをパースし、端末能力の pie chart 画像を作成
#       show ap association - ESSID, VLAN, PHY
#       show user - Name, IP, OS, Role
#

from glob import glob
import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser
from colorama import Fore, Style
from collections import defaultdict
import plotly.graph_objects as go
import plotly.express as px


#
#   display pie chart
#
def draw_pie_chart(data_dict, title, filename, marker, width=400, height=400):
    labels = list(data_dict.keys())
    values = list(data_dict.values())
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, sort=False, hole=.5, insidetextorientation='horizontal')])
    fig.update_traces(textinfo='value+label', marker=marker)
    fig.update_layout(title_text=title, width=width, height=height)
    fig.write_image(filename)
    print(f"Saved pie chart to {filename}")


#
#   START
#

parser = argparse.ArgumentParser(description="Generate pie charts for client capabilities.")
parser.add_argument('infiles', help="Input file(s)", type=str, nargs='+')
parser.add_argument('--pattern', '-p', help='regex for AP name', type=str, default='.*')
parser.add_argument('--ssid', help='Parse specific SSID(s)', type=str, default='.*')
parser.add_argument('--debug', help='Enable debug log', action='store_true')
args = parser.parse_args()

if args.debug:
    log.setloglevel(log.LOG_DEBUG)
else:
    log.setloglevel(log.LOG_INFO)


cmds = ['show ap association', 'show user-table']
assoc_tbl = []
user_tbl = []

if '*' in args.infiles:
    infiles = glob(args.infiles)
else:
    infiles = args.infiles

for f in infiles:
    print(f"Processing {f}")
    aos = AOSParser(f, cmds, merge=True)

    _assoc_tbl = aos.get_table(cmds[0], 'Name', 'bssid', 'mac', 'assoc', 'essid', 'vlan-id', 'phy')
    if _assoc_tbl:
        assoc_tbl.extend(_assoc_tbl)

    _user_tbl = aos.get_table(cmds[1], 'IP', 'MAC', 'AP name', 'Type', 'Role')
    if _user_tbl:
        user_tbl.extend(_user_tbl)

#
#   Parse assoc table
#
mac2vlan = defaultdict(str)
mac2phy = defaultdict(str)
mac2ess = defaultdict(str)

for r in assoc_tbl:
    name, bss, mac, assoc, ess, vlan, phy = r
    if assoc != 'y':
        continue        # skip non-associated clients
    if mac in mac2phy:
        continue        # already processed
    if vlan != '':
        mac2vlan[mac] = int(vlan)
    else:
        log.warn(f"Empty vlan for {mac}")
    mac2phy[mac] = phy
    mac2ess[mac] = ess

#
#   Process user table
#
ess2vlanset = defaultdict(set)
userctr = defaultdict(int)          # users per SSID
macset = set()                      # for de-dup
cap_band = defaultdict(int, {'2.4GHz':0, '5GHz':0})
cap_gen = defaultdict(int, {'Legacy':0, '11n':0, '11ac':0, '11ax':0})
cap_ss = defaultdict(int, {'1ss':0, '2ss':0})
cap_randmac = defaultdict(int, {'Normal MAC':0, 'Random MAC':0})
cap_os = defaultdict(int)

print(f"Total {len(user_tbl)} client records found.")
for r in user_tbl:
    ip, mac, apn, os, role = r

    if not re.search(args.pattern, apn):
        continue

    if mac in macset:   # de-dup
        log.info(f"Duplicate record for {mac}, skipping...")
        continue
    macset.add(mac)

    if mac not in mac2vlan:
        log.warn(f"No assoc info found for {mac}, skipping...")
        continue

    vlan = mac2vlan[mac]
    ess = mac2ess[mac]
    ess2vlanset[ess].add(vlan)
    userctr[ess] += 1
    phy = mac2phy[mac]
    os = "N/A" if os == '' else os

    if re.search(args.ssid, ess):
        if '5GHz' in phy or phy.startswith('a-'):
            cap_band['5GHz'] += 1
        elif '2.4GHz' in phy or phy.startswith('b-') or phy.startswith('g-'):
            cap_band['2.4GHz'] += 1
        elif '6GHz' in phy:
            cap_band['6GHz'] += 1

        if '-HT-' in phy:
            cap_gen['11n'] += 1
        elif '-VHT-' in phy:
            cap_gen['11ac'] += 1
        elif '-HE-' in phy:
            cap_gen['11ax'] += 1
        else:
            cap_gen['Legacy'] += 1

        r = re.search(r"-(\dss)", phy)
        if r:
            ss = r.group(1)
        else:
            ss = '1ss'  # non-HT
        cap_ss[ss] += 1

        if mac[1] in '26ae':
            cap_randmac['Random MAC'] += 1
        else:
            cap_randmac['Normal MAC'] += 1

        cap_os[os] += 1

if cap_gen['Legacy'] == 0:
    del(cap_gen['Legacy'])
    if cap_gen['11n'] == 0:
        del(cap_gen['11n'])



#
#   Print summary
#
print("\nUser count per ESSID:")
for ess, count in sorted(userctr.items(), key=lambda x: x[1], reverse=True):
    print(f"{ess:20}: {count}")

print("\nVLANs per ESSID:")
for ess in sorted(ess2vlanset.keys()):
    vlans = ess2vlanset[ess]
    if len(vlans) == 0:
        continue
    vlans_str = ', '.join(map(str, sorted(vlans)))
    print(f"{ess:20}: {vlans_str}")

print()

#   Draw pie charts using plotly
col1 = dict(colors=px.colors.qualitative.Set1, line=dict(color='#ffffff', width=1))
col2 = dict(colors=px.colors.qualitative.Safe, line=dict(color='#ffffff', width=1))
col3 = dict(colors=px.colors.qualitative.Plotly, line=dict(color='#ffffff', width=1))
draw_pie_chart(cap_band, "Radio Band", f'client_cap_band.png', col1)
draw_pie_chart(cap_gen, "Wi-Fi Generation", f'client_cap_gen.png', col1)
draw_pie_chart(cap_ss, "Spatial Streams", f'client_cap_ss.png', col1)
draw_pie_chart(cap_randmac, "MAC Type", f'client_cap_mac.png', col2)
draw_pie_chart(cap_os, "OS", f'client_cap_os.png', col2)
draw_pie_chart(userctr, "Clients per SSID", f'clients_per_ssid.png', col3, width=600)

sys.exit(0)
