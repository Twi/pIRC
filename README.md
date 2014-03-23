# pIRC

Slim, concise python-based IRC bot library. Based on this [pyrc library](https://github.com/sarenji/pyrc).

## Installation

```bash
$ pip install pIRC
```

## Example Usage

```python
import pIRC

if __name__ == '__main__':
    bot = pIRC.CustomBot('irc.website.com', 
                        nick        = 'DaBot',
                        names       = ['Hey Bot','Yo Bot']
                        channels    = ['#Chan-chan'],
                        realname    = 'pIRC Bot',
                        ident       = 'BOT',
                        command     = '$',
                        replace     = dict(
                            me = 'self.config["nick"]'
                            ),
                        verbose = True,
                        break_on_match = False,
                        hookscripts = ['custom_hooks'],
                        password = 'thisisnotapassword',
                        reload_override = True
                        )
    bot.connect()
```
```python
## filename: custom_hooks.py

import sys
import pIRC.hooks as hooks

MODULES = ['parse']

@hooks.command('^reload$')
def modreload(self, target, sender, *args):
  for x in MODULES:
    if x in sys.modules:
      reload(sys.modules[x])
    else:
      sys.modules[x] = __import__(x)
  self.load_hooks()

@hooks.command('^repeat (.*)$')
def repeat(self, target, sender, *args):
  self.message(target, "%s says %s"%(sender,args[1]))

@hooks.msg('^how are you doing today :me:\?')
def greeting_reply(self, target, sender, *args):
    self.message(target, "I'm doing just fine, %s."%sender)
```
```python
## filename: parse.py

from re import match

def nuh(userhost):
  return match('(\S*)!(\S*)@(\S*)',string).groups()
```
Then on IRC, after the bot logs in:
```
<user> Hey Bot, repeat command via name
<DaBot> user said command via name
<user> how are you doing today DaBot?
<DaBot> I'm doing just fine, user.
<user> $repeat command via command string
<DaBot> user said command via command string
```

## TODO
* More descriptive documentation
* Add more default IRC controls