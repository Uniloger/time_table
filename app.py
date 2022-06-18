import pandas as pd 
import streamlit as st
import plotly_express as px
import plotly.graph_objects as go
import datetime as dt
import copy

#vars
my_date = dt.date.today()
year, week_num, day_of_week = my_date.isocalendar()
#functions 
def cols_to_object(nexts):
    for c, column in nexts.iteritems():
        nexts[c]= nexts[c].astype('object')
    return nexts

def assign_shifts(prefs, assignation_order, res, nexts):
    for l in assignation_order:
        for t in l:
            for df in prefs:
                if df.at[t[0], t[1]] > 0:
                    i = res[res['fullname']==df.w_id[0]].index[0]
                    if res.at[i, 'shifts'] < 3: 
                        if df.w_id[0] not in nexts.iloc[t[0]].to_list():
                            if t[1]=='morning_shift' and nexts.at[t[0], 'morning_radware'] == 0:
                                if (t[0] == 0) or  nexts.at[t[0]-1, 'night'] != df.w_id[0]:
                                    res.at[i, 'shifts']+=1
                                    nexts[ 'morning_radware'].iloc[t[0]] = df.w_id[0]
                            elif t[1]=='morning_shift' and nexts.at[t[0], 'morning_infinidat'] == 0:
                                res.at[i, 'shifts']+=1
                                nexts.at[t[0],  'morning_infinidat'] = df.w_id[0]
                            elif t[1]=='day_shift' and nexts.at[t[0], 'day_radware'] == 0:
                                res.at[i, 'shifts']+=1
                                nexts.at[t[0], 'day_radware'] = df.w_id[0]
                            elif t[1]=='day_shift' and nexts.at[t[0], 'day_infinidat'] == 0:
                                res.at[i, 'shifts']+=1
                                nexts.at[t[0],  'day_infinidat'] = df.w_id[0]
                            elif t[1]=='night_shift' and nexts.at[t[0], 'night'] == 0:
                                res.at[i, 'shifts']+=1
                                nexts.at[t[0], 'night'] = df.w_id[0]
    return nexts


def get_individual_prefs(res):
    prefs = []
    cols = ['morning_shift', 'day_shift', 'night_shift']
    #pref[cols] = pref[cols].replace({0:1})
    pref.day_of_week= pref.day_of_week.str.lower()
    for i in range(len(res)):
        cp= pref.copy()
        r = res.iloc[i]
        cp.w_id = r.fullname
        for k, column in r[2:9].iteritems():
            for j, row in cp.iterrows():
                if k==cp.day_of_week[j]:
                    if 'morning' in r[k]:
                        cp.at[j, 'morning_shift'] = 1
                    if 'day' in r[k]:
                        cp.at[j,'day_shift'] = 1
                    if 'night' in r[k]:
                        cp.at[j, 'night_shift'] = 1         
        prefs.append(cp)
    return prefs


    

def create_melted(res):
  melted = []
  pr =  get_individual_prefs(res)
  for i in range(len(pr)):
    pr[i]['day_ind'] = pr[i].index
    w_id = pr[i].w_id.iloc[0]
    k = pd.melt(pr[i], id_vars=['day_of_week', 'day_ind'], value_vars=['morning_shift','day_shift', 'night_shift'])
    k = k.sort_values(by = ['day_ind'])
    k['shift_ind'] = 0
    for i in range(len(k)):
        if k.variable.iloc[i] == 'day_shift':
            k.shift_ind.iloc[i] = 1
        elif k.variable.iloc[i] == 'night_shift':
            k.shift_ind.iloc[i] = 2
        else:
            pass
    k = k.sort_values(by = ['day_ind', 'shift_ind'])
    k.drop(['day_ind','shift_ind'], axis = 1, inplace = True)
    k.rename(columns = {'value':w_id}, inplace =True)
    k = k.reset_index(drop = True)
    melted.append(k)
  final_table = melted[0]
  for i in range(len(melted)):
    final_table[melted[i].iloc[:, 2:].columns[0]] = melted[i].iloc[:, 2:]
  return final_table

