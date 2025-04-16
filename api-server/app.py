# app.py
from flask import Flask, jsonify
from flask_cors import CORS
from api.water_forecast_api import file_upload_routes
from api.scheduler_api import scheduler_routes
from api.hydraulic_sim_api import hydraulic_bp  # 导入新的水力模拟API蓝图

app = Flask(__name__)
CORS(app)  # 启用CORS支持

# 添加根路由
@app.route('/')
def index():
    return jsonify({
        "message": "Welcome to Intelligent Water Utility System API",
        "available_endpoints": [
            "/api/files/upload",
            "/api/scheduler/network/data",
            "/api/scheduler/network/simulate",
            "/api/hydraulic/upload-inp",  # 添加新的端点
            "/api/hydraulic/network-data",
            "/api/hydraulic/simulate"
        ]
    })

# 注册所有路由蓝图
app.register_blueprint(file_upload_routes, url_prefix='/api/files')
app.register_blueprint(scheduler_routes, url_prefix='/api/scheduler')
app.register_blueprint(hydraulic_bp)  # 注册水力模拟API蓝图

if __name__ == '__main__':
    print("已注册的路由:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    app.run(debug=True)
