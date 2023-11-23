#!/usr/bin/python3
#
#	read Traffic Analysis table from MM Dashboard
#

import re
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

#----------------------------------- edit connection parameters

MM_ADDR = '192.168.1.1'
user    = 'admin'
passwd  = 'admini'
cert_verify = False

#----------------------------------- choose columns from:
# sta_mac_address client_ht_phy_type openflow_state client_ip_address client_user_name client_dev_type client_ap_location client_conn_port client_conn_type client_timestamp client_role_name client_active_uac client_standby_uac ap_cluster_name client_health total_moves successful_moves steer_capability ssid ap_name channel channel_str channel_busy tx_time rx_time channel_free channel_interference current_channel_utilization radio_band bssid speed max_negotiated_rate noise_floor radio_ht_phy_type snr total_data_frames total_data_bytes avg_data_rate tx_avg_data_rate rx_avg_data_rate tx_frames_transmitted tx_frames_dropped tx_bytes_transmitted tx_bytes_dropped tx_time_transmitted tx_time_dropped tx_data_transmitted tx_data_dropped tx_data_retried tx_data_transmitted_retried tx_data_bytes_transmitted tx_abs_data_bytes tx_data_bytes_dropped tx_time_data_transmitted tx_time_data_dropped tx_mgmt rx_frames rx_bytes rx_data rx_data_bytes rx_abs_data_bytes rx_data_retried tx_data_frame_rate_dist rx_data_frame_rate_dist tx_data_bytes_rate_dist rx_data_bytes_rate_dist connection_type_classification total_data_throughput tx_data_throughput rx_data_throughput client_auth_type client_auth_subtype client_encrypt_type client_fwd_mode

columns = 'sta_mac_address client_ip_address client_user_name ap_name channel ssid client_role_name client_health'

query = '''
<aruba_queries><query>
    <qname>backend-observer-fw_visibility_rec-20</qname>
    <type>list</type>
    <list_query>
        <device_type>fw_visibility_rec</device_type>
        <requested_columns>fw_dest_alias_id fw_session_id fw_dest_alias_display_name fw_total_bytes
         fw_tx_bytes fw_rx_bytes fw_total_pkts fw_client_ip app_id fw_ingress_name fw_session_count
          client_role_name client_dev_type</requested_columns>
        <group_by_aggregates>none mapped mapped sum sum sum sum count_distinct count_distinct count_distinct sum count_distinct count_distinct</group_by_aggregates>
        <sort_by_field>fw_total_bytes</sort_by_field>
        <sort_order>desc</sort_order>
        <pagination>
            <start_row>0</start_row>
            <num_rows>200</num_rows>
        </pagination>
    </list_query>
    <group_by>fw_dest_alias_id</group_by>
    <filter>
        <global_operator>and</global_operator>
        <filter_list>
            <filter_item_entry>
                <field_name>fw_total_pkts</field_name>
                <comp_operator>not_equals</comp_operator><value><![CDATA[0]]></value>
            </filter_item_entry>
            <filter_item_entry>
                <field_name>fw_denied_session</field_name>
                <comp_operator>equals</comp_operator><value><![CDATA[0]]></value>
            </filter_item_entry>
        </filter_list>
    </filter>
</query></aruba_queries>
'''

query = '''
<aruba_queries><query>
    <qname>backend-observer-fw_visibility_rec-20</qname>
    <type>list</type>
    <list_query>
        <device_type>fw_visibility_rec</device_type>
        <requested_columns>fw_dest_alias_id fw_session_id fw_dest_alias_display_name fw_total_bytes
         fw_tx_bytes fw_rx_bytes fw_total_pkts</requested_columns>
        <group_by_aggregates>none mapped mapped sum sum sum sum</group_by_aggregates>
        <sort_by_field>fw_total_bytes</sort_by_field>
        <sort_order>desc</sort_order>
        <pagination>
            <start_row>0</start_row>
            <num_rows>10</num_rows>
        </pagination>
    </list_query>
    <group_by>fw_dest_alias_id</group_by>
    <filter>
        <global_operator>and</global_operator>
        <filter_list>
            <filter_item_entry>
                <field_name>fw_total_pkts</field_name>
                <comp_operator>not_equals</comp_operator><value><![CDATA[0]]></value>
            </filter_item_entry>
            <filter_item_entry>
                <field_name>fw_denied_session</field_name>
                <comp_operator>equals</comp_operator><value><![CDATA[0]]></value>
            </filter_item_entry>
        </filter_list>
    </filter>
</query></aruba_queries>
'''


#-----------------------------------
req = requests.Session()
post_data = {"opcode": "login", "url": "/login.html", "needxml": "0", "uid": user, "passwd": passwd}
r = req.post(f"https://{MM_ADDR}:4343/screens/wms/wms.login", data=post_data, verify=cert_verify)

if 'set-cookie' not in r.headers:
	print("ERROR: Set-Cookie header not found in response.")
	exit()

setcookie = r.headers['set-cookie']
m = re.search("SESSION=([^;]+)", setcookie)
if not m:
	print(f"ERROR: Session ID not found in Set-Cookie: {setcookie}")
	exit()
sid = m.group(1)

re.sub('[\t\r\n]', '', query)
post_data = {"query": query, "UIDARUBA": sid}
r = req.post(f"https://{MM_ADDR}:4343/screens/cmnutil/execUiQuery.xml", data=post_data, verify=cert_verify)


#-----------------------------------
col_name = []
col_mlen = []
for m in re.finditer("<column_name>([^<]*)</column_name>", r.text):
	col_name.append(m.group(1))
	col_mlen.append(len(m.group(1)))

num_cols = len(col_name)
table = []
row = []
col_len = []
i = 0
for m in re.finditer("<value>([^<]*)</value>", r.text):
	row.append(m.group(1))
	col_len.append(len(m.group(1)))
	i += 1
	if i == num_cols:
		table.append(row)
		col_mlen = list(map(max, col_mlen, col_len))
		i = 0
		row = []
		col_len = []

col_mlen = [l+2 for l in col_mlen]
for i in range(num_cols):
	print(f"{col_name[i]:{col_mlen[i]}}", end='')
print("")
for i in range(num_cols):
	print(f"{'-'*len(col_name[i]):{col_mlen[i]}}", end='')
print("")

for l in table:
	for i in range(num_cols):
		print(f"{l[i]:{col_mlen[i]}}", end='')
	print("")

print(f"\nTotal records: {len(table)}")