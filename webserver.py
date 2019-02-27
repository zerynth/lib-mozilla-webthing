import streams
import socket
import json

# we'll store here available API routes and methods
_routes = {}


def register_handler(path, method, func, args=()):
    # Register a new available path in the webserver.

    # * *path* is part of URL, e.g. "/my-path"
    # * *method* is the HTTP method which will be used for this path. E.g. GET, PUT, POST, ....
    # * *func* is a function or method which will be called when a request to this endpoint is received.
    #     This function will receive a payload as argument, and must return a dictionary to be sent as  JSON result for the request.
    #     Instead of returning a dictionary it is possible to return a tuple (status code, name, data) for
    #     specifying the HTTP return code. E.g. (404, 'Not Found', {}).
    # * *args* is a tuple of additional arguments which we'll be passed to `func`. Please note that the request payload
    #     will always be the last argument.
    global _routes
    if path not in _routes:
        _routes[path] = {}
    method = method.lower()
    _routes[path][method] = (func, args)


def remove_handler(path, method):
    # Remove a previously registered handler, identified by a path and a HTTP method.

    # * *path* is part of URL, e.g. "/my-path"
    # * *method* is the HTTP method which will be used for this path. E.g. GET, PUT, POST, ....
    global _routes
    if path in _routes:
        del _routes[path][method]


def start():
    sock = socket.socket()
    sock.bind(80)
    sock.listen()
    while True:
        #sleep(200)
        try:
            client_sock, address = sock.accept()
            client = streams.SocketStream(client_sock)

            method, path, payload = _parse_request(client)
            #print(method, path, payload)
            if path not in _routes:
                print("Not found: %s" % path)
                _send_code(client, 404, "Not Found")
            elif method not in _routes[path]:
                print("Invalid method %s for path %s" % (method, path))
                _send_code(client, 405, "Method Not Allowed")
            else:
                try:
                    #print(_routes[path][method])
                    fun, static_args = _routes[path][method]

                    #print(static_args,payload)

                    result = fun(static_args, payload)
                    # If result a simple variable we send it as it is,
                    # otherwise it's a tuple (code, name, response)
                    if type(result) == PTUPLE:
                        _send_code(client, result[0], result[1], body=result[2])
                    else:
                        _send_response(client, result)
                except NameError:
                    _send_code(client, 400, "Bad Request")
                except Exception as e:
                    print("Error executing callback")
                    print(e)
                    _send_code(client, 500, "Internal Server Error")

            client.close()
        except Exception as e:
            print("Error while sending response")
            print(e)


def _parse_request(client):
    line = client.readline()
    method, path, _ = line.split(" ")

    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    data_length = 0
    while line not in ("\r\n", "\n"):
        line = client.readline()
        if line.lower().startswith("content-length:"):
            data_length = int(line[16:-1])
            sleep(10)

    data = client.read(data_length)
    parsed_data = json.loads(data)

    return (method.lower(), path, parsed_data)


def _send_code(client, code, message, body=None):
    print("HTTP/1.1 %s %s\r" % (code, message), stream=client)
    print("Connection: close\r", stream=client)
    if body:
        print("Content-Type: text/json\r\n\r", stream=client)
        print(json.dumps(body), stream=client)
    else:
        print("Content-Type: text/html\r\n\r", stream=client)
        print("<html><body><h1>%s %s</h1></body></html>" % (code, message), stream=client)


def _send_response(client, data):
    print("HTTP/1.1 200 Ok\r", stream=client)
    print("Content-Type: text/json\r", stream=client)
    print("Connection: close\r\n\r", stream=client)
    print(json.dumps(data), stream=client)
