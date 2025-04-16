from flask import Blueprint, request, jsonify
import os
import pandas as pd
from datetime import datetime
import uuid
import shutil
import logging
from flask import send_file
import subprocess
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

@file_upload_routes.route('/water-forecast/predict', methods=['POST'])

def predict_water_forecast():
    """运行训练和预测模型，返回预测结果文件路径"""
    try:
        # 构建项目路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        water_forecast_dir = os.path.join(base_dir, 'water-forecast-master')  # 注意这里使用小写
        prediction_file_path = os.path.join(water_forecast_dir, 'results/predictions/predict_data.csv')
        
        logger.info(f"开始运行训练和预测流程")
        
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
