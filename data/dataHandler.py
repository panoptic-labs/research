#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec  8 07:47:48 2022


This is the data handler class for panoptic.

@author: juan
"""

from datetime import datetime
import json
import time
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import os
class data:
    
    
    def __init__(self,token:str):
        '''
        This is the data class that we use to query the google big query 
        ethereum public database. 

        Parameters
        ----------
        token : str
            The location of the json token file for google big query. You will
            need to provide your own. This can be found here: 
            https://cloud.google.com/bigquery/docs/quickstarts/quickstart-client-libraries
        Raises
        ------
        Exception
            If it doesn't find the google cloud qkey'

        '''
        
        isFile = os.path.isfile(token)
        if isFile:
            print('google big query key loaded')
        else:
            raise Exception("🔴 the json file for the google cloud key doesn't seem to be here. check your path")
        
        self.token=token
        self.bigQueryDB='`bigquery-public-data.crypto_ethereum.logs`'
        
        
        
        
        
        
    def queryPool(self,poolAddress:str,
                      initialBlock:int=None,
                      endBlock:int=None,
                      filename:str=None)->pd.core.frame.DataFrame:
        '''
        

        Parameters
        ----------
        poolAddress : str
            the 0xbunchOfDigits address of the pool
        initialBlock : int, optional
            The first block to start querying from. The default is None.
        endBlock : int, optional
            The last block to query from. The default is None.
        filename : str, optional
            an adress where to sto store the csv file. DO NOT INCLUDE EXTENSION. The default is None.

        Raises
        ------
        Exception
            If this is raised it is becuase there was an issue with google big query. Check your
            google cloud account for permissions and stuff

        Returns
        -------
        df : pandas.core.frame.DataFrame
            a dataFrame with the requested query

        '''


        #######################################################################
        
        # these are all google auth and google big query stuff. 
        
        #######################################################################
        keyPath=self.token
        DB=self.bigQueryDB
        credentials = service_account.Credentials.from_service_account_file(
            keyPath, scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        client = bigquery.Client(credentials=credentials, project=credentials.project_id)


        #######################################################################
        # Get the Ethereum blockchain data
        #TODO check if its easier to operate here than to manipulate the 
        #data log with pandas        
        #######################################################################
        mainQuery ='''
        SELECT address, block_number, transaction_hash, block_timestamp,
          log_index, transaction_index,
          CONCAT('0x',(CAST(SUBSTRING(Data, 3, 64) as string))) as amount0,
          CONCAT('0x',(CAST(SUBSTRING(Data, 67, 64) as string))) as amount1,
          CONCAT('0x',(CAST(SUBSTRING(Data, 131, 64) as string))) as sqrtPrice,
          CONCAT('0x',(CAST(SUBSTRING(Data, 195, 64) as string))) as liquidity,
         IF 
          ((CAST(CONCAT('0x',(CAST(SUBSTRING(DATA, 317, 16) AS string))) AS int)) > CAST('0xf00000' AS int), (CAST(CONCAT('0x',(CAST(SUBSTRING(DATA, 317, 16) AS string))) AS int))- CAST('0xffffff' AS int), CAST(CONCAT('0x',(CAST(SUBSTRING(DATA, 317, 16) AS string))) AS int)) AS tick 
        FROM {} 
        WHERE 
        DATA != '' 
        AND transaction_hash != '' 
        AND address = '{}' 
        AND (CAST(SUBSTRING(DATA, 259, 64) AS string)) != '' 
        '''.format(DB,poolAddress)



        if initialBlock is  not None:
            mainQuery=mainQuery+" AND block_number >={initialBlock} "
        
        if endBlock is not None:
            mainQuery=mainQuery+" AND block_number <={endBlock} "

        
        A='''
          ORDER BY 
          block_timestamp ASC, transaction_index 
        '''
        mainQuery=mainQuery+A

        # import pdb
        # pdb.set_trace()
        print("🟢 begin query...")
        query_job = client.query(mainQuery)  # API request

        while query_job.state != "DONE":
            print("  ⏲️ querying...")
            query_job.reload()
            time.sleep(4)

        if query_job.state == "DONE":
            print("✅ Query job is done. ✍ Exporting to csv...")
            df = query_job.to_dataframe()
            

            
            if filename is None:
                filename=poolAddress
            #generates a time stamp
            lastTimeStamp=df['block_timestamp'].iloc[-1] 
            filename=filename+'_'+str(lastTimeStamp)+'.csv'
            
            #converts to csv 
            df.to_csv(filename, index=False)
        else:
            raise Exception("🔴 Query job did not complete!")

        print("ALL DONE!")
        
        return df


if __name__=='__main__':
    KEY='ebq.json'
    POOL='0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8'
    
    handler=data(KEY)
    df=handler.queryPool(poolAddress=POOL)
    
    
    
