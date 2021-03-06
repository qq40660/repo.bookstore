#coding=utf-8
#
# Copyright (C) 2013  Kliyes.com  All rights reserved.
#
# author: JingYang.
#
# This file is part of BookStore.

import random, os, uuid
import logging

from django.conf import settings

logger = logging.getLogger("mysite")

def isFileExist(path):
    '''判断文件或目录是否存在'''
    if os.path.exists(path):    
        return True
    return False 

def remove(path, fileName):
    '''remove file from the filesystem'''
    if not fileName:
        return False
    
    fullpath = os.path.join(path, fileName)
    try:
        os.remove(fullpath)
        return True
    except OSError:
        logger.info("delete file %s error" % fullpath)
        return False
    
    
    
    