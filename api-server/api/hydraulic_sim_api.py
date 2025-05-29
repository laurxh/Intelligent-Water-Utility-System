# api/hydraulic_sim_api.py
from flask import Blueprint, jsonify, request, current_app
import os
import wntr
import traceback
from werkzeug.utils import secure_filename
import time
hydraulic_bp = Blueprint('hydraulic', __name__, url_prefix='/api/hydraulic')

# 全局变量存储当前加载的INP文件路径
CURRENT_INP_FILE = None
CURRENT_INP_FILENAME = None

@hydraulic_bp.route('/upload-inp', methods=['POST'])
def upload_inp_file():
    """上传INP文件并固定命名为Net2.inp"""
    global CURRENT_INP_FILE, CURRENT_INP_FILENAME
    
    try:
        # 检查是否有文件被上传
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "没有文件被上传"
            }), 400
            
        file = request.files['file']
        
        # 检查文件名是否为空
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "没有选择文件"
            }), 400
            
        # 检查文件扩展名
        if not file.filename.lower().endswith('.inp'):
            return jsonify({
                "success": False,
                "error": "只接受.inp文件"
            }), 400
            
        # 保存文件，固定命名为Net2.inp
        original_filename = secure_filename(file.filename)
        fixed_filename = "Net2.inp"
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_folder = os.path.join(base_dir, 'Water-Hydraulic-Simulation', 'Networks')
        
        # 确保上传文件夹存在
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file_path = os.path.join(upload_folder, fixed_filename)
        file.save(file_path)
        
        # 尝试加载文件验证其有效性
        try:
            wn = wntr.network.WaterNetworkModel(file_path)
            # 文件有效，更新全局变量
            CURRENT_INP_FILE = file_path
            CURRENT_INP_FILENAME = fixed_filename
        except Exception as e:
            # 文件无效，删除并返回错误
            os.remove(file_path)
            return jsonify({
                "success": False,
                "error": f"无效的INP文件: {str(e)}"
            }), 400
        
        return jsonify({
            "success": True,
            "message": "文件上传成功并保存为Net2.inp",
            "filename": fixed_filename,
            "original_filename": original_filename
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@hydraulic_bp.route('/network-data', methods=['GET'])
def get_network_data():
    """获取水网络拓扑图数据"""
    global CURRENT_INP_FILE, CURRENT_INP_FILENAME
    
    try:
        if not CURRENT_INP_FILE or not os.path.exists(CURRENT_INP_FILE):
            return jsonify({
                "success": False,
                "error": "未加载INP文件，请先上传"
            }), 400
            
        #network_data = export_network_data(CURRENT_INP_FILE)
        network_data=export_network_data(after_simulation=False)
        return jsonify({
            "success": True,
            "data": network_data,
            "file_name": CURRENT_INP_FILENAME
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@hydraulic_bp.route('/simulate', methods=['POST'])
def run_simulation():
    """运行水力模拟"""
    global CURRENT_INP_FILE, CURRENT_INP_FILENAME
    
    try:
        if not CURRENT_INP_FILE or not os.path.exists(CURRENT_INP_FILE):
            return jsonify({
                "success": False,
                "error": "未加载INP文件，请先上传"
            }), 400
            
        simulated_network_data = export_network_data(after_simulation=True)
        return jsonify({
            "success": True,
            "message": "模拟完成",
            "network_data": simulated_network_data,
            "file_name": CURRENT_INP_FILENAME
        })
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"发生异常: {str(e)}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_trace
        }), 500

def export_network_data(after_simulation=False, hour=0):
    """
    导出管网数据，用于前端绘制管网拓扑图
    
    参数:
        after_simulation (bool): 是否导出模拟后的管网数据，默认为False表示导出模拟前的原始数据
        hour (int): 要获取的模拟时间（小时），默认为0表示模拟开始时刻
    
    返回:
        dict: 包含nodes和links的字典
            nodes: 所有节点的列表，每个节点包含id、坐标、类型、需求等信息
            links: 所有连接的列表，每个连接包含id、起点id、终点id、类型等信息
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 构建inp文件的绝对路径
    networks_dir = os.path.join(BASE_DIR, 'Water-Hydraulic-Simulation', 'networks')
    inp_files = [f for f in os.listdir(networks_dir) if f.endswith('.inp')]

    if not inp_files:
        raise FileNotFoundError(f"在 {networks_dir} 目录下没有找到.inp文件")

    if len(inp_files) > 1:
        print(f"警告: 在目录下发现多个.inp文件: {inp_files}，将使用第一个文件")

    # 使用找到的第一个.inp文件
    inp_file_name = inp_files[0]
    inp_file_path = os.path.join(networks_dir, inp_file_name)

    print(f"使用的inp文件: {inp_file_path}")
    
    # 加载水力网络模型
    wn = wntr.network.WaterNetworkModel(inp_file_path)
    print(f"加载网络模型: {inp_file_path}")
    
    # 如果需要模拟后的数据，则运行模拟
    results = None
    time_step_index = 0  # 默认使用第一个时间步（0小时）
    
    if after_simulation:
        try:
            print("开始运行EPANET模拟...")
            # 使用EPANET模拟器运行模拟
            sim = wntr.sim.EpanetSimulator(wn)
            results = sim.run_sim()
            print("EPANET模拟完成")
            
            # 获取所有时间步
            time_steps = results.node['pressure'].index
            print(f"模拟生成了 {len(time_steps)} 个时间步")
            
            # 如果指定了hour=0，直接使用第一个时间步
            if hour == 0:
                time_step_index = 0
                current_time = time_steps[time_step_index]
                print(f"使用第一个时间步（模拟开始时刻）: 索引={time_step_index}, 实际时间={current_time}秒")
            else:
                # 查找对应于指定小时的时间步
                target_time = hour * 3600  # 转换为秒
                
                # 查找最接近目标时间的时间步
                time_differences = [abs(t - target_time) for t in time_steps]
                time_step_index = time_differences.index(min(time_differences))
                
                current_time = time_steps[time_step_index]
                print(f"找到最接近 {hour} 小时的时间步: 索引={time_step_index}, 实际时间={current_time}秒")
            
        except Exception as e:
            print(f"运行模拟时出错: {str(e)}")
            # 如果模拟失败，返回原始数据
            after_simulation = False
    
    nodes = []
    links = []
    
    # 处理所有节点（junctions, reservoirs, tanks）
    for node_id, node in wn.nodes():
        node_data = {
            'id': node_id,
            'node_type': node.node_type,
            'coordinates': list(node.coordinates) if node.coordinates else [0, 0],
        }
        
        # 针对不同类型节点添加特定属性
        if node.node_type == 'Junction':
            # 对于模拟前的数据，添加基本需水量
            if not after_simulation:
                node_data['base_demand'] = round(float(node.base_demand),10)
                node_data['demand_unit'] = 'm^3/s'  # 单位为立方米/秒
            
            node_data['elevation'] = node.elevation
            
            # 如果是模拟后的数据，添加压力和实际水量信息
            if after_simulation and results is not None:
                try:
                    # 获取指定时间步的压力数据
                    pressure = results.node['pressure'].loc[results.node['pressure'].index[time_step_index], node_id]
                    node_data['pressure'] = round(float(pressure), 10)  # 保留两位小数
                    node_data['pressure_unit'] = 'm'  # 单位为米
                    
                    # 获取指定时间步的实际需水量数据
                    actual_demand = results.node['demand'].loc[results.node['demand'].index[time_step_index], node_id]
                    node_data['actual_demand'] = round(float(actual_demand), 10)  # 保留三位小数
                except Exception as e:
                    print(f"获取节点 {node_id} 压力/需水量数据时出错: {str(e)}")
                    node_data['pressure'] = None
                    node_data['actual_demand'] = None
        
        elif node.node_type == 'Reservoir':
            node_data['head'] = node.head
            
            # 如果是模拟后的数据，可以添加其他相关信息
            if after_simulation and results is not None:
                try:
                    # 水库的压力头
                    pressure = results.node['pressure'].loc[results.node['pressure'].index[time_step_index], node_id]
                    node_data['pressure'] = round(float(pressure), 10)  # 保留两位小数
                    # 水库的出水量
                    demand = results.node['demand'].loc[results.node['demand'].index[time_step_index], node_id]
                    node_data['outflow'] = round(float(demand), 10)  # 水库出水为负需水量
                except Exception as e:
                    print(f"获取水库 {node_id} 数据时出错: {str(e)}")
        
        elif node.node_type == 'Tank':
            # 模拟前的水箱初始水位
            node_data['level'] = node.level
            node_data['max_level'] = node.max_level
            node_data['min_level'] = node.min_level
            
            # 如果是模拟后的数据，添加当前水位信息和流量信息
            if after_simulation and results is not None:
                try:
                    # 获取指定时间步的水位数据
                    pressure = results.node['pressure'].loc[results.node['pressure'].index[time_step_index], node_id]
                    node_data['pressure'] = round(float(pressure), 10)  # 保留两位小数
                    node_data['pressure_unit'] = 'm'  # 单位为米
                    current_level = results.node['pressure'].loc[results.node['pressure'].index[time_step_index], node_id]
                    node_data['current_level'] = round(float(current_level), 2)
                    
                    # 获取水箱的流入/流出量
                    demand = results.node['demand'].loc[results.node['demand'].index[time_step_index], node_id]
                    node_data['inflow'] = round(float(demand), 10)  # 水箱流入为负需水量
                except Exception as e:
                    print(f"获取水箱 {node_id} 水位/流量数据时出错: {str(e)}")
                    node_data['current_level'] = None
                    node_data['inflow'] = None
        
        nodes.append(node_data)
    
    # 处理所有连接（管道/阀门/泵）
    for link_id, link in wn.links():
        # 确保source和target是字符串ID而不是对象
        link_data = {
            'id': link_id,
            'link_type': link.link_type,
            'source': link.start_node_name,
            'target': link.end_node_name,
        }
        
        # 针对不同类型连接添加特定属性
        if link.link_type == 'Pipe':
            link_data['length'] = link.length
            link_data['diameter'] = link.diameter
            link_data['roughness'] = link.roughness
            
            # 如果是模拟后的数据，添加流量信息
            if after_simulation and results is not None:
                try:
                    # 获取指定时间步的流量数据
                    flow = results.link['flowrate'].loc[results.link['flowrate'].index[time_step_index], link_id]
                    link_data['flow'] = round(float(flow), 10)  # 保留三位小数
                except Exception as e:
                    print(f"获取管道 {link_id} 流量数据时出错: {str(e)}")
                    link_data['flow'] = None
        
        elif link.link_type == 'Pump':
            # 对于模拟前的数据，添加初始开关状态
            link_data['initial_status'] = link.initial_status
            
            # 如果是模拟后的数据，添加当前开关状态和流量
            if after_simulation and results is not None:
                try:
                    # 获取指定时间步的状态和流量数据
                    status = results.link['status'].loc[results.link['status'].index[time_step_index], link_id]
                    flow = results.link['flowrate'].loc[results.link['flowrate'].index[time_step_index], link_id]
                    link_data['current_status'] = "Open" if float(status) > 0 else "Closed"
                    link_data['flow'] = round(float(flow), 10)  # 保留三位小数
                    link_data['flow_unit'] = 'm^3/s'  # 单位为立方米/秒
                except Exception as e:
                    print(f"获取泵 {link_id} 状态/流量数据时出错: {str(e)}")
                    link_data['current_status'] = None
                    link_data['flow'] = None
        
        elif link.link_type == 'Valve':
            link_data['diameter'] = link.diameter
            # 对于模拟前的数据，添加初始开关状态
            link_data['initial_status'] = link.initial_status
            
            # 如果是模拟后的数据，添加当前开关状态和流量
            if after_simulation and results is not None:
                try:
                    # 获取指定时间步的状态和流量数据
                    status = results.link['status'].loc[results.link['status'].index[time_step_index], link_id]
                    flow = results.link['flowrate'].loc[results.link['flowrate'].index[time_step_index], link_id]
                    link_data['current_status'] = "Open" if float(status) > 0 else "Closed"
                    link_data['flow'] = round(float(flow), 10)  # 保留三位小数
                    link_data['flow_unit'] = 'm^3/s'  # 单位为立方米/秒
                except Exception as e:
                    print(f"获取阀门 {link_id} 状态/流量数据时出错: {str(e)}")
                    link_data['current_status'] = None
                    link_data['flow'] = None
        
        links.append(link_data)
    
    # 归一化节点坐标到0-1范围，便于前端显示
    # 找出坐标的最大值和最小值
    min_x = min(node['coordinates'][0] for node in nodes)
    max_x = max(node['coordinates'][0] for node in nodes)
    min_y = min(node['coordinates'][1] for node in nodes)
    max_y = max(node['coordinates'][1] for node in nodes)
    
    # 计算坐标范围
    x_range = max_x - min_x
    y_range = max_y - min_y
    
    # 防止除以零
    if x_range == 0:
        x_range = 1
    if y_range == 0:
        y_range = 1
        
    print(f"坐标范围: x=({min_x}, {max_x}), y=({min_y}, {max_y})")
    
    # 归一化所有节点坐标
    for node in nodes:
        node['coordinates'][0] = (node['coordinates'][0] - min_x) / x_range
        node['coordinates'][1] = (node['coordinates'][1] - min_y) / y_range
    
    # 打印一些调试信息
    print(f"导出节点数量: {len(nodes)}, 连接数量: {len(links)}")
    
    return {'nodes': nodes, 'links': links}
@hydraulic_bp.route('/generate-coverage-map', methods=['POST'])
def generate_coverage_map():
    """生成不同布置点数的覆盖率图"""
    try:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        networks_dir = os.path.join(BASE_DIR, 'Water-Hydraulic-Simulation', 'networks')
        inp_files = [f for f in os.listdir(networks_dir) if f.endswith('.inp')]

        if not inp_files:
            raise FileNotFoundError(f"在 {networks_dir} 目录下没有找到.inp文件")

        if len(inp_files) > 1:
            print(f"警告: 在目录下发现多个.inp文件: {inp_files}，将使用第一个文件")

        # 使用找到的第一个.inp文件
        inp_file_name = inp_files[0]
        inp_file_path = os.path.join(networks_dir, inp_file_name)

        # 加载水力网络模型
        wn = wntr.network.WaterNetworkModel(inp_file_path)
        
        # 构建图结构
        nodes = []
        for node_id, node in wn.nodes():
            print(node_id)
            nodes.append(node_id)
        G = {node: [] for node in nodes}
        for link_id, link in wn.links():
            start_node = link.start_node_name
            end_node = link.end_node_name
            # 使用链接长度作为权重，如果没有长度，则使用默认值1
            weight = link.length if hasattr(link, 'length') and link.length else 1
            
            # 添加双向边
            G[start_node].append((end_node, weight))
            G[end_node].append((start_node, weight))
        
        # 计算不同布置点数的覆盖率
        max_points = len(nodes)
        coverage_data = {}
        
        # 初始化已选择的点
        exist = {node: False for node in nodes}
        selected_nodes = []
        
        # 选择第一个点（可以根据需要选择特定的起始点）
        start_node = nodes[0]
        exist[start_node] = True
        selected_nodes.append(start_node)
        coverage_data["1"] = calculate_coverage(nodes, G, exist)
        
        # 迭代选择剩余的点并计算覆盖率
        for i in range(2, max_points + 1):
            next_node = work(nodes, G, exist)
            coverage_data[str(i)] = calculate_coverage(nodes, G, exist)
        print(coverage_data)
        return jsonify({
            "success": True,
            "message": "覆盖率图生成成功",
            "coverage_data": coverage_data,
        })
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
import heapq
def work(nodes, G, exist):
        """
        寻找未被选择点中到已选择点最短距离最大的点,返回该点标识符
        """
        dist = {node: 1e9 for node in nodes}
        pq = []
        visited = {node: False for node in nodes}
        
        # 初始化已选择的点
        for node in nodes:
            if exist[node]:
                dist[node] = 0
                heapq.heappush(pq, (dist[node], node))
        
        # Dijkstra算法
        while pq:
            _, u = heapq.heappop(pq)
            if visited[u]:
                continue
            visited[u] = True
            
            for v, w in G[u]:
                if dist[v] > dist[u] + w:
                    dist[v] = dist[u] + w
                    heapq.heappush(pq, (dist[v], v))
        
        # 找到未选择点中距离最大的点
        max_dist = -1
        max_node = None
        for node in nodes:
            if exist[node]:
                continue
            if dist[node] > max_dist:
                max_dist = dist[node]
                max_node = node
        
        exist[max_node] = True
        return max_node
def calculate_coverage(nodes, G, exist):
        """
        计算覆盖率：(有监测点或相邻有监测点的节点数) / 总节点数
        """
        dist = {node: 1e9 for node in nodes}
        pq = []
        visited = {node: False for node in nodes}
        
        # 初始化已选择的点
        for node in nodes:
            if exist[node]:
                dist[node] = 0
                heapq.heappush(pq, (dist[node], node))
        
        # Dijkstra算法
        while pq:
            _, u = heapq.heappop(pq)
            if visited[u]:
                continue
            visited[u] = True
            
            for v, w in G[u]:
                if dist[v] > dist[u] + w:
                    dist[v] = dist[u] + w
                    heapq.heappush(pq, (dist[v], v))
        
        # 找到未选择点中距离最大的点
        max_dist = 0
        max_node = None
        for node in nodes:
            if exist[node]:
                continue
            if dist[node] > max_dist:
                max_dist = dist[node]
                max_node = node
        
        return max_dist
@hydraulic_bp.route('/generate-plan', methods=['POST'])
def generate_plan():
    """根据指定的布点数生成监测方案"""
    try:
        # 获取请求中的布点数和网络数据
        data = request.get_json()
        point_count = data.get('point_count', 0)
        network_data = data.get('network_data', None)  # 获取前端传来的网络数据
        
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        networks_dir = os.path.join(BASE_DIR, 'Water-Hydraulic-Simulation', 'networks')
        inp_files = [f for f in os.listdir(networks_dir) if f.endswith('.inp')]

        if not inp_files:
            raise FileNotFoundError(f"在 {networks_dir} 目录下没有找到.inp文件")

        # 使用找到的第一个.inp文件
        inp_file_name = inp_files[0]
        inp_file_path = os.path.join(networks_dir, inp_file_name)

        # 加载水力网络模型
        wn = wntr.network.WaterNetworkModel(inp_file_path)
        
        # 获取所有节点
        nodes = []
        node_coords = {}  # 存储节点坐标
        for node_id, node in wn.nodes():
            nodes.append(node_id)
            # 保存节点坐标
            node_coords[node_id] = list(node.coordinates) if node.coordinates else [0, 0]
        
        # 验证布点数是否有效
        if point_count <= 0 or point_count > len(nodes):
            return jsonify({
                "success": False,
                "error": f"布点数必须大于0且不超过节点总数({len(nodes)})"
            }), 400
            
        # 构建图结构
        G = {node: [] for node in nodes}
        links_data = []  # 存储连接信息
        for link_id, link in wn.links():
            start_node = link.start_node_name
            end_node = link.end_node_name
            weight = link.length if hasattr(link, 'length') and link.length else 1
            
            # 添加双向边
            G[start_node].append((end_node, weight))
            G[end_node].append((start_node, weight))
            
            # 保存连接信息
            links_data.append({
                'id': link_id,
                'source': start_node,
                'target': end_node
            })
        
        # 初始化已选择的点
        exist = {node: False for node in nodes}
        selected_nodes = []
        
        # 选择第一个点
        start_node = nodes[0]
        exist[start_node] = True
        selected_nodes.append(start_node)
        
        # 迭代选择剩余的点
        for i in range(1, point_count):
            next_node = work(nodes, G, exist)
            if next_node:
                exist[next_node] = True
                selected_nodes.append(next_node)
        
        # 计算覆盖率
        max_distance = calculate_coverage(nodes, G, exist)
        
        # 构建方案数据
        plan_data = {
            "plan_id": f"plan_{point_count}_{int(time.time())}",
            'max_distance': max_distance,  # 最远距离，单位：m
            "sensor_count": len(selected_nodes),
            "sensors": selected_nodes,  # 简化为直接返回节点ID列表
            "detailed_sensors": []
        }
        
        # 添加传感器详细信息
        for node_id in selected_nodes:
            node_type = wn.get_node(node_id).node_type
            # 计算每个传感器覆盖的区域（这里简化为与该节点直接相连的节点）
            coverage_area = [neighbor for neighbor, _ in G[node_id]]
            
            sensor_data = {
                "node_id": node_id,
                "node_type": node_type,
                "coverage_area": coverage_area
            }
            plan_data["detailed_sensors"].append(sensor_data)
        
        # 添加网络拓扑数据，用于在弹窗中绘制
        nodes_data = []
        for node_id in nodes:
            # 从前端传来的数据中获取坐标，如果没有则使用后端计算的坐标
            x, y = node_coords[node_id]
            
            # 如果前端传来了网络数据，优先使用前端的坐标
            if network_data and 'nodes' in network_data:
                for node in network_data['nodes']:
                    if node['id'] == node_id and 'x' in node and 'y' in node:
                        x, y = node['x'], node['y']
                        break
            
            nodes_data.append({
                'id': node_id,
                'x': x,
                'y': y,
                'isSensor': node_id in selected_nodes
            })
        
        # 添加网络拓扑数据到返回结果
        plan_data["network_topology"] = {
            "nodes": nodes_data,
            "links": links_data
        }
        
        return jsonify({
            "success": True,
            "message": "方案生成成功",
            "plan_data": plan_data
        })
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def shortest_path_distance(G, start, end):
    """使用Dijkstra算法计算两点间的最短路径距离"""
    dist = {node: float('inf') for node in G}
    dist[start] = 0
    pq = [(0, start)]
    visited = set()
    
    while pq:
        d, node = heapq.heappop(pq)
        
        if node in visited:
            continue
            
        visited.add(node)
        
        if node == end:
            return d
            
        for neighbor, weight in G[node]:
            if neighbor not in visited:
                new_dist = d + weight
                if new_dist < dist[neighbor]:
                    dist[neighbor] = new_dist
                    heapq.heappush(pq, (new_dist, neighbor))
    
    return float('inf')
