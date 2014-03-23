import inspect
import sys
import socket
import string
import re
import os

import threads

class Bot(object):
    def __init__(self, host, **kwargs):
        '''
        Initializes a new pyrc.Bot.
        '''
        nick = "PyrcBot" if self.__class__ == Bot else self.__class__.__name__
        password = os.environ.get('PASSWORD', None)

        self.config = dict(kwargs)
        self.config.setdefault('host', host)
        self.config.setdefault('port', 6667)
        self.config.setdefault('name', nick)
        self.config.setdefault('names', [self.config['nick']])
        self.config.setdefault('ident', nick.lower())
        self.config.setdefault('nick', self.config['name'])
        self.config.setdefault('realname', "pIRC Bot")
        self.config.setdefault('channels', [])
        self.config.setdefault('command', '!')
        self.config.setdefault('password', password)
        self.config.setdefault('break_on_match', True)
        self.config.setdefault('verbose', True)
        self.config.setdefault('replace', {})

        self._inbuffer = ""
        self._commands = []
        self._privmsgs = []
        self._raws = []    
        self._threads = []
        self.socket = None
        self.initialized = False
        self.listeners = {}

        # init funcs
        self._add_listeners()
        self._loadhooks()
        self._compile_strip_prefix()

    def message(self, recipient, s):
        "High level interface to sending an IRC message."
        self._cmd("PRIVMSG %s :%s" % (recipient, s))

    def connect(self):
        '''
        Connects to the IRC server with the options defined in `config`
        '''
        self._connect()

        try:
            self._listen()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            self.close()

    def _listen(self):
        """
        Constantly listens to the input from the server. Since the messages come
        in pieces, we wait until we receive 1 or more full lines to start parsing.

        A new line is defined as ending in \r\n in the RFC, but some servers
        separate by \n. This script takes care of both.
        """
        while True:
            self._inbuffer = self._inbuffer + self.socket.recv(2048)
            # Some IRC servers disregard the RFC and split lines by \n rather than \r\n.

            temp = self._inbuffer.split("\n")
            self._inbuffer = temp.pop()

            for line in temp:
                # Strip \r from \r\n for RFC-compliant IRC servers.
                line = line.rstrip('\r')
                if self.config['verbose']: print line
                self._run_listeners(line)

    def _run_listeners(self, line):
        """
        Each listener's associated regular expression is matched against raw IRC
        input. If there is a match, the listener's associated function is called
        with all the regular expression's matched subgroups.
        """
        for regex, callbacks in self.listeners.iteritems():
            match = regex.match(line)

            if not match:
                continue

            for callback in callbacks:
                callback(*match.groups())

    def _loadhooks(self):
        for func in self.__class__.__dict__.values():
          if callable(func) and hasattr(func, '_type'):
            if func._type == 'COMMAND':
                self._commands.append(func)
            elif func._type == 'PRIVMSG':
                self._privmsgs.append(func)
            elif func._type == 'RAW':
                self._raws.append(func)
            elif func._type == 'REPEAT':
                self._threads.append(threads.JobThread(func, self))
            else:
                raise "This is not a type I've ever heard of."

    def _receivemessage(self, target, sender, message):
        message = message.strip()
        to_continue = True
        suffix = False
        if target.startswith("#"):
            suffix = self._strip_prefix(message)
        if suffix:
            to_continue = self._parsefuncs(target, sender, suffix, self._commands)
        else: # if it's not a channel, there's no need to use a prefix or highlight the bot's nick
            to_continue = self._parsefuncs(target, sender, message, self._commands)

        # if no command was executed
        if to_continue:
            to_continue = self._parsefuncs(target, sender, message, self._privmsgs)
            
        # if allowed to continue
        if to_continue:
            self._parsefuncs(target, sender, message, self._raws)
    
    def _parsefuncs(self, target, sender, message, funcs):
        for func in funcs:
            func._matcher = re.sub(':(\w*):',self._match_replace,func._matcher)
            match = re.compile(func._matcher).search(message)
            if match:
                group_dict = match.groupdict()
                groups = match.groups()

                if group_dict and (len(groups) > len(group_dict)):
                  # match.groups() also returns named parameters
                    raise "You cannot use both named and unnamed parameters"
                elif group_dict:
                    func(self, target, sender, **group_dict)
                else:
                    func(self, target, sender, *groups)

                if self.config['break_on_match']: return False
        return True
        
    def _match_replace(self, match):
        if match.group(1) in self.config['replace']:
            return eval(self.config['replace'][match.group(1)])
        else:
            return ''

    def _compile_strip_prefix(self):
        """
        regex example:
        ^(((BotA|BotB)[,:]?\s+)|%)(.+)$
        
        names = [BotA, BotB]
        command = %
        """

        name_regex_str = r'^(?:(?:(%s)[,:]?\s+)|%s)(.+)$' % (re.escape("|".join(self.config['names'])), re.escape(self.config['command']))
        self._name_regex = re.compile(name_regex_str, re.IGNORECASE)

    def _strip_prefix(self, message):
        """
        Checks if the bot was called by a user.
        Returns the suffix if so.

        Prefixes include the bot's nick as well as a set symbol.
        """
        
        search = self._name_regex.search(message)
        if search:
            return search.groups()[1]

        return None

    def _join(self, *channels):
        self._cmd('JOIN %s' % (' '.join(channels)))
        
    def _part(self, *channels):
        self._cmd('PART %s' % (' '.join(channels)))

    def _cmd(self, raw_line):
        if self.config['verbose']: print "> %s" % raw_line
        self.socket.send(raw_line + "\r\n")

    def _connect(self):
        """Connects a socket to the server using options defined in `config`."""
        self.socket = socket.socket()
        self.socket.connect((self.config['host'], self.config['port']))
        self._cmd("NICK %s" % self.config['nick'])
        self._cmd("USER %s %s 0 :%s" %
            (self.config['ident'], self.config['host'], self.config['realname']))

    def close(self):
        for thread in self._threads:
            thread.shutdown()
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()


    def _add_listeners(self):
        self._add_listener(r'^:\S+ 433 .*', self._nick)
        self._add_listener(r'^PING :(.*)', self._ping)
        self._add_listener(r'^:(\S+) PRIVMSG (\S+) :(.*)', self._privmsg)
        self._add_listener(r'^:(\S+)!\S+ INVITE \S+ :?(.*)', self._invite)
        self._add_listener(r'^\S+ MODE %s :*\+([a-zA-Z]+)' % self.config['nick'],
            self._mode)

    def _add_listener(self, regex, func):
        array = self.listeners.setdefault(re.compile(regex), [])
        array.append(func)

      # Default listeners

    def _add_raw_listener(self, regex, func):
        self._add_listener(re.compile(r'%s'%regex), func)
        
    def _add_num_listener(self, num, func):
        self._add_listener(r'^:\S+ %d %s :?(.*)'%(num,self.config['nick']),func)
    
    def _nick(self, nick=True):
        if nick is True:
            self.config["nick"] = self.config["name"]
        else:
            self.config["nick"] = nick
        self._cmd("NICK %s" % self.config["nick"])

    def _ping(self, host):
        self._cmd("PONG :%s" % host)

    def _privmsg(self, sender, target, message):
        self._receivemessage(target, sender, message)

    def _invite(self, inviter, channel):
        self._join(channel)

    def _mode(self, modes):
        print 'mode test'
        if 'i' in modes and self._should_autoident():
            self._cmd("PRIVMSG NickServ :identify %s" % self.config['password'])

        # Initialize (join rooms and start threads) if the bot is not
        # auto-identifying, or has just identified.
        # if ('r' in modes or not self._should_autoident()) and not self.initialized:
        self.initialized = True
        if self.config['channels']:
            self._join(*self.config['channels'])
        # TODO: This doesn't ensure that threads run at the right time, e.g.
        # after the bot has joined every channel it needs to.
        self._startthreads()
        
    def _startthreads(self):
        for thread in self._threads:
            if not thread.is_alive():
                thread.start()

    def _should_autoident(self):
        return self.config['password']

