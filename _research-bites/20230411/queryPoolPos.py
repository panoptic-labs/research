import requests
import json
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import pandas as pd
import numpy as np
import yfinance as yf


def getPool(pool_id:str):
    query = """query get_pools($pool_id: ID!) {
      pools(where: {id: $pool_id}) {
        tick
        sqrtPrice
        feeTier
        token0 {
          symbol
          decimals
        }
        token1 {
          symbol
          decimals
        }
      }
    }"""
    client = Client(
        transport=RequestsHTTPTransport(
            url='https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
            verify=True,
            retries=5,
        ))
    variables = {"pool_id": pool_id}
    response = client.execute(gql(query), variable_values=variables)
    return response['pools'][0]


def include_token_name(A:dict):
    A['name']=A['token0']['symbol']+'-'+A['token1']['symbol']+'-'+str(int(A['feeTier'])/10000)+'%'
    return A
    


    

def get_uniswap_v3_positions(pool_id: str, last_position_id: str = None):
    where_clause = '{pool: $poolId, liquidity_gt: 0' + (', id_gt: $lastPositionId' if last_position_id else '') + '}'
    query = f"""
    query ($poolId: ID!, $lastPositionId: ID) {{
        positions(where: {where_clause}, first: 1000, orderBy: id) {{
            id
            owner {{
                id
            }}
            token0 {{
                symbol
            }}
            token1 {{
                symbol
            }}
            tickLower {{
                tickIdx
            }}
            tickUpper {{
                tickIdx
            }}
            liquidity
            depositedToken0
            depositedToken1
            withdrawnToken0
            withdrawnToken1
        }}
    }}
    """
    url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
    variables = {"poolId": pool_id, "lastPositionId": last_position_id}
    response = requests.post(url, json={"query": query, "variables": variables})
    return response.json()



def get_all_positions(pool_id: str):
    all_positions = []
    last_position_id = None

    while True:
        result = get_uniswap_v3_positions(pool_id, last_position_id)
     
        positions = result["data"]["positions"]

        if not positions:
            break

        all_positions.extend(positions)
        last_position_id = positions[-1]["id"]

    return all_positions


def get_price(token:str):
    if token=='WETH' or token=='WBTC':
        token=token[1:]
    if token=='sETH2':
        token='ETH'
    
    asset=yf.Ticker(token+'-USD')
    price=asset.history(period='1d')['Close'].iloc[0]
    return price
    
    
    


