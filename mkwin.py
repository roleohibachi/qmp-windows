#!/usr/bin/python3
#references
#https://www.qemu.org/docs/master/qemu-qmp-ref.html#Input
#https://github.com/miurahr/qemu-kvm/tree/050c98e391b96129273be5e163d90b8b6ae01cc2/QMP
#https://pve.proxmox.com/pve-docs/api-viewer/
#https://pypi.org/project/proxmoxer/
#virtio driver iso: https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/

#This will spin up a new windows VM, enable ssh, and install drivers and the guest agent.

import qmp
import json
import time
import os
from proxmoxer import ProxmoxAPI
from winqmp import * #this one's mine

input('Read everything before doing anything. Seriously, this is not meant to be run non-interactive!')

#you may need to cat id_rsa.pub >> authorized_keys for this to work
proxmox = ProxmoxAPI('localhost', user='root', backend='ssh_paramiko')
winvm = proxmox.nodes('ares').qemu('666')

#Do these yourself, in a directory where you'v got lots of space:
#wget -O windev_VM_vmware https://aka.ms/windev_VM_vmware
#unzip windev_VM_vmware
#winvm.delete.create() #confusing, I know... but this is how you delete the existing 666 vm
#os.system('qm importovf 666 WinDev2004Eval.ovf tank -format qcow2')
#if that doesn't work, you'll instead:
#tar xvf WinDev2004Eval.ovf
#pvesh create /nodes/ares/qemu -vmid 666 -sockets 1 -cores 2 -memory 2048
#qm importdisk 666 WinDev2004Eval-disk-0.vmdk tank -format qcow2

winvm.config.set(name='win10')
winvm.config.set(ostype='win10')

#everything must be sata until guest agent and virtio drivers are installed
winvm.config.set(sata1='iso:iso/virtio-win.iso,media=cdrom,size=363020K')
winvm.config.set(boot='c')
winvm.config.set(delete='scsihw') #this just sets it to the default hw
winvm.config.set(net0='rtl8139=7E:C9:51:27:D9:60,bridge=vmbr0,firewall=1')

winvm.config.set(agent='1') #won't work until later

winvm.status.start.create()
#time.sleep(120)
input("press enter when warm. You'll want to pop a console to follow along. You won't be able to connect once we open the QMP socket")

addr='/var/run/qemu-server/666.qmp'
qemu = qmp.QEMUMonitorProtocol(addr)
qemu.connect()

launch_powershell(qemu)

#enable ssh
#should be already done for us, but if needed, uncomment:
#sendwincmd(qemu, 'Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0')
#time.sleep(10)
#sendwincmd(qemu, 'Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0')
#time.sleep(10)

sendwincmd(qemu, '''ssh-keygen -f c:/users/user/.ssh/id_rsa -N '""' ''')
time.sleep(1)
qmsendkey(qemu,'ret') #if there are already keys generated, gotta escape the interactive subshell

sendwincmd(qemu, 'Set-Service ssh-agent -startuptype auto')
sendwincmd(qemu, 'Start-Service ssh-agent')
sendwincmd(qemu, 'ssh-add c:/users/user/.ssh/id_rsa')

pubkey=''
with open('/root/.ssh/id_rsa.pub','r') as pubkeyfile:
  pubkey+=pubkeyfile.read().replace('\n','')

sendwincmd(qemu, 'Add-Content -Path c:/programdata/ssh/administrators_authorized_keys -Value "'+pubkey+'"')
sendwincmd(qemu, 'icacls c:/programdata/ssh/administrators_authorized_keys /inheritance:r')
sendwincmd(qemu, 'icacls c:/programdata/ssh/administrators_authorized_keys /grant SYSTEM:`(F`)')
sendwincmd(qemu, 'icacls c:/programdata/ssh/administrators_authorized_keys /grant BUILTIN\Administrators:`(F`)')
sendwincmd(qemu, 'Set-Service sshd -startuptype auto')
sendwincmd(qemu, 'Start-Service sshd')

#load drivers
sendwincmd(qemu, 'get-childitem -recurse -path d:/*/w10/amd64/*.inf | foreach-object { pnputil -a $_.fullname }')
time.sleep(1)

#defeat driver signing. Due to window focus issues, this must be accomplished with the mouse.
#TODO this will break at different resolutions. Am I SURE it won't work with keyboard input?
#“BCDEDIT /set nointegritychecks ON” doesn't work.
qemu.cmd_obj(json.loads('{ "execute": "input-send-event", "arguments": { "events": [{ "type": "abs", "data" : { "axis": "x", "value" : 19000 } },{ "type": "abs", "data" : { "axis": "y", "value" : 16000 } } ] } }' ))
qemu.cmd_obj(json.loads('{ "execute": "input-send-event", "arguments": { "events": [ { "type": "btn", "data" : { "down": true, "button": "left" } } ] } }' ))
qemu.cmd_obj(json.loads('{ "execute": "input-send-event", "arguments": { "events": [ { "type": "btn", "data" : { "down": false, "button": "left" } } ] } }' ))

time.sleep(10)

sendwincmd(qemu, 'get-childitem -recurse -path d:/*/w10/amd64/*.inf | foreach-object { pnputil -a $_.fullname -install }')
time.sleep(10)

#install guest agent
sendwincmd(qemu, 'd:/guest-agent/qemu-ga-x86_64.msi')
time.sleep(10)

#shutdown
qmsendkey(qemu,'meta_l-x')
time.sleep(1)
qmsendkey(qemu,'u')
time.sleep(1)
qmsendkey(qemu,'u')
time.sleep(60)

winvm.config.set(net0='virtio=7E:C9:51:27:D9:60,bridge=vmbr0,firewall=1')
winvm.config.set(scsihw='virtio-scsi-pci')
winvm.config.set(delete='sata1')

winvm.status.start.create()
time.sleep(120)


