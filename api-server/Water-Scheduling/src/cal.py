import wntr
import copy
import math
import random
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error
import matplotlib.pyplot as plt
import joblib
import os
import pandas as pd
import ast
import re
water_plant_ids = []
# 添加水厂编号
lim = 40

# 加载网络
wn = wntr.network.WaterNetworkModel('./networks/Net2.inp')

def add_plant_id(plant_id):
    water_plant_ids.append(plant_id)
def predict_new_data(new_data, model_path='model/final_model.keras',
                    scaler_X_path='model/scaler_X.pkl', 
                    scaler_y_path='model/scaler_y.pkl'):
    """
    使用训练好的模型预测新数据
    
    参数:
    new_data: 需要预测的新数据，形状为[n_samples, input_dim]
    model_path: 模型文件路径
    scaler_X_path: 输入标准化器路径
    scaler_y_path: 输出标准化器路径
    
    返回:
    预测结果，形状为[n_samples, 2]
    """
    # 加载模型和标准化器
    model = keras.models.load_model(model_path)
    scaler_X = joblib.load(scaler_X_path)
    scaler_y = joblib.load(scaler_y_path)
    
    # 预处理输入数据
    scaled_input = scaler_X.transform(new_data)
    
    # 获取预测结果
    scaled_output = model.predict(scaled_input)
    
    # 反向转换输出
    predictions = scaler_y.inverse_transform(scaled_output)
    return predictions[0]
def main():
    # 添加水厂编号
    add_plant_id('1')  # 在WNTR中，节点ID通常是字符串
    add_plant_id('8')
    new_data=[]
    for node_id, node in wn.nodes():
        if node.node_type == 'Junction':
            # 生成0.001到0.01之间的随机需水量(单位:立方米/秒)
            #print(random_demand)
            new_data.append(node.base_demand)
    new_data = np.array(new_data).reshape(1, -1)
    # 获取预测结果
    predictions = predict_new_data(new_data)
    print(predictions)
    # 修改节点的基本需水量
    for i in range(0, 2):
        # 在WNTR中修改节点需水量
        node = wn.get_node(water_plant_ids[i])
        
        # 清除现有的需水模式
        node.demand_timeseries_list.clear()
        
        # 将NumPy数组元素转换为Python浮点数
        demand_value = float(-predictions[i])
        
        # 添加一个新的基本需水量，不指定模式
        node.add_demand(demand_value, None)
        print(f"节点 {water_plant_ids[i]} 的需水量设置为: {demand_value}")

    
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
