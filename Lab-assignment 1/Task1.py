#Task1:
"""Write a function named jains that takes two throughput values (int and/or float) as arguments and
returns a JFI."""

def jains(x,y):
    teller = (x+y)**2
    nevner = 2*(x**2+y**2) 
    resultat = teller/nevner
    return resultat
print(jains(4,3))

#Task2:
""""Write a new function jainsall function that takes a list of throughput values (integers and/or float)
and returns a JFI."""

liste = [1,2,3,4,5,6,7,8,9]
def jainsall(liste):
    teller = 0
    nevner = 0
    for i in liste:
        teller += i
        nevner += i ** 2
        resultat = teller / nevner
    return resultat

print(jainsall(liste))

#Task3:
""" Read the throughput values from a file and then use your jainsall function to calculate a JFI.
The text file contains:
7 Mbps
12 Mbps
15 Mbps
32 Mbps
You should only consider the numeric values."""


task3_List = [] #create an empty list

with open("Task3DataNettverk.txt") as task3:
   for line in task3:
      print(line) 
      split_line = line.split() #The split() method splits a string into a list-whitespace as a default
      task3_List.append(int(split_line[0]))  #only appending the first value

print(jainsall(task3_List))

#Task4:
"""Read the throughput values from a file and then use your
jainsall function to calculate a JFI. Note:
you must use the same units.
The text file contains:
7 Mbps
1200 Kbps
15 Mbps
32 Mbps"""

task4_List = [] #create an empty list

with open("Task4.txt") as task4:
    for line in task4:
        split_line = line.split() #The split() method splits a string into a list-whitspace as a default
        if()
        print(line)
        split_line = line.split()  #The split() method splits a string into a list-whitspace as a default
        task4_List.append(int(split_line[0])) #only appending the first value 
        print(jainsall(task4_List))
    