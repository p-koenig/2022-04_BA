from python_scripts.interpretation_net_evaluate import run_evaluation, extend_inet_parameter_setting
from python_scripts.plot_results import plot_evaluation_results

from sklearn.model_selection import ParameterGrid
from joblib import Parallel, delayed
from contextlib import redirect_stdout
import socket
from tqdm import tqdm
import time

import os

import numpy as np

                
def sleep_minutes_function(minutes):   
    for _ in tqdm(range(minutes)):
        time.sleep(60)

                
def main(): 
    
    sleep_minutes = 0

        
    filename = str(os.path.basename(__file__)).split('.')[0]
    timestr = filename + '-' + time.strftime("%Y%m%d-%H%M%S.%f")[:-3]
    
    os.makedirs(os.path.dirname('./running_evaluations/'), exist_ok=True)
    with open('./running_evaluations/temp-' + socket.gethostname() + '_' + timestr + '.txt', 'a+') as f:
        with redirect_stdout(f):  
            
            if sleep_minutes > 0:
                sleep_minutes_function(sleep_minutes)
        
            evaluation_grid = {
                
                'n_jobs': [7],   
                'force_evaluate_real_world': [False],
                'number_of_random_evaluations_per_distribution': [10],
                'optimize_sampling': [False],
                
                'dt_setting': [10], # 1=vanilla; 2=SDT1; 3=SDT-1  ------- 'dt_type', 'decision_sparsity', 'function_representation_type'                
                'inet_setting': [1], 
                'dataset_size': [10000], #10000, 50000
                
                'maximum_depth': [3],
                'number_of_variables':[
                                               3,
                                               9, 
                                               10, 
                                               13, 
                                               15, 
                                               16, 
                                               23,
                                               28,
                                               29,
                                               32,
                                              ],      
                
                
                'function_generation_type': ['distribution'],# 'make_classification_distribution', 'make_classification_distribution_trained', 'distribution', 'distribution_trained', 'make_classification', 'make_classification_trained', 'random_decision_tree', 'random_decision_tree_trained'
                
                'distrib_by_feature': [True],
                'max_distributions_per_class': [1],
                'distribution_list': [['uniform', 'normal', 'gamma', 'beta', 'poisson']], #[['uniform', 'gamma', 'poisson', 'exponential', 'weibull']],#['uniform', 'normal', 'gamma', 'exponential', 'beta', 'binomial', 'poisson'], 
                'distribution_list_eval': [['uniform', 'normal', 'gamma', 'beta', 'poisson']],#[['uniform', 'normal', 'gamma', 'beta', 'poisson']],#[['uniform', 'gamma', 'poisson', 'exponential', 'weibull']],#[['uniform', 'normal', 'gamma', 'beta', 'poisson']],
                'distrib_param_max': [5],
                
                'exclude_linearly_seperable': [True],
                'data_generation_filtering':  [True, False], 
                'fixed_class_probability':  [True, False], 
                'balanced_data': [True],
                'weighted_data_generation':  [True, False], 
                'shift_distrib':  [True, False],        
                
                'separate_weight_bias': [False],
                'normalize_lambda_nets': [False],
                'data_reshape_version':  [None], #default to 2 options:(None, 0,1 2,3) #3=autoencoder dimensionality 
                                
                'noise_injected_level': [0],
                
                'resampling_strategy': [None], #'ADASYN', 'SMOTE',, None
                'resampling_threshold': [0.2],   
                'restore_best_weights': [True],
                'patience_lambda': [50],
                
                'random_evaluation_dataset_size': [500],
                
                'lambda_network_layers': [[128]],

            }


            print(evaluation_grid)
            
            parameter_grid = list(ParameterGrid(evaluation_grid))
            
            #for parameter_setting in parameter_grid:
                #print(parameter_setting)
                
            print('Possible Evaluations: ', len(parameter_grid))
                
            Parallel(n_jobs=7, backend='loky', verbose=10000)(delayed(run_evaluation)(enumerator, timestr, parameter_setting) for enumerator, parameter_setting in enumerate(parameter_grid))

            #for parameter_setting in parameter_grid:
                #run_evaluation.remote(parameter_setting)
            print('COMPUTATION FINISHED')    
                        
            for i in range(len(parameter_grid)):
                del parameter_grid[i]['number_of_variables']
                parameter_grid[i]['dt_setting'] = np.floor((parameter_grid[i]['dt_setting']-1) / 3).astype(int)
                #print(parameter_grid[i])
            
            parameter_grid = [ii for n,ii in enumerate(parameter_grid) if ii not in parameter_grid[:n]]
            #parameter_grid = list(set(parameter_grid))
            
            print('Possible Evaluations Types: ', len(parameter_grid)) 
                
            #inet_setting_parameters = [extend_inet_parameter_setting({'inet_setting': inet_setting_value}) for inet_setting_value in evaluation_grid['inet_setting']]
                        
            #structure_list = [inet_setting['dense_layers'] for inet_setting in inet_setting_parameters]
            #dropout_list = [inet_setting['dropout'] for inet_setting in inet_setting_parameters]
                
            plot_evaluation_results(timestr=timestr, parameter_grid=parameter_grid, score_string='accuracy')  
            
            plot_evaluation_results(timestr=timestr, parameter_grid=parameter_grid, score_string='f1_score')              
            
            
if __name__ == "__main__": 

        
	main()
