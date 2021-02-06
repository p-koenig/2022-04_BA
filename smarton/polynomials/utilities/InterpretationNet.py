#######################################################################################################################################################
#######################################################################Imports#########################################################################
#######################################################################################################################################################

#from itertools import product       # forms cartesian products
#from tqdm import tqdm_notebook as tqdm
#import pickle
import numpy as np
import pandas as pd
import scipy as sp

from functools import reduce
from more_itertools import random_product 

#import math

from joblib import Parallel, delayed
from collections.abc import Iterable
#from scipy.integrate import quad

from sklearn.model_selection import train_test_split
#from sklearn.metrics import accuracy_score, log_loss, roc_auc_score, f1_score, mean_absolute_error, r2_score
from similaritymeasures import frechet_dist, area_between_two_curves, dtw


import tensorflow as tf

import autokeras as ak

import random 

from keras.models import Sequential
from keras.layers.core import Dense, Dropout

from matplotlib import pyplot as plt
import seaborn as sns


#udf import
from utilities.LambdaNet import *
from utilities.metrics import *
from utilities.utility_functions import *

from tqdm import tqdm_notebook as tqdm

#######################################################################################################################################################
#############################################################Setting relevant parameters from current config###########################################
#######################################################################################################################################################

def initialize_InterpretationNet_config_from_curent_notebook(config):
    globals().update(config['data'])
    globals().update(config['lambda_net'])
    globals().update(config['i_net'])
    globals().update(config['evaluation'])
    globals().update(config['computation'])
    
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    if int(tf.__version__[0]) >= 2:
        tf.random.set_seed(RANDOM_SEED)
    else:
        tf.set_random_seed(RANDOM_SEED)
        
    global list_of_monomial_identifiers
        
    list_of_monomial_identifiers_extended = []
    for i in range((d+1)**n):    
        monomial_identifier = dec_to_base(i, base = (d+1)).zfill(n) 
        list_of_monomial_identifiers_extended.append(monomial_identifier)


    list_of_monomial_identifiers = []
    for monomial_identifier in list_of_monomial_identifiers_extended:
        monomial_identifier_values = list(map(int, list(monomial_identifier)))
        if sum(monomial_identifier_values) <= d:
            list_of_monomial_identifiers.append(monomial_identifier)
    

#######################################################################################################################################################
#################################################################I-NET RESULT CALCULATION##############################################################
#######################################################################################################################################################


def calculate_interpretation_net_results(lambda_net_train_dataset_list, 
                                         lambda_net_valid_dataset_list, 
                                         lambda_net_test_dataset_list):
    
    return_model = False
    if n_jobs==1 or (samples_list != None and len(samples_list) == 1) or (len(lambda_net_train_dataset_list) == 1 and samples_list == None):
        return_model = True
        
    if samples_list == None: 
        results_list = Parallel(n_jobs=n_jobs, 
                                verbose=11, 
                                backend='multiprocessing')(delayed(train_nn_and_pred)(lambda_net_train_dataset,
                                                                                       lambda_net_valid_dataset,
                                                                                       lambda_net_test_dataset,
                                                                                       callback_names=['early_stopping'],
                                                                                       return_model=return_model) for lambda_net_train_dataset,
                                                                                                                      lambda_net_valid_dataset,
                                                                                                                      lambda_net_test_dataset  in zip(lambda_net_train_dataset_list,
                                                                                                                                                      lambda_net_valid_dataset_list,
                                                                                                                                                      lambda_net_test_dataset_list))      

        history_list = [result[0] for result in results_list]

        scores_list = [result[1] for result in results_list]

        function_values_complete_list = [result[2] for result in results_list]
        function_values_valid_list = [function_values[0] for function_values in function_values_complete_list]
        function_values_test_list = [function_values[1] for function_values in function_values_complete_list]

        inet_preds_list = [result[3] for result in results_list]
        inet_preds_valid_list = [inet_preds[0] for inet_preds in inet_preds_list]
        inet_preds_test_list = [inet_preds[1] for inet_preds in inet_preds_list]

        distrib_dict_list = [result[4] for result in results_list]

        if not nas:
            generate_history_plots(history_list, by='epochs')
            save_results(history_list, scores_list, by='epochs')    
        
        model_list = []
        if return_model:
            model_list = [result[5] for result in results_list]

    else:
        results_list = Parallel(n_jobs=n_jobs, verbose=11, backend='multiprocessing')(delayed(train_nn_and_pred)(lambda_net_train_dataset.sample(samples),
                                                                                                      lambda_net_valid_dataset,
                                                                                                      lambda_net_test_dataset, 
                                                                                                      callback_names=['early_stopping'],
                                                                                                      return_model=return_model) for samples in samples_list)     

        history_list = [result[0] for result in results_list]

        scores_list = [result[1] for result in results_list]

        function_values_complete_list = [result[2] for result in results_list]
        function_values_valid_list = [function_values[0] for function_values in function_values_complete_list]
        function_values_test_list = [function_values[1] for function_values in function_values_complete_list]

        inet_preds_list = [result[3] for result in results_list]
        inet_preds_valid_list = [inet_preds[0] for inet_preds in inet_preds_list]
        inet_preds_test_list = [inet_preds[1] for inet_preds in inet_preds_list]


        distrib_dict_list = [result[4] for result in results_list]

        if not nas:
            generate_history_plots(history_list, by='samples')
            save_results(history_list, scores_list, by='samples')
    
        model_list = []
        if return_model:
            model_list = [result[5] for result in results_list]
            
    return (history_list, 
            scores_list, 
            
            function_values_complete_list, 
            function_values_valid_list, 
            function_values_test_list, 
            
            inet_preds_list, 
            inet_preds_valid_list, 
            inet_preds_test_list, 
            
            distrib_dict_list,
            model_list)
        
    
    
#######################################################################################################################################################
######################################################################I-NET TRAINING###################################################################
#######################################################################################################################################################


