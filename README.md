# aos-tools

Small tools to parse/process AOS logs, etc.

## esx-names.py

Ekahau survey result does not have AP name if 'advertise-ap-name' is not enabled on Aruba controller.
This script will update the Ekahau file with actual AP name.
You need to feed BSS to AP name mapping by 'show ap bss-table' output.

Command syntax:
```
  esx-names.py <file containing show ap bss-table output> --esx <.esx file>
```

