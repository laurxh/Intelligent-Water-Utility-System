import wntr
import copy
import math
import random

water_plant_ids = []
# 添加水厂编号
lim = 40

# 加载网络
wn = wntr.network.WaterNetworkModel('./networks/Net2.inp')

def add_plant_id(plant_id):
    water_plant_ids.append(plant_id)

def main():
    # 添加水厂编号
    print("dsada")
    add_plant_id('1')  # 在WNTR中，节点ID通常是字符串
    add_plant_id('8')
    
    # 修改节点的基本需水量
    for i in water_plant_ids:
        random_number = random.uniform(0, 0.02)
        print(i, random_number)
        
        # 在WNTR中修改节点需水量
        # 注意：WNTR中负需水量表示供水，与EPANET相同
        node = wn.get_node(i)
        
        # 直接设置基本需水量，不使用需水模式
        # 清除现有的需水模式
        node.demand_timeseries_list.clear()
        
        # 添加一个新的基本需水量，不指定模式
        node.add_demand(-random_number, None)
    
    # 打印节点1的基本需水量
    node_1 = wn.get_node('1')
    if node_1.demand_timeseries_list:
        print(f"节点1的基本需水量: {node_1.demand_timeseries_list[0].base_value}")
    else:
        print("节点1没有需水量设置")
    
    # 保存修改后的网络
    modified_inp = './networks/Net2.inp'
    
    # 使用正确的方法保存INP文件
    wntr.network.io.write_inpfile(wn, modified_inp)

if __name__ == "__main__":
    main()
