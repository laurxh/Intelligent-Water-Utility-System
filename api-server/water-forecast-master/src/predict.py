import yaml
import pandas as pd
import datetime
from models.prophet import ProphetModel
from models.arima import ARIMAModel
from models.sarimax import SARIMAXModel
from models.nn import *
from models.skmodels import *
from train import load_dataset
from visualization.visualize import plot_prophet_forecast
# Map model names to their respective class definitions
MODELS_DEFS = {
    'PROPHET': ProphetModel,
    'ARIMA': ARIMAModel,
    'SARIMAX': SARIMAXModel,
    'LSTM': LSTMModel,
    'GRU': GRUModel,
    '1DCNN': CNN1DModel,
    'LINEAR_REGRESSION': LinearRegressionModel,
    'RANDOM_FOREST': RandomForestModel
}


def forecast(days, cfg=None, model=None, save=False):
    '''
    Generate a forecast for a certain number of days
    :param days: Length of forecast
    :param cfg: Project config
    :param model: Model object
    :param save: Flag indicating whether to save the forecast
    :return: DataFrame containing predicted consumption for each future date
    '''

    if cfg is None:
        cfg = yaml.full_load(open(os.getcwd() + "/config.yml", 'r'))

    if model is None:
        model_name = cfg['FORECAST']['MODEL'].upper()
        model_def = MODELS_DEFS.get(model_name, lambda: "Invalid model specified in cfg['FORECAST']['MODEL']")
        hparams = cfg['HPARAMS'][model_name]
        model = model_def(hparams)  # Create instance of model
        model.load(cfg['FORECAST']['MODEL_PATH'], scaler_path=cfg['PATHS']['SERIALIZATIONS'] + 'standard_scaler.joblib')
    else:
        model_name = model.name
    if isinstance(model, (NNModel, SKLearnModel)):
        train_df, test_df = load_dataset(cfg)
        recent_data = model.get_recent_data(train_df)
    else:
        recent_data = None
    results = model.forecast(days, recent_data=recent_data)
    if model.name == 'Prophet':
        plot_prophet_forecast(model.model, model.future_prediction, save_dir=cfg['PATHS']['FORECAST_VISUALIZATIONS'], train_date=model.train_date)
        # 不再保存详细预测结果文件
    if save:
        try:
            # 使用正确的配置键 PREPROCESSED_DATA
            if 'PREPROCESSED_DATA' in cfg['PATHS']:
                preprocessed_data_path = cfg['PATHS']['PREPROCESSED_DATA']
            else:
                # 如果找不到 PREPROCESSED_DATA，尝试其他可能的键
                possible_keys = ['PROCESSED_DATA', 'PROCESSED', 'PREPROCESS_DATA', 'DATA_PROCESSED', 'TRAIN_DATA']
                for key in possible_keys:
                    if key in cfg['PATHS']:
                        preprocessed_data_path = cfg['PATHS'][key]
                        break
                else:
                    # 如果找不到任何可能的键，抛出异常
                    raise KeyError("无法在配置中找到预处理数据的路径")
            
            # 读取预处理数据文件
            preprocessed_df = pd.read_csv(preprocessed_data_path)
            
            # 确定日期列的名称
            date_column_preprocessed = 'Date' if 'Date' in preprocessed_df.columns else 'ds'
            
            # 确保日期列是日期类型
            preprocessed_df[date_column_preprocessed] = pd.to_datetime(preprocessed_df[date_column_preprocessed])
            
            # 获取预处理数据中的最后一个日期
            last_date = preprocessed_df[date_column_preprocessed].max()
            
            # 确定预测结果中的日期列名
            date_column_results = 'Date' if 'Date' in results.columns else 'ds'
            
            # 确保预测结果中的日期列是日期类型
            results[date_column_results] = pd.to_datetime(results[date_column_results])
            
            # 过滤出比预处理数据中最后一个日期更晚的数据
            future_results = results[results[date_column_results] > last_date]
            
            # 保存预测结果
            future_results.to_csv(cfg['PATHS']['PREDICTIONS'] + 'predict_data.csv',
                        index=False, index_label=False)
            print(f"已保存从 {last_date} 之后的预测数据")
        except Exception as e:
            print(f"Error filtering data: {e}")
            # 如果出错，保存所有预测结果
            results.to_csv(cfg['PATHS']['PREDICTIONS'] + 'predict_data.csv',
                        index=False, index_label=False)
            print("由于发生错误，已保存所有预测数据")

    return results


if __name__ == '__main__':
    cfg = yaml.full_load(open("./config.yml", 'r'))
    days = cfg['FORECAST']['DAYS']
    forecast(days, cfg=cfg, save=True)
