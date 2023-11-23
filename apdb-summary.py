#
#   apdb-summary.py
#
#   show ap database で、AP model/group のサマリ
#

import sys
import re
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_DATABASE_LONG_TABLE, AP_ACTIVE_TABLE
from collections import defaultdict

#
#   main
#
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Parse show ap database and print summary")
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
    aos = AOSParser(args.infile, ["show ap database long"], merge=True)
    apdb_table  = aos.get_table("show ap database long")
    if apdb_table is None:
        print("show ap database long output not found.")
        sys.exit(-1)
    print(f"done. {len(apdb_table)-1} APs found.")

    #
    #   summarize
    #
    groups = defaultdict(lambda: 0)
    aptypes = defaultdict(lambda: 0)
    for r in apdb_table[1:]:
        apg = r[1]
        apt = r[2]
        groups[apg] += 1
        aptypes[apt] += 1

    print("AP Groups")
    print("---------")
    for apg in sorted(groups.keys()):
        print(f"{apg:10}: {groups[apg]}")

    print("\nAP Types")
    print("---------")
    for apt in sorted(aptypes.keys()):
        print(f"{apt:10}: {aptypes[apt]}")

