#!/usr/bin/env python
# from box import Box
# name = "John"
# boxed = Box(
#   {
#   "var": {
#     "name":"John"
#   }
# }
# )
# print("name is {var.name}".format(**boxed))
dict1 = {  'Ritika': 5, 'Sam': 7, 'John' : 10 }
 
# Create second dictionary
dict2 = {'Aadi': 8,'Sam': 20,'Mark' : 11 }

# Merge contents of dict2 in dict1
dict1.update(dict2)
print('Updated dictionary 1 :')
print(dict1)
