from argparse import ArgumentParser
from socket import socket, AF_INET, SOCK_DGRAM
from urllib.parse import quote, unquote

DEFAULT_ORIGIN_SERVER_PORT = 8080

def parseArgsHttpServer() -> tuple:
    """
    Purpose: Takes in command line arguments for the "httpserver" program; Parses out
             the replica server port to run the HTTP server on along with the origin
             server's address and the origin server's port number; If no origin server
             port number is passed in, the default port number 8080 is returned,
    :return: tuple representing the origin server address, the origin server port, and
             the replica server port to run the HTTP server on.
    """
    parser = ArgumentParser()
    parser.add_argument("-p", dest="port", type=int, required=True, help="<port>")
    parser.add_argument("-o", dest="origin_server", type=str, required=True, help="<origin>")
    args = parser.parse_args()
    if args.origin_server.rfind(":") == -1:  # i.e., if no origin server port number is passed in
        origin_server = args.origin_server
        origin_port = str(DEFAULT_ORIGIN_SERVER_PORT)  # default=8080
    else:
        origin_server = args.origin_server[ : args.origin_server.rfind(":") ]
        origin_port = args.origin_server[ args.origin_server.rfind(":")+1 : ]
    replica_server_port = args.port
    return origin_server, origin_port, replica_server_port

def getLocalIpAddress() -> str:
    """
    Purpose: Gets the IP adadress of the local machine and returns it.
    :return: str representing the local IP address.
    """
    s = socket(AF_INET, SOCK_DGRAM)
    s.connect( ("8.8.8.8", 80) )
    local_ip_address = s.getsockname()[0]
    s.close()
    return local_ip_address

def formatPath(raw_path: str) -> str:
    """
    Purpose: Takes in the path requested in a GET request to "httpserver", finds the
             component of the path after the last "/", replaces spaces with underscores,
             and returns the quoted version of the path (if the path is not currently
             quoted) using urllib.parse.
    :param raw_path: str representing 
    :return: str representing
    """
    path = raw_path.split("/")[-1]
    path = path.replace(" ", "_") 
    return path if (path != unquote(path)) else quote(path)

