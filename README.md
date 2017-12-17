# baseitem
A simple library for converting complex data-types to and from native Python data-types.

## Get It Now
```sh
pip install baseitem
```

## How to Use It?
```python
# -*- coding: utf-8 -*-
from baseitem import BaseItem, Type, dumps_item


class Shoe(BaseItem):
    """
    The Object class for shoe.
    """

    color = Type(data_type=str)
    size = Type(data_type=int)


class Person(BaseItem):
    """
    The Object class for person.
    """
  
    # It must be `str`, or exception will be triggered.
    name = Type(data_type=str)
  
    # It must be `str`, or exception will be triggered.
    sex = Type(data_type=str)
  
    # It must be `int`, or exception will be triggered.
    age = Type(data_type=int)
  
    # It must be `list`, and its child-record must be `str`, or exception will be triggered.
    hobbies = Type(data_type=list, child_type=str)
  
    # It must be `Shoe`, or exception will be triggered.
    shoe = Type(data_type=Shoe)
  
    # It must be `list`, and its child-record must be `Shoe`, or exception will be triggered.
    shoes = Type(data_type=list, child_type=Shoe)


if __name__ == u'__main__':
    # The 1st method for initing attribute.
    sean = Person(sex=u'man')
    
    # The 2nd method for initing attribute.
    sean.name = u'Sean'
    
    # The 3rd method for initing attribute.
    sean[u'age'] = 25
    
    shoe0 = Shoe()
    # The 4th method for initing attribute.
    setattr(shoe0, u'color', u'red')
    shoe0.size = 43
    sean.shoe = shoe0
    sean.shoes = [shoe0]
    
    # The 1st method for getting attribute.
    print(sean.name)  # u'Sean'
    
    # The 2nd method for getting attribute.
    print(sean[u'sex'])  # u'man'
    
    # The 3rd method for getting attribute.
    print(getattr(sean, u'age', 0))  # 25
    
    # This method will convert Person class to a dictionary-data
    p_dict = dumps_item(sean)  # {u'name': u'Sean', u'sex': u'man', u'age': 25, u'hobbies': [], u'shoe': {u'color': u'red', u'size': 43}, u'shoes': [{u'color': u'red', u'size': 43}]}
    
```
