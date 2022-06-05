# Copyright (c) 2019, Ahmed M. Alaa
# Licensed under the BSD 3-clause license (see LICENSE.txt)

from __future__ import absolute_import, division, print_function

import sys, os, time
import numpy as np
import pandas as pd
import scipy as sc
import itertools

from mpmath import *
from sympy import *

from scipy.optimize import minimize

import warnings
warnings.filterwarnings("ignore")
if not sys.warnoptions:
    warnings.simplefilter("ignore")

from pysymbolic_adjusted.models.special_functions import MeijerG
from pysymbolic_adjusted.utilities.performance import compute_Rsquared

#from sympy.printing.theanocode import theano_function
import sympy as sym
from sympy.utilities.autowrap import ufuncify

from gplearn.genetic import SymbolicRegressor

import types


def load_hyperparameter_config():

    hyperparameter_space = {
                        'hyper_1': (np.array([1.0,1.0]), [1,0,0,1]),
                        'hyper_2': (np.array([0.0,0.0,1.0,0.0,1.0]), [1,2,2,2]),
                        'hyper_3': (np.array([2.0,2.0,2.0,1.0,1.0]), [0,1,3,1]),
                        'hyper_4': (np.array([0.0,0.0,20.0]), [1,0,0,2])
                        }

    return hyperparameter_space                    


def Optimize(Loss, theta_0):
    opt       = minimize(Loss, theta_0, method='CG', options={'xtol': 1e-8, 'disp': True})
    Loss_     = opt.fun
    theta_opt = opt.x
    
    return theta_opt, Loss_ 


def symbolic_modeling(f, G_order, theta_0, npoints=None, xrange=None, n_vars=1, data=None):
        
    if data is not None:
        X = data
    elif n_vars == 1:
        X  = np.linspace(xrange[0], xrange[1], npoints).reshape((-1,1))
    else:
        X  = np.random.uniform(low=xrange[0], high=xrange[1], size=(npoints, n_vars))
        
        
    def Loss(theta):
        print('theta', theta)
        print('G_order', G_order)
        G     = MeijerG(theta=theta, order=G_order)
        if type(f) is types.FunctionType:
            loss_ = np.mean((f(X) - G.evaluate(X))**2)
        else:
            print('f', f)
            print('f.predict(X)', f.predict(X))
            print('G.evaluate(X)', G.evaluate(X))
            loss_ = np.mean((f.predict(X) - G.evaluate(X))**2)
        print("Expression:", G.expression())
        print("Loss:", loss_)
        
        return loss_
    
    theta_opt, Loss_ = Optimize(Loss, theta_0)
    symbolic_model   = MeijerG(theta=theta_opt, order=G_order)

    return symbolic_model, Loss_ 

def get_symbolic_model(f, npoints=None, xrange=None, n_vars=1, data=None):

    hyperparameter_space = load_hyperparameter_config() 
    loss_threshold       = 10e-5

    symbol_exprs         = []
    losses_              = [] 

    for k in range(len(hyperparameter_space)):

        symbolic_model, Loss_ = symbolic_modeling(f, 
                                                  [2, 2, 2, 1, 1],#hyperparameter_space['hyper_'+str(k+1)][1], 
                                                  [0, 1, 3, 1],#hyperparameter_space['hyper_'+str(k+1)][0], 
                                                  npoints, 
                                                  xrange, 
                                                  n_vars, 
                                                  data)

        symbol_exprs.append(symbolic_model)
        losses_.append(Loss_)

        if losses_[-1] <= loss_threshold:
            break 

    best_model = np.argmin(np.array(losses_))

    if data is not None:
        X = data
    elif n_vars == 1:
        X  = np.linspace(xrange[0], xrange[1], npoints).reshape((-1,1))
    else:
        X  = np.random.uniform(low=xrange[0], high=xrange[1], size=(npoints, n_vars))    
    
    if type(f) is types.FunctionType:
        Y_true     = f(X).reshape((-1,1))
    else:
        Y_true     = f.predict(X).reshape((-1,1))
    Y_est      = symbol_exprs[best_model].evaluate(X).reshape((-1,1))

    R2_perf    = compute_Rsquared(Y_true, Y_est)
    
    return symbol_exprs[best_model], R2_perf    


def symbolic_regressor(f, npoints=None, xrange=None, n_vars=1, data=None):

    if data is not None:
        X = data
    elif n_vars == 1:
        X  = np.linspace(xrange[0], xrange[1], npoints).reshape((-1,1))
    else:
        X  = np.random.uniform(low=xrange[0], high=xrange[1], size=(npoints, n_vars))

    #print(f)
    #print('X[0]', X[0])
    #print('X.shape', X.shape)
    
    
    if type(f) is types.FunctionType:
        y  = f(X)
    else:
        #print(f.summary())
        y  = f.predict(X)

    est_gp = SymbolicRegressor(population_size=5000,
                               generations=20, stopping_criteria=0.01,
                               p_crossover=0.7, p_subtree_mutation=0.1,
                               p_hoist_mutation=0.05, p_point_mutation=0.1,
                               max_samples=0.9, verbose=1,
                               parsimony_coefficient=0.01, random_state=0)

    est_gp.fit(X, y)

    sym_expr = str(est_gp._program)

    converter = {
        'sub': lambda x, y : x - y,
        'div': lambda x, y : x/y,
        'mul': lambda x, y : x*y,
        'add': lambda x, y : x + y,
        'neg': lambda x    : -x,
        'pow': lambda x, y : x**y
    }

    #x, X0   = symbols('x X0')
    sym_reg = simplify(sympify(sym_expr, locals=converter))
    #print('str(sym_reg)', str(sym_reg))
    #sym_reg = sym_reg.subs(X0,x)

    Y_true  = y.reshape((-1,1))
    #print('SUBS str(sym_reg)', str(sym_reg))
    
    
    function_vars = [sym.symbols('X' + str(i)) for i in range(n_vars)]
    #lambda_function = lambdify([function_vars], sym_reg, modules=["scipy", "numpy"])
    #if len(function_vars) >= 1:
    #    Y_est = [lambda_function(data_point) for data_point in X]
    #else:
    #Y_est = [lambda_function() for i in range(X.shape[0])]    
    function_values = []
    for data_point in X:
        function_value = sym_reg.evalf(subs={var: data_point[index] for index, var in enumerate(list(function_vars))})
        try:
            function_value = float(function_value)
        except TypeError as te:
            function_value = np.inf
        function_values.append(function_value)
    Y_est = np.nan_to_num(function_values).ravel()
                
    #Y_est   = np.array([sympify(str(sym_reg)).subs(x,X[k]) for k in range(len(X))]).reshape((-1,1))
    
    print(sym_reg)
    
    R2_perf = compute_Rsquared(Y_true, Y_est)

    return sym_reg, R2_perf

