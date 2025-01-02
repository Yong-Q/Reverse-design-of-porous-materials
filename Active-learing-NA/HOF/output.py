import os
import csv

folder_path = "./out_COF"
bat_files = [file for file in os.listdir(folder_path) if file.endswith('.dat')]

#output_csv_name = 'out_COFCU.csv'
#with open(output_csv_name, 'w', newline='') as f:
#    writer = csv.writer(f)
#    writer.writerow(['File Name', 'Line 6', 'Line 7'])

for file_name in bat_files:
    basename = os.path.splitext(file_name)[0]  # 获取去掉后缀的文件名
    with open(os.path.join(folder_path, file_name), 'r') as f:
        lines = f.read().splitlines()

        try:
            line_6 = float(lines[5].split(' ')[1])
            line_7 = float(lines[6].split(' ')[1])
            line_4=lines[3].split(' ')
        except IndexError:
            line_6 = 0.0
            line_7 = 1.0
            line_4 = ['N/A']
        result = (line_6 / line_7) * 4

        output_txt='cycle_tot.txt'
        with open(output_txt, 'a') as f:  # 使用 'a' 模式追加内容
            f.write(f"{basename} {line_6} {line_7} {result} \n")  # 将数据格式化并写入

        os.remove(os.path.join(folder_path, file_name))
