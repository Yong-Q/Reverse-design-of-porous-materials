from typing import Optional, Union, List
import numpy as np
from pathlib import Path
import argparse
import queue
import pormake as pm
#from pormake import *
import time
import threading

from concurrent.futures import ThreadPoolExecutor, TimeoutError
import multiprocessing
from typing import List
#import pm  # 假设你在使用的 pm 模块
from func_timeout import func_set_timeout
import func_timeout
import timeout_decorator
import asyncio
import os


stop_event = threading.Event()
pm.log.disable_print()
pm.log.disable_file_print()  

import signal
@timeout_decorator.timeout(20)
def write_cif_file(mof, path, name):
    """子函数：将 CIF 文件写入指定路径"""
    mof.write_cif(f"{path}/{name}.cif")

def long_running_function(name, db):
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(30)  
    mof = name_to_mof(name, db)
    return mof
def handler(signum, frame):
    raise TimeoutError("Function execution has timed out.")

def monitor_process(target_process, timeout):
    start_time = time.time()
    while target_process.is_alive():
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            print('Process timeout, terminating...')
            target_process.terminate()  # 终止子进程
            target_process.join()  # 等待子进程终止
            return "Process terminated due to timeout"
        time.sleep(0.1)  # 检查频率
    return "Process completed within timeout"
# Builder function
def monitor_process1(process_pid, timeout):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            os.kill(process_pid, 0)  # 检查进程是否还在运行
            time.sleep(0.2)  # 检查间隔
        except ProcessLookupError:
            print(f"Process {process_pid} has terminated.")
            return
    print(f"Process {process_pid} timed out. Terminating...")
    os.kill(process_pid, signal.SIGTERM)
    print(f"Process {process_pid} terminated due to timeout")

def worker(name, db, result_queue):
    try:
        result = name_to_mof(name, db)
        #time.sleep(4)
        #print("111")
        result_queue.put(result)
    except Exception as e:
        result_queue.put(e)
def run_worker(name, db, timeout):
    
    result_queue = multiprocessing.Queue()
    t = multiprocessing.Process(target=worker, args=(name, db, result_queue))
    t.start()
    start_time = time.time()
    process_pid = t.pid
    print(f"Started process with PID {process_pid}")
    """
    start_time = time.time()
    result_queue = queue.Queue()
    t = threading.Thread(target=worker, args=(name, db, result_queue))  # 这里修正了
    t.start()
    
    result_queue1 = multiprocessing.Queue()
    p = multiprocessing.Process(target=monitor_process, args=(t,10))
    p.start()
    t.join()
    """

   # time.sleep(2)
    

    #
    #monitor_process1(process_pid, 2)
    #p.join()
    
    
    #p.join(4)
    """
    while time.time() - start_time > 4:
        if  t.is_alive():
            actual_time = time.time() - start_time
            print(f"执行时间: {actual_time:.2f} 秒")
            print('worker overtime')
            stop_event.set() 
            #return None
        time.sleep(0.1)  #
    #time.sleep(3)
    """
    #t.join(4)  # 等待线程完成或超时
    if not result_queue.empty():
            result= result_queue.get()
            #os.kill(t.pid, signal.SIGTERM)
            return result
    return None 

    """
    if t.is_alive():
        print('11')
        
        print('worker overtime')
        #t.join()  # 可选：确保线程完成
        stop_event.set() 
        actual_time = time.time() - start_time
        print(f"执行时间: {actual_time:.2f} 秒")
        #t.terminate()
        t.join()
        return None
        
    else:
        print('worker finished')
        actual_time = time.time() - start_time
        print(f"实际执行时间: {actual_time:.2f} 秒")
        if not result_queue.empty():
            return result_queue.get()
        return None
    """

@timeout_decorator.timeout(20) 
def name_to_mof(_mof_name: str, db: pm.Database):
    tokens: List[str] = _mof_name.split("+")
    _topo_name = tokens[0]
    
    _node_bb_names = []
    _edge_bb_names = []
    for bb in tokens[1:]:
        if bb.startswith("N") or bb.startswith('C'):
            _node_bb_names.append(bb)

        if bb.startswith("E") or bb.startswith('L'):
            _edge_bb_names.append(bb)
        #time.sleep(1)

    _topology = db.get_topo(_topo_name)
    _node_bbs = [db.get_bb(f'{n}.xyz') for n in _node_bb_names]
    _edge_bbs = {tuple(et): None if n == 'E0' else db.get_bb(f'{n}.xyz')
                for et, n in zip(_topology.unique_edge_types, _edge_bb_names)}

    _builder = pm.Builder()
    _mof = _builder.build_by_type(_topology, _node_bbs, _edge_bbs)

    return _mof

