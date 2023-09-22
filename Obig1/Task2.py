from pickle import GET # Import the GET function from the pickle library 
from socket import * # Import socket functions from the socket library 
import sys # Import the sys module

server_host = sys.argv[1] # Set the server host to the first argument in the command line server_host = sys.argv[1
server_port = int(sys.argv[2]) # Set the server port to the second argument in the command line, converted to an integer server_port = int(sys.argv[2])
filename = sys.argv[3] # Set the filename to the third argument in the command line filename = sys.argv[3] 

host_port = ("%s:%s" %(server_host, server_port)) # Set the host port to the server host and port host_port = ("%s:%s" %(server_host, server_port))

# Try to open a socket connection to the server 
try:
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((server_host, server_port))

# Send a GET request for the specified file clientSocket.sendall(("GET /" + filename + "\nHTTP/1.1 200 OK\n
    clientSocket.sendall(("GET /" + filename + "\nHTTP/1.1 200 OK\n\n").encode())
    response_message = clientSocket.recv(1024) #Receive the resonse message from the server 
    print("The response message is: ", response_message.decode()) #Print the response messange to the consolr

except IOError:
    sys.exit(1) #Handle an IOError by exiting the program

clientSocket.close() #Close the client socket connection



