#!/usr/bin/env python
# coding: utf-8

# # Training example of MOF-NET.
# 
# Training for prediction of hydrogen working capacity between 100 bar and 5 bar.

# ### Check available GPUs and set a GPU

# In[1]:


import os
import sys
os.system('nvidia-smi')


# In[2]:


import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import tensorflow as tf
print(tf.__version__)

import tensorflow.keras as keras

tf.config.list_physical_devices('CPU')


# ### Import desired libraries

# In[8]:


import pickle
from pathlib import Path
from collections import defaultdict
from itertools import cycle, permutations
from functools import partial

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ### Import MOF-NET

# In[4]:


from mofnet import DataLoader, MOFNet


# In[5]:
#os.chdir('a')

data_loader = DataLoader.from_state("data_loader_state-20200117.npz")

# This hash dicts map budilding block names to unique index.
topo_hash = data_loader.topo_hash
node_hash = data_loader.node_hash
edge_hash = data_loader.edge_hash






# ### Set name of training

# In[6]:


training_name = "cycle_tot_xe"


# In[7]:


os.makedirs(training_name, exist_ok=True)


# In[8]:


print(os.getcwd())


# ### Load working capacity data

# In[9]:


# bar unit.
gas_type = [
  "Xe","Kr","a"
]

names = ["key"] + [str(p) for p in gas_type]

gcmc_data_dir = "./"

uptake_data_paths = [
    gcmc_data_dir+"cycle_tot.txt",
]

# Hydrogen working capacity
wc_data_list = []
for path in uptake_data_paths:
    data = pd.read_table(path, index_col=0, header=None, names=names, sep="\s+")
    data = data["Xe"]
    wc_data_list.append(data)
wc_data = pd.concat(wc_data_list)


# In[10]:


[len(data) for data in wc_data_list]


# In[12]:


wc_data


# ### Prepare dataset

# In[13]:


# Normalize working capacity.
data = wc_data.copy()
# shuffle.
data = data.sample(frac=1)
data.describe()


# In[14]:


# Extract maximum values.
max_wc_dict = defaultdict(lambda: (None, -1.0))

for idx, wc in wc_data.items():
    topo = idx.split("+")[0]
    if max_wc_dict[topo][1] < wc:
        max_wc_dict[topo] = (idx, wc)


# In[15]:


top_data = data.loc[[v[0] for v in max_wc_dict.values()]]



# In[16]:


# Remove top data from dataset
data.drop(index=top_data.index, inplace=True)
data.describe()
n_train = int(len(data) * 0.9)
print(n_train)




n_data = len(data)
n_train = int(n_data * 0.9)

# Add top data to training set.
train_data = pd.concat([top_data, data.iloc[:n_train]])
train_data.describe()
test_data = data.iloc[n_train:]
train_data1=train_data



# Save train and test index.
with open("%s/train_data_index.txt"%training_name, "w") as f:
    for k in train_data.index:
        f.write(k+"\n")
        
# Save train and test index.
with open("%s/test_data_index.txt"%training_name, "w") as f:
    for k in test_data.index:
        f.write(k+"\n")


# #### Apply resampling

# In[23]:


# Make histogram dict by value.
hist_dict = defaultdict(lambda: 0)

bin_size = 0.001
for v in train_data:
    hist_dict[int(v/bin_size)] += 1

# Plot result.
#sorted_hist_dict = sorted(hist_dict.items(), key=lambda x: x[0])
#plt.bar(np.arange(len(sorted_hist_dict))*bin_size, [v[1] for v in sorted_hist_dict], width=0.9*bin_size)
#plt.show()


# In[24]:


choice_prob = np.array([1 / hist_dict[int(v/bin_size)] for v in train_data])
choice_prob = choice_prob / np.sum(choice_prob)


# In[25]:


resampled_train_data = train_data.sample(n=10000, weights=choice_prob, replace=True)
resampled_train_data.hist(bins=100)


# In[28]:


not_included_keys = list(set(train_data.index) - set(resampled_train_data.index))
len(not_included_keys)


# In[29]:


train_data = pd.concat([
    resampled_train_data,
    train_data.loc[not_included_keys]
]).sample(frac=1)

train_data.hist(bins=100, alpha=0.5)




# In[31]:


step = 0

# Load data loader.
data_loader = DataLoader.from_state("data_loader_state-20200117.npz")

# Make TF dataset from the data.
train_set = data_loader.make_dataset(
    np.array(train_data.index, dtype=str),
    np.array(train_data),
    batch_size=128,
)

test_set = data_loader.make_dataset(
    np.array(test_data.index, dtype=str),
    np.array(test_data),
    batch_size=128,
)

test_bulk = data_loader.make_dataset(
    np.array(test_data.index, dtype=str),
    np.array(test_data),
    batch_size=100,
    repeat=False,
    shuffle=False,
)


train_set_iter = iter(train_set)
test_set_iter = iter(test_set)


min_step = 0
loss_val_list = []

optimizer = tf.optimizers.Adam()

summray_dir = "%s/summary" % training_name

summary_writer_train = tf.summary.create_file_writer("%s/train" % summray_dir)
summary_writer_test = tf.summary.create_file_writer("%s/test" % summray_dir)


