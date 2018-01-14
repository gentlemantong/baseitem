# -*- coding: utf-8 -*-
import logging
import re
import sys
import weakref
from abc import ABCMeta
from collections import MutableMapping, defaultdict
from pprint import pformat
from time import time

import six

_child_allowed_types = [list]

if sys.version_info < (3, 4):
    _char_types = [str, unicode]
else:
    _char_types = [str]

live_refs = defaultdict(weakref.WeakKeyDictionary)


class ItemMeta(ABCMeta):

    def __new__(mcs, class_name, bases, attrs):
        classcell = attrs.pop('__classcell__', None)
        new_bases = tuple(base._class for base in bases if hasattr(base, '_class'))
        _class = super(ItemMeta, mcs).__new__(mcs, 'x_' + class_name, new_bases, attrs)

        fields = getattr(_class, 'fields', {})
        new_attrs = {}
        for n in dir(_class):
            v = getattr(_class, n)
            if isinstance(v, dict):
                fields[n] = v
            elif n in attrs:
                new_attrs[n] = attrs[n]

        new_attrs['fields'] = fields
        new_attrs['_class'] = _class
        if classcell is not None:
            new_attrs['__classcell__'] = classcell
        return super(ItemMeta, mcs).__new__(mcs, class_name, bases, new_attrs)


class ObjectRef(object):
    """
    从这个类（而不是Object）继承到保存实例的记录
    """

    __slots__ = ()

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        live_refs[cls][obj] = time()
        return obj


class DictItem(MutableMapping, ObjectRef):

    fields = {}

    def __init__(self, *args, **kwargs):
        self._values = {}
        if args or kwargs:  # avoid creating dict for most common case
            for k, v in six.iteritems(dict(*args, **kwargs)):
                self[k] = v

    def __getitem__(self, key):
        return self._values[key]

    def __setitem__(self, key, value):
        if key in self.fields:
            data_type = self.fields[key][u'data_type']
            if data_type in _child_allowed_types:
                child_type = self.fields[key][u'child_type']
                val_list = []
                for val in value:
                    try:
                        if (child_type in _char_types and type(val) in _char_types) or isinstance(val, child_type):
                            val_list.append(val)
                        else:
                            raise TypeError(u"({0}, {1}) is not a valid child-record for '{2}' while whose standard"
                                            u" child_type is {3}".format(val, type(val), key, child_type))
                    except Exception as e:
                        logging.exception(u"Invalid child-record, it'll be passed! - {0}".format(e))
                self._values[key] = val_list
            elif (data_type in _char_types and type(value) in _char_types) or isinstance(value, data_type):
                self._values[key] = value
            else:
                raise TypeError(u"({0}, {1}) is not valid for '{2}' while whose standard type is {3}".format(
                    value, type(value), key, data_type))
        else:
            raise KeyError("%s does not support field: %s" % (self.__class__.__name__, key))

    def __delitem__(self, key):
        del self._values[key]

    def __getattr__(self, name):
        return self._values[name]

    def __setattr__(self, name, value):
        if not name.startswith(u'_'):
            self.__setitem__(name, value)
        else:
            super(DictItem, self).__setattr__(name, value)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        return iter(self._values)

    __hash__ = ObjectRef.__hash__

    def keys(self):
        return self._values.keys()

    def __repr__(self):
        return pformat(dict(self))

    def copy(self):
        return self.__class__(self)


class Type(dict):
    """字段数据类型类"""

    def __init__(self, data_type=None, child_type=None):
        """
        初始化字段类型
        :param data_type: 当前字段类型
        :param child_type: 子字段类型
        """
        if data_type is None and child_type is None:
            raise AttributeError(u"You must init 'data_type' at least!")
        if data_type is None and child_type is not None:
            raise AttributeError(u"It's not allowed that 'data_type' is None while 'child_type' is not None!")
        if data_type is not None and child_type is None:
            if data_type in _child_allowed_types:
                raise AttributeError(u"While 'data_type' is in {0}, the 'child_type' must be inited!".format(
                    _child_allowed_types))
            super(Type, self).__init__(data_type=data_type)
        if data_type is not None and child_type is not None:
            if data_type not in _child_allowed_types:
                raise AttributeError(u"The 'child_type' can only be inited while 'data_type' is in {0}!".format(
                    _child_allowed_types))
            super(Type, self).__init__(data_type=data_type, child_type=child_type)


@six.add_metaclass(ItemMeta)
class BaseItem(DictItem):
    """结果父类"""

    def __init__(self, *args, **kwargs):
        """
        初始化结果父类
        :param args: args
        :param kwargs: kwargs
        """
        super(BaseItem, self).__init__(*args, **kwargs)


def dumps_item(item):
    """
    将BaseItem对象转换为dict，尚未赋值的字段会初始化为零值
    :param item: BaseItem对象
    :return: 结果dict
    """
    if not isinstance(item, BaseItem):
        raise TypeError(u'Invalid item: {0}'.format(type(item)))

    result_dict = dict()
    keys = item.keys()
    fields = item.fields
    field_keys = fields.keys()
    for key in field_keys:
        data_type = fields[key][u'data_type']
        if key not in keys:    # 将尚未赋值的字段初始化为零值
            if issubclass(data_type, BaseItem):
                result_dict[key] = dict()
            else:
                init_str = '{0}()'.format(__regular_by_scope(u'\'', u'\'', str(fields[key][u'data_type']))[0])
                result_dict[key] = eval(init_str)
        else:    # 将已经赋值的字段转为对应的字典值
            if data_type in _child_allowed_types:
                val_list = []
                child_type = fields[key][u'child_type']
                values = getattr(item, key)
                for val in values:
                    if issubclass(child_type, BaseItem):
                        val_obj = dumps_item(val)
                    else:
                        val_obj = val
                    val_list.append(val_obj)
                result_dict[key] = val_list
            elif issubclass(data_type, BaseItem):
                result_dict[key] = dumps_item(getattr(item, key))
            else:
                result_dict[key] = getattr(item, key)
    return result_dict


def __regular_by_scope(start, end, text, schema=0):
    """
    使用正则表达式提取文本中指定首尾范围的所有字符，以列表的形式返回
    :param start: 起始字符
    :param end: 结尾字符
    :param text: 原始文本
    :param schema: 匹配模式
        0-不包含起始字符和结尾字符
        1-包含起始字符，不包含结尾字符
        2-不包含起始字符，包含结尾字符
        3-包含起始字符和结尾字符
    :return: 结果列表
    """
    if schema == 0:
        expression = r'(?<=%s)(.+?)(?=%s)' % (start, end)
    elif schema == 1:
        expression = r'(?=%s)(.+?)(?=%s)' % (start, end)
    elif schema == 2:
        expression = r'(?<=%s)(.+?)(?<=%s)' % (start, end)
    elif schema == 3:
        expression = r'(?=%s)(.+?)(?<=%s)' % (start, end)
    else:
        raise ValueError(u'Invalid schema value! Param schema must be in [0, 1, 2, 3]! - schema:{0}'.format(schema))
    return re.findall(expression, text)
