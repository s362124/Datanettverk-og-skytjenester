#import socket module
from socket import * 
import sys # In order to terminate the program
serverSocket = socket(AF_INET, SOCK_STREAM) #Create a socket object

#Prepare a sever socket
serverHost = "localhost" #Define the host address for the server
serverPort = 6794 #Define the port number for the server
serverSocket = socket(AF_INET, SOCK_STREAM) 
serverSocket.bind((serverHost, serverPort)) #Bind the socket to the host and port
serverSocket.listen(1) #Listen for incoming connections

print("Web server is up on port: ", serverPort) #Print the port number the server is running on



while True:
	#Establish the connection 
	print('Ready to serve...')
	connectionSocket, addr = serverSocket.accept()
	print("Connection from: "+ str(addr)) #Print the address of the connection
	
	try:
		message = connectionSocket.recv(1024) 
		print(message.decode()) #Store the message from the client into the variable "message"
		
		filename = message.split()[1] #Split the message to extract the filename
		f = open(filename[1:]) #Open the file stored in the variable "filename"
		 
		outputdata = f.read() #Read the content of the file and store it into the variable "outputdata"
		#Send one HTTP header line into socket
		connectionSocket.sendall("HTTP/1.1 200 OK\r\n\r\n".encode())
		
		#Send the content of the requested file to the client 
		for i in range(0, len(outputdata)): #Loop through the variable "outputdata" and send the content to the client
			connectionSocket.send(outputdata[i].encode()) 
		connectionSocket.send("\r\n".encode())
		connectionSocket.close() #Close the connection socket


#Handle IOError exception if the file not found
	except IOError:
		#Send response message for file not found
    
		connectionSocket.send("HTTP/1.1 404 Not Found\r\n\r\n".encode())
		connectionSocket.send("<html><head></head><body><h1>404 Not Found </h1></body></html>\r\n".encode())

		
		#Close client socket
		connectionSocket.close()
		
serverSocket.close()
sys.exit()#Terminate the program after sending the corresponding data