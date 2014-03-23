from functools import wraps

class command(object):
  def __init__(self, matcher=None):
    self._matcher = matcher

  def __call__(self, func):
    # Default the command's name to an exact match of the function's name.
    # ^func_name$
    matcher = self._matcher
    if matcher is None:
      matcher = r'^%s$' % func.func_name

    # convert matcher to regular expression
    matcher = matcher

    @wraps(func)
    def wrapped_command(*args, **kwargs):
      return func(*args, **kwargs)
    wrapped_command._type = "COMMAND"
    wrapped_command._matcher = matcher
    return wrapped_command
    
class raw(object):
  def __init__(self, matcher=None):
    self._matcher = matcher

  def __call__(self, func):
    # convert matcher to regular expression
    matcher = self._matcher

    @wraps(func)
    def wrapped_command(*args, **kwargs):
      return func(*args, **kwargs)
    wrapped_command._type = "RAW"
    wrapped_command._matcher = matcher
    return wrapped_command


class msg(object):
  def __init__(self, matcher=None):
    self._matcher = matcher

  def __call__(self, func):
    # convert matcher to regular expression
    matcher = self._matcher

    @wraps(func)
    def wrapped_command(*args, **kwargs):
      return func(*args, **kwargs)
    wrapped_command._type = "PRIVMSG"
    wrapped_command._matcher = matcher
    return wrapped_command

def interval(milliseconds):
  def wrapped(func):
    @wraps(func)
    def wrapped_command(*args, **kwargs):
      return func(*args, **kwargs)
    wrapped_command._type = "REPEAT"
    wrapped_command._interval = milliseconds
    return wrapped_command
  return wrapped
