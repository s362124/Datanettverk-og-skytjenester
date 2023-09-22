import socket #Import the socket module so that the program can use the socket
from _thread import * #Import the _thread module so that the program can use the _thread.start_new_thread function
from threading import Thread #from threading import Thread - Import the Thread module so that the program can use the Thread class

#Create a function that processes data received from the client
def clientThread(client):
    while True:
        data = client.recv(1024) #Receive data from the client
        if not data:
            break
        client.send(data) #Send data to the client
        client.close() # Close the connection with the clien

        #Create a function that will run the main part of the program
        def Main():
            serverHost = "" #Initialize the serverHost variable to an empty string
            serverPort = 6794 #Initialize the serverPort variable to 6794
            clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Initialize a socket for the connection
            clientSocket.bind((serverHost, serverPort)) #Bind the socket to the host and port
            print("Socket binded to port: ", serverPort) #Print a message

            clientSocket.listen(5) #Listens for up to 5 connection requests
            print("Socket is listning...") #Prints a message to the console that the socket is listening for requests

            while True: #This loop will run indefinitely until an error occurs or the connection is terminated 
                client, addr = clientSocket.accept()  #This line will accept connections from a client
                print("Connected to", addr[0],":",str(addr[1])) #This line will print the address of the client that connected
                Thread(target = clientThread, args = (client,)).start() #This line will start a thread to handle client requests
                clientSocket.close() #This line will close the client socket to end the connection

                if __name__ == "__main__":  #Run the Main() function if this file is being run as the main program.
                    Main()
                