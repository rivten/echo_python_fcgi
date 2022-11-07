#!/usr/bin/env /usr/bin/python3

import sys
import io
import os
import socket
import enum

def get_header(b):
    return {
        "version": int(b[0]),
        "type": int(b[1]),
        "requestId": int(b[2]) * 256 + int(b[3]),
        "contentLength": int(b[4]) * 256 + int(b[5]),
        "paddinglength": int(b[6]),
        "reserved": int(b[7]),
    }

def get_begin_request(b):
    return {
        "role": int(b[0]) * 256 + int(b[1]),
        "flags": int(b[2]),
        "reserved": b[3:8],
    }

def get_fcgi_params(b):
    params = {} 
    while len(b) > 0:
        assert(b[0] >> 7 == 0)
        assert(b[1] >> 7 == 0)
        nameLength = int(b[0])
        valueLength = int(b[1])
        params[b[2:nameLength + 2].decode('utf-8')] = b[nameLength + 2:nameLength + valueLength + 2].decode('utf-8')
        b = b[nameLength + valueLength + 2:]
    return params

def get_fcgi_stdin(b):
    return b.decode('utf-8')

class RequestType(enum.Enum):
    BEGIN_REQUEST = 1
    END_REQUEST = 3
    FCGI_PARAMS = 4
    FCGI_STDIN = 5
    FCGI_STDOUT = 6
    FCGI_STDERR = 7

s = socket.fromfd(0, socket.AF_INET, socket.SOCK_STREAM)
while True:
    (conn, address) = s.accept()
    with conn:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            request = {}
            while len(data) > 0:
                header = get_header(data)
                assert(header['version'] == 1)
                request['header'] = header
                data = data[8:]
                content = data[:header['contentLength']]
                data = data[header['contentLength']:]
                match header['type']:
                    case RequestType.BEGIN_REQUEST.value:
                        begin_request = get_begin_request(content)
                    case RequestType.FCGI_PARAMS.value:
                        fcgi_params = get_fcgi_params(content)
                        if not "params" in request:
                            request['params'] = {}
                        for k, v in fcgi_params.items():
                            request['params'][k] = v
                    case RequestType.FCGI_STDIN.value:
                        fcgi_stdin = get_fcgi_stdin(content)
                        if not 'stdin' in request:
                            request['stdin'] = ''
                        request['stdin'] += fcgi_stdin
                    case _:
                        assert(False)
            #print(request, file=sys.stderr)

            # STDOUT
            response = io.BytesIO()
            c = request['stdin']
            content = f'HTTP/1.1 200 OK\r\nDate: Mon, 27 Jul 2009 12:28:53 GMT\r\nServer: Apache/2.2.14 (Win32)\r\nLast-Modified: Wed, 22 Jul 2009 19:15:56 GMT\r\nContent-Length: {len(c)}\r\nContent-Type: text/html\r\nConnection: Closed\r\n\r\n{c}'.encode()
            contentLength = len(content)
            response.write((1).to_bytes(1, 'little'))
            response.write((RequestType.FCGI_STDOUT.value).to_bytes(1, 'little'))
            response.write((request['header']['requestId'] // 256).to_bytes(1, 'little'))
            response.write((request['header']['requestId'] % 256).to_bytes(1, 'little'))
            response.write((contentLength // 256).to_bytes(1, 'little'))
            response.write((contentLength % 256).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))

            response.write(content)
            #print(response.getvalue(), file=sys.stderr)
            conn.send(response.getvalue())

            # STDERR
            response = io.BytesIO()
            response.write((1).to_bytes(1, 'little'))
            response.write((RequestType.FCGI_STDERR.value).to_bytes(1, 'little'))
            response.write((request['header']['requestId'] // 256).to_bytes(1, 'little'))
            response.write((request['header']['requestId'] % 256).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))

            #print(response.getvalue(), file=sys.stderr)
            conn.send(response.getvalue())

            # END REQUEST
            response = io.BytesIO()
            response.write((1).to_bytes(1, 'little'))
            response.write((RequestType.END_REQUEST.value).to_bytes(1, 'little'))
            response.write((request['header']['requestId'] // 256).to_bytes(1, 'little'))
            response.write((request['header']['requestId'] % 256).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((8).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))

            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            response.write((0).to_bytes(1, 'little'))
            #print(response.getvalue(), file=sys.stderr)
            conn.send(response.getvalue())
