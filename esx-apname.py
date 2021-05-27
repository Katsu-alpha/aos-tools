#!/usr/bin/python3 -u
#
#   Update Ekahau esx file with actual AP name
#

import os
import re
import sys
import json
import glob
from zipfile import ZipFile, ZIP_DEFLATED
import argparse
import mylogger as log
from aos_parser import AOSParser, AP_BSS_TABLE

if __name__ == '__main__':

    ESX_AccessPoints   = "accessPoints.json"
    ESX_MeasuredRadios = "measuredRadios.json"
    ESX_APMeasurements = "accessPointMeasurements.json"
    ESX_suffix = "_apname"

    parser = argparse.ArgumentParser(
        description="Update Ekahau esx file with actual AP names")
    parser.add_argument('files', help="A file containing show ap bss-table output", type=str, nargs='*')
    parser.add_argument('--esx', help='Ekahau esx file to update', type=str)
    parser.add_argument('--esxdir', help='Directory where Ekahau esx files exist', type=str)
    parser.add_argument('--vendor', help='Use vendor name for non-Aruba APs', action='store_true')
    parser.add_argument('--dryrun', help='Do not create esx file', action='store_true')
    parser.add_argument('--debug', help='Enable debug log', action='store_true')
    parser.add_argument('--info', help='Enable informational log', action='store_true')
    args = parser.parse_args()

    if args.debug:
        log.setloglevel(log.LOG_DEBUG)
    elif args.info:
        log.setloglevel(log.LOG_INFO)
    else:
        log.setloglevel(log.LOG_WARN)

    dir = args.esxdir
    if dir is not None:
        if not dir.endswith("/"):
            dir += "/"
        dir += "*.esx"
        esxfiles = glob.glob(dir)
    else:
        esxfile = args.esx
        if esxfile is None:
            log.err("please specify either --esx or --esxdir option")
            sys.exit(-1)
        esxfiles = [esxfile]

    #
    #   parse BSS table
    #
    print("Parsing bss-table ... ", end="")
    aos = AOSParser(args.files, AP_BSS_TABLE)
    bss_tables = aos.get_tables(AP_BSS_TABLE)

    bss_to_apn = {}
    for bss_table in bss_tables:
        idx_apn = bss_table[0].index("ap name")
        idx_bss = bss_table[0].index("bss")
        for row in bss_table[1:]:
            apn = row[idx_apn]
            bss = row[idx_bss]
            if bss in bss_to_apn:
                apn2 = bss_to_apn[bss]
                if apn2 == "DUP":
                    continue        # skip the bss with multiple AP names
                if apn == apn2:
                    continue        # duplicate entry
                log.warn(f'duplicate BSSID found! AP "{apn}" and "{apn2}" have the same BSSID "{bss}"')
                bss_to_apn[bss] = "DUP"       # duplicate marker
                continue
            bss_to_apn[bss] = apn

    print("done.")

    #
    #   modify esx files
    #
    for esxfile in esxfiles:

        print(f"Processing {esxfile} ...")

        with ZipFile(esxfile) as esxf:
            with esxf.open(ESX_AccessPoints, "r") as f:
                ap_json = json.loads(f.read().decode("utf8"))
            with esxf.open(ESX_MeasuredRadios, "r") as f:
                measure_json = json.loads(f.read().decode("utf8"))
            with esxf.open(ESX_APMeasurements, "r") as f:
                apmeasure_json = json.loads(f.read().decode("utf8"))

        #
        #   create dicts
        #
        apid_to_mids = {}        # AP ID to Measurement ID
        for r in ap_json['accessPoints']:
            apid_to_mids[r['id']] = []      # initialize list of MID

        for r in measure_json['measuredRadios']:
            apid_to_mids[r['accessPointId']].extend(r['accessPointMeasurementIds'])

        mid_to_bss = {}         # Measurement ID to BSSID
        for r in apmeasure_json['accessPointMeasurements']:
            mid_to_bss[r['id']] = r['mac']

        #
        #   start conversion
        #
        num_processed = 0
        for ap in ap_json['accessPoints']:
            apn = ap['name']
            apid = ap['id']
            if 'vendor' in ap:
                vendor = ap['vendor']
            else:
                vendor = "unknown"
            r = re.match("実際 AP-([0-9a-f][0-9a-f]:[0-9a-f][0-9a-f])", apn)
            if not r:
                r = re.match("Measured AP-([0-9a-f][0-9a-f]:[0-9a-f][0-9a-f])", apn)
                if not r:
                    continue        # no need to replace the name

            last2 = r.group(1)
            for mid in apid_to_mids[apid]:
                bss = mid_to_bss[mid]
                if bss[-5:] == last2:
                    break

            if vendor == "Aruba":
                if bss in bss_to_apn:
                    full_apn = bss_to_apn[bss]
                    if full_apn == "DUP":
                        log.warn(f'"{apn}" ({vendor}) -> {bss} -> DUP')
                        continue
                else:
                    log.debug(f'"{apn}" ({vendor}) -> {bss} -> no match.')
                    continue
            else:
                if not args.vendor:
                    log.debug(f'"{apn}" ({vendor}) -> {bss} -> skip.')
                    continue
                full_apn = vendor + "-" + last2

            log.info(f'"{apn}" ({vendor}) -> {bss} -> "{full_apn}"')
            ap['name'] = full_apn
            num_processed += 1

        log.info(f"{num_processed} AP names replaced.")

        if args.dryrun:
            continue        # do not update zip

        #
        #   update zip
        #
        f = os.path.splitext(os.path.basename(esxfile))
        new_fn = f[0] + ESX_suffix + f[1]
        print(f"Writing {new_fn} ... ", end="")

        with ZipFile(esxfile, "r") as orig_zf, ZipFile(new_fn, "w", ZIP_DEFLATED) as new_zf:
            for item in orig_zf.infolist():
                if item.filename == ESX_AccessPoints:
                    new_zf.writestr(ESX_AccessPoints, json.dumps(ap_json, indent=2, ensure_ascii=False).encode("utf8"))
                else:
                    new_zf.writestr(item, orig_zf.read(item.filename))

        print("done.")

    sys.exit(0)
