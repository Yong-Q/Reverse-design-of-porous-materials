#!/usr/bin/env python
# coding: utf-8

# In[3]:

import time
import shutil
import pormake as pm
from os import wait
import pickle
import numpy as np
import os
from mofnet import DataLoader, MOFNet

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.problems import get_problem
from pymoo.visualization.scatter import Scatter
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.core.problem import Problem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize
import pymoo.gradient.toolbox as anp


# In[4]:


data_loader = DataLoader.from_state("data_loader_state-20200117.npz")

# This hash dicts map budilding block names to unique index.
topo_hash = data_loader.topo_hash
node_hash = data_loader.node_hash
edge_hash = data_loader.edge_hash

mofnet = MOFNet()
mofnet.initialize_weights()
training_name = "cycle_tot"
mofnet.load_weights("cycle_tot/mofnet-{n:}-min.h5".format(n=training_name))


# In[5]:


mofnet_n2 = MOFNet()
mofnet_n2.initialize_weights()
training_name_xe = "cycle_tot"
mofnet_n2.load_weights("cycle_tot_xe/mofnet-{n:}-min.h5".format(n=training_name_xe))


# In[6]:

def remove_comments_from_cif(file_path, output_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    with open(output_path, 'w') as file:
        for line in lines:
            # 去除以 '#' 或 ';' 开头的注释行
            if not (line.strip().startswith('#') or line.strip().startswith(';')):
                file.write(line)

def process_cif_files_in_directory(directory_path):
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if os.path.isfile(file_path) and filename.lower().endswith('.cif'):
            output_path = os.path.join(directory_path, f"{filename}")
            remove_comments_from_cif(file_path, output_path)
            #print(f"Processed {filename}")

def mofnet_prediction(x_test_name):
    test_bulk=data_loader.make_dataset(
        np.array(x_test_name, dtype=str),
        np.array([0.0]*len(x_test_name)),
        batch_size=10000,
        repeat=False,
        shuffle=False,
    )
    prediction=[]
    for x, y in test_bulk:
        prediction.append(mofnet(x))
    return prediction[0]


# In[7]:


def mofnet_n2_prediction(x_test_name):
    test_bulk=data_loader.make_dataset(
        np.array(x_test_name, dtype=str),
        np.array([0.0]*len(x_test_name)),
        batch_size=10000,
        repeat=False,
        shuffle=False,
    )
    prediction=[]
    for x, y in test_bulk:
        prediction.append(mofnet_n2(x)*10)
    return prediction[0]


# In[8]:



def get_mof_name(topo,avail_nbbs,n_ebbs,variables_list):
    name_list=[]
    global ii
    for variables in variables_list:
        name=topo
        for i in range(len(avail_nbbs)):
            name=name+"+"+avail_nbbs[i][2][variables[i]]
        for j in range(len(avail_nbbs),len(avail_nbbs)+n_ebbs):
            name=name+"+"+edge_cn_arr[variables[j]]
        name_list.append(name)
    file_name = f'name_list_{ii}.txt'
    with open(file_name, 'a') as f:
        for name in name_list:
            f.write(name + '\n')
    return name_list


# In[9]:


def get_mof_name_independent(topo,x):
        topo_cn=topo_cn_arr[topo_cn_arr[:,0]==topo][0] #connection profile of each bbs in the topo
        n_bbs=topo_cn[2][0]+topo_cn[2][1] #unique nbb amounts in the topo
        n_ebbs=topo_cn[2][1] #unique ebb amounts in the topo
        avail_nbbs=[]
        xu_list=[]
        for nbb_cn in topo_cn[1]:
            nbb=bb_cn_arr[bb_cn_arr[:,0]==nbb_cn][0]
            avail_nbbs.append(nbb)
        for avail_nbb in avail_nbbs:
            xu_list.append(avail_nbb[1]-1)
        for avail_ebb in range(n_ebbs):
            xu_list.append(len(edge_cn_arr)-1)
        return get_mof_name(topo,avail_nbbs,n_ebbs,x)


# In[10]:

with open('T1.pickle', 'rb') as file:
    topo_cn_arr = pickle.load(file)
#topo_cn_arr = np.array(topo_cn_arr, dtype=object)
with open('node.pkl', 'rb') as file:
    bb_cn_arr = pickle.load(file)
bb_cn_arr = np.array(bb_cn_arr, dtype=object)
with open('edge.pickle', 'rb') as file:
    edge_cn_arr = pickle.load(file)
edge_cn_arr = np.array(edge_cn_arr, dtype=object)


avail_ebbs = bb_cn_arr
avail_topos=[]

print(topo_cn_arr[1][2][0])
topo_cn_arr = np.array(topo_cn_arr, dtype=object)
for i in range(len(topo_cn_arr)):
    if (topo_cn_arr[i][2][0]<4)&(topo_cn_arr[i][2][1]<4):
        avail_topos.append(topo_cn_arr[i][0])
#print(avail_topos)
#      avail_topos.append(topo_cn_arr[:,0]) 

#edge_cn_arr=edge_cn_arr[edge_cn_arr[:,0]==2][0]
"""
#global variables
with open('topo_cn_arr.pickle', 'rb') as file:
    topo_cn_arr = pickle.load(file)
with open('bb_cn_arr.pickle', 'rb') as file:
    bb_cn_arr = pickle.load(file)
avail_ebbs=bb_cn_arr[bb_cn_arr[:,0]==2][0]
avail_topos=topo_cn_arr[:,0]
#np.savetxt("avail_topos.txt",avail_topos,fmt="%s")
"""
topo_cn_arr,bb_cn_arr,avail_ebbs,avail_topos #[name,nbb_types,n_nbbs&ebbs],[cn,n_bbs,bbs_list]


# In[11]:


class carbon_problem(Problem):

    def __init__(self,topo_name):  
        self.topo=topo_name 
        self.topo_cn=topo_cn_arr[topo_cn_arr[:,0]==self.topo][0] #connection profile of each bbs in the topo
        self.n_bbs=self.topo_cn[2][0]+self.topo_cn[2][1] #unique nbb amounts in the topo
        self.n_ebbs=self.topo_cn[2][1] #unique ebb amounts in the topo
        self.avail_nbbs=[]
        self.xu_list=[]
        for nbb_cn in self.topo_cn[1]:
            nbb=bb_cn_arr[bb_cn_arr[:,0]==nbb_cn][0]
            self.avail_nbbs.append(nbb)
        for avail_nbb in self.avail_nbbs:
            self.xu_list.append(avail_nbb[1]-1)
        for avail_ebb in range(self.n_ebbs):
            self.xu_list.append(len(edge_cn_arr)-1)
        super().__init__(n_var=self.n_bbs, n_obj=2, n_ieq_constr=0, vtype=int)
        self.xl = np.zeros(self.n_var).astype(int)
        self.xu = np.array(self.xu_list)
        print(self.topo_cn,self.xu)

    def _evaluate(self, x, out, *args, **kwargs):
        self.mof_name_list = get_mof_name(self.topo, self.avail_nbbs, self.n_ebbs, x)
        f1_scores = -mofnet_prediction(self.mof_name_list)[:, 0]
        f2_scores = -mofnet_n2_prediction(self.mof_name_list)[:, 0]

        # Create a table with mof_name_list, f1_scores, and f2_scores
        results_table = list(zip(self.mof_name_list, f1_scores, f2_scores))

        # Calculate the threshold for the top 10%
        threshold_f1 = np.percentile(f1_scores, 10)
        threshold_f2 = np.percentile(f2_scores, 10)

        # Get the indices of the top 10% for f1 and f2
        top_10_percent_indices_f1 = np.where(f1_scores <= threshold_f1)[0]
        top_10_percent_indices_f2 = np.where(f2_scores <= threshold_f2)[0]

        # Get the union of the indices
        top_10_percent_indices = np.union1d(top_10_percent_indices_f1, top_10_percent_indices_f2)

        # Get the corresponding mof_name_list, f1_scores, and f2_scores
        top_results = [results_table[i] for i in top_10_percent_indices]

        # Save the results
        with open('top_10_percent_results.txt', 'a') as f:
            for name, score_f1, score_f2 in top_results:
                f.write(f"{name}\t{score_f1}\t{score_f2}\n")
        
        # Prepare the output for the optimization
        f1 = np.array([result[1] for result in results_table])
        f2 = np.array([result[2] for result in results_table])
        out["F"] = anp.column_stack([f1, f2])
        
        
        global ii
        file_name1 = f'output{ii-1}.txt'
        if os.path.exists(file_name1):
            with open(file_name1, 'a') as f:
                np.savetxt(f, out["F"], fmt='%.6f')
        else:
            np.savetxt(file_name1, out["F"], fmt='%.6f', header='F1 F2', comments='')
        ii += 1
        if ii > 1:
            print(ii)
            with open(f'top_10_percent_mof{ii-1}.txt', 'w') as f:
                for name, _, _ in top_results:
                    f.write(f"{name}\n")
            file_name = f'top_10_percent_mof{ii-1}.txt'
            os.makedirs(f"{ii-1}", exist_ok=True)
            save_dir=ii-1
            print(f"file_name: {file_name}, save_dir: {save_dir}")  # 调试输出
            import subprocess
            subprocess.run(["python", "build_materials2.py", "-c", file_name, "-s", str(save_dir)])
            process_cif_files_in_directory(str(save_dir))
            subprocess.run(["python", "data_cdftinput.py", "--folder_path", str(save_dir)])
            result = subprocess.run(["bash", "cdft.sh"], capture_output=True, text=True)
            subprocess.run(["python", "output.py"])
            #shutil.copy('cycle_tot.txt','./a/cycle_tot.txt')
            #进入a文件夹，执行脚本，并将文件拷贝出来
            #os.chdir('a')
            #train_mofnet()
            subprocess.run(["python", "train_mofneta.py"], check=False, stderr=subprocess.DEVNULL)
            subprocess.run(["python", "train_mofnetxe.py"], check=False, stderr=subprocess.DEVNULL) 
            #shutil.copy('./a/cycle_tot/mofnet-cycle_tot-min.h5', './cycle_tot/mofnet-cycle_tot-min.h5')
            
            print(os.getcwd())
            mofnet.load_weights("cycle_tot/mofnet-{n:}-min.h5".format(n=training_name))
            mofnet_n2.load_weights("cycle_tot_xe/mofnet-{n:}-min.h5".format(n=training_name_xe))
            """
            result = subprocess.run(["qsub", "cdft.sh"], capture_output=True, text=True)
            job_id = result.stdout.strip()
            print(f"Submitted job with ID: {job_id}")

            # Wait for the job to complete
            while True:
                result = subprocess.run(["qstat", job_id], capture_output=True, text=True)
                if "Unknown Job Id" in result.stderr:
                    print(f"Job {job_id} has completed.")
                    break
                else:
                    print(f"Job {job_id} is still running...")
                    time.sleep(30)  # Wait for 30 seconds before checking again
            """

            # build MOF2
            # caluate
            # train
        

    def _calc_pareto_front(self, n_points=100):
        initial_pop=[]
        for i in range(self.n_var):
            x0=np.linspace(0, self.xu[i], n_points, dtype=int)
            initial_pop.append(x0)
            
        X = np.column_stack(initial_pop)
        return self.evaluate(X, return_values_of=["F"])
 

# In[12]:
from pymoo.core.callback import Callback
class MyCallback(Callback):
    def __init__(self):
        super().__init__()

    def notify(self, algorithm):
        # 在每一次迭代时打印当前代数
        print(f"Generation: {algorithm.n_gen}")
callback = MyCallback()

algorithm = NSGA2(pop_size=100,
                      sampling=IntegerRandomSampling(),
                        crossover=SBX(prob=1.0, eta=3.0, vtype=float, repair=RoundingRepair()),
                        mutation=PM(prob=0.5, eta=3.0, vtype=float, repair=RoundingRepair()))


# In[ ]:

import random
for target_topo in avail_topos:
    
    problem = carbon_problem(target_topo)    
    ii=0   
    random_integer = random.randint(1, 100000)
    res = minimize(problem,
                       algorithm,
                       termination=('n_gen', 2),
                       seed=random_integer,
                       callbacks=[callback],
                       save_history=True,verbose=True)
    #plot = Scatter()
    #plot.add(problem.pareto_front(), plot_type="line", color="black", alpha=0.7)
    #plot.add(res.F, color="red")
    #plot.show()
    final_mofs=get_mof_name_independent(target_topo,res.X)
    final_results=np.vstack((get_mof_name_independent(target_topo,res.X),res.F.T)).T #[name,q_co2,lg(q_n2)]
    np.savetxt("nsga_result/"+target_topo+".txt",final_results,fmt="%s")
    del problem


# In[ ]:






# In[14]:





# In[ ]:




