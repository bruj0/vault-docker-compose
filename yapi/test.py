#!/usr/bin/env python
from box import Box
name = "John"
boxed = Box(
  {
  "var": {
    "name":"John"
  }
}
)
print("name is {var.name}".format(**boxed))
