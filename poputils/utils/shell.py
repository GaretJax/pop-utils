"""
Utilities to manage shell output and interaction.
"""

import sys
import time


GRAY, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


def wait(obj, status, updater=None, interval=1, state='available'):
    """
    Waits until the ``state`` attribute of the ``obj`` object changes its value
    to ``status``.
    
    The object is updated each ``interval`` seconds through the ``updater``
    callale and the status checked.
    """
    
    if updater is None:
        def updater(obj):
            obj.update()
            return obj
    
    sys.stdout.write('    ')
    sys.stdout.flush()
    cnt = 4
    
    while obj.state != status:
        time.sleep(interval)
        obj = updater(obj)
        
        if cnt > 1:
            sys.stdout.write('\b' * cnt + '.' + ' ' * (cnt-1))
            sys.stdout.flush()
            cnt -= 1
        else:
            cnt = 4
            sys.stdout.write('\b' * cnt + ' ' * cnt)
            sys.stdout.flush()
        
    print '\b\b\b\b\b' + '... [' + hilite('OK', GREEN) + ']'

    return obj

class Step(object):
    
    width = 72
    
    def __init__(self, step):
        self.step = step
    
    def __enter__(self):
        self.start = time.time()
        
        s = '[step {0}]  '.format(self.step)
        l = len(s)
        print hilite(s, YELLOW),
        
        self.indenter = Indenter(l, False)
        self.indenter.__enter__()
        
        self.wrapper = Wrapper(self.width - l)
        self.wrapper.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wrapper.__exit__(exc_type, exc_val, exc_tb)
        self.indenter.__exit__(exc_type, exc_val, exc_tb)
        
        d = time.time() - self.start
        if d >= 60:
            t = ' ({0:02.0f}m {1:02.9f}s)'.format(d // 60, d % 60)
        else:
            t = ' ({0:05.2f}s)'.format(d)
        
        if exc_type is None:
            s = 'SUCCESS'
            l = len(s)
            s = hilite(s, GREEN)
        else:
            s = 'FAILED'
            l = len(s)
            s = hilite(s, RED)
        
        l += len(t)
        
        if exc_type:
            err = exc_type.__name__ + ":"
            try:
                msg = exc_val.args[0]
            except (AttributeError, IndexError):
                msg = str(exc_val)
                
            msg = Wrapper.wrap(msg, 72 - len(err) - 1)
            msg = Indenter.indent(msg, len(err) + 1).lstrip()
            print '\n', hilite(err, RED, True), msg, '\n'
        
        print ' ' * (self.width - l) + s + t
        
        print "-" * self.width


class Indenter(object):
    def __init__(self, width=4, firstline=True):
        self.width = width
        self.line = firstline
    
    def __enter__(self):
        self.stdout, sys.stdout = sys.stdout, self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.stdout
    
    def isatty(self):
        return self.stdout.isatty()
    
    @staticmethod
    def indent(string, width):
        lines = string.split('\n')
        lines = [' ' * width + line if line else '' for line in lines]
        return '\n'.join(lines)
    
    def write(self, string):
        text = self.indent(string, self.width)
        
        if not self.line and text != '\n':
            text = text[self.width:]
        self.stdout.write(text)
        
        self.line = string.count('\n')
    
    def flush(self):
        self.stdout.flush()


class Wrapper(object):
    def __init__(self, width=72, firstline=None):
        self.width = width
        self.first = firstline if firstline else width

    def __enter__(self):
        self.stdout, sys.stdout = sys.stdout, self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.stdout

    def isatty(self):
        return self.stdout.isatty()

    @staticmethod
    def wrap(text, width=72, firstline=None):
        linewidth = firstline if firstline else width

        l = 0
        line = []
        lines = []

        # Remove shell escape sequences
        #text = 

        for word in text.split(' '):
            if l + len(word) > linewidth:
                line = ' '.join(line)
                sublines = line.split('\n')

                if len(sublines) > 1:
                    lines += sublines[:-1]
                    line = [sublines[-1],]
                    l = len(sublines[-1])
                else:
                    lines.append(sublines[0])
                    line = []
                    l = 0

                linewidth = width

            line.append(word)
            l += len(word) + 1

        lines.append(' '.join(line))

        return '\n'.join(lines)

    def write(self, string):
        text = self.wrap(string, self.width, self.first)
        
        self.firstline = self.width
        self.stdout.write(text)

    def flush(self):
        self.stdout.flush()


def hilite(string, color=None, bold=False, background=None):
    if not sys.stdout.isatty():
        color = None
        bold = None
        background = None
    
    attr = []
    
    if color:
        attr.append(str(color + 30))
    
    if background:
        attr.append(str(background + 40))
    
    if bold:
        attr.append('1')
    
    return '\x1b[{0}m{1}\x1b[0m'.format(';'.join(attr), string)


class Border(object):
    def __init__(self, width=72, newlines=True, char='-'):
        self.width = width
        self.newlines = newlines
        self.char = char

    def __enter__(self):
        if self.newlines:
            print
        print self.char * self.width 
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print self.char * self.width
        if self.newlines:
            print


def main(parser, func):
    parser.add_argument('-d', '--debug', action='store_true')
    
    try:
        args = parser.parse_args()
        print '\n' + "-" * 72
        status = func(args)
        print
        return status
    except Exception:
        if args.debug:
            import traceback
            print
            print '\n'.join(traceback.format_exc().split('\n'))
        else:
            print "\nThe command execution failed due to en error. Use the --debug option to\nprint the full traceback."
        print
        return 1
        