# In[32]:


# Make MOF-NET and the graph.
tf.summary.trace_on(graph=True, profiler=True)
#tf.summary.trace_on(graph=True, profiler=True)
print("Tracing started.")
mofnet = MOFNet()
mofnet.initialize_weights()

with summary_writer_train.as_default():
    tf.summary.trace_export(
        name="initilize_mofnet",
        profiler_outdir=".",
        step=0
    )


# In[33]:


# Define loss and training loop.
def calculate_loss(y_true, y_pred):
    loss = tf.reduce_mean(
        tf.square(y_true-y_pred),
    )
    
    return loss
    

@tf.function
def train_step(model, x, y, optimizer):
    with tf.GradientTape() as tape:
        y_pred = model(x, training=True)
        loss = calculate_loss(y_true=y, y_pred=y_pred)
        
    grads = tape.gradient(loss, model.trainable_weights)
    optimizer.apply_gradients(zip(grads, model.trainable_weights))
    
    return y_pred, loss


import pickle
import signal
import time
step = 0 

try:
    mofnet.load_weights("{n:}/mofnet-{n:}-min.h5".format(n=training_name))
    print("Weights loaded successfully.")
except Exception as e:
    print("Could not load weights: ", e)



state_list=[]
acc_total_loss_train = 0
n_total_loss_train = 0
for data_x, data_y in data_loader.make_dataset(
    np.array(pd.concat([train_data1, test_data]).index, dtype=str),
    np.array(pd.concat([train_data1, test_data])),
    batch_size=1000,
    repeat=False,
    shuffle=False,
):
    data_y_pred = mofnet(data_x)
    data_loss = calculate_loss(y_true=data_y, y_pred=data_y_pred)
    acc_total_loss_train += data_loss
    n_total_loss_train += 1

# Calculate the loss on the test set
acc_total_loss_test = 0
n_total_loss_test = 0
for test_x, test_y in test_bulk:
    test_y_pred = mofnet(test_x)
    test_loss = calculate_loss(y_true=test_y, y_pred=test_y_pred)
    acc_total_loss_test += test_loss
    n_total_loss_test += 1

# Use the larger of the two losses
train_loss_val = (acc_total_loss_train / n_total_loss_train).numpy().item()
test_loss_val = (acc_total_loss_test / n_total_loss_test).numpy().item()

print("Train loss on entire dataset: {:7.8f}".format(train_loss_val))
print("Test loss on entire dataset: {:7.8f}".format(test_loss_val))

original_total_loss_val = max(train_loss_val, test_loss_val)


print("Original model loss on entire dataset: {:7.8f}".format(original_total_loss_val))
min_mse = original_total_loss_val
while True:
    if step > 5000:
        print(111)
        break
    
    x, y = next(train_set_iter)
    y_pred, loss = train_step(mofnet, x, y, optimizer)
    
    # Skip the first step logging
    if step == 0:
        step += 1
        continue
    
    if step % 100 == 0:
        test_x, test_y = next(test_set_iter)
        test_y_pred = mofnet(test_x)
        
        test_loss = calculate_loss(y_true=test_y, y_pred=test_y_pred)
        
        with summary_writer_train.as_default():
            tf.summary.scalar("mofnet/loss", loss, step=step)
            
        with summary_writer_test.as_default():
            tf.summary.scalar("mofnet/loss", test_loss, step=step)
        
    if step % 250 == 0:
        mofnet.save_weights("{n:}/mofnet-{n:}-final.h5".format(n=training_name))
        
        # Calculate validation loss.
        y_true_list = []
        y_pred_list = []
        acc_test_loss = 0
        n_test_loss = 0
        for test_x, test_y in test_bulk:
            test_y_pred = mofnet(test_x)
            test_loss = calculate_loss(y_true=test_y, y_pred=test_y_pred)
            
            acc_test_loss += test_loss
            n_test_loss += 1

        loss_val = (acc_test_loss/n_test_loss).numpy().item()
        loss_val_list.append(loss_val)
        
        print("[{:d}] Loss Val: {:7.8f}, MIN MSE ({:d}): {:.8f}".format(step, loss_val, min_step, min_mse))
        if loss_val < min_mse:
            min_step = step
            print("New MIN MSE: %7.8f" % loss_val)
            mofnet.save_weights("{n:}/mofnet-{n:}-min.h5".format(n=training_name))
            min_mse = loss_val
    
            
        state_list.append([step, loss_val, min_step, min_mse])
        
        # 保存状态
       # with open('training_state.pkl', 'wb') as f:
       #     pickle.dump(state_list, f)

    step += 1

def cleanup_and_exit():
    # Ensure all resources are released and the process ends
    print("Training loop has ended.")
    tf.keras.backend.clear_session()
    return 0

exit_code = cleanup_and_exit()
print(f"Exit code: {exit_code}")
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Training loop timed out.")

# Set the timeout duration (in seconds)
timeout_duration = 1  # 1 hour

# Register the timeout handler
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(timeout_duration)

try:
    sys.exit(exit_code)
except TimeoutException as e:
    print(e)
    sys.exit(1)