def getPoolInfoAndPositions(pool_id:str):
    #BASE=1.0001
    print('getting pool info...')
    pool=getPool(pool_id)
    pool=include_token_name(pool)
    print('getting pool position...')
    df=pd.DataFrame(get_all_positions(pool_id))
   # N=len(df)
    #df['Tl']=[int(json.loads(df['tickLower'].iloc[i].replace("\'", "\""))['tickIdx']) for i in range(N)]
    #df['Th']=[int(json.loads(df['tickUpper'].iloc[i].replace("\'", "\""))['tickIdx']) for i in range(N)]

    # takes only positions that have not been withdrawn
    #df=df[df['withdrawnToken1']=='0']
    #df=df[df['withdrawnToken0']=='0']
    #price=BASE**int(pool['tick'])/(10**(int(pool['token1']['decimals'])-int(pool['token1']['decimals'])))
    
    price0=get_price(pool['token0']['symbol'])
    price1=get_price(pool['token1']['symbol'])

    # subgraph returns everything as a string, bc reasons
    df['liquidity']=df['liquidity'].apply(lambda x: np.float(x))
    df['depositedToken0']=df['depositedToken0'].apply(lambda x: np.float(x))
    df['depositedToken1']=df['depositedToken1'].apply(lambda x: np.float(x))
    df['withdrawnToken0']=df['withdrawnToken0'].apply(lambda x: np.float(x))
    df['withdrawnToken1']=df['withdrawnToken1'].apply(lambda x: np.float(x))

    df['totalLiq']=(df['depositedToken0']-df['withdrawnToken0'])*price0+(df['depositedToken1']-df['withdrawnToken1'])*price1
    df['prop']=df['totalLiq']/df['totalLiq'].sum()
    pool['positions']=df
    return pool


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    plt.style.use('../../stylesheet/panoptic-dark-16_9.mplstyle')
    
    
    POOL_LIST=['0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640',
                '0xcbcdf9626bc03e24f779434178a73a0b4bad62ed',
                '0x8ad599c3a0ff1de082011efddc58f1908eb6e6d8',
                #'0x5777d92f208679db4b9778590fa3cab3ac9e2168',
                '0x4585fe77225b41b697c938b018e2ac67ac5a20c0',
                '0x3416cf6c708da44db2624d63ea0aaef7113527c6',
                '0x7379e81228514a1d2a6cf7559203998e20598346',
                '0x4e68ccd3e89f51c3074ca5072bbac773960dfa36']
    cc=0
    pool_data=[]
    for p in POOL_LIST:
        pool_data.append(getPoolInfoAndPositions(p))
        dfg=pool_data[-1]['positions'].groupby(by='owner')['prop'].sum()
        dfg2=pool_data[-1]['positions'].groupby(by='owner')['totalLiq'].sum()

        N=len(dfg)
        prop_owners=np.arange(1,N+1)/N
        dfg=dfg.sort_values(ascending=False)
        dfg2=dfg2.sort_values(ascending=False)

        if cc<6:
            ls='solid'
        else:
            ls='dashed'
        plt.plot(prop_owners,np.cumsum(dfg), linestyle=ls, label=pool_data[-1]['name'])
        plt.title('Proportion of Liquidity Vs Owners')
        plt.ylabel('Proportion of Liquidity')
        plt.xlabel('Proportion of Owners')
        plt.xlim([0,0.2])
        plt.ylim([0,1])
        plt.legend()
        cc+=1
    plt.show()
#%%
    cc=0
    for p in range(len(POOL_LIST)):

        dfg=pool_data[p]['positions'].groupby(by='owner')['prop'].sum()
        dfg2=pool_data[p]['positions'].groupby(by='owner')['totalLiq'].sum()

        N=len(dfg)
        prop_owners=np.arange(1,N+1)/N
        dfg=dfg.sort_values(ascending=False)
        dfg2=dfg2.sort_values(ascending=False)
        owners=np.arange(1,N+1)

        if cc<6:
            ls='solid'
        else:
            ls='dashed'

        plt.semilogy(owners,np.cumsum(dfg2), linestyle=ls, label=pool_data[p]['name'])
        plt.title('Cumulative Liquidity Vs Owners')
        plt.ylabel('Total Liquidity (USD)')
        plt.xlabel('Owner Rank')
        plt.yticks([1e3,1e4,1e5,1e6,1e7,1e8,1e9])
        plt.ylim([1e3,1e9])
        plt.xlim([1,100])
        plt.legend()
        cc+=1

    plt.show()
    cc=0
       #%%     
    cc=0
    for p in range(len(POOL_LIST)):

        dfg=pool_data[p]['positions'].groupby(by='owner')['prop'].sum()
        dfg2=pool_data[p]['positions'].groupby(by='owner')['totalLiq'].sum()
        N=len(dfg)
        owners=np.arange(1,N+1)
        dfg=dfg.sort_values(ascending=False)
        dfg2=dfg2.sort_values(ascending=False)
        
        if cc<6:
            ls='solid'
        else:
            ls='dashed'
        plt.semilogy(owners,dfg2, linestyle=ls, label=pool_data[p]['name'])
        plt.title('Liquidity Vs Owners')
        plt.ylabel('Liquidity (USD)')
        plt.xlabel('Owner rank')
        plt.yticks([1e0,1e2,1e4,1e6,1e8,1e10])
        plt.ylim(1e-1,1e10)
        plt.xlim([0,500])
        plt.legend(loc='upper right')
        
        
        cc+=1
#%%
pm=[]
for p in pool_data:
    
    pos=p['positions'].groupby(by='owner')['totalLiq'].sum()
    
    pm.append({'pos':pos.max()/pos.sum(), 
               'name':p['name']
               })
    print('  {}, {}M'.format(p['name'], round(pos.max()/1e6,2)))

aux=pd.DataFrame(pm)



    