def train_nn_and_pred(lambda_net_train_dataset,
                      lambda_net_valid_dataset,
                      lambda_net_test_dataset, 
                      callback_names = [],
                      return_model = False):       
   
    global optimizer
    
    globals().update(generate_paths())
    
    ############################## DATA PREPARATION ###############################

    if seed_in_inet_training:
        normalizer = Normalizer().fit([np.array(lambda_net_train_dataset.train_settings_list['seed'])])
        train_seed_list = normalizer.transform([np.array(lambda_net_train_dataset.train_settings_list['seed'])])[0]
        valid_seed_list = normalizer.transform([np.array(lambda_net_valid_dataset.train_settings_list['seed'])])[0]
        test_seed_list = normalizer.transform([np.array(lambda_net_test_dataset.train_settings_list['seed'])])[0]

        X_train = np.hstack([np.expand_dims(train_seed_list, axis=1), np.array(lambda_net_train_dataset.weight_list)])
        X_valid = np.hstack([np.expand_dims(valid_seed_list, axis=1), np.array(lambda_net_valid_dataset.weight_list)])
        X_test = np.hstack([np.expand_dims(test_seed_list, axis=1), np.array(lambda_net_test_dataset.weight_list)])
    else:   #normalize if included in training   
        X_train = np.array(lambda_net_train_dataset.weight_list)
        X_valid = np.array(lambda_net_valid_dataset.weight_list)
        X_test = np.array(lambda_net_test_dataset.weight_list) 
        
    if evaluate_with_real_function: #target polynomial as inet target
        y_train = np.array(lambda_net_train_dataset.target_polynomial_list)
        y_valid = np.array(lambda_net_valid_dataset.target_polynomial_list)
        y_test = np.array(lambda_net_test_dataset.target_polynomial_list)
    else: #lstsq lambda pred polynomial as inet target
        y_train = np.array(lambda_net_train_dataset.lstsq_lambda_pred_polynomial_list)
        y_valid = np.array(lambda_net_valid_dataset.lstsq_lambda_pred_polynomial_list)
        y_test = np.array(lambda_net_test_dataset.lstsq_lambda_pred_polynomial_list)
        
        
        if convolution_layers != None or lstm_layers != None or (nas and nas_type != 'SEQUENTIAL'):
            X_train, X_train_flat = restructure_data_cnn_lstm(X_train, version=data_reshape_version, subsequences=None)
            X_valid, X_valid_flat = restructure_data_cnn_lstm(X_valid, version=data_reshape_version, subsequences=None)
            X_test, X_test_flat = restructure_data_cnn_lstm(X_test, version=data_reshape_version, subsequences=None)

        
    ############################## OBJECTIVE SPECIFICATION AND LOSS FUNCTION ADJUSTMENTS ###############################
        
    if consider_labels_training: #coefficient-based evaluation
        if evaluate_with_real_function: #based on in-metric fv calculation of real and predicted polynomial
            random_evaluation_dataset = np.random.uniform(low=x_min, high=x_max, size=(random_evaluation_dataset_size, n))
            list_of_monomial_identifiers_numbers = np.array([list(monomial_identifiers) for monomial_identifiers in list_of_monomial_identifiers]).astype(float)
            
            if nas:
                loss_function = 'mean_absolute_error'
                metrics = [r2_tf_fv, mean_absolute_error_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, preds_include_params=True), r2_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, preds_include_params=True)]            
            else:
                loss_function = 'mean_absolute_error'
                metrics = [r2_tf_fv, mean_absolute_error_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers), r2_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers)]
            
            valid_data = (X_valid, y_valid)
            y_train_model = y_train
        else: #in-metric prediction of lambda-nets
            base_model = generate_base_model()
            random_evaluation_dataset = np.random.uniform(low=x_min, high=x_max, size=(random_evaluation_dataset_size, n))
            list_of_monomial_identifiers_numbers = np.array([list(monomial_identifiers) for monomial_identifiers in list_of_monomial_identifiers]).astype(float)
            
            if nas:
                loss_function = mean_absolute_error_extended       
                metrics = [r2_extended, mean_absolute_error_tf_fv_lambda_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, base_model, preds_include_params=True), r2_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, preds_include_params=True)]             
            else:
                loss_function = mean_absolute_error_extended       
                metrics = [r2_extended, mean_absolute_error_tf_fv_lambda_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, base_model), r2_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers)]    
            
            if data_reshape_version != None:
                y_train_model = np.hstack((y_train, X_train_flat))   
                valid_data = (X_valid, np.hstack((y_valid, X_valid_flat)))   
            else:
                y_train_model = np.hstack((y_train, X_train))   
                valid_data = (X_valid, np.hstack((y_valid, X_valid)))     
    else: #fv-based evaluation
        if evaluate_with_real_function: #based on in-loss fv calculation of real and predicted polynomial
            random_evaluation_dataset = np.random.uniform(low=x_min, high=x_max, size=(random_evaluation_dataset_size, n))
            list_of_monomial_identifiers_numbers = np.array([list(monomial_identifiers) for monomial_identifiers in list_of_monomial_identifiers]).astype(float)
            
            if nas:
                loss_function = mean_absolute_error_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, preds_include_params=True)
                metrics = [r2_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, preds_include_params=True), 'mean_absolute_error']            
            else:  
                loss_function = mean_absolute_error_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers)
                metrics = [r2_tf_fv_poly_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers), 'mean_absolute_error']                 
            
            valid_data = (X_valid, y_valid)
            y_train_model = y_train
        else: #in-loss prediction of lambda-nets
            base_model = generate_base_model()
            random_evaluation_dataset = np.random.uniform(low=x_min, high=x_max, size=(random_evaluation_dataset_size, n))
            list_of_monomial_identifiers_numbers = np.array([list(monomial_identifiers) for monomial_identifiers in list_of_monomial_identifiers]).astype(float)
            
            if nas:
                loss_function = mean_absolute_error_tf_fv_lambda_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, base_model, preds_include_params=True)      
                metrics = [r2_tf_fv_lambda_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, base_model, preds_include_params=True), mean_absolute_error_extended]
            else:
                loss_function = mean_absolute_error_tf_fv_lambda_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, base_model)      
                metrics = [r2_tf_fv_lambda_extended_wrapper(random_evaluation_dataset, list_of_monomial_identifiers_numbers, base_model), mean_absolute_error_extended]
            
            if data_reshape_version != None:
                y_train_model = np.hstack((y_train, X_train_flat))   
                valid_data = (X_valid, np.hstack((y_valid, X_valid_flat)))   
            else:
                y_train_model = np.hstack((y_train, X_train))   
                valid_data = (X_valid, np.hstack((y_valid, X_valid)))               
        
    ############################## BUILD MODEL ###############################
    
    if nas:
        from tensorflow.keras.utils import CustomObjectScope
        with CustomObjectScope({'custom_loss': loss_function}):                
            if nas_type == 'SEQUENTIAL':
                directory = './data/autokeras/automodel/' + nas_type + '_' + str(n) + 'n' + str(d) + '_d' + filename

                auto_model = ak.StructuredDataRegressor(
                    loss='custom_loss',
                    #output_dim=sparsity,
                    overwrite=True,
                    max_trials=nas_trials,
                    directory=directory,
                    seed=RANDOM_SEED)
            else:
                if nas_type == 'CNN': 
                    input_node = ak.Input()
                    output_node = ak.ConvBlock()(input_node)
                    output_node = ak.DenseBlock()(output_node)
                    output_node = ak.RegressionHead()(output_node)
                if nas_type == 'LSTM':
                    input_node = ak.Input()
                    output_node = ak.RNNBlock()(input_node)
                    output_node = ak.DenseBlock()(output_node)
                    output_node = ak.RegressionHead()(output_node)
                elif nas_type == 'CNN-LSTM': 
                    input_node = ak.Input()
                    output_node = ak.ConvBlock()(input_node)
                    output_node = ak.RNNBlock()(output_node)
                    output_node = ak.DenseBlock()(output_node)
                    output_node = ak.RegressionHead()(output_node)  
                elif nas_type == 'CNN-LSTM-parallel':                         
                    input_node = ak.Input()
                    output_node1 = ak.ConvBlock()(input_node)
                    output_node2 = ak.RNNBlock()(input_node)
                    output_node = ak.Merge()([output_node1, output_node2])
                    output_node = ak.DenseBlock()(output_node)
                    output_node = ak.RegressionHead()(output_node)  

                directory = './data/autokeras/automodel/' + nas_type + '_' + str(n) + 'n' + str(d) + '_d' + filename

                auto_model = ak.AutoModel(inputs=input_node, 
                                    outputs=output_node,
                                    loss='custom_loss',
                                    overwrite=True,
                                    max_trials=nas_trials,
                                    directory=directory,
                                    seed=RANDOM_SEED)

            ############################## PREDICTION ###############################
            auto_model.fit(
                x=X_train,
                y=y_train_model,
                validation_data=valid_data,
                epochs=epochs
                )


            history = auto_model.tuner.oracle.get_best_trials(min(nas_trials, 5))
            model = auto_model.export_model()

            y_valid_pred = model.predict(X_valid)[:,:sparsity]
            y_test_pred = model.predict(X_test)[:,:sparsity]

        
    else: 
        model = Sequential()

        model.add(Dense(dense_layers[0], activation='relu', input_dim=X_train.shape[1])) #1024

        #if dropout > 0:
            #model.add(Dropout(dropout))

        for neurons in dense_layers[1:]:
            model.add(Dense(neurons, activation='relu'))
            #if dropout > 0:
                #model.add(Dropout(dropout))

        if dropout > 0:
            model.add(Dropout(dropout))
        model.add(Dense(nCr(n+d, d))) 

        callbacks = return_callbacks_from_string(callback_names)            

        if optimizer == "custom":
            optimizer = keras.optimizers.Adam(learning_rate=0.0001)

        model.compile(optimizer=optimizer,
                      loss=loss_function,
                      metrics=metrics
                     )

        verbosity = 1 if n_jobs ==1 else 0

        ############################## PREDICTION ###############################

        history = model.fit(X_train,
                  y_train_model,
                  epochs=epochs, 
                  batch_size=batch_size, 
                  validation_data=valid_data,
                  callbacks=callbacks,
                  verbose=verbosity)
    
        history = history.history
    
        y_valid_pred = model.predict(X_valid)
        y_test_pred = model.predict(X_test)
    
    pred_list = [y_valid_pred, y_test_pred]
              
        
    ############################## FUNCTION VALUE CALCULATION ###############################
    
    lambda_test_data_preds_valid = lambda_net_valid_dataset.make_prediction_on_test_data()
    lambda_test_data_preds_test = lambda_net_test_dataset.make_prediction_on_test_data() 
              
    target_poly_test_data_fvs_valid = lambda_net_valid_dataset.return_target_poly_fvs_on_test_data()
    target_poly_test_data_fvs_test = lambda_net_test_dataset.return_target_poly_fvs_on_test_data() 
                
    lstsq_lambda_pred_polynomial_test_data_fvs_valid = lambda_net_valid_dataset.return_lstsq_lambda_pred_polynomial_fvs_on_test_data()
    lstsq_lambda_pred_polynomial_test_data_fvs_test = lambda_net_test_dataset.return_lstsq_lambda_pred_polynomial_fvs_on_test_data() 
             
    lstsq_target_polynomial_test_data_fvs_valid = lambda_net_valid_dataset.return_lstsq_target_polynomial_fvs_on_test_data()
    lstsq_target_polynomial_test_data_fvs_test = lambda_net_test_dataset.return_lstsq_target_polynomial_fvs_on_test_data() 
        
    inet_poly_test_data_fvs_valid = parallel_fv_calculation_from_polynomial(y_valid_pred, lambda_net_valid_dataset.test_data_list)
    inet_poly_test_data_fvs_test = parallel_fv_calculation_from_polynomial(y_test_pred, lambda_net_test_dataset.test_data_list) 
    
    
    function_values_valid = [lambda_test_data_preds_valid, 
                            target_poly_test_data_fvs_valid, 
                            lstsq_lambda_pred_polynomial_test_data_fvs_valid, 
                            lstsq_target_polynomial_test_data_fvs_valid,
                            inet_poly_test_data_fvs_valid]
    
    function_values_test = [lambda_test_data_preds_test, 
                            target_poly_test_data_fvs_test, 
                            lstsq_lambda_pred_polynomial_test_data_fvs_test, 
                            lstsq_target_polynomial_test_data_fvs_test,
                            inet_poly_test_data_fvs_test]
    
    function_values = [function_values_valid, function_values_test]    
    
    
    ############################## EVALUATION ###############################
    
    #evaluate inet poly against target polynomial on fv-basis
    scores_inetPoly_VS_targetPoly_test_data_fv_valid, distrib_inetPoly_VS_targetPoly_test_data_fv_valid = evaluate_interpretation_net(y_valid_pred,
                                                                                   lambda_net_valid_dataset.target_polynomial_list, 
                                                                                   inet_poly_test_data_fvs_valid, 
                                                                                   target_poly_test_data_fvs_valid)  
    scores_inetPoly_VS_targetPoly_test_data_fv_test, distrib_inetPoly_VS_targetPoly_test_data_fv_test = evaluate_interpretation_net(y_test_pred, 
                                                                                  lambda_net_test_dataset.target_polynomial_list, 
                                                                                  inet_poly_test_data_fvs_test, 
                                                                                  target_poly_test_data_fvs_test)

    #evaluate inet poly against lambda-net preds on fv-basis
    scores_inetPoly_VS_predLambda_test_data_fv_valid, distrib_inetPoly_VS_predLambda_test_data_fv_valid = evaluate_interpretation_net(y_valid_pred, 
                                                                                   None, 
                                                                                   inet_poly_test_data_fvs_valid, 
                                                                                   lambda_test_data_preds_valid)
    scores_inetPoly_VS_predLambda_test_data_fv_test, distrib_inetPoly_VS_predLambda_test_data_fv_test = evaluate_interpretation_net(y_test_pred, 
                                                                                  None, 
                                                                                  inet_poly_test_data_fvs_test, 
                                                                                  lambda_test_data_preds_test)       
        
    #evaluate inet poly against lstsq target poly on fv-basis
    scores_inetPoly_VS_lstsqTarget_test_data_fv_valid, distrib_inetPoly_VS_lstsqTarget_test_data_fv_valid = evaluate_interpretation_net(y_valid_pred, 
                                                                                    lambda_net_valid_dataset.lstsq_target_polynomial_list, 
                                                                                    inet_poly_test_data_fvs_valid, 
                                                                                    lstsq_target_polynomial_test_data_fvs_valid)
    scores_inetPoly_VS_lstsqTarget_test_data_fv_test, distrib_inetPoly_VS_lstsqTarget_test_data_fv_test = evaluate_interpretation_net(y_test_pred, 
                                                                                   lambda_net_test_dataset.lstsq_target_polynomial_list, 
                                                                                   inet_poly_test_data_fvs_test, 
                                                                                   lstsq_target_polynomial_test_data_fvs_test)  

    #evaluate inet poly against lstsq lambda poly on fv-basis
    scores_inetPoly_VS_lstsqLambda_test_data_fv_valid, distrib_inetPoly_VS_lstsqLambda_test_data_fv_valid = evaluate_interpretation_net(y_valid_pred, 
                                                                                    lambda_net_valid_dataset.lstsq_lambda_pred_polynomial_list, 
                                                                                    inet_poly_test_data_fvs_valid, 
                                                                                    lstsq_lambda_pred_polynomial_test_data_fvs_valid)
    scores_inetPoly_VS_lstsqLambda_test_data_fv_test, distrib_inetPoly_VS_lstsqLambda_test_data_fv_test = evaluate_interpretation_net(y_test_pred, 
                                                                                   lambda_net_test_dataset.lstsq_lambda_pred_polynomial_list, 
                                                                                   inet_poly_test_data_fvs_test, 
                                                                                   lstsq_lambda_pred_polynomial_test_data_fvs_test)     
      
    #evaluate lstsq lambda pred poly against lambda-net preds on fv-basis
    scores_lstsqLambda_VS_predLambda_test_data_fv_valid, distrib_lstsqLambda_VS_predLambda_test_data_fv_valid = evaluate_interpretation_net(lambda_net_valid_dataset.lstsq_lambda_pred_polynomial_list, 
                                                                                      None, 
                                                                                      lstsq_lambda_pred_polynomial_test_data_fvs_valid, 
                                                                                      lambda_test_data_preds_valid)
    scores_lstsqLambda_VS_predLambda_test_data_fv_test, distrib_lstsqLambda_VS_predLambda_test_data_fv_test = evaluate_interpretation_net(lambda_net_test_dataset.lstsq_lambda_pred_polynomial_list, 
                                                                                     None, 
                                                                                     lstsq_lambda_pred_polynomial_test_data_fvs_test, 
                                                                                     lambda_test_data_preds_test)
    
    #evaluate lstsq lambda pred poly against lstsq target poly on fv-basis
    scores_lstsqLambda_VS_lstsqTarget_test_data_fv_valid, distrib_lstsqLambda_VS_lstsqTarget_test_data_fv_valid = evaluate_interpretation_net(lambda_net_valid_dataset.lstsq_lambda_pred_polynomial_list, 
                                                                                       lambda_net_valid_dataset.lstsq_target_polynomial_list, 
                                                                                       lstsq_lambda_pred_polynomial_test_data_fvs_valid, 
                                                                                       lstsq_target_polynomial_test_data_fvs_valid)
    scores_lstsqLambda_VS_lstsqTarget_test_data_fv_test, distrib_lstsqLambda_VS_lstsqTarget_test_data_fv_test = evaluate_interpretation_net(lambda_net_test_dataset.lstsq_lambda_pred_polynomial_list, 
                                                                                      lambda_net_test_dataset.lstsq_target_polynomial_list, 
                                                                                      lstsq_lambda_pred_polynomial_test_data_fvs_test, 
                                                                                      lstsq_target_polynomial_test_data_fvs_test)    
    
    #evaluate lstsq lambda pred poly against target poly on fv-basis
    scores_lstsqLambda_VS_targetPoly_test_data_fv_valid, distrib_lstsqLambda_VS_targetPoly_test_data_fv_valid = evaluate_interpretation_net(lambda_net_valid_dataset.lstsq_lambda_pred_polynomial_list, 
                                                                                      lambda_net_valid_dataset.target_polynomial_list, 
                                                                                      lstsq_lambda_pred_polynomial_test_data_fvs_valid, 
                                                                                      target_poly_test_data_fvs_valid)
    scores_lstsqLambda_VS_targetPoly_test_data_fv_test, distrib_lstsqLambda_VS_targetPoly_test_data_fv_test = evaluate_interpretation_net(lambda_net_test_dataset.lstsq_lambda_pred_polynomial_list, 
                                                                                     lambda_net_test_dataset.target_polynomial_list, 
                                                                                     lstsq_lambda_pred_polynomial_test_data_fvs_test, 
                                                                                     target_poly_test_data_fvs_test)    
    
    #evaluate lambda-net preds against lstsq target poly on fv-basis
    scores_predLambda_VS_lstsqTarget_test_data_fv_valid, distrib_predLambda_VS_lstsqTarget_test_data_fv_valid = evaluate_interpretation_net(None, 
                                                                                      lambda_net_valid_dataset.lstsq_target_polynomial_list, 
                                                                                      lambda_test_data_preds_valid, 
                                                                                      lstsq_target_polynomial_test_data_fvs_valid)
    scores_predLambda_VS_lstsqTarget_test_data_fv_test, distrib_predLambda_VS_lstsqTarget_test_data_fv_test = evaluate_interpretation_net(None, 
                                                                                     lambda_net_test_dataset.lstsq_target_polynomial_list, 
                                                                                     lambda_test_data_preds_test, 
                                                                                     lstsq_target_polynomial_test_data_fvs_test)
        
    #evaluate lambda-net preds against target poly on fv-basis
    scores_predLambda_VS_targetPoly_test_data_fv_valid, distrib_predLambda_VS_targetPoly_test_data_fv_valid = evaluate_interpretation_net(None, 
                                                                                     lambda_net_valid_dataset.target_polynomial_list, 
                                                                                     lambda_test_data_preds_valid, 
                                                                                     target_poly_test_data_fvs_valid)
    scores_predLambda_VS_targetPoly_test_data_fv_test, distrib_predLambda_VS_targetPoly_test_data_fv_test = evaluate_interpretation_net(None, 
                                                                                    lambda_net_test_dataset.target_polynomial_list, 
                                                                                    lambda_test_data_preds_test, 
                                                                                    target_poly_test_data_fvs_test)
      
    #evaluate lstsq target poly against target poly on fv-basis
    scores_lstsqTarget_VS_targetPoly_test_data_fv_valid, distrib_lstsqTarget_VS_targetPoly_test_data_fv_valid = evaluate_interpretation_net(lambda_net_valid_dataset.lstsq_target_polynomial_list, 
                                                                                      lambda_net_valid_dataset.target_polynomial_list, 
                                                                                      lstsq_target_polynomial_test_data_fvs_valid, 
                                                                                      target_poly_test_data_fvs_valid)
    scores_lstsqTarget_VS_targetPoly_test_data_fv_test, distrib_lstsqTarget_VS_targetPoly_test_data_fv_test = evaluate_interpretation_net(lambda_net_test_dataset.lstsq_target_polynomial_list, 
                                                                                     lambda_net_test_dataset.target_polynomial_list, 
                                                                                     lstsq_target_polynomial_test_data_fvs_test, 
                                                                                     target_poly_test_data_fvs_test)
        
    scores_dict = pd.DataFrame(data=[scores_inetPoly_VS_targetPoly_test_data_fv_valid, 
                                     scores_inetPoly_VS_targetPoly_test_data_fv_test, 
                                     scores_inetPoly_VS_predLambda_test_data_fv_valid,
                                     scores_inetPoly_VS_predLambda_test_data_fv_test,
                                     scores_inetPoly_VS_lstsqTarget_test_data_fv_valid,
                                     scores_inetPoly_VS_lstsqTarget_test_data_fv_test,
                                     scores_inetPoly_VS_lstsqLambda_test_data_fv_valid,
                                     scores_inetPoly_VS_lstsqLambda_test_data_fv_test,
                                     scores_lstsqLambda_VS_predLambda_test_data_fv_valid,
                                     scores_lstsqLambda_VS_predLambda_test_data_fv_test,
                                     scores_lstsqLambda_VS_lstsqTarget_test_data_fv_valid,
                                     scores_lstsqLambda_VS_lstsqTarget_test_data_fv_test,
                                     scores_lstsqLambda_VS_targetPoly_test_data_fv_valid,
                                     scores_lstsqLambda_VS_targetPoly_test_data_fv_test,
                                     scores_predLambda_VS_lstsqTarget_test_data_fv_valid,
                                     scores_predLambda_VS_lstsqTarget_test_data_fv_test,
                                     scores_predLambda_VS_targetPoly_test_data_fv_valid,
                                     scores_predLambda_VS_targetPoly_test_data_fv_test,
                                     scores_lstsqTarget_VS_targetPoly_test_data_fv_valid,
                                     scores_lstsqTarget_VS_targetPoly_test_data_fv_test],
                               index=['inetPoly_VS_targetPoly_valid', 
                                      'inetPoly_VS_targetPoly_test', 
                                      'inetPoly_VS_predLambda_valid',
                                      'inetPoly_VS_predLambda_test',
                                      'inetPoly_VS_lstsqTarget_valid',
                                      'inetPoly_VS_lstsqTarget_test',
                                      'inetPoly_VS_lstsqLambda_valid',
                                      'inetPoly_VS_lstsqLambda_test',
                                      'lstsqLambda_VS_predLambda_valid',
                                      'lstsqLambda_VS_predLambda_test',
                                      'lstsqLambda_VS_lstsqTarget_valid',
                                      'lstsqLambda_VS_lstsqTarget_test',
                                      'lstsqLambda_VS_targetPoly_valid',
                                      'lstsqLambda_VS_targetPoly_test',
                                      'predLambda_VS_lstsqTarget_valid',
                                      'predLambda_VS_lstsqTarget_test',
                                      'predLambda_VS_targetPoly_valid',
                                      'predLambda_VS_targetPoly_test',
                                      'lstsqTarget_VS_targetPoly_valid',
                                      'lstsqTarget_VS_targetPoly_test'])
    
    mae_distrib_dict = pd.DataFrame(data=[distrib_inetPoly_VS_targetPoly_test_data_fv_valid['MAE'], 
                                     distrib_inetPoly_VS_targetPoly_test_data_fv_test['MAE'], 
                                     distrib_inetPoly_VS_predLambda_test_data_fv_valid['MAE'],
                                     distrib_inetPoly_VS_predLambda_test_data_fv_test['MAE'],
                                     distrib_inetPoly_VS_lstsqTarget_test_data_fv_valid['MAE'],
                                     distrib_inetPoly_VS_lstsqTarget_test_data_fv_test['MAE'],
                                     distrib_inetPoly_VS_lstsqLambda_test_data_fv_valid['MAE'],
                                     distrib_inetPoly_VS_lstsqLambda_test_data_fv_test['MAE'],
                                     distrib_lstsqLambda_VS_predLambda_test_data_fv_valid['MAE'],
                                     distrib_lstsqLambda_VS_predLambda_test_data_fv_test['MAE'],
                                     distrib_lstsqLambda_VS_lstsqTarget_test_data_fv_valid['MAE'],
                                     distrib_lstsqLambda_VS_lstsqTarget_test_data_fv_test['MAE'],
                                     distrib_lstsqLambda_VS_targetPoly_test_data_fv_valid['MAE'],
                                     distrib_lstsqLambda_VS_targetPoly_test_data_fv_test['MAE'],
                                     distrib_predLambda_VS_lstsqTarget_test_data_fv_valid['MAE'],
                                     distrib_predLambda_VS_lstsqTarget_test_data_fv_test['MAE'],
                                     distrib_predLambda_VS_targetPoly_test_data_fv_valid['MAE'],
                                     distrib_predLambda_VS_targetPoly_test_data_fv_test['MAE'],
                                     distrib_lstsqTarget_VS_targetPoly_test_data_fv_valid['MAE'],
                                     distrib_lstsqTarget_VS_targetPoly_test_data_fv_test['MAE']],
                               index=['inetPoly_VS_targetPoly_valid', 
                                      'inetPoly_VS_targetPoly_test', 
                                      'inetPoly_VS_predLambda_valid',
                                      'inetPoly_VS_predLambda_test',
                                      'inetPoly_VS_lstsqTarget_valid',
                                      'inetPoly_VS_lstsqTarget_test',
                                      'inetPoly_VS_lstsqLambda_valid',
                                      'inetPoly_VS_lstsqLambda_test',
                                      'lstsqLambda_VS_predLambda_valid',
                                      'lstsqLambda_VS_predLambda_test',
                                      'lstsqLambda_VS_lstsqTarget_valid',
                                      'lstsqLambda_VS_lstsqTarget_test',
                                      'lstsqLambda_VS_targetPoly_valid',
                                      'lstsqLambda_VS_targetPoly_test',
                                      'predLambda_VS_lstsqTarget_valid',
                                      'predLambda_VS_lstsqTarget_test',
                                      'predLambda_VS_targetPoly_valid',
                                      'predLambda_VS_targetPoly_test',
                                      'lstsqTarget_VS_targetPoly_valid',
                                      'lstsqTarget_VS_targetPoly_test'])
    
    r2_distrib_dict = pd.DataFrame(data=[distrib_inetPoly_VS_targetPoly_test_data_fv_valid['R2'], 
                                     distrib_inetPoly_VS_targetPoly_test_data_fv_test['R2'], 
                                     distrib_inetPoly_VS_predLambda_test_data_fv_valid['R2'],
                                     distrib_inetPoly_VS_predLambda_test_data_fv_test['R2'],
                                     distrib_inetPoly_VS_lstsqTarget_test_data_fv_valid['R2'],
                                     distrib_inetPoly_VS_lstsqTarget_test_data_fv_test['R2'],
                                     distrib_inetPoly_VS_lstsqLambda_test_data_fv_valid['R2'],
                                     distrib_inetPoly_VS_lstsqLambda_test_data_fv_test['R2'],
                                     distrib_lstsqLambda_VS_predLambda_test_data_fv_valid['R2'],
                                     distrib_lstsqLambda_VS_predLambda_test_data_fv_test['R2'],
                                     distrib_lstsqLambda_VS_lstsqTarget_test_data_fv_valid['R2'],
                                     distrib_lstsqLambda_VS_lstsqTarget_test_data_fv_test['R2'],
                                     distrib_lstsqLambda_VS_targetPoly_test_data_fv_valid['R2'],
                                     distrib_lstsqLambda_VS_targetPoly_test_data_fv_test['R2'],
                                     distrib_predLambda_VS_lstsqTarget_test_data_fv_valid['R2'],
                                     distrib_predLambda_VS_lstsqTarget_test_data_fv_test['R2'],
                                     distrib_predLambda_VS_targetPoly_test_data_fv_valid['R2'],
                                     distrib_predLambda_VS_targetPoly_test_data_fv_test['R2'],
                                     distrib_lstsqTarget_VS_targetPoly_test_data_fv_valid['R2'],
                                     distrib_lstsqTarget_VS_targetPoly_test_data_fv_test['R2']],
                               index=['inetPoly_VS_targetPoly_valid', 
                                      'inetPoly_VS_targetPoly_test', 
                                      'inetPoly_VS_predLambda_valid',
                                      'inetPoly_VS_predLambda_test',
                                      'inetPoly_VS_lstsqTarget_valid',
                                      'inetPoly_VS_lstsqTarget_test',
                                      'inetPoly_VS_lstsqLambda_valid',
                                      'inetPoly_VS_lstsqLambda_test',
                                      'lstsqLambda_VS_predLambda_valid',
                                      'lstsqLambda_VS_predLambda_test',
                                      'lstsqLambda_VS_lstsqTarget_valid',
                                      'lstsqLambda_VS_lstsqTarget_test',
                                      'lstsqLambda_VS_targetPoly_valid',
                                      'lstsqLambda_VS_targetPoly_test',
                                      'predLambda_VS_lstsqTarget_valid',
                                      'predLambda_VS_lstsqTarget_test',
                                      'predLambda_VS_targetPoly_valid',
                                      'predLambda_VS_targetPoly_test',
                                      'lstsqTarget_VS_targetPoly_valid',
                                      'lstsqTarget_VS_targetPoly_test'])    
    
    distrib_dicts = {'MAE': mae_distrib_dict, 
                     'R2': r2_distrib_dict}
    
    if return_model or n_jobs==1:
        return history, scores_dict, function_values, pred_list, distrib_dicts, model         
    else: 
        return history, scores_dict, function_values, pred_list, distrib_dicts       
    
    
    
