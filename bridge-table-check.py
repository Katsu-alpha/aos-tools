#
#   show datapath bridge チェッカー
#
#   - check duplicate entry
#

import argparse
import sys
import mylogger as log
from aos_parser import AOSParser
from collections import defaultdict

parser = argparse.ArgumentParser(
    description="Check datapath bridge table")
parser.add_argument('infile', help="Input file containing 'show datapath bridge' output", type=str, nargs=1)
parser.add_argument('--debug', help='Enable debug log', action='store_true')
args = parser.parse_args()

if args.debug:
    log.setloglevel(log.LOG_DEBUG)
else:
    log.setloglevel(log.LOG_INFO)


cmd = "show datapath bridge"
aos = AOSParser(args.infile, cmd)
br_table = aos.get_tables(cmd)
if br_table is None:
    print("show ap bss-table output not found.")
    sys.exit(-1)

br_d = defaultdict(list)
for r in br_table[0][1:]:
    br_d[r[0]].append((r[1], r[3], r[4]))

for mac, br_l in br_d.items():
    if len(br_l) == 1:
        continue
    for vlan, dest, flags in br_l:
        print(f'{mac} {vlan:5}{dest:10}{flags}')
