# ----------- Imports -----------

import math
from os import path, mkdir
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from configparser import ConfigParser

# ------- Static variables ------

ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz'

# ----- Function declaration ----

def parse_config(config_path):

    config = ConfigParser()
    config.read(config_path)
    
    parse_func = {'Integer': ConfigParser.getint,
                  'Float': ConfigParser.getfloat,
                  'Boolean': ConfigParser.getboolean}
    parsed_config = dict()
    for sec in config.sections():
        for k, v in config[sec].items():
            parsed_config[k] = parse_func[sec](self=config, section=sec, option=k)

    return parsed_config

def config_to_dic(config):
    
    tmp = dict()
    for sec in config.sections():
        tmp.update(config[sec])
    return tmp

def get_config_string(config):

    string = ''
    for k, v in config._sections.items():
        string += '[{0}]:\n{1}'.format(k, get_dic_string(v))
    return string

def get_dic_string(dic):

    string = ''
    items = list(dic.items())
    for i in range(len(items)):
        k, v = items[i]
        string += '{0}.\t\t{1} = {2}\n'.format(i+1, k, v)
    return string + '\n'

def execute_with_time(function, args):

    start_time = datetime.now()
    
    result = function(*args)

    duration = datetime.now() - start_time
    sec = duration.total_seconds()
    print('{0} - Execution Duration: {1} ({2} s)'.format(function, duration, sec))
    return result, duration

def create_dir(path_):
    
    if not path.exists(path_):
        mkdir(path_)
        
def export_pickle(obj, path_):
    
    with open(path_, 'wb') as f:
        pickle.dump(obj, f)#, protocol=2)
    
def export_csv(df, path_):
    
    df.to_csv(path_, index=False)
    
def get_obj_info(obj, detailed = False):

    obj_description = ''
    for attr in dir(obj):
        attr_str = "obj.{0} = {1}\n".format(attr, getattr(obj, attr))
        if(detailed):
            obj_description += attr_str
        elif('.__' not in attr_str and '<bound method' not in attr_str and '<built-in method' not in attr_str):
            obj_description += attr_str

    return obj_description
        
# - deprecated
        
# returns binominal coefficient (n Choose r)
def nCr(n,r):
    
    f = math.factorial
    return f(n) // f(r) // f(n-r)

#test for exact equality
def arreq_in_list(myarr, list_arrays):
    
    return next((True for elem in list_arrays if np.array_equal(elem, myarr)), False)

# functions for monomials creation
def encode(n, alphabet = ALPHABET):
    
    try:
        return alphabet[n]
    except IndexError:
        raise Exception("cannot encode: %s" % n)

def dec_to_base(dec = 0, base = 16, alphabet = ALPHABET):
    
    if dec < base:
        return encode(dec, alphabet)
    else:
        return dec_to_base(dec // base, base, alphabet) + encode(dec % base, alphabet)