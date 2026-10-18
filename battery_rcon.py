import os
import re
import socket
import struct

# match enable-rcon / rcon.port / rcon.password in the test server's server.properties
HOST = os.environ.get('RCON_HOST', '127.0.0.1')
PORT = int(os.environ.get('RCON_PORT', '25575'))
PASSWORD = os.environ.get('RCON_PASSWORD', 'notechtest')


class Rcon:
    def __init__(self):
        self.s = socket.create_connection((HOST, PORT), timeout=900)
        self.n = 0
        self.cmd(PASSWORD, 3)

    def _recv(self):
        n = struct.unpack('<i', self._read(4))[0]
        d = self._read(n)
        return d[8:-2].decode('utf-8', 'replace')

    def _read(self, n):
        b = b''
        while len(b) < n:
            b += self.s.recv(n - len(b))
        return b

    def cmd(self, c, typ=2):
        self.n += 1
        body = c.encode() + b'\x00\x00'
        self.s.sendall(struct.pack('<iii', len(body) + 8, self.n, typ) + body)
        out = self._recv()
        if typ == 2:
            print(f'> {c}\n  {re.sub(r"§.", "", out)[:600]}', flush=True)
        return out
