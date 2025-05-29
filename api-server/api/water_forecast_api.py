from flask import Blueprint, request, jsonify
import os
import pandas as pd
from datetime import datetime
import uuid
import shutil
import logging
from flask import send_file
import subprocess
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import io
import base64
from flask import jsonify
matplotlib.use('Agg')
# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

file_upload_routes = Blueprint('file_upload', __name__)

# 定义各类文件的存储路径
STORAGE_PATHS = {
    'water_forecast': 'Water-Forecast-Master/data/preprocessed/all',
    'smart_scheduling': 'smart-scheduling/data',
    'hydraulic_sim': 'hydraulic-simulation/data'
}

@file_upload_routes.route('/upload', methods=['POST'])
def upload_file():
    """处理CSV文件上传并保存到指定目录，确保每个模块目录下只有一个CSV文件"""
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "没有上传文件"}), 400
        
        file = request.files['file']
        
        # 检查文件是否为空
        if file.filename == '':
            return jsonify({"success": False, "error": "未选择文件"}), 400
        
        # 检查文件类型
        if not file.filename.endswith('.csv'):
            return jsonify({"success": False, "error": "只支持CSV文件格式"}), 400
        
        # 获取文件应该保存的目标模块
        module_type = request.form.get('module_type', 'water_forecast')
        if module_type not in STORAGE_PATHS:
            return jsonify({"success": False, "error": f"不支持的模块类型: {module_type}"}), 400
        
        # 构建保存路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_dir = os.path.join(base_dir, STORAGE_PATHS[module_type])
        
        # 确保目录存在
        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        
        # 删除目录中所有现有的CSV文件
        for existing_file in os.listdir(save_dir):
            if existing_file.endswith('.csv'):
                try:
                    os.remove(os.path.join(save_dir, existing_file))
                    logger.info(f"已删除旧文件: {existing_file}")
                except Exception as e:
                    logger.warning(f"删除旧文件 {existing_file} 失败: {str(e)}")
        
        # 使用固定文件名，确保每个模块只有一个CSV文件
        fixed_filename = file.filename
        final_file_path = os.path.join(save_dir, fixed_filename)
        
        # 先保存到临时文件
        temp_file_path = os.path.join(save_dir, f"temp_{fixed_filename}")
        file.save(temp_file_path)
        
        # 验证CSV文件格式
        try:
            df = pd.read_csv(temp_file_path)
            # 这里可以添加更多的验证逻辑
        except Exception as e:
            # 如果CSV格式有问题，删除文件并返回错误
            os.remove(temp_file_path)
            return jsonify({"success": False, "error": f"CSV文件格式错误: {str(e)}"}), 400
        
        # 移动文件
        shutil.move(temp_file_path, final_file_path)
        
        # 记录文件保存路径
        logger.info(f"文件已保存到: {final_file_path}")
        
        # 返回相对路径，方便前端请求
        relative_path = STORAGE_PATHS[module_type] + "/" + fixed_filename
        
        return jsonify({
            "success": True, 
            "message": "文件上传成功",
            "file_path": relative_path,
            "file_name": fixed_filename,
            "original_name": file.filename  # 保留原始文件名，以便前端显示
        })
        
    except Exception as e:
        logger.error(f"上传文件出错: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_upload_routes.route('/content', methods=['GET'])
def get_file_content():
    """获取文件内容"""
    try:
        # 获取请求路径
        request_path = request.args.get('path')
        if not request_path:
            return jsonify({"success": False, "error": "缺少文件路径参数"}), 400
        
        logger.info(f"请求的文件路径: {request_path}")
        
        # 尝试几种可能的路径解析方式
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 方法1: 直接使用请求路径的最后部分(文件名)
        filename = os.path.basename(request_path)
        
        # 在所有可能的目录中查找文件
        file_found = False
        file_path = None
        
        # 首先尝试直接构建完整路径
        direct_path = os.path.join(base_dir, request_path)
        logger.info(f"尝试直接路径: {direct_path}")
        if os.path.exists(direct_path) and os.path.isfile(direct_path):
            file_path = direct_path
            file_found = True
            logger.info(f"找到文件(直接路径): {file_path}")
        
        # 如果直接路径不存在，尝试在所有存储路径中查找文件名
        if not file_found:
            for module, rel_path in STORAGE_PATHS.items():
                possible_path = os.path.join(base_dir, rel_path, filename)
                logger.info(f"尝试可能的路径: {possible_path}")
                if os.path.exists(possible_path) and os.path.isfile(possible_path):
                    file_path = possible_path
                    file_found = True
                    logger.info(f"找到文件(存储路径): {file_path}")
                    break
        
        # 如果请求路径包含"Intelligent Water Utility System/api-server/"，尝试移除这部分
        if not file_found and "Intelligent Water Utility System/api-server/" in request_path:
            clean_path = request_path.replace("Intelligent Water Utility System/api-server/", "")
            possible_path = os.path.join(base_dir, clean_path)
            logger.info(f"尝试清理后的路径: {possible_path}")
            if os.path.exists(possible_path) and os.path.isfile(possible_path):
                file_path = possible_path
                file_found = True
                logger.info(f"找到文件(清理路径): {file_path}")
        
        # 如果仍未找到文件
        if not file_found:
            # 记录当前目录结构，帮助调试
            logger.error(f"找不到文件: {request_path}")
            logger.error(f"基础目录: {base_dir}")
            logger.error(f"目录内容: {os.listdir(base_dir)}")
            for module, rel_path in STORAGE_PATHS.items():
                full_path = os.path.join(base_dir, rel_path)
                if os.path.exists(full_path):
                    logger.error(f"{rel_path} 目录内容: {os.listdir(full_path)}")
                else:
                    logger.error(f"{rel_path} 目录不存在")
            
            return jsonify({
                "success": False, 
                "error": f"找不到文件: {request_path}",
                "base_dir": base_dir,
                "attempted_paths": [
                    direct_path,
                    *[os.path.join(base_dir, rel_path, filename) for rel_path in STORAGE_PATHS.values()]
                ]
            }), 404
        
        # 读取CSV文件
        try:
            df = pd.read_csv(file_path)
            
            # 处理数据类型，确保可以被JSON序列化
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].astype(str)
                elif pd.api.types.is_float_dtype(df[col]):
                    # 处理NaN值
                    df[col] = df[col].fillna(0).astype(float)
                elif pd.api.types.is_integer_dtype(df[col]):
                    df[col] = df[col].fillna(0).astype(int)
                else:
                    # 处理其他类型的NaN值
                    df[col] = df[col].fillna('').astype(str)
            
            # 将DataFrame转换为字典列表
            data = df.head(100).to_dict(orient='records')  # 只返回前100行，避免数据过大
            # 获取列名
            columns = df.columns.tolist()
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].astype(str)
                elif pd.api.types.is_float_dtype(df[col]):
                    df[col] = df[col].fillna(0).astype(float)
                elif pd.api.types.is_integer_dtype(df[col]):
                    df[col] = df[col].fillna(0).astype(int)
                else:
                 df[col] = df[col].fillna('').astype(str)
            
            # 确保返回的数据格式与前端期望一致
            response_data = {
                "success": True, 
                "columns": columns,
                "data": data,
                "total_rows": len(df),
                "returned_rows": len(data)
            }
            sample_data = data[:2] if data else []  # 取前两条记录作为样本
            logger.info(f"返回给前端的数据样本: {sample_data}")
            logger.info(f"返回的列名顺序: {columns}")
            logger.info(f"成功读取文件，返回{len(data)}行数据")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"读取CSV文件失败: {str(e)}")
            return jsonify({"success": False, "error": f"读取CSV文件失败: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"获取文件内容出错: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
def filter_prediction_results(forecast_days):
    """
    筛选预测结果，只保留前forecast_days+1行的数据（包含表头）
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prediction_file_path = os.path.join(base_dir, 'Water-Forecast-Master/results/predictions/predict_data.csv')
        
        if not os.path.exists(prediction_file_path):
            print(f"⚠️ 预测结果文件不存在: {prediction_file_path}")
            return False
        
        # 读取CSV文件
        df = pd.read_csv(prediction_file_path)
        print(f"原始数据行数: {len(df)}")
        
        # 只保留前forecast_days行数据
        df_filtered = df.head(forecast_days)
        
        # 保存回原文件
        df_filtered.to_csv(prediction_file_path, index=False)
        
        print(f"✅ 已保存前{forecast_days}行数据到预测结果文件")
        return True
            
    except Exception as e:
        print(f"❌ 筛选预测结果时出错: {str(e)}")
        return False
@file_upload_routes.route('/water-forecast/predict', methods=['POST'])

def predict_water_forecast():
    """运行训练和预测模型，返回预测结果文件路径"""
    try:
        # 构建项目路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        water_forecast_dir = os.path.join(base_dir, 'water-forecast-master')  # 注意这里使用小写
        prediction_file_path = os.path.join(water_forecast_dir, 'results/predictions/predict_data.csv')
        request_data = request.get_json()
        forecast_days = request_data.get('forecast_days', 7)  # 默认7天
        
        print(f"收到预测请求，预测天数: {forecast_days}")
        
        logger.info(f"最终获取的预测天数: {forecast_days}")
        
        # 验证预测天数
        if not isinstance(forecast_days, int) or forecast_days < 1:
            logger.error(f"无效的预测天数: {forecast_days}")
            return jsonify({"success": False, "error": "预测天数必须是正整数"}), 400
        
        logger.info(f"开始运行训练和预测流程，预测天数: {forecast_days}")
        
        # 检查目录是否存在
        if not os.path.exists(water_forecast_dir):
            logger.error(f"water-forecast-master 目录不存在: {water_forecast_dir}")
            return jsonify({"success": False, "error": "water-forecast-master 目录不存在"}), 404
        
        # 检查脚本是否存在
        train_script = os.path.join(water_forecast_dir, 'src/train.py')
        predict_script = os.path.join(water_forecast_dir, 'src/predict.py')
        
        if not os.path.exists(train_script):
            logger.error(f"训练脚本不存在: {train_script}")
            return jsonify({"success": False, "error": "训练脚本不存在"}), 404
        
        if not os.path.exists(predict_script):
            logger.error(f"预测脚本不存在: {predict_script}")
            return jsonify({"success": False, "error": "预测脚本不存在"}), 404
        
        # 运行训练和预测脚本
        try:
            # 切换到water-forecast-master目录
            current_dir = os.getcwd()
            os.chdir(water_forecast_dir)
            
            logger.info(f"当前工作目录: {os.getcwd()}")
            
            # 运行训练脚本
            logger.info("开始运行训练脚本...")
            train_cmd = ["python", "./src/train.py"]
            logger.info(f"执行命令: {' '.join(train_cmd)}")
            
            train_result = subprocess.run(train_cmd, 
                                         capture_output=True, 
                                         text=True)
            
            if train_result.returncode != 0:
                logger.error(f"训练脚本运行失败: {train_result.stderr}")
                return jsonify({
                    "success": False, 
                    "error": "模型训练失败", 
                    "details": train_result.stderr
                }), 500
            
            logger.info(f"训练脚本运行完成")
            
            # 运行预测脚本
            logger.info("开始运行预测脚本...")
            predict_cmd = ["python", "./src/predict.py"]
            logger.info(f"执行命令: {' '.join(predict_cmd)}")
            
            predict_result = subprocess.run(predict_cmd, 
                                           capture_output=True, 
                                           text=True)
            
            if predict_result.returncode != 0:
                logger.error(f"预测脚本运行失败: {predict_result.stderr}")
                return jsonify({
                    "success": False, 
                    "error": "模型预测失败", 
                    "details": predict_result.stderr
                }), 500
                
            logger.info(f"预测脚本运行完成")
            
            # 切回原目录
            os.chdir(current_dir)
            
        except Exception as e:
            # 确保切回原目录
            if os.getcwd() != current_dir:
                os.chdir(current_dir)
            logger.error(f"运行脚本过程中出错: {str(e)}")
            return jsonify({"success": False, "error": f"运行模型脚本出错: {str(e)}"}), 500
        
        # 检查文件是否存在
        if not os.path.exists(prediction_file_path):
            logger.warning(f"预测完成后，结果文件不存在: {prediction_file_path}")
            return jsonify({"success": False, "error": "预测完成，但结果文件不存在"}), 404
        
        logger.info(f"预测完成，找到预测结果文件: {prediction_file_path}")
        filter_prediction_results(forecast_days)
        return jsonify({
            "success": True,
            "message": "训练和预测完成",
            "prediction_file": 'water-forecast-master/results/predictions/predict_data.csv'
        })
    
    except Exception as e:
        logger.error(f"获取预测结果出错: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_upload_routes.route('/prediction-result', methods=['GET'])
def get_prediction_result():
    """获取水量预测结果文件内容"""
    try:
        # 构建预测结果文件路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prediction_file_path = os.path.join(base_dir, 'Water-Forecast-Master/results/predictions/predict_data.csv')
        
        logger.info(f"尝试读取预测结果文件: {prediction_file_path}")
        
        # 检查文件是否存在
        if not os.path.exists(prediction_file_path):
            logger.error(f"预测结果文件不存在: {prediction_file_path}")
            return jsonify({"success": False, "error": "预测结果文件不存在"}), 404
        
        # 读取CSV文件
        try:
            df = pd.read_csv(prediction_file_path)
            
            # 处理数据类型，确保可以被JSON序列化
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].astype(str)
                elif pd.api.types.is_float_dtype(df[col]):
                    df[col] = df[col].fillna(0).astype(float)
                elif pd.api.types.is_integer_dtype(df[col]):
                    df[col] = df[col].fillna(0).astype(int)
                else:
                    df[col] = df[col].fillna('').astype(str)
            
            # 将DataFrame转换为字典列表
            data = df.head(100).to_dict(orient='records')  # 只返回前100行，避免数据过大
            # 获取列名
            columns = df.columns.tolist()
            
            # 构建响应数据
            response_data = {
                "success": True, 
                "columns": columns,
                "data": data,
                "total_rows": len(df),
                "file_path": 'Water-Forecast-Master/results/predictions/predict_data.csv'
            }
            
            logger.info(f"成功读取预测结果文件，返回{len(data)}行数据")
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"读取预测结果CSV文件失败: {str(e)}")
            return jsonify({"success": False, "error": f"读取预测结果CSV文件失败: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"获取预测结果文件内容出错: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@file_upload_routes.route('/download-prediction', methods=['GET'])
def download_prediction_file():
    """下载预测结果文件"""
    try:
        # 构建预测结果文件路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prediction_file_path = os.path.join(base_dir, 'Water-Forecast-Master/results/predictions/predict_data.csv')
        
        logger.info(f"尝试下载预测结果文件: {prediction_file_path}")
        
        # 检查文件是否存在
        if not os.path.exists(prediction_file_path):
            logger.error(f"预测结果文件不存在: {prediction_file_path}")
            return jsonify({"success": False, "error": "预测结果文件不存在"}), 404
        
        # 返回文件供下载
        return send_file(
            prediction_file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name='water_prediction_results.csv'
        )
        
    except Exception as e:
        logger.error(f"下载预测结果文件出错: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@file_upload_routes.route('/merge', methods=['GET'])
def get_merge_chart():
    try:
        # 获取当前文件所在目录（api-server/api/）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 获取api-server目录（上一级目录）
        api_server_dir = os.path.dirname(current_dir)
        
        # 构建文件路径
        original_data_path = os.path.join(api_server_dir, "water-forecast-master", "data", "preprocessed", "all", "preprocessed_data.csv")
        prediction_data_path = os.path.join(api_server_dir, "water-forecast-master", "results", "predictions", "predict_data.csv")
        
        # 打印路径用于调试
        print(f"当前文件目录: {current_dir}")
        print(f"API服务器目录: {api_server_dir}")
        print(f"原始数据路径: {original_data_path}")
        print(f"预测数据路径: {prediction_data_path}")
        
        # 检查文件是否存在
        if not os.path.exists(original_data_path):
            return jsonify({
                'success': False,
                'message': f'原始数据文件不存在: {original_data_path}'
            }), 404
            
        if not os.path.exists(prediction_data_path):
            return jsonify({
                'success': False,
                'message': f'预测数据文件不存在: {prediction_data_path}'
            }), 404
        
        # 读取数据
        original_df = pd.read_csv(original_data_path)
        prediction_df = pd.read_csv(prediction_data_path)
        
        print(f"原始数据形状: {original_df.shape}")
        print(f"预测数据形状: {prediction_df.shape}")
        print(f"原始数据列名: {original_df.columns.tolist()}")
        print(f"预测数据列名: {prediction_df.columns.tolist()}")
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # 自动检测数值列
        original_numeric_cols = original_df.select_dtypes(include=['float64', 'int64']).columns
        prediction_numeric_cols = prediction_df.select_dtypes(include=['float64', 'int64']).columns
        
        if len(original_numeric_cols) == 0:
            return jsonify({
                'success': False,
                'message': f'原始数据文件中没有找到数值列。可用列: {original_df.columns.tolist()}'
            }), 400
            
        if len(prediction_numeric_cols) == 0:
            return jsonify({
                'success': False,
                'message': f'预测数据文件中没有找到数值列。可用列: {prediction_df.columns.tolist()}'
            }), 400
        
        # 使用第一个数值列作为y轴数据
        original_y = original_df[original_numeric_cols[0]]
        prediction_y = prediction_df[prediction_numeric_cols[0]]
        
        # 创建x轴数据
        original_x = range(len(original_df))
        prediction_x = range(len(original_df), len(original_df) + len(prediction_df))
        
        # 绘制原始数据（蓝色）
        ax.plot(original_x, original_y, 
               color='#1f77b4', linewidth=2.5, label='原始数据', alpha=0.8)
        
        # 绘制预测数据（红色）
        ax.plot(prediction_x, prediction_y, 
               color='#d62728', linewidth=2.5, label='预测数据', alpha=0.8)
        
        # 在连接点添加标记
        if len(original_df) > 0 and len(prediction_df) > 0:
            ax.axvline(x=len(original_df)-1, color='gray', linestyle='--', alpha=0.5, label='预测起始点')
        
        # 设置图表样式
        ax.set_title('水位数据与预测对比图', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('时间点', fontsize=12)
        ax.set_ylabel(f'{original_numeric_cols[0]}', fontsize=12)
        ax.legend(fontsize=12, loc='best')
        ax.grid(True, alpha=0.3)
        
        # 设置背景色
        ax.set_facecolor('#f8f9fa')
        
        # 调整布局
        plt.tight_layout()
        
        # 将图表转换为base64字符串
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()  # 关闭图表释放内存
        
        return jsonify({
            'success': True,
            'image_base64': f'data:image/png;base64,{image_base64}',
            'message': '合并图表生成成功'
        })
        
    except FileNotFoundError as e:
        print(f"文件未找到错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'文件未找到: {str(e)}'
        }), 404
    except pd.errors.EmptyDataError as e:
        print(f"数据为空错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'CSV文件为空或格式错误'
        }), 400
    except Exception as e:
        print(f"生成合并图表错误: {str(e)}")
        import traceback
        traceback.print_exc()  # 打印完整的错误堆栈
        return jsonify({
            'success': False,
            'message': f'生成图表时发生错误: {str(e)}'
        }), 500
import matplotlib.pyplot as plt
import io
import base64

@file_upload_routes.route('/get_original_chart', methods=['GET'])
def get_original_chart():
    try:
        print("开始执行 get_original_chart")
        
        # 获取当前工作目录
        current_dir = os.getcwd()
        print(f"当前工作目录: {current_dir}")
        
        # 尝试不同的路径
        possible_paths = [
            "api-server/water-forecast-master/data/preprocessed/all/preprocessed_data.csv",
            "water-forecast-master/data/preprocessed/all/preprocessed_data.csv",
            "data/preprocessed/all/preprocessed_data.csv",
            "../water-forecast-master/data/preprocessed/all/preprocessed_data.csv",
            "./api-server/water-forecast-master/data/preprocessed/all/preprocessed_data.csv"
        ]
        
        csv_path = None
        for path in possible_paths:
            print(f"检查路径: {path}")
            if os.path.exists(path):
                csv_path = path
                print(f"找到文件: {path}")
                break
        
        if csv_path is None:
            # 列出当前目录结构帮助调试
            print("当前目录内容:")
            for item in os.listdir('.'):
                print(f"  {item}")
            
            return jsonify({
                'success': False,
                'message': '找不到CSV文件，请检查文件路径'
            }), 500
        
        # 读取CSV数据
        df = pd.read_csv(csv_path)
        print(f"CSV读取成功，数据形状: {df.shape}")
        
        # 获取需水量数据
        consumption = df.iloc[:, 1]  # 第二列：需水量
        
        # 创建图表
        plt.figure(figsize=(12, 6))
        plt.plot(consumption, color='blue', linewidth=1)
        plt.title('用水需求量')
        plt.xlabel('时间')
        plt.ylabel('需水量')
        plt.grid(True, alpha=0.3)
        
        # 转换为base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        plt.close()
        return jsonify({
            'success': True,
            'image_base64': f'data:image/png;base64,{img_base64}'
        })
        
    except Exception as e:
        print(f"错误详情: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
