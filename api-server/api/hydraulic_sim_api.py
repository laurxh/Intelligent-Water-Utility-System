# api/hydraulic_sim_api.py
from flask import Blueprint, jsonify, request, current_app
import os
import wntr
import traceback
from werkzeug.utils import secure_filename

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

def export_network_data(after_simulation=False):
    """
    导出管网数据，用于前端绘制管网拓扑图
    
    参数:
        inp_file_path (str): INP文件路径
        after_simulation (bool): 是否导出模拟后的管网数据，默认为False表示导出模拟前的原始数据
    
    返回:
        dict: 包含nodes和links的字典
            nodes: 所有节点的列表，每个节点包含id、坐标、类型、需求等信息
            links: 所有连接的列表，每个连接包含id、起点id、终点id、类型等信息
    """
    # 加载水力网络模型
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 构建inp文件的绝对路径
    inp_file_path = os.path.join(BASE_DIR,'Water-Hydraulic-Simulation', 'networks', 'Net2.inp')
    wn = wntr.network.WaterNetworkModel(inp_file_path)
    print(f"加载网络模型: {inp_file_path}")
    
    # 如果需要模拟后的数据，则运行模拟
    results = None
    if after_simulation:
        try:
            print("开始运行EPANET模拟...")
            # 使用EPANET模拟器运行模拟
            sim = wntr.sim.EpanetSimulator(wn)
            results = sim.run_sim()
            print("EPANET模拟完成")
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
            'x': node.coordinates[0] if node.coordinates else 0,
            'y': node.coordinates[1] if node.coordinates else 0,
        }
        
        # 针对不同类型节点添加特定属性
        if node.node_type == 'Junction':
            # 对于模拟前的数据，添加基本需水量
            node_data['base_demand'] = node.base_demand
            node_data['demand_unit'] = 'm^3/s'  # 单位为立方米/秒
            
            node_data['elevation'] = node.elevation
            
            # 如果是模拟后的数据，添加压力和实际水量信息
            if after_simulation and results is not None:
                try:
                    # 获取最后一个时间步的压力数据
                    pressure = results.node['pressure'].loc[results.node['pressure'].index[-1], node_id]
                    node_data['pressure'] = round(float(pressure), 10)  # 保留两位小数
                    node_data['pressure_unit'] = 'm'  # 单位为米
                    
                    # 获取最后一个时间步的实际需水量数据
                    actual_demand = results.node['demand'].loc[results.node['demand'].index[-1], node_id]
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
                    head = results.node['head'].loc[results.node['head'].index[-1], node_id]
                    node_data['current_head'] = round(float(head), 2)
                    # 水库的出水量
                    demand = results.node['demand'].loc[results.node['demand'].index[-1], node_id]
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
                    # 获取最后一个时间步的水位数据
                    # 获取水箱的流入/流出量
                    demand = results.node['demand'].loc[results.node['demand'].index[-1], node_id]
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
                    # 获取最后一个时间步的流量数据
                    flow = results.link['flowrate'].loc[results.link['flowrate'].index[-1], link_id]
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
                    # 获取最后一个时间步的状态和流量数据
                    status = results.link['status'].loc[results.link['status'].index[-1], link_id]
                    flow = results.link['flowrate'].loc[results.link['flowrate'].index[-1], link_id]
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
                    # 获取最后一个时间步的状态和流量数据
                    status = results.link['status'].loc[results.link['status'].index[-1], link_id]
                    flow = results.link['flowrate'].loc[results.link['flowrate'].index[-1], link_id]
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
    min_x = min(node['x'] for node in nodes)
    max_x = max(node['x'] for node in nodes)
    min_y = min(node['y'] for node in nodes)
    max_y = max(node['y'] for node in nodes)
    
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
        node['x'] = (node['x'] - min_x) / x_range
        node['y'] = (node['y'] - min_y) / y_range
    
    print(f"导出节点数量: {len(nodes)}, 连接数量: {len(links)}")
    
    return {'nodes': nodes, 'links': links}
