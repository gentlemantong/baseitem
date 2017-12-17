# -*- coding: utf-8 -*-
import logging
import re
import sys

import six
from scrapy.item import DictItem, ItemMeta, Field

_child_allowed_types = [list]

if sys.version_info < (3, 4):
    _char_types = [str, unicode]
else:
    _char_types = [str]


class Type(Field):
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

    def __getattr__(self, name):
        """
        重写属性获取方法
        :param name: 属性名
        :return: 属性值
        """
        if name in self.fields:
            return self._values[name]
        else:
            raise AttributeError(u'Invalid field: {0}!'.format(name))

    def __setattr__(self, name, value):
        """
        重写属性赋值方法
        :param name: 属性名
        :param value: 属性值
        :return: 无
        """
        if not name.startswith(u'_'):
            if name in self.fields:
                data_type = self.fields[name][u'data_type']
                if data_type in _child_allowed_types:
                    child_type = self.fields[name][u'child_type']
                    val_list = []
                    for val in value:
                        try:
                            if (child_type in _char_types and type(val) in _char_types) or isinstance(val, child_type):
                                val_list.append(val)
                            else:
                                raise TypeError(u"({0}, {1}) is not a valid child-record for '{2}' while whose standard"
                                                u" child_type is {3}".format(val, type(val), name, child_type))
                        except Exception as e:
                            logging.exception(u"Invalid child-record, it'll be passed! - {0}".format(e))
                    self._values[name] = val_list
                elif (data_type in _char_types and type(value) in _char_types) or isinstance(value, data_type):
                    self._values[name] = value
                else:
                    raise TypeError(u"({0}, {1}) is not valid for '{2}' while whose standard type is {3}".format(
                        value, type(value), name, data_type))
            else:
                raise AttributeError(u'Invalid field: {0}!'.format(name))
        else:
            super(BaseItem, self).__setattr__(name, value)


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
                        val_obj = dumps_item_to_dict(val)
                    else:
                        val_obj = getattr(item, key)
                    val_list.append(val_obj)
                result_dict[key] = val_list
            elif issubclass(data_type, BaseItem):
                result_dict[key] = dumps_item_to_dict(getattr(item, key))
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
