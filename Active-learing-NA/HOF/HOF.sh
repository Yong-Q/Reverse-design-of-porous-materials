#!/bin/bash
#PBS -N HOFNSGA2
#PBS -l walltime=99999:00:00
#PBS -l nodes=node07:ppn=128
#PBS -j oe



source /opt/modules/module.sh
module load conda
source activate tensorflow
python testcarbon_problem.py 
