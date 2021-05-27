# aos-tools

Small tools to parse/process AOS logs, etc.

## esx-names.py

Sometimes customer does not allow us to enable 'advertise-ap-name' before survey starts.
The AP names in Ekahau survey result will be shown as 'Measured AP-<last 2 octets of BSSID>' in such case and it is annoying to look up actual AP names when we need to know the location or configuration of it.
This script will update the Ekahau file with actual AP name using BSS table ('show ap bss-table' output)

#### Command Syntax
```
  esx-names.py <bss-table file> --esx <.esx file>
```
<bss-table file> - The file containing the 'show ap bss-table' output. e.g. tech-support.log
<.esx file> - Ekahau .esx file to process

#### Options
```
  --esxdir <directory containing .esx files>
  --vendor  Update AP name with vendor name if the BSS is not found in bss-table
  --dryrun  Do not create .esx file
  --debug   Enable debug log
```

## apdb2xls.py
  
This script creates MS Excel file from 'show ap database long' output.


#### Command Syntax
```
  apdb2xls.py <infile> [<outfile>]
```
`<infile>` - The file containing 'show ap database long' output. e.g. tech-support.log
`<outfile>` - (optional) The filename to save the Excel data. 'ap-database.xlsx' is used if not specified.

  
## ap2xls.py
  
This script joins 2 AP tables (show ap database long and show ap active) then write the result to an MS Excel file.

#### Command Syntax
```
  ap2xls.py <infile> [<outfile>]
```
`<infile>` - The file containing 'show ap database long' output. e.g. tech-support.log
`<outfile>` - (optional) The filename to save the Excel data. 'ap-table.xlsx' is used if not specified.