def monitor_future(future, timeout):
    
    while not future.done():
        
        elapsed = time.time() - start_time
        if elapsed > timeout:
            future.cancel()  # 尝试取消任务
            print("Operation cancelled due to timeout")
            return
        print(f"Still waiting... Elapsed time: {elapsed:.2f} seconds")
        #time.sleep(2)  # 定期检查

def build_materials(
        candidate_file: Union[str, Path], 
        bb_dir: Optional[Union[str,Path]] = None, 
        topo_dir: Optional[Union[str,Path]] = None,
        save_dir: Union[str, Path] = 'small/', 
        large_dir: Union[str, Path] = 'large/', 
        cutoff: float = 45.0,
    ):
    # Basic settings for accessing database of pormake
    if isinstance(bb_dir, str):
        bb_dir = Path(bb_dir)
    if isinstance(topo_dir, str):
        topo_dir = Path(topo_dir)

    db = pm.Database(bb_dir=bb_dir, topo_dir=topo_dir)
    

    # Directory settings & validation
    #candidate_file = "./hmof_candidates.txt"
    #save_dir = "./small"
    #large_dir = "./large"

    try:
        if not Path(candidate_file).resolve().exists():
            raise Exception('Error: hmof_candidates.txt file does not exist!')
    except Exception as e:
        print(e)
        exit()

    Path(save_dir).resolve().mkdir(exist_ok=True, parents=True)
    Path(large_dir).resolve().mkdir(exist_ok=True, parents=True)


    # Obtain hmof_candidates
    with open(candidate_file, "r") as f:
        mof_names = f.read().split()

    print("Start generation.")

    # Generate all candidates
    for name in mof_names:
        print(name, end=" ")
        #global start_time
        #start_time = time.time()
        timeout = 10  
        pool = ThreadPoolExecutor(max_workers=1)
        
        try:
                
                try:
                    #mof = await asyncio.wait_for(name_to_mof(name, db), timeout=10.0)
                    mof=name_to_mof(name, db)
                except timeout_decorator.TimeoutError:
                #except asyncio.TimeoutError:
                    print("Function execution has timed out.")
                    continue
                
                #mof=name_to_mof(name, db)
                #mof=run_worker(name,db,10)
                """
                future = pool.submit(name_to_mof, name, db)
                
                #monitor_future(future, timeout=1)
                try:
                    mof=(future.result(timeout=10))
                except TimeoutError as err:
                    pool.shutdown()
                    print(f'线程{future}因超时已终止')
                """
                #mof = executor.submit(name_to_mof, name, db)
                """
                try:
                    mof = future.result(timeout=timeout) 
                     
                except TimeoutError:
                    print("Timeout. Skip.")
                    continue
                """
                if isinstance(mof, str):
                    print(mof, ", skip.")
                    continue

                min_cell_length = np.min(mof.atoms.cell.cellpar()[:3])
                if min_cell_length < 4.5:
                    print("Too small cell. Skip.")
                    continue

                max_cell_length = np.max(mof.atoms.cell.cellpar()[:3])
                try:
                    if max_cell_length < cutoff:
                        #mof.write_cif("{}/{}.cif".format(save_dir, name))
                        write_cif_file(mof, save_dir, name)
                      #  print("Success (small).")
                    else:
                        #mof.write_cif("{}/{}.cif".format(large_dir, name))
                        write_cif_file(mof, save_dir, name)
                      #  print("Success (large).")
                except timeout_decorator.TimeoutError:
                    print("write_cif_file Function execution has timed out.")
                    continue
            

        except Exception as e:
            print("Fails.", e)

    print("End generation.")
"""
async def main():
    await build_materials(
        candidate_file=args.candidates, 
        bb_dir=args.bb_dir, 
        topo_dir=args.topo_dir,
        save_dir=args.save_dir,
        large_dir=args.large_dir,
        cutoff=args.cutoff,
    )
"""


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='make candidates'
    )
    parser.add_argument('-c', '--candidates', '--candidate-file', default='/home/qiuyong/PORMAKE/bulk_pormake_generation/4.txt')
    parser.add_argument('-b', '--bb-dir', '--building-block-dir', default='/home/qiuyong/PORMAKE/pormake/database/bbs')
    parser.add_argument('-t', '--topo-dir', '--topology-dir', default='/home/qiuyong/PORMAKE/pormake/database/topologies')
    parser.add_argument('-s', '--save-dir', type=str, default='small/')
    parser.add_argument('-l', '--large-dir', type=str, default='large/')
    parser.add_argument('-co', '--cutoff', type=float, default=60.0)

    args = parser.parse_args()
    
    build_materials(
        candidate_file=args.candidates, 
        bb_dir=args.bb_dir, 
        topo_dir=args.topo_dir,
        save_dir=args.save_dir,
        large_dir=args.large_dir,
        cutoff=args.cutoff,
    )
    
    #asyncio.run(main())