#######################################################################################################################################################
################################################################SAVING AND PLOTTING RESULTS############################################################
#######################################################################################################################################################    
    
    
def generate_history_plots(history_list, by='epochs'):
    
    globals().update(generate_paths())
    
    for i, history in enumerate(history_list):  
        
        if by == 'epochs':
            index= (i+1)*each_epochs_save_lambda if each_epochs_save_lambda==1 else i*each_epochs_save_lambda if i > 1 else each_epochs_save_lambda if i==1 else 1
        elif by == 'samples':
            index = i
        
        plt.plot(history[list(history.keys())[1]])
        if consider_labels_training or evaluate_with_real_function:
            plt.plot(history[list(history.keys())[len(history.keys())//2+1]])
        plt.title('model ' + list(history.keys())[len(history.keys())//2+1])
        plt.ylabel('metric')
        plt.xlabel('epoch')
        plt.legend(['train', 'valid'], loc='upper left')
        if by == 'epochs':
            plt.savefig('./data/results/' + interpretation_network_string + filename + '/' + list(history.keys())[len(history.keys())//2+1] +  '_' + interpretation_network_string + filename + '_epoch_' + str(index).zfill(3) + '.png')
        elif by == 'samples':
            plt.savefig('./data/results/' + interpretation_network_string + filename + '/' + list(history.keys())[len(history.keys())//2+1] +  '_' + interpretation_network_string + filename + '_samples_' + str(samples_list[index]).zfill(5) + '.png')
        
        plt.plot(history['loss'])
        if consider_labels_training or evaluate_with_real_function:
            plt.plot(history['val_loss'])
        plt.title('model loss')
        plt.ylabel('loss')
        plt.xlabel('epoch')
        plt.legend(['train', 'valid'], loc='upper left')
        if by == 'epochs':
            plt.savefig('./data/results/' + interpretation_network_string + filename + '/loss_' + interpretation_network_string + filename + '_epoch_' + str(index).zfill(3) + '.png')    
        elif by == 'samples':
            plt.savefig('./data/results/' + interpretation_network_string + filename + '/loss_' + interpretation_network_string + filename + '_samples_' + str(samples_list[index]).zfill(5) + '.png')    
        if i < len(history_list)-1:
            plt.clf() 
            
            
def save_results(history_list, scores_list, by='epochs'):
    
    globals().update(generate_paths())
    
    if by == 'epochs':
        path = './data/results/' + interpretation_network_string + filename + '/history_epochs' + interpretation_network_string + filename + '.pkl'
    elif by == 'samples':
        path = './data/results/' + interpretation_network_string + filename + '/history_samples' + interpretation_network_string + filename + '.pkl'
    with open(path, 'wb') as f:
        pickle.dump(history_list, f, protocol=2)   
        
        
    if by == 'epochs':
        path = './data/results/' + interpretation_network_string + filename + '/scores_epochs' + interpretation_network_string + filename + '.pkl'
    elif by == 'samples':
        path = './data/results/' + interpretation_network_string + filename + '/scores_samples' + interpretation_network_string + filename + '.pkl'    
    with open(path, 'wb') as f:
        pickle.dump(scores_list, f, protocol=2)  
        


def generate_inet_comparison_plot(scores_list, plot_metric_list, ylim=None):
    
    globals().update(generate_paths())
    
    epochs_save_range_lambda = range(epoch_start//each_epochs_save_lambda, epochs_lambda//each_epochs_save_lambda) if each_epochs_save_lambda == 1 else range(epoch_start//each_epochs_save_lambda, epochs_lambda//each_epochs_save_lambda+1) if multi_epoch_analysis else range(1,2)


    if samples_list == None:
        x_axis_steps = [(i+1)*each_epochs_save_lambda if each_epochs_save_lambda==1 else i*each_epochs_save_lambda if i > 1 else each_epochs_save_lambda if i==1 else 1 for i in epochs_save_range_lambda]
        x_max = epochs_lambda
    else:
        x_axis_steps = samples_list
        x_max = samples_list[-1]

    if evaluate_with_real_function:
        #Plot Polynom, lamdba net, and Interpration net
        length_plt = len(plot_metric_list)
        if length_plt >= 2:
            fig, ax = plt.subplots(length_plt//2, 2, figsize=(30,20))
        else:
            fig, ax = plt.subplots(1, 1, figsize=(15,10))

        for index, metric in enumerate(plot_metric_list):

            inetPoly_VS_targetPoly_test = []
            #inetPoly_VS_predLambda_test = []
            #inetPoly_VS_lstsqTarget_test = []
            #inetPoly_VS_lstsqLambda_test = []
            #lstsqLambda_VS_predLambda_test = []
            #lstsqLambda_VS_lstsqTarget_test = []
            lstsqLambda_VS_targetPoly_test = []
            #predLambda_VS_lstsqTarget_test = []
            predLambda_VS_targetPoly_test = []
            lstsqTarget_VS_targetPoly_test = []

            for scores in scores_list:
                inetPoly_VS_targetPoly_test.append(scores[metric].loc['inetPoly_VS_targetPoly_test'])
                predLambda_VS_targetPoly_test.append(scores[metric].loc['predLambda_VS_targetPoly_test'])
                lstsqLambda_VS_targetPoly_test.append(scores[metric].loc['lstsqLambda_VS_targetPoly_test'])     
                lstsqTarget_VS_targetPoly_test.append(scores[metric].loc['lstsqTarget_VS_targetPoly_test'])

            plot_df = pd.DataFrame(data=np.vstack([inetPoly_VS_targetPoly_test, predLambda_VS_targetPoly_test, lstsqLambda_VS_targetPoly_test, lstsqTarget_VS_targetPoly_test]).T, 
                                   index=x_axis_steps,
                                   columns=['inetPoly_VS_targetPoly_test', 'predLambda_VS_targetPoly_test', 'lstsqLambda_VS_targetPoly_test', 'lstsqTarget_VS_targetPoly_test'])
            
            if length_plt >= 2:
                ax[index//2, index%2].set_title(metric)
                sns.set(font_scale = 1.25)
                p = sns.lineplot(data=plot_df, ax=ax[index//2, index%2])
            else:
                ax.set_title(metric)
                sns.set(font_scale = 1.25)
                p = sns.lineplot(data=plot_df, ax=ax)

            if ylim != None:
                p.set(ylim=ylim)
                
            p.set_yticklabels(p.get_yticks(), size = 20)
            p.set_xticklabels(p.get_xticks(), size = 20)        

        location = './data/plotting/'
        folder = interpretation_network_string + filename + '/'
        if samples_list == None:
            file = 'multi_epoch_REAL_' + interpretation_network_string+  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity)  + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'
        else:
            file = 'sample_list' + '-'.join([str(samples_list[0]), str(samples_list[-1])]) +'_REAL_' + interpretation_network_string +  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity)  + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'

        path = location + folder + file

        plt.savefig(path, format='pdf')
        plt.show()

    else:
        #Plot Polynom, lamdba net, and Interpration net
        length_plt = len(plot_metric_list)
        if length_plt >= 2:
            fig, ax = plt.subplots(length_plt//2, 2, figsize=(30,20))
        else:
            fig, ax = plt.subplots(1, 1, figsize=(15,10))
        for index, metric in enumerate(plot_metric_list):

            #inetPoly_VS_targetPoly_test = []
            inetPoly_VS_predLambda_test = []
            #inetPoly_VS_lstsqTarget_test = []
            inetPoly_VS_lstsqLambda_test = []
            lstsqLambda_VS_predLambda_test = []
            #lstsqLambda_VS_lstsqTarget_test = []
            #lstsqLambda_VS_targetPoly_test = []
            #predLambda_VS_lstsqTarget_test = []
            predLambda_VS_targetPoly_test = []
            #lstsqTarget_VS_targetPoly_test = []

            for scores in scores_list:
                inetPoly_VS_lstsqLambda_test.append(scores[metric].loc['inetPoly_VS_lstsqLambda_test'])
                inetPoly_VS_predLambda_test.append(scores[metric].loc['inetPoly_VS_predLambda_test'])
                lstsqLambda_VS_predLambda_test.append(scores[metric].loc['lstsqLambda_VS_predLambda_test'])     
                predLambda_VS_targetPoly_test.append(scores[metric].loc['predLambda_VS_targetPoly_test'])     

            plot_df = pd.DataFrame(data=np.vstack([inetPoly_VS_predLambda_test, inetPoly_VS_lstsqLambda_test, lstsqLambda_VS_predLambda_test, predLambda_VS_targetPoly_test]).T, 
                                   index=x_axis_steps,
                                   columns=['inetPoly_VS_predLambda_test', 'inetPoly_VS_lstsqLambda_test', 'lstsqLambda_VS_predLambda_test', 'predLambda_VS_targetPoly_test'])

            if length_plt >= 2:
                ax[index//2, index%2].set_title(metric)
                sns.set(font_scale = 1.25)
                p = sns.lineplot(data=plot_df, ax=ax[index//2, index%2])
            else:
                ax.set_title(metric)
                sns.set(font_scale = 1.25)
                p = sns.lineplot(data=plot_df, ax=ax)

            if ylim != None:
                p.set(ylim=ylim)
                
            p.set_yticklabels(p.get_yticks(), size = 20)
            p.set_xticklabels(p.get_xticks(), size = 20)  

        location = './data/plotting/'
        folder = interpretation_network_string + filename + '/'
        if samples_list == None:
            file = 'multi_epoch_MODEL_' + interpretation_network_string +  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity)   + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'
        else: 
            file = 'sample_list' + '-'.join([str(samples_list[0]), str(samples_list[-1])]) +'_MODEL_' + interpretation_network_string +  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity) + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'

        path = location + folder + file

        plt.savefig(path, format='pdf')
        plt.show()

        
def generate_values_for_single_polynomial_prediction_evaluation(function_values_test_list, rand_index=5):


    return plot_data_single, plot_data, x_vars, columns_single



def plot_and_save_single_polynomial_prediction_evaluation(lambda_net_test_dataset_list, function_values_test_list, rand_index=1, plot_type=2):
    
    globals().update(generate_paths())
    
    lambda_model_preds = function_values_test_list[-1][0][rand_index].ravel()
    real_poly_fvs = function_values_test_list[-1][1][rand_index]
    lstsq_lambda_preds_poly = function_values_test_list[-1][2][rand_index]
    lstsq_target_poly = function_values_test_list[-1][3][rand_index]
    inet_poly_fvs = function_values_test_list[-1][4][rand_index]


    x_vars = ['x' + str(i) for i in range(1, n+1)]

    columns = x_vars.copy()
    columns.append('FVs')

    columns_single = x_vars.copy()

    eval_size_plot = inet_poly_fvs.shape[0]
    vars_plot = lambda_net_test_dataset_list[-1].test_data_list[rand_index]


    if evaluate_with_real_function:
        columns_single.extend(['Lambda Model Preds', 'Target Poly FVs', 'LSTSQ Target Poly FVs', 'I-Net Poly FVs'])
        plot_data_single = pd.DataFrame(data=np.column_stack([vars_plot, lambda_model_preds, real_poly_fvs, lstsq_target_poly, inet_poly_fvs]), columns=columns_single)
        preds_plot_all = np.vstack([lambda_model_preds, real_poly_fvs, lstsq_target_poly, inet_poly_fvs]).ravel()
        vars_plot_all_preds = np.vstack([vars_plot for i in range(len(columns_single[n:]))])

        lambda_model_preds_str = np.array(['Lambda Model Preds' for i in range(eval_size_plot)])
        real_poly_fvs_str = np.array(['Target Poly FVs' for i in range(eval_size_plot)])
        lstsq_target_poly_str = np.array(['LSTSQ Target Poly FVs' for i in range(eval_size_plot)])
        inet_poly_fvs_str = np.array(['I-Net Poly FVs' for i in range(eval_size_plot)])

        identifier = np.concatenate([lambda_model_preds_str, real_poly_fvs_str, lstsq_target_poly_str, inet_poly_fvs_str])
    else:
        columns_single.extend(['Lambda Model Preds', 'Target Poly FVs', 'LSTSQ Lambda Poly FVs', 'I-Net Poly FVs'])
        plot_data_single = pd.DataFrame(data=np.column_stack([vars_plot, lambda_model_preds, real_poly_fvs, lstsq_lambda_preds_poly, inet_poly_fvs]), columns=columns_single)
        preds_plot_all = np.vstack([lambda_model_preds, real_poly_fvs, lstsq_lambda_preds_poly, inet_poly_fvs]).ravel()
        vars_plot_all_preds = np.vstack([vars_plot for i in range(len(columns_single[n:]))])

        lambda_model_preds_str = np.array(['Lambda Model Preds' for i in range(eval_size_plot)])
        real_poly_fvs_str = np.array(['Target Poly FVs' for i in range(eval_size_plot)])
        lstsq_lambda_preds_poly_str = np.array(['LSTSQ Lambda Poly FVs' for i in range(eval_size_plot)])
        inet_poly_fvs_str = np.array(['I-Net Poly FVs' for i in range(eval_size_plot)])

        identifier = np.concatenate([lambda_model_preds_str, real_poly_fvs_str, lstsq_lambda_preds_poly_str, inet_poly_fvs_str])

    plot_data = pd.DataFrame(data=np.column_stack([vars_plot_all_preds, preds_plot_all]), columns=columns)
    plot_data['Identifier'] = identifier    
    
    
    
    location = './data/plotting/'
    folder = interpretation_network_string + filename + '/'
    
    if plot_type == 1:
        pp = sns.pairplot(data=plot_data,
                      #kind='reg',
                      hue='Identifier',
                      y_vars=['FVs'],
                      x_vars=x_vars)
        
        if evaluate_with_real_function:
            file = 'pp3in1_REAL_' + str(rand_index) + '_' + interpretation_network_string +  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity)  + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'        
        else:
            file = 'pp3in1_PRED_' + str(rand_index) + '_' + interpretation_network_string +  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity)  + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'            
        
    elif plot_type == 2:

        pp = sns.pairplot(data=plot_data,
                          #kind='reg',
                          hue='Identifier',
                          #y_vars=['FVs'],
                          #x_vars=x_vars
                         )
        
        if evaluate_with_real_function:        
            file = 'pp3in1_extended_REAL_' + str(rand_index) + '_' + interpretation_network_string +  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity) + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'        
        else:
            file = 'pp3in1_extended_PRED_' + str(rand_index) + '_' + interpretation_network_string +  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity) + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'  
        
    elif plot_type == 3:
        
        pp = sns.pairplot(data=plot_data_single,
                          #kind='reg',
                          y_vars=columns_single[n:],
                          x_vars=x_vars)

        if evaluate_with_real_function:        
            file = 'pp1_REAL_' + str(rand_index) + '_' + interpretation_network_string+  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity) + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'        
        else:
            file = 'pp1_PRED_' + str(rand_index) + '_' + interpretation_network_string+  '_lambda_' + filename + '_' + str(interpretation_dataset_size) + '_train_' + str(lambda_dataset_size) + '_variables_' + str(n) + '_degree_' + str(d) + '_sparsity_' + str(sparsity) + '_amin_' + str(a_min) + '_amax_' + str(a_max) + '_xmin_' + str(x_min) + '_xmax_' + str(x_max) + training_string + '.pdf'            
        
    path = location + folder + file
    pp.savefig(path, format='pdf')

    return pp




def restructure_data_cnn_lstm(X_data, version=2, subsequences=None):

    #version == 0: one sequence for biases and one sequence for weights per layer (padded to maximum size)
    #version == 1: each path from input bias to output bias combines in one sequence for biases and one sequence for weights per layer (no. columns == number of paths and no. rows = number of layers/length of path)
    #version == 2:each path from input bias to output bias combines in one sequence for biases and one sequence for weights per layer + transpose matrices  (no. columns == number of layers/length of path and no. rows = number of paths )

    base_model = generate_base_model()
       
    if seed_in_inet_training:
        pass
    else:
        X_data_flat = X_data
        
        shaped_weights_list = []
        for data in tqdm(X_data):
            shaped_weights = shape_flat_weights(data, base_model.get_weights())
            shaped_weights_list.append(shaped_weights)
            
        max_size = 0
        for weights in shaped_weights:
            max_size = max(max_size, max(weights.shape))      
    
         
        if version == 0: #one sequence for biases and one sequence for weights per layer (padded to maximum size)
            X_data_list = []
            for shaped_weights in tqdm(shaped_weights_list):
                padded_network_parameters_list = []
                for layer_weights, biases in pairwise(shaped_weights):
                    padded_weights_train_list = []
                    for weights in layer_weights:
                        padded_weights = np.pad(weights, (int(np.floor((max_size-weights.shape[0])/2)), int(np.ceil((max_size-weights.shape[0])/2))), 'constant')
                        padded_weights_list.append(padded_weights)
                    padded_biases = np.pad(biases, (int(np.floor((max_size-biases.shape[0])/2)), int(np.ceil((max_size-biases.shape[0])/2))), 'constant')
                    padded_network_parameters_list.append(padded_biases)
                    padded_network_parameters_list.extend(padded_weights_list)   
                X_data_list.append(padded_network_parameters_list)
            X_data = np.array(X_data_list)    

        elif version == 1 or version == 2: #each path from input bias to output bias combines in one sequence for biases and one sequence for weights per layer
            lambda_net_structure = list(flatten([n, lambda_network_layers, 1]))                    
            number_of_paths = reduce(lambda x, y: x * y, lambda_net_structure)
                        
            X_data_list = []
            for shaped_weights in tqdm(shaped_weights_list):        
                network_parameters_sequence_list = np.array([]).reshape(number_of_paths, 0)    
                for layer_index, (weights, biases) in zip(range(1, len(lambda_net_structure)), pairwise(shaped_weights)):

                    layer_neurons = lambda_net_structure[layer_index]    
                    previous_layer_neurons = lambda_net_structure[layer_index-1]

                    assert biases.shape[0] == layer_neurons
                    assert weights.shape[0]*weights.shape[1] == previous_layer_neurons*layer_neurons

                    bias_multiplier = number_of_paths//layer_neurons
                    weight_multiplier = number_of_paths//(previous_layer_neurons * layer_neurons)

                    extended_bias_list = []
                    for bias in biases:
                        extended_bias = np.tile(bias, (bias_multiplier,1))
                        extended_bias_list.extend(extended_bias)


                    extended_weights_list = []
                    for weight in weights.flatten():
                        extended_weights = np.tile(weight, (weight_multiplier,1))
                        extended_weights_list.extend(extended_weights)      

                    network_parameters_sequence = np.concatenate([extended_weights_list, extended_bias_list], axis=1)
                    network_parameters_sequence_list = np.hstack([network_parameters_sequence_list, network_parameters_sequence])


                number_of_paths = network_parameters_sequence_list.shape[0]
                number_of_unique_paths = np.unique(network_parameters_sequence_list, axis=0).shape[0]
                number_of_nonUnique_paths = number_of_paths-number_of_unique_paths
                
                if number_of_nonUnique_paths > 0:
                    print("Number of non-unique rows: " + str(number_of_nonUnique_paths))
                    print(network_parameters_sequence_list)
                    
                X_data_list.append(network_parameters_sequence_list)
            X_data = np.array(X_data_list)          
            
            if version == 2: #transpose matrices (if false, no. columns == number of paths and no. rows = number of layers/length of path)
                X_data = np.transpose(X_data, (0, 2, 1))
                
        if lstm_layers != None and cnn_layers != None: #generate subsequences for cnn-lstm
            subsequences = 1 #for each bias+weights
            timesteps = X_train.shape[1]//subsequences

            X_data = X_data.reshape((X_data.shape[0], subsequences, timesteps, X_data.shape[2]))

        return X_data, X_data_flat