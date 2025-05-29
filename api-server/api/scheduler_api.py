# api/scheduler_api.py
from flask import Blueprint, jsonify, request
import wntr
import os
import random
import csv
import matplotlib.pyplot as plt
import tempfile
# 如果已经有蓝图定义，使用现有的，否则创建新的
# 假设您现有的文件可能已经有一些代码和变量
water_plant_ids = ['1','8']
try:
    scheduler_routes
except NameError:
    scheduler_routes = Blueprint('scheduler_routes', __name__)

# 添加网络数据路由
@scheduler_routes.route('/network/data', methods=['GET'])
def get_network_data():
    """获取水网络拓扑图数据"""
    try:
        network_data = export_network_data()
        return jsonify({
            "success": True,
            "data": network_data
        })
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# 添加模拟路由
@scheduler_routes.route('/network/simulate', methods=['POST'])
def run_scheduler():
    """运行调度算法"""
    try:
        # 获取项目根目录路径
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 构建 Water-Scheduling 目录的绝对路径
        water_scheduling_dir = os.path.join(BASE_DIR, 'Water-Scheduling')
        print(f"Water-Scheduling 目录: {water_scheduling_dir}")
        
        # 确保目录存在
        if not os.path.exists(water_scheduling_dir):
            return jsonify({
                "success": False,
                "error": f"目录不存在: {water_scheduling_dir}"
            }), 404
        
        # 使用 subprocess 调用 cal.py 脚本，设置工作目录为 Water-Scheduling
        import subprocess
        import sys
        
        # 注意这里使用相对路径 ./src/cal.py，与您手动运行的方式一致
        result = subprocess.run(
            [sys.executable, "./src/cal.py"], 
            capture_output=True, 
            text=True,
            cwd=water_scheduling_dir  # 关键：设置工作目录为 Water-Scheduling
        )
        
        print(f"脚本退出码: {result.returncode}")
        print(f"标准输出: {result.stdout[:200]}..." if result.stdout else "无标准输出")
        print(f"错误输出: {result.stderr}" if result.stderr else "无错误输出")
        
        if result.returncode != 0:
            return jsonify({
                "success": False,
                "error": f"计算脚本执行失败: {result.stderr}"
            }), 500
        simulated_network_data = export_network_data(after_simulation=True)
        return jsonify({
            "success": True,
            "message": "模拟完成",
             "network_data": simulated_network_data  # 返回模拟后的网络数据
        })
    except Exception as e:
        import traceback
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
    inp_file_path = os.path.join(BASE_DIR,'Water-Scheduling', 'networks', 'Net2.inp')
    
    # 加载水力网络模型
    wn = wntr.network.WaterNetworkModel(inp_file_path)
    print(f"加载网络模型: {inp_file_path}")
    
    # 如果需要模拟后的数据，则运行模拟
    results = None
    time_step_index = 0  # 默认使用第一个时间步
    
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
        is_water_plant = node_id in water_plant_ids
        node_data = {
            'id': node_id,
            'node_type': node.node_type,
            'coordinates': list(node.coordinates) if node.coordinates else [0, 0],
            'is_water_plant': is_water_plant,  # 添加水厂标记
        }
        
        # 针对不同类型节点添加特定属性
        if node.node_type == 'Junction':
            # 对于模拟前的数据，添加基本需水量
            if not after_simulation:
                node_data['base_demand'] = round(float(node.base_demand),10)
                node_data['demand_unit'] = 'm^3/s'  # 单位为立方米/秒
            
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
                    head = results.node['head'].loc[results.node['head'].index[time_step_index], node_id]
                    node_data['current_head'] = round(float(head), 2)
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
            print("dsad",node_data['level'])
            # 如果是模拟后的数据，添加当前水位信息和流量信息
            if after_simulation and results is not None:
                try:
                    # 获取指定时间步的水位数据
                    #current_level = results.node['level'].loc[results.node['level'].index[time_step_index], node_id]
                    #node_data['current_level'] = round(float(current_level), 10)
                    #print("dsad",node_data['current_level'])
                    # 获取水箱的流入/流出量
                    pressure = results.node['pressure'].loc[results.node['pressure'].index[time_step_index], node_id]
                    node_data['pressure'] = round(float(pressure), 10)  # 保留两位小数
                    node_data['pressure_unit'] = 'm'  # 单位为米
                    demand = results.node['demand'].loc[results.node['demand'].index[time_step_index], node_id]
                    node_data['inflow'] = round(float(demand), 10)  # 水箱流入为负需水量
                    print(demand)
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
            print(link.diameter)
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
from io import StringIO
@scheduler_routes.route('/network/generate-random', methods=['POST'])
def generate_random_demands():
    """为所有节点生成随机需水量"""
    try:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        inp_file_path = os.path.join(BASE_DIR, 'Water-Scheduling', 'networks', 'Net2.inp')
        
        # 加载水力网络模型
        wn = wntr.network.WaterNetworkModel(inp_file_path)
        
        # 为每个节点生成随机需水量
        for node_id, node in wn.nodes():
            if node.node_type == 'Junction':
                # 生成0.001到0.01之间的随机需水量(单位:立方米/秒)
                random_demand = round(random.uniform(0, 0.01), 10)
                print(random_demand)
                node.demand_timeseries_list[0].base_value = random_demand
        
        # 保存修改后的模型
        wntr.network.io.write_inpfile(wn,inp_file_path)
        # 返回更新后的网络数据
        network_data = export_network_data()
        
        return jsonify({
            "success": True,
            "message": "已成功生成随机需水量数据",
            "data": network_data
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"生成随机需水量时出错: {str(e)}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_trace
        }), 500

# 2. 导入CSV文件更新需水量
@scheduler_routes.route('/network/import-demands', methods=['POST'])
def import_demands():
    """从CSV文件导入需水量数据"""
    try:
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "error": "未上传文件"
            }), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "未选择文件"
            }), 400
            
        if not file.filename.endswith('.csv'):
            return jsonify({
                "success": False,
                "error": "请上传CSV文件"
            }), 400
        
        # 读取CSV文件内容
        file_content = file.read().decode('utf-8')
        csv_data = list(csv.reader(StringIO(file_content)))
        
        # 验证CSV格式
        if len(csv_data) == 0:
            return jsonify({
                "success": False,
                "error": "CSV文件为空"
            }), 400
            
        # 加载水力网络模型
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        inp_file_path = os.path.join(BASE_DIR, 'Water-Scheduling', 'networks', 'Net2.inp')
        wn = wntr.network.WaterNetworkModel(inp_file_path)
        
        # 更新节点需水量
        updated_nodes = []
        errors = []
        
        for row_index, row in enumerate(csv_data, 1):
            # 检查行格式
            if len(row) < 2:
                errors.append(f"第{row_index}行格式错误: 列数不足")
                continue
                
            node_id = row[0].strip()
            
            # 检查需水量是否为数字
            try:
                demand = float(row[1].strip())
            except ValueError:
                errors.append(f"第{row_index}行格式错误: '{row[1]}' 不是有效数字")
                continue
            
            # 检查节点是否存在且为Junction类型
            if node_id not in wn.node_name_list:
                errors.append(f"节点 '{node_id}' 不存在")
                continue
                
            if wn.nodes[node_id].node_type != 'Junction':
                errors.append(f"节点 '{node_id}' 不是Junction类型，无法设置需水量")
                continue
            
            # 更新节点需水量
            wn.nodes[node_id].demand_timeseries_list[0].base_value = demand
            updated_nodes.append(node_id)
        
        # 检查是否有任何节点被更新
        if not updated_nodes:
            return jsonify({
                "success": False,
                "error": "没有任何节点被更新" + (f"，错误: {'; '.join(errors)}" if errors else "")
            }), 400
        
        # 保存修改后的模型
        wntr.network.io.write_inpfile(wn, inp_file_path)
        
        # 返回更新后的网络数据
        network_data = export_network_data()
        
        # 如果有错误但也有成功更新的节点，返回部分成功信息
        if errors:
            return jsonify({
                "success": True,
                "message": f"已更新{len(updated_nodes)}个节点，但有{len(errors)}个错误",
                "errors": errors,
                "updated_nodes": updated_nodes,
                "data": network_data
            })
        
        # 全部成功
        return jsonify({
            "success": True,
            "message": f"已成功更新 {len(updated_nodes)} 个节点的需水量",
            "updated_nodes": updated_nodes,
            "data": network_data
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"导入需水量数据时出错: {str(e)}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_trace
        }), 500

# 3. 修改单个节点需水量
@scheduler_routes.route('/network/update-demand', methods=['POST'])
def update_node_demand():
    """更新单个节点的需水量"""
    try:
        data = request.json
        if not data or 'node_id' not in data or 'demand' not in data:
            return jsonify({
                "success": False,
                "error": "请提供节点ID和需水量"
            }), 400
            
        node_id = data['node_id']
        demand = float(data['demand'])
        
        # 加载水力网络模型
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        inp_file_path = os.path.join(BASE_DIR, 'Water-Scheduling', 'networks', 'Net2.inp')
        wn = wntr.network.WaterNetworkModel(inp_file_path)
        
        # 检查节点是否存在且是Junction类型
        if node_id not in wn.node_name_list:
            return jsonify({
                "success": False,
                "error": f"节点 {node_id} 不存在"
            }), 404
            
        if wn.nodes[node_id].node_type != 'Junction':
            return jsonify({
                "success": False,
                "error": f"节点 {node_id} 不是Junction类型，无法设置需水量"
            }), 400
            
        # 更新需水量
        wn.nodes[node_id].demand_timeseries_list[0].base_value = demand
        
        # 保存修改后的模型
        wntr.network.io.write_inpfile(wn,inp_file_path)
        
        # 返回更新后的网络数据
        network_data = export_network_data()
        
        return jsonify({
            "success": True,
            "message": f"已成功更新节点 {node_id} 的需水量为 {demand}",
            "data": network_data
        })
    except ValueError:
        return jsonify({
            "success": False,
            "error": "需水量必须是有效的数值"
        }), 400
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"更新节点需水量时出错: {str(e)}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_trace
        }), 500
    
@scheduler_routes.route('/network/heatmap', methods=['POST'])
def generate_heatmap():
    """生成网络压力或流量的热力图，并显示节点ID"""
    try:
        # 导入必要的库并设置 matplotlib 为非交互模式
        import matplotlib
        matplotlib.use('Agg')  # 设置为非交互式后端
        
        # 尝试使用不同的方式设置字体
        try:
            # 方法1：使用系统可用字体
            import matplotlib.font_manager as fm
            font_path = fm.findfont(fm.FontProperties(family=['sans-serif']))
            prop = fm.FontProperties(fname=font_path)
            matplotlib.rcParams['font.family'] = prop.get_name()
        except:
            # 方法2：如果上面失败，尝试使用基本设置
            matplotlib.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Bitstream Vera Sans']
        
        import matplotlib.pyplot as plt
        plt.ioff()  # 关闭交互模式
        from flask import send_file
        from io import BytesIO
        
        # 获取请求中的网络数据
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        inp_file_path = os.path.join(BASE_DIR, 'Water-Scheduling', 'networks', 'Net2.inp')
        
        # 使用WNTR加载网络
        wn = wntr.network.WaterNetworkModel(inp_file_path)
        
        # 运行水力模拟
        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim()
        
        # 获取压力结果 - 0小时的压力（第一个时间步）
        pressure = results.node['pressure'].iloc[0]
        
        # 创建图形
        plt.figure(figsize=(8, 7))
        
        # 使用WNTR的内置函数绘制热力图，但不设置中文标题
        ax = wntr.graphics.plot_network(
            wn, 
            node_attribute=pressure,
            node_size=50,
            title='Pressure Heatmap (unit: m)',  # 使用英文避免乱码
            node_cmap='jet',
            link_width=1.5,
            link_alpha=0.7,
            add_colorbar=True
        )
        
        # 添加节点ID标签
        for node_name, node in wn.nodes():
            x, y = node.coordinates
            ax.text(x + 0.5, y + 0.5, node_name, fontsize=7, ha='left', va='bottom', 
                    color='blue', bbox=dict(facecolor='white', alpha=0.5, pad=0.2, edgecolor='none'))
        
        # 调整布局
        plt.tight_layout()
        
        # 将图像保存到内存中
        img_buffer = BytesIO()
        plt.savefig(img_buffer, format='png', dpi=200, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close('all')
        
        # 直接返回图像数据
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=False,
            download_name='network_heatmap.png'
        )
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print("Error in generate_heatmap:", error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_trace
        }), 500
