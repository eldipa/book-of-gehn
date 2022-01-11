#!/usr/bin/env python3

'''
Start a web server like Python's http.server will do but with an
additional tweak: if the URL requested matches one trigger glob
pattern, a command is executed.

With this, a server could recompute something just pressing F5
from a browser.
'''

import glob, os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
from functools import partial
import contextlib, socket, subprocess
from http import HTTPStatus

class ReactiveHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, cmd='make', triggers=None, **kwargs):
        self.triggers = triggers
        self.cmd = cmd
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if not self.may_recompile_or_fail():
            return

        super().do_GET()

    def do_HEAD(self):
        if not self.may_recompile_or_fail():
            return

        super().do_HEAD()

    def should_recompile(self):
        path = self.translate_path(self.path)
        for trigger in self.triggers:
            watchset = glob.glob(trigger, recursive=True)
            if path in watchset:
                print(f"Target matched: {trigger}")
                return True

        return False

    def may_recompile_or_fail(self):
        if self.should_recompile():
            path = self.translate_path(self.path)
            env = dict(os.environ)

            if os.path.splitext(path)[1] == '.html':
                env['PAGETARGET'] = path
                print(f"Recompiling {path}")
            else:
                print(f"Recompiling <all>")

            ret = subprocess.call(self.cmd, shell=True, env=env)
            if ret != 0:
                self.send_error(HTTPStatus.IM_A_TEAPOT, "Recompilation failed")
                return False

        return True


def _get_best_family(*address):
    infos = socket.getaddrinfo(
        *address,
        type=socket.SOCK_STREAM,
        flags=socket.AI_PASSIVE,
    )
    family, type, proto, canonname, sockaddr = next(iter(infos))
    return family, sockaddr


def serve(HandlerClass,
         ServerClass,
         protocol="HTTP/1.0", port=8000, bind=None):
    """Test the HTTP request handler class.

    This runs an HTTP server on port 8000 (or the port argument).

    """
    ServerClass.address_family, addr = _get_best_family(bind, port)

    HandlerClass.protocol_version = protocol
    with ServerClass(addr, HandlerClass) as httpd:
        host, port = httpd.socket.getsockname()[:2]
        url_host = f'[{host}]' if ':' in host else host
        print(
            f"Serving HTTP on {host} port {port} "
            f"(http://{url_host}:{port}/) ..."
        )
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)

if __name__ == '__main__':
    # Note: copied from http.server. My bad.
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
                        help='Specify alternative directory '
                        '[default:current directory]')
    parser.add_argument('--command', '-c', default='make',
                        help='Specify what command run when a trigger is activated.')
    parser.add_argument('--trigger', '-t',
                        action='append',
                        dest='triggers',
                        help='Glob target to watch (you can add more than one)')
    parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    handler_class = partial(ReactiveHTTPRequestHandler,
                                triggers=args.triggers,
                                cmd=args.command,
                                directory=args.directory)

    # ensure dual-stack is not disabled; ref #38907
    class DualStackServer(ThreadingHTTPServer):
        def server_bind(self):
            # suppress exception when protocol is IPv4
            with contextlib.suppress(Exception):
                self.socket.setsockopt(
                    socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

    serve(
        HandlerClass=handler_class,
        ServerClass=DualStackServer,
        port=args.port,
        bind=args.bind,
    )
