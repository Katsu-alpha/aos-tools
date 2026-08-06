#
#   download OUI ventor mapping from https://standards-oui.ieee.org/
#   create ouimap.py file including python dict
#

import re
import requests


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}
r = requests.get('https://standards-oui.ieee.org/', headers=headers)

ouimap = {}
for l in r.text.splitlines():
    if m:=re.match(r'[0-9A-F]{6}\s+\(base 16\)\s+(.+)', l):
        oui = l[:2] + ':' + l[2:4] + ':' + l[4:6]
        oui = oui.lower()
        vendor = m.group(1)
        ouimap[oui] = vendor

print(f"downloaded {len(ouimap)} OUI vendor mapping from https://standards-oui.ieee.org/")

with open('ouimap.py', 'w') as f:
    f.write('#!/usr/bin/env python\n')
    f.write('#\n')
    f.write('#   OUI vendor mapping\n')
    f.write('#   downloaded from https://standards-oui.ieee.org/\n')
    f.write('#\n')
    f.write('ouimap = {\n')
    for k in sorted(ouimap.keys()):
        f.write(f'    "{k}": "{ouimap[k]}",\n')
    f.write('}\n')

print(f"created ouimap.py file.")

