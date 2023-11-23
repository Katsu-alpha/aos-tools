#!/usr/bin/python3 -u

import sys
import time
import paramiko
from paramiko_expect import SSHClientInteraction
from aos_parser import AOSParser, DATAPATH_SESSION_DPI
import mylogger as log

import re
import getpass

def myprompt(msg, dflt = ''):
    s = ''
    if dflt == '':
        while s == '':
            s = input(f"{msg}: ")
    else:
        s = input(f"{msg}[{dflt}]: ")
        if s == '':
            s = dflt

    return s




if __name__ == '__main__':


    controller_ip = '192.168.1.1'
    username = 'admin'
    ena_pass = 'enable'
    prompt = r'\(.* #'
    log.setloglevel(log.LOG_INFO)
    #log.setloglevel(log.LOG_DEBUG)
    #controller_ip = myprompt("Controller IP", controller_ip)
    #username = myprompt("Username", username)
    #password = getpass.getpass("Password: ")
    password = 'admini'

    # Create a new SSH client object
    client = paramiko.SSHClient()

    # Set SSH key parameters to auto accept unknown hosts
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Connect to the host
    client.connect(hostname=controller_ip, username=username, password=password)

    # Create a client interaction class which will interact with the host
    log.info(f"connecting to {controller_ip}")
    with SSHClientInteraction(client, timeout=10, display=False) as conn:
        conn.expect(prompt)
        conn.send('no paging')
        conn.expect(prompt)

        #
        #   collect datapath session table
        #
        log.info("collecting datapath table #1")
        conn.send('show datapath session dpi')
        conn.expect(prompt)
        r1 = conn.current_output_clean
        time.sleep(10)

        log.info("collecting datapath table #2")
        conn.send('show datapath session dpi')
        conn.expect(prompt)
        r2 = conn.current_output_clean

        #
        #   disconnect
        #
        conn.send('exit')

    #
    #   parse datapath entries
    #
    data = "show datapath session dpi\n" + r1
    aos = AOSParser(data, DATAPATH_SESSION_DPI)
    log.info(f"Session#1 - got {len(aos.get_table(DATAPATH_SESSION_DPI))-1} entries.")
    tbl = aos.get_table(DATAPATH_SESSION_DPI, "Source IP or MAC", "Destination IP", "Prot", "SPort", "DPort", "Bytes", "AppID")
    ip_pat = "192.168.1."
    ses_bytes = {}
    ses_sip = {}
    ses_dip = {}
    ses_app = {}

    for r in tbl:
        sip, dip, prot, sport, dport, byte, app = r
        byte = int(byte)
        if not sip.startswith(ip_pat) and not dip.startswith(ip_pat):
            continue
        ses_key = f"{sip:16}:{dip:16}:{prot:5}:{sport:5}:{dport:5}"
        ses_bytes[ses_key] = byte
        ses_sip[ses_key] = sip
        ses_dip[ses_key] = dip
        ses_app[ses_key] = app

    for key in sorted(ses_bytes.keys()):
        log.debug(f"{key} : {ses_bytes[key]} bytes, {ses_app[key]}")


    data = "show datapath session dpi\n" + r2
    aos = AOSParser(data, DATAPATH_SESSION_DPI)
    log.info(f"Session#2 - got {len(aos.get_table(DATAPATH_SESSION_DPI))-1} entries.")
    tbl = aos.get_table(DATAPATH_SESSION_DPI, "Source IP or MAC", "Destination IP", "Prot", "SPort", "DPort", "Bytes", "AppID")
    dbytes = {}
    log_ips = {"192.168.1.50"}

    for r in tbl:
        sip, dip, prot, sport, dport, byte, app = r
        byte = int(byte)
        if not sip.startswith(ip_pat) and not dip.startswith(ip_pat):
            continue
        ses_key = f"{sip:16}:{dip:16}:{prot:5}:{sport:5}:{dport:5}"

        if ses_key in ses_bytes:
            delta = byte - ses_bytes[ses_key]
            if delta < 0:
                log.warn(f"invalid bytes: {ses_key}: {ses_bytes[ses_key]} -> {byte}")
                delta = byte        # take the latest bytes value


            if sip in log_ips or dip in log_ips:
                if delta != 0:
                    log.debug(f"{ses_key} : {byte} bytes, +{byte-ses_bytes[ses_key]}")
            dbytes[ses_key] = delta
        else:
            dbytes[ses_key] = byte
            ses_sip[ses_key] = sip
            ses_dip[ses_key] = dip
            ses_app[ses_key] = app
            if sip in log_ips or dip in log_ips:
                log.debug(f"{ses_key} : {byte} bytes, (NEW Session)")

    #
    #   集計
    #
    ip_bytes = {}
    ip_numses = {}
    app_bytes = {}
    for ses, byte in dbytes.items():

        if byte == 0:
            continue

        sip = ses_sip[ses]
        dip = ses_dip[ses]
        if sip == controller_ip or dip == controller_ip:
            continue        # skip controller session

        if sip.startswith(ip_pat):
            try:
                ip_bytes[sip] += byte
                ip_numses[sip] += 1
            except KeyError:
                ip_bytes[sip] = byte
                ip_numses[sip] = 1
        if dip.startswith(ip_pat):
            try:
                ip_bytes[dip] += byte
                ip_numses[dip] += 1
            except KeyError:
                ip_bytes[dip] = byte
                ip_numses[dip] = 1

        app = ses_app[ses]
        try:
            app_bytes[app] += byte
        except KeyError:
            app_bytes[app] = byte


    print("Top 10 talker clients")
    for k in sorted(ip_bytes.keys(), key=lambda x: ip_bytes[x], reverse=True)[:10]:
        print(f"{k:18} {ip_bytes[k]} bytes / {ip_numses[k]} active sessions")

    print("Top 10 apps")
    for k in sorted(app_bytes.keys(), key=lambda x: app_bytes[x], reverse=True)[:10]:
        print(f"{k:10} {app_bytes[k]} bytes")
