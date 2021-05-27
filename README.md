# aos-tools

Small tools to parse/process AOS logs, etc.

## esx-names.py

Sometimes customer does not allow us to enable 'advertise-ap-name' before survey starts.
The AP names in Ekahau survey result will be shown as 'Measured AP-<last 2 octets of BSSID>' in such case and it takes to time to look up actual AP names.
This script will update the Ekahau file with actual AP name using BSS table ('show ap bss-table' output)

#### Command Syntax
```
  esx-names.py <bss-table file> --esx <.esx file>
```
<bss-table file> - A file containing the 'show ap bss-table' output. e.g. tech-support.log
<.esx file> - Ekahau .esx file

#### Options
```
  --esxdir <directory containing .esx files>
  --vendor  Update AP name with vendor name if the BSS is not found in bss-table
  --dryrun  Do not create .esx file
  --debug   Enable debug log
```
