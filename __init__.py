
import sys
import base as New


def reload_modules(modlist):
    for x in modlist:
        if x in sys.modules:
            reload(sys.modules[x])
            print x + ' has been reloaded.'
        else:
            sys.modules[x] = __import__(x)
            print x + ' has been loaded.'
        
class CustomBot(New.Bot):
    """
    Config Vars
    
    host            (string)    : address to connect to
    port            (integer)   : port to connect with
    name            (string)    : bot's original name                                                   [seealso: nick]
    names           (list)      : a list of names that the bot will respond to for a command            [seealso: command]
    ident           (string)    : the 'user' part of 'nick!user@host * name'
    nick            (string)    : the 'nick' part of 'nick!user@host * name'; bot's temporary name
    realname        (string)    : the 'name' part of 'nick!user@host * name'
    channels        (list)      : a list of channels to autojoin on successful connect
    command         (string)    : a (sequence of) character(s) the bot will respond to for a command    [seealso: names]
    password        (string)    : passed to nickserv for authentication
    break_on_match  (bool)      : determines whether multiple matches are allowed per recieved line
    verbose         (bool)      : determines whether debug info is printed to the console
    replace         (dict)      : dictionary for custom regex variable replacement; form of ':key:';
                                    if key does not exist in the dict, :key: is removed from the regex
    hookscripts     (list)      : a list of module names that contain custom hooks
    reload_regex    (string)    : custom regex to be used in the default module reload implementation
    reload_func     (callable)  : custom func to be used in the default module reload implementation
    reload_override (bool)      : determines whether the default module implementation is used
    """

    def __init__(self, host, *args, **kwargs):
        
        super(CustomBot,self).__init__(host, *args,**kwargs)
        self.config.setdefault('hookscripts',[])
        self.config.setdefault('reload_override',False)
        
        for x in self.config['hookscripts']:
            sys.modules[x] = __import__(x)
            if self.config['verbose']: print x + ' has been imported.'
        
        self.load_hooks()
        
        if not self.config['reload_override']:
            self.config.setdefault('reload_regex','^:(\S+) PRIVMSG (\S+) :\%sreload$'%self.config['command'])
            self.config.setdefault('reload_func',self.load_hooks)
            self._add_raw_listener(r'%s'%self.config['reload_regex'],self.config['reload_func'])
        
    def load_hooks(self):
        if callable(self.config['hookscripts']):
            try:
                scripts = iter(self.config['hookscripts'])
            except TypeError:
                scripts = self.config['hookscripts']()
        else:
            scripts = list(self.config['hookscripts'])
        for x in scripts:
            [setattr(self.__class__,k,v) for k,v in sys.modules[x].__dict__.iteritems() if hasattr(v,'_type')]
            if self.config['verbose']: print "Hook script '%s' has been loaded."%x
        self._loadhooks()
        self._startthreads()
        
    def ns(self, message):
        self._cmd("PRIVMSG NickServ :%s"%message)
        
    def cs(self, message):
        self._cmd("PRIVMSG ChanServ :%s"%message)