def matrices_sum(prefs):
    #Sum up the matrices
    df = prefs[0].copy()
    for i in range(1,len(prefs)):
        df.morning_shift = df.morning_shift + prefs[i].morning_shift
        df.day_shift = df.day_shift + prefs[i].day_shift
        df.night_shift = df.night_shift + prefs[i].night_shift
    return df
    
def get_assignation_order(df):
    val = {}
    vals = []
    for c, column in df.iloc[:,1:4].iteritems():
        for r, rows in df.iterrows():
            vals.append(df.at[r,c])
            val[tuple([r,c])] = df.at[r,c]
    vals = list(set(vals)) 
    assignation_order = []
    for n in vals:
        assignation_order.append([k for k,v in val.items() if v == n])
    return assignation_order



def check_for_late_resp(res):
    res.dropna(inplace = True)
    resp_copy= copy.deepcopy(res)
    for i in range(len(res)):
        if  (res.timestamp.iloc[i].date().isocalendar()[1]!=week_num) & (res.fullname.iloc[i] !=''):
            resp_copy.drop(i, inplace = True)
    resp_copy.timestamp = pd.to_datetime(resp_copy.timestamp)
    for i, row in resp_copy.iterrows():
        name = row.fullname
        if name == '':
            resp_copy.drop(i, axis = 0, inplace = True)     
        stamp = row.timestamp
        ch_index = i
        for k,row in resp_copy.iterrows():
            if row.fullname == name and row.timestamp > stamp:
                resp_copy.drop(ch_index, axis = 0, inplace = True)
    return resp_copy.reset_index(drop = True)

######################################################
######################################################
######################################################
#Starting to process

st.header('Shifts 24.7 web app')

workers = pd.read_csv(r'~/time_table/workers.csv')
pref = pd.read_csv(r'~/time_table/preferences.csv')
nexts = pd.read_csv(r'~/time_table/nexts.csv')
#res = pd.read_csv(r'~/time_table/responses.csv')

workers.fillna('Worker', inplace= True)

#need to figure out how exactly i process the csv file.
st.write('please upload the responses file here:')
uploaded_file = st.file_uploader("Choose a file", type = 'csv')
if uploaded_file is not None:
    res = pd.read_csv(uploaded_file)
    res['shifts']=0
    res.columns=['timestamp', 'fullname', 'sunday', 'monday', 'tuesday', 'wednesday','thursday', 'friday', 'sabbath', 'comments', 'shifts']
    res.timestamp = res.timestamp.dropna()
    res.timestamp=pd.to_datetime(res.timestamp, errors='coerce')
    res.fullname = res.fullname.dropna()
    res.fillna('', inplace= True)
    res = check_for_late_resp(res)
    no_resp = []
    st.write('Who still needs to fill the form?')
    no_resp = [x for x in workers.Workers.tolist() if x not in res.fullname.tolist()]    
    st.write(no_resp)
    res = check_for_late_resp(res)
    preferences =  get_individual_prefs(res)
    df = matrices_sum(preferences)
    ao = get_assignation_order(df)
    nxt = cols_to_object(nexts)
    shifts = assign_shifts(preferences, ao, res, nxt)
    st.write(shifts.astype(str))
    final_table = create_melted(res)
    shifts = shifts.to_csv(index=False).encode('utf-8')
    final_table = final_table.to_csv(index= False).encode('utf-8')
    #shifts = st.dataframe(shifts)
    st.download_button('"Download shifts table as CSV"', shifts, file_name='shifts.csv', mime='text/csv' )
    st.download_button('"Download personal answers table as CSV"', final_table, file_name='personal_answers.csv', mime='text/csv' )
    


    
    

    


    




  




	
