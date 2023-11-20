#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 15 10:16:31 2023

@author: juan
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import scipy.stats as stats


# Function to perform ANOVA and extract required statistics
def perform_anova_and_get_stats(data1, data2):
    # Perform ANOVA
    anova_result = stats.f_oneway(data1, data2)
    p_value = anova_result.pvalue

    # Extract statistics for annotation
    stats_data1 = {
        'mean': np.mean(data1),
        'q1': np.percentile(data1, 25),
        'q2': np.median(data1),
        'q3': np.percentile(data1, 75)
    }
    stats_data2 = {
        'mean': np.mean(data2),
        'q1': np.percentile(data2, 25),
        'q2': np.median(data2),
        'q3': np.percentile(data2, 75)
    }

    return p_value, stats_data1, stats_data2





def plotComparisson(df,name,truncation=None):
    plt.style.use('panoptic-dark-16:9.mplstyle')

    cols=[ 'vol',  'r']
    labels=['SFPM > BSM', 'SFPM < BSM']

    

    fig, axs = plt.subplots(1, 3, figsize=(18, 6))
    plt.rcParams.update({'font.size': 10})  # Resetting to default or smaller size for annotations
        
    title_fontsize = 24  # Larger font size for titles
    suptitle_fontsize=26
    label_fontsize = 18  # Larger font size for axis labels
    
    if truncation is not None:
        plt.suptitle(f'Truncated at r<{truncation}',fontsize=suptitle_fontsize)
        df=df[df['r']<truncation]
        
    above=df[df['adj_premia']<df['total_fees_usd']]
    below=df[df['adj_premia']>df['total_fees_usd']]
    
    
    df=df[df['Tr']<356*3]
    
    
    axs[0].loglog(df['adj_premia'],df['total_fees_usd'],'.',linewidth=5)
    axs[0].plot(df['adj_premia'],df['adj_premia'],':',linewidth=1.5,label='Equal premia')
    axs[0].set_title(f'{name}.  {round(100*len(above)/len(df),2)}% above', fontsize=title_fontsize)
    axs[0].set_xlabel('BSM premia (USD)', fontsize=label_fontsize)
    axs[0].set_ylabel('SFPM premia (USD)', fontsize=label_fontsize)
    axs[0].set_xlim([1e-1,1e5])
    axs[0].set_ylim([1e-1,1e5])
    


    # Creating 3 x 1 subplot with ANOVA results and annotations
    
    
    for i, c in enumerate(cols):
        all_data = [above[c], below[c]]
    
        # Perform ANOVA and get statistics
        p_value, stats_above, stats_below = perform_anova_and_get_stats(above[c], below[c])
    
        # Plot boxplot
        bp = axs[i+1].boxplot(all_data, vert=True, patch_artist=True, labels=labels)
        axs[i+1].set_title(f'{c}, p-value: {p_value:.2e}', fontsize=title_fontsize)
        axs[i+1].set_xlabel('Groups', fontsize=label_fontsize)
        axs[i+1].set_ylabel('Values', fontsize=label_fontsize)
        if c == 'r':
            axs[i+1].set_ylim([1,3])
    
        # Annotate statistics
        for j, stats_data in enumerate([stats_above, stats_below]):
            y = bp['medians'][j].get_ydata()[0]  # Adjust y position for annotation
            axs[i+1].annotate(f"Mean: {stats_data['mean']:.2f}\nQ1: {stats_data['q1']:.2f}\nQ2: {stats_data['q2']:.2f}\nQ3: {stats_data['q3']:.2f}", 
                            (j + 1, y), 
                            textcoords="offset points", 
                            xytext=(0, 10),
                            ha='center')
    
    plt.tight_layout()
    name_save=name
    if truncation is not None:
        name_save+='truncated'
        name= name+f', r<{truncation}'
    plt.savefig(f'{name_save}.png')
    plt.show()

    # computes CDF
    tr=np.linspace(1,11,100)
    aux=0*tr
    
    
    for i in range(len(tr)):
        aux[i]=100*np.sum(tr[i]*df['total_fees_usd']>df['adj_premia'])/len(df)
    
            
    plt.figure(figsize=(6,3))
    plt.plot(tr,aux)
    
    title_fontsize = 16  # Larger font size for titles
    label_fontsize = 12  # Larger font size for axis labels
    plt.xlabel(r'Liquidity utilization factor, $\ell$', fontsize=label_fontsize)
    plt.title(f'{name}', fontsize=title_fontsize)
    plt.ylabel('% Positions SFPM>BSM', fontsize=label_fontsize)
    plt.xlim([0,9])
    
    name_save=f'{name}_lut'
    if truncation is not None:
        name_save+='truncated'
        name= name+f', r<{truncation}'
    plt.savefig(f'{name_save}.png')
    



    
    
    

    
