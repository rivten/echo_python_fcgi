run:
    lighttpd -D -f lighttpd.conf

do_request:
    curl -X POST http://localhost:3000/hello/index/blah\?param=v1\&other=v2 -H "Content-Type: application/json" -d '{"name": "rivten"}'
