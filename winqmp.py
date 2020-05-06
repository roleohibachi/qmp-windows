#!/usr/bin/python3
import qmp
import json
import time

def validateqcode(qcode):
  #note this allows all conventional qcodes:
  #'a', 'shift-a'
  #as well as extended ones, which work in qmsendkey() too.
  #'ctrl-shift-a'
  validcodes=['unmapped','pause','ro','kp_comma','kp_equals','power','hiragana','henkan','yen','sleep','wake','audionext','audioprev','audiostop','audioplay','audiomute','volumeup','volumedown','mediaselect','mail','calculator','computer','ac_home','ac_back','ac_forward','ac_refresh','ac_bookmarks','muhenkan','katakanahiragana','shift','shift_r','alt','alt_r','ctrl','ctrl_r','menu','esc','1','2','3','4','5','6','7','8','9','0','minus','equal','backspace','tab','q','w','e','r','t','y','u','i','o','p','bracket_left','bracket_right','ret','a','s','d','f','g','h','j','k','l','semicolon','apostrophe','grave_accent','backslash','z','x','c','v','b','n','m','comma','dot','slash','asterisk','spc','caps_lock','f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','num_lock','scroll_lock','kp_divide','kp_multiply','kp_subtract','kp_add','kp_enter','kp_decimal','sysrq','kp_0','kp_1','kp_2','kp_3','kp_4','kp_5','kp_6','kp_7','kp_8','kp_9','less','f11','f12','print','home','pgup','pgdn','end','left','up','down','right','insert','delete','stop','again','props','undo','front','copy','open','paste','find','cut','lf','help','meta_l','meta_r','compose']
  output=all(code in validcodes for code in qcode.lower().split('-'))
  return output

def qmsendkey(qemu, qcode):
  #this supports all standard send-key QKeyCode values, as well as
  #combined modifiers of the type 'shift-a' and 'ctrl-alt-del'.
  #it will not correctly send complex sequential modifiers, like
  #'alt-kp_9-kp_9' (these will be sent as 'alt-kp_9')
  assert validateqcode(qcode)
  output='{ "execute": "send-key", "arguments": { "keys": [ '
  for code in qcode.split('-'):
    output+='{ "type": "qcode", "data": "'+code+'" },'
  output=output[:-1] # remove trailing comma
  output+='] } }'
  return qemu.cmd_obj(json.loads(output))

def qmsendwinaltcode(qemu, char='a'):
  #Send a character via CP437 encoding, with the windows left-alt-key trick.
  #TODO: extend this to unicode, which is also supported by the left-alt-key. Low priority.
  assert len(char)==1
  output='''{ "execute": "input-send-event", "arguments": { "events": [ { "type": "key", "data" : { "down": true, "key": {"type": "qcode", "data": "alt" } } },'''
  for digit in str(char.encode('cp437')[0]):
    output+='''{ "type": "key", "data" : { "down": true, "key": {"type": "qcode", "data": "kp_''' + digit + '''" } } },'''
    output+='''{ "type": "key", "data" : { "down": false, "key": {"type": "qcode", "data": "kp_''' + digit + '''" } } },'''
  output+='''{ "type": "key", "data" : { "down": false, "key": {"type": "qcode", "data": "alt" } } } ] } }'''
  return qemu.cmd_obj(json.loads(output))

def qmsendstr(qemu, string):
  #can't recommend using this for anything but simple alphanumeric text. Most characters aren't allowed. Perhaps someone has written a translation scheme, but it will vary with input encodings (yuck).
  for char in list(string):
    if char.isupper():
      char = 'shift-'+char.lower()
    qmsendkey(qemu, char)

def qmsendwinstr(qemu, string):
  #works with anything in CP437. No emoji or you'll break the poor thing.
  for char in string:
    qmsendwinaltcode(qemu, char)

def sendwincmd(qemu, cmd="echo test"):
  qmsendwinstr(qemu, cmd)
  qmsendkey(qemu, 'ret')

def launch_powershell(qemu):
  #launch admin powershell
  qmsendkey(qemu,'meta_l-x')
  time.sleep(1)
  qmsendkey(qemu,'a') #"admin powershell"
  time.sleep(2)
  #defeat UAC
  qmsendkey(qemu,'shift-tab')
  time.sleep(1)
  qmsendkey(qemu,'ret')
  time.sleep(10)


