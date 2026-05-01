#
#   get-bss-dict.py
#   show ap bss-table をパースし、bss2ess/bss2ap dict を書き出し
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser

#
#   START
#

parser = argparse.ArgumentParser(description="Create python dictionary from BSS table")
parser.add_argument('infiles', help="Input file(s)", type=str, nargs='*')
parser.add_argument('--debug', help='Enable debug log', action='store_true')
parser.add_argument('--out', '-o', help='Output file', type=str, default='bssdic.py')
args = parser.parse_args()

if args.debug:
    log.setloglevel(log.LOG_DEBUG)
else:
    log.setloglevel(log.LOG_INFO)

#
#   GET BSSID list
#
cmd = ["show ap bss-table.*"]
cols = ["bss", "ess", "ap name"]


for enc in ['utf-8', 'macroman']:
    try:
        aos = AOSParser(args.infiles, cmd, merge=True, encoding=enc)
        break
    except UnicodeDecodeError:
        pass
else:
    print("unknown encoding, abort.")
    sys.exit(-1)


ap_bss_tbl = aos.get_table(cmd[0], *cols)
if ap_bss_tbl is None:
    print("show ap bss-table output not found.")
    sys.exit(-1)

#
#   create bss2ess/bss2ap dicts
#
bss2ess = {}
bss2ap = {}
for r in ap_bss_tbl:
    bss, ess, apn = r
    bss2ess[bss] = ess
    bss2ap[bss] = apn



fn = args.out
with open(fn, 'w') as f:
    f.write("# BSSID dictionary\n")
    f.write("bss2ess = {\n")
    for bss, ess in bss2ess.items():
        f.write(f"    '{bss}': '{ess}',\n")
    f.write("}\n\n")

    f.write("bss2apn = {\n")
    for bss, ap in bss2ap.items():
        f.write(f"    '{bss}': '{ap}',\n")
    f.write("}\n")
print(f"Wrote BSSID dictionary to {fn}")


sys.exit(0)
