#!/usr/bin/python
'''
Modified from source on:
http://apple.stackexchange.com/questions/4286/is-there-a-mac-os-x-terminal-version-of-the-free-command-in-linux-systems
'''

import subprocess
import re

def getMemUsage():
    # Get process info
    vm = subprocess.Popen(['vm_stat'], stdout=subprocess.PIPE).communicate()[0]
    total = subprocess.Popen("/usr/sbin/sysctl hw.memsize | cut -d: -f2", shell=True, stdout=subprocess.PIPE).communicate()[0]

    # Process vm_stat
    vmLines = vm.split('\n')
    sep = re.compile(':[\s]+')
    vmStats = {}
    for row in range(1,len(vmLines)-2):
        rowText = vmLines[row].strip()
        rowElements = sep.split(rowText)
        vmStats[(rowElements[0])] = int(rowElements[1].strip('\.')) * 4096

    # Process total
    total = int(total.strip())

    # In Megabytes
    result = {}
    result['wired'] = vmStats["Pages wired down"]/1024/1024
    result['active'] = vmStats["Pages active"]/1024/1024
    result['inactive'] = vmStats["Pages inactive"]/1024/1024
    result['free'] = vmStats["Pages free"]/1024/1024
    result['speculative'] = vmStats["Pages speculative"]/1024/1024
    result['total'] = total/1024/1024
    
    return result

print getMemUsage()