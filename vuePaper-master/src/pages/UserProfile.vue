<!-- 水量预测-->
<template>
  <div class="content">
    <!-- 保留原有的上传部分 -->
    <div class="header-container">
      <h4 class="title">数据导入</h4>

      <div class="buttons-container">
        <button class="btn btn-success btn-sm" @click="generateChart">
          <i class="ti-bar-chart"></i> 生成图表
        </button>

        <label for="csv-upload" class="btn btn-primary btn-sm">
          <i class="ti-import"></i> 导入CSV
        </label>
        <input type="file" id="csv-upload" accept=".csv" @change="handleFileUpload" style="display: none"
          ref="fileInput" />
      </div>
    </div>



    <!-- 成功通知提示 -->
    <div v-if="showNotification" :class="['notification', notificationType]">
      <i :class="notificationIcon"></i>
      <span>{{ notificationMessage }}</span>
      <button class="close-btn" @click="closeNotification">×</button>
    </div>

    <!-- 上传进度条 -->
    <div v-if="uploading" class="progress-container">
      <div class="progress">
        <div class="progress-bar" role="progressbar" :style="{ width: uploadProgress + '%' }"
          :aria-valuenow="uploadProgress" aria-valuemin="0" aria-valuemax="100">
          {{ uploadProgress }}%
        </div>
      </div>
    </div>

    <!-- 上传的文件 -->
    <div v-if="uploadedFile" class="uploaded-file-container">
      <div class="uploaded-file" @click="viewFileContent">
        <i class="ti-file-text file-icon"></i>
        <span class="file-name">{{ uploadedFile.name }}</span>
        <span class="view-text">点击查看</span>
      </div>
    </div>

    <!-- 预测结果文件 -->
    <div v-if="predictionResult" class="prediction-result-container">
      <h5 class="mt-4 mb-3">预测结果</h5>
      <div class="prediction-chart-container mb-4">
        <h6 class="mb-3">水量预测趋势图</h6>
        <div class="chart-wrapper">
          <div v-if="loadingChart" class="chart-loading">
            <div class="spinner-border text-primary" role="status">
              <span class="sr-only">加载中...</span>
            </div>
          </div>
          <canvas id="predictionChart" ref="predictionChart" height="300"></canvas>
        </div>
      </div>
      <div class="prediction-file">
        <div class="prediction-file-info" @click="viewPredictionResult">
          <i class="ti-bar-chart file-icon"></i>
          <span class="file-name">水量预测结果</span>
          <span class="view-text">点击查看</span>
        </div>
        <button class="btn btn-sm btn-outline-primary download-btn" @click="downloadPredictionFile">
          <i class="ti-download"></i> 下载
        </button>
      </div>
    </div>

    <!-- 文件内容预览模态框 -->
    <div v-if="showFilePreview" class="file-preview-modal">
      <div class="file-preview-content">
        <div class="file-preview-header">
          <h5>{{ previewTitle }}</h5>
          <button class="close-btn" @click="closeFilePreview">×</button>
        </div>
        <div class="file-preview-body">
          <div v-if="loadingFileContent" class="text-center py-3">
            <div class="spinner-border text-primary" role="status">
              <span class="sr-only">加载中...</span>
            </div>
          </div>
          <div v-else class="table-responsive">
            <table class="table table-striped table-sm">
              <thead>
                <tr>
                  <th v-for="(header, idx) in fileHeaders" :key="idx">{{ header }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIdx) in fileRows.slice(0, 100)" :key="rowIdx">
                  <td v-for="(header, cellIdx) in fileHeaders" :key="cellIdx">{{ row[header] }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="fileRows.length > 100" class="text-center text-muted">
              <small>仅显示前100行数据</small>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- 图表预览模态框 -->
    <div v-if="showChartPreview" class="file-preview-modal">
      <div class="file-preview-content">
        <div class="file-preview-header">
          <h5>需水量图表</h5>
          <button class="close-btn" @click="closeChartPreview">×</button>
        </div>
        <div class="file-preview-body">
          <div v-if="loadingChart" class="text-center py-3">
            <div class="spinner-border text-primary" role="status">
              <span class="sr-only">加载中...</span>
            </div>
          </div>
          <div class="chart-container">
            <canvas id="dataConsumptionChart" ref="dataConsumptionChart" height="400"></canvas>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部分隔线 -->
    <hr class="mt-5 mb-4">

    <!-- 预测水量按钮 - 放在最底部 -->
    <div class="forecast-button-container"
      style="position: absolute; bottom: 20px; left: 0; right: 0; width: 100%; display: flex; justify-content: center; align-items: center;">
      <button class="btn btn-primary forecast-button" style="font-size: 0.9rem; padding: 0.4rem 0.8rem;"
        @click="forecastWater" :disabled="isForecasting || !uploadedFile">
        <i class="ti-bar-chart mr-1"></i>
        {{ isForecasting ? '预测中...' : '预测水量' }}
      </button>
    </div>

  </div>
</template>



<script>
import axios from 'axios';
import Papa from 'papaparse'; // 需要安装这个库: npm install papaparse
import Chart from 'chart.js/auto';  // 添加这一行导入 Chart.js
export default {
  data() {
    return {
      showNotification: false,
      notificationType: 'success',
      notificationMessage: '',
      notificationIcon: 'ti-check-circle',
      uploading: false,
      uploadProgress: 0,

      // 上传文件相关数据
      uploadedFile: null,
      showFilePreview: false,
      fileHeaders: [],
      fileRows: [],
      loadingFileContent: false,
      previewTitle: '',

      // 预测相关数据
      isForecasting: false,
      forecastStatus: '',
      forecastStatusType: 'text-info',
      forecastStatusIcon: 'ti-info-circle',
      predictionResult: null,
      showChartPreview: false,
      loadingChart: false,
      dataConsumptionChart: null
    }
  },

  methods: {
    generateChart() {
      if (!this.uploadedFile) {
        this.showErrorNotification('请先上传CSV文件');
        return;
      }

      this.showChartPreview = true;
      this.loadingChart = true;

      // 直接使用已经解析好的数据创建图表
      if (this.fileRows.length === 0) {
        this.showErrorNotification('没有可用的数据，请重新上传文件');
        this.loadingChart = false;
        this.showChartPreview = false;
        return;
      }

      console.log(this.fileRows);

      // 使用 nextTick 确保 DOM 已更新
      this.$nextTick(() => {
        // 延迟一点时间确保模态框已完全显示
        setTimeout(() => {
          this.createConsumptionChart();
        }, 300);
      });
    },


    // 创建需水量图表
    createConsumptionChart() {
      try {
        console.log("开始创建图表...");

        // 获取日期和需水量数据
        const dateField = this.fileHeaders[0]; // 假设第一列是日期
        const consumptionField = this.fileHeaders[1]; // 假设第二列是需水量

        console.log("使用的日期字段:", dateField);
        console.log("使用的需水量字段:", consumptionField);

        // 将Vue响应式对象转换为普通JavaScript对象
        const plainData = JSON.parse(JSON.stringify(this.fileRows));
        console.log("转换后的数据示例:", plainData[0]);

        // 过滤掉日期为空的数据
        const filteredData = plainData.filter(row => {
          return row[dateField] && row[dateField].trim() !== "";
        });

        console.log("过滤前数据条数:", plainData.length);
        console.log("过滤后数据条数:", filteredData.length);

        // 准备图表数据
        const dates = filteredData.map(row => row[dateField]);
        const consumption = filteredData.map(row => parseFloat(row[consumptionField]) || 0);

        // 获取canvas元素
        const canvas = this.$refs.dataConsumptionChart;
        if (!canvas) {
          console.error("找不到canvas元素");
          this.showErrorNotification("找不到图表容器");
          this.loadingChart = false;
          return;
        }

        // 获取2D上下文
        const ctx = canvas.getContext('2d');

        // 销毁旧图表
        if (this.dataConsumptionChart) {
          this.dataConsumptionChart.destroy();
        }

        // 创建新图表
        this.dataConsumptionChart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: dates,
            datasets: [{
              label: '需水量',
              data: consumption,
              borderColor: 'rgb(20, 180, 170)',
              backgroundColor: 'rgba(20, 180, 170, 0.2)',
              borderWidth: 2.5,
              fill: true,

              // 关键参数：增加曲线平滑度
              tension: 0.4,  // 值范围0-1，越大曲线越平滑

              // 减小或隐藏数据点
              pointRadius: 0,  // 设为0完全隐藏数据点
              pointHoverRadius: 4,  // 鼠标悬停时显示点

              // 可选：使线条看起来更平滑
              borderJoinStyle: 'round',

              // 可选：如果想要更平滑的填充区域
              segment: {
                borderColor: ctx => 'rgb(20, 180, 170)'
              }
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,

            // 添加标题配置，使"需水量"居中显示
            plugins: {
              title: {
                display: true,
                align: 'center',
                position: 'top',
                font: {
                  size: 16,
                  weight: 'bold'
                },
                padding: {
                  top: 10,
                  bottom: 10
                }
              },
              // 如果您想保留图例但让其居中
              legend: {
                display: true,
                position: 'top',
                align: 'center'
              }
            },

            elements: {
              line: {
                tension: 0.4  // 全局设置线条平滑度
              }
            }
          }
        });

        this.loadingChart = false;
      } catch (error) {
        console.error("创建图表时出错:", error);
        this.showErrorNotification("创建图表时出错: " + error.message);
        this.loadingChart = false;
      }
    },
    // 关闭图表预览
    closeChartPreview() {
      this.showChartPreview = false;
    },
    handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      if (!file.name.endsWith('.csv')) {
        this.showErrorNotification('请上传CSV格式的文件');
        this.$refs.fileInput.value = '';
        return;
      }

      // 在上传前先解析CSV文件
      const reader = new FileReader();
      reader.onload = (e) => {
        // 使用Papa Parse解析CSV数据
        Papa.parse(e.target.result, {
          header: true,
          complete: (results) => {
            // 保存解析结果到前端
            this.fileHeaders = results.meta.fields;
            this.fileRows = results.data;
            console.log("前端解析的CSV数据:", this.fileHeaders, this.fileRows[0]);

            // 然后再上传到服务器
            this.uploadCSVFile(file);
          },
          error: (error) => {
            this.showErrorNotification(`解析CSV文件失败: ${error.message}`);
            this.$refs.fileInput.value = '';
          }
        });
      };
      reader.onerror = () => {
        this.showErrorNotification('读取文件失败');
        this.$refs.fileInput.value = '';
      };
      reader.readAsText(file);
    },

    async uploadCSVFile(file) {
      try {
        this.uploading = true;
        this.uploadProgress = 0;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('module_type', 'water_forecast'); // 指定模块类型

        const response = await axios.post('http://localhost:5000/api/files/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            this.uploadProgress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        });

        if (response.data.success) {
          this.showSuccessNotification('CSV文件上传成功！');
          // 保存上传的文件信息
          this.uploadedFile = {
            name: file.name,
            path: response.data.filePath || `Intelligent Water Utility System/api-server/Water-Forecast-Master/data/preprocessed/all/${file.name}`,
            size: file.size,
            uploadDate: new Date().toISOString()
          };
        } else {
          this.showErrorNotification(`上传失败: ${response.data.error}`);
        }
      } catch (error) {
        console.error('文件上传出错:', error);
        this.showErrorNotification(`上传出错: ${error.response?.data?.error || error.message}`);
      } finally {
        this.uploading = false;
        this.$refs.fileInput.value = '';
      }
    },
    showSuccessNotification(message) {
      this.notificationType = 'success';
      this.notificationIcon = 'ti-check-circle';
      this.notificationMessage = message;
      this.showNotification = true;

      setTimeout(() => {
        this.closeNotification();
      }, 5000);
    },

    showErrorNotification(message) {
      this.notificationType = 'error';
      this.notificationIcon = 'ti-alert-circle';
      this.notificationMessage = message;
      this.showNotification = true;

      setTimeout(() => {
        this.closeNotification();
      }, 5000);
    },

    closeNotification() {
      this.showNotification = false;
    },

    // 查看文件内容
    async viewFileContent() {
      console.log('viewFileContent 方法被调用');
      if (!this.uploadedFile) return;

      this.previewTitle = this.uploadedFile.name;
      this.showFilePreview = true;
      this.loadingFileContent = true;

      try {
        // 调用后端API获取文件内容
        const response = await axios.get(`http://localhost:5000/api/files/content?path=${encodeURIComponent(this.uploadedFile.path)}`);

        if (response.data.success) {
          // 后端已经解析了CSV，直接使用返回的数据
          this.fileHeaders = response.data.columns;
          this.fileRows = response.data.data;
          // 添加调试信息
          console.log("设置后的列头:", this.fileHeaders);
          console.log("设置后的第一行数据:", this.fileRows[0]);

          // 检查第一行数据的键是否与列头匹配
          if (this.fileRows.length > 0) {
            console.log("第一行数据的键:", Object.keys(this.fileRows[0]));
          }
        } else {
          console.error('获取文件内容失败:', response.data.error);
          this.showErrorNotification(`获取文件内容失败: ${response.data.error}`);
        }
      } catch (error) {
        console.error('获取文件内容出错:', error);
        this.showErrorNotification(`获取文件内容出错: ${error.message}`);
      } finally {
        this.loadingFileContent = false;
      }
    },

    // 查看预测结果
    async forecastWater() {
      if (!this.uploadedFile) {
        this.showErrorNotification('请先上传CSV文件');
        return;
      }

      this.isForecasting = true;
      this.forecastStatus = '正在预测水量，请稍候...';
      this.forecastStatusType = 'text-info';
      this.forecastStatusIcon = 'ti-time';

      try {
        // 发送预测请求
        const forecastResponse = await axios.post('http://localhost:5000/api/files/water-forecast/predict');

        if (forecastResponse.data.success) {
          this.forecastStatus = '预测完成！';
          this.forecastStatusType = 'text-success';
          this.forecastStatusIcon = 'ti-check-circle';
          this.showSuccessNotification('水量预测完成！');

          // 设置预测结果，使预测结果区域可见
          this.predictionResult = {
            path: 'Water-Forecast-Master/results/predictions/predict_data.csv',
            date: new Date().toISOString()
          };

          // 获取预测结果数据并绘制图表
          try {
            // 调用后端API获取预测结果文件内容
            const resultResponse = await axios.get('http://localhost:5000/api/files/prediction-result');

            if (resultResponse.data.success) {
              // 使用返回的数据
              this.fileHeaders = resultResponse.data.columns;
              this.fileRows = resultResponse.data.data;
              console.log("预测结果列头:", this.fileHeaders);
              console.log("预测结果第一行数据:", this.fileRows[0]);

              // 绘制预测结果图表
              this.drawPredictionChartFromData(this.fileHeaders, this.fileRows);
            } else {
              this.showErrorNotification('获取预测结果数据失败');
            }
          } catch (resultError) {
            console.error('获取预测结果数据出错:', resultError);
            this.showErrorNotification(`获取预测结果数据出错: ${resultError.message}`);
          }
        } else {
          this.forecastStatus = `预测失败: ${forecastResponse.data.error}`;
          this.forecastStatusType = 'text-danger';
          this.forecastStatusIcon = 'ti-alert-circle';
          this.showErrorNotification(`预测失败: ${forecastResponse.data.error}`);
        }
      } catch (error) {
        console.error('预测水量出错:', error);
        this.forecastStatus = `预测出错: ${error.response?.data?.error || error.message}`;
        this.forecastStatusType = 'text-danger';
        this.forecastStatusIcon = 'ti-alert-circle';
        this.showErrorNotification(`预测出错: ${error.response?.data?.error || error.message}`);
      } finally {
        this.isForecasting = false;
      }
    },

    // 从API返回的数据绘制图表
    // 从API返回的数据绘制图表
    // 在methods中添加
    async viewPredictionResult() {
      this.previewTitle = "预测结果";
      this.showFilePreview = true;
      this.loadingFileContent = true;

      try {
        const response = await axios.get('http://localhost:5000/api/files/prediction-result');
        if (response.data.success) {
          this.fileHeaders = response.data.columns;
          this.fileRows = response.data.data;
        } else {
          this.showErrorNotification(`获取预测结果失败: ${response.data.error}`);
        }
      } catch (error) {
        this.showErrorNotification(`获取预测结果出错: ${error.message}`);
      } finally {
        this.loadingFileContent = false;
      }
    },

    // 绘制图表的方法
    drawPredictionChart(data) {
      this.loadingChart = true;

      // 确保Chart.js已经导入
      if (typeof Chart === 'undefined') {
        console.error('Chart.js未加载');
        this.showErrorNotification('图表库未加载，无法显示图表');
        this.loadingChart = false;
        return;
      }

      // 获取日期和预测水量列
      const dateField = this.fileHeaders[0]; // 假设第一列是日期
      const valueField = this.fileHeaders[1]; // 假设第二列是预测水量

      // 准备数据
      const dates = this.fileRows.map(row => row[dateField]);
      const values = this.fileRows.map(row => parseFloat(row[valueField]));

      // 获取canvas元素
      const ctx = this.$refs.predictionChart;
      if (!ctx) {
        console.error('找不到图表canvas元素');
        this.loadingChart = false;
        return;
      }

      // 销毁旧图表
      if (this.chart) {
        this.chart.destroy();
      }

      // 创建新图表
      this.chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: dates,
          datasets: [{
            label: '预测水量 (m³)',  // 在标签中添加单位
            data: values,
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 2,
            pointRadius: 3
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: false,
              title: {
                display: true,
                text: '水量 (m³)'  // 添加Y轴标题和单位
              }
            },
            x: {
              title: {
                display: true,
                text: '日期'  // 添加X轴标题
              }
            }
          },
          plugins: {
            legend: {
              display: true,
              position: 'top'
            }
          }
        }
      });

      this.loadingChart = false;
    },
    // 下载预测结果文件
    downloadPredictionFile() {
      if (!this.predictionResult) return;

      // 创建一个隐藏的<a>元素来触发下载
      const downloadLink = document.createElement('a');
      downloadLink.href = 'http://localhost:5000/api/files/download-prediction';
      downloadLink.download = 'water_prediction_results.csv';
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
    },

    // 关闭文件预览
    closeFilePreview() {
      this.showFilePreview = false;
    },

    // 预测水量
    async forecastWater() {
      if (!this.uploadedFile) {
        this.showErrorNotification('请先上传CSV文件');
        return;
      }

      this.isForecasting = true;
      this.forecastStatus = '正在预测水量，请稍候...';
      this.forecastStatusType = 'text-info';
      this.forecastStatusIcon = 'ti-time';

      try {
        const response = await axios.post('http://localhost:5000/api/files/water-forecast/predict');

        if (response.data.success) {
          this.forecastStatus = '预测完成！';
          this.forecastStatusType = 'text-success';
          this.forecastStatusIcon = 'ti-check-circle';
          this.showSuccessNotification('水量预测完成！');

          // 设置预测结果，使预测结果区域可见
          this.predictionResult = {
            path: 'Water-Forecast-Master/results/predictions/predict_data.csv',
            date: new Date().toISOString()
          };
          // 删除或注释掉以下代码，以防止自动打开预测结果
          // setTimeout(() => {
          //   this.viewPredictionResult();
          // }, 500);
          const resultResponse = await axios.get('http://localhost:5000/api/files/prediction-result');

          if (resultResponse.data.success) {
            // 使用返回的数据
            this.fileHeaders = resultResponse.data.columns;
            this.fileRows = resultResponse.data.data;
            console.log("预测结果列头:", this.fileHeaders);
            console.log("预测结果第一行数据:", this.fileRows[0]);

            // 在数据加载完成后绘制图表
            this.$nextTick(() => {
              this.drawPredictionChart();
            });
          } else {
            this.showErrorNotification('获取预测结果数据失败');
          }
        } else {
          this.forecastStatus = `预测失败: ${response.data.error}`;
          this.forecastStatusType = 'text-danger';
          this.forecastStatusIcon = 'ti-alert-circle';
          this.showErrorNotification(`预测失败: ${response.data.error}`);
        }
      } catch (error) {
        console.error('预测水量出错:', error);
        this.forecastStatus = `预测出错: ${error.response?.data?.error || error.message}`;
        this.forecastStatusType = 'text-danger';
        this.forecastStatusIcon = 'ti-alert-circle';
        this.showErrorNotification(`预测出错: ${error.response?.data?.error || error.message}`);
      } finally {
        this.isForecasting = false;
      }
    }
  }
};
</script>

<style scoped>
.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title {
  margin: 0;
}

.import-button {
  display: flex;
  align-items: center;
}

/* 通知样式 */
.notification {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 4px;
  animation: slide-in 0.3s ease-out;
  pointer-events: none;
  /* 允许点击通知下方的元素 */
}

.success {
  background-color: #e6f7e6;
  color: #28a745;
  border-left: 4px solid #28a745;
}

.error {
  background-color: #f8d7da;
  color: #dc3545;
  border-left: 4px solid #dc3545;
}

.notification i {
  margin-right: 8px;
  font-size: 16px;
}

.notification span {
  flex-grow: 1;
}

.close-btn {
  background: none;
  border: none;
  color: inherit;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
}

/* 进度条样式 */
.progress-container {
  margin: 15px 0;
}

.progress {
  height: 10px;
  border-radius: 5px;
  background-color: #e9ecef;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background-color: #007bff;
  color: white;
  text-align: center;
  font-size: 10px;
  line-height: 10px;
  transition: width 0.3s ease;
}

/* 上传文件样式 */
.uploaded-file-container {
  margin-top: 20px;
}

.uploaded-file {
  display: flex;
  align-items: center;
  padding: 15px;
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.uploaded-file:hover {
  background-color: #e9f5ff;
  border-color: #b8daff;
}

/* 预测结果文件样式 */
.prediction-result-container {
  margin-top: 30px;
}

.prediction-file {
  display: flex;
  align-items: center;
  background-color: #f0f8ff;
  border: 1px solid #b8daff;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 20px;
}

.prediction-file-info {
  display: flex;
  align-items: center;
  flex-grow: 1;
  cursor: pointer;
}

.download-btn {
  margin-left: 10px;
}

.file-icon {
  font-size: 24px;
  color: #007bff;
  margin-right: 12px;
}

.file-name {
  font-weight: 500;
  flex-grow: 1;
}

.view-text {
  color: #007bff;
  font-size: 14px;
  margin-right: 10px;
}

/* 文件预览模态框样式 */
.file-preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.file-preview-content {
  background-color: white;
  border-radius: 6px;
  width: 90%;
  max-width: 1200px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
}

.file-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
}

.file-preview-header h5 {
  margin: 0;
  font-weight: 500;
}

.file-preview-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.file-preview-body table {
  width: 100%;
  border-collapse: collapse;
}

.file-preview-body th {
  background-color: #f8f9fa;
  position: sticky;
  top: 0;
  z-index: 1;
}

/* 预测状态样式 */
.forecast-button-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 30px;
}

.forecast-button {
  padding: 10px 20px;
  font-size: 16px;
}

.forecast-status {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  margin-top: 10px;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.forecast-status i {
  margin-right: 8px;
}

@keyframes slide-in {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }

  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.chart-button-container {
  margin: 15px 0;
}

.generate-chart-btn {
  padding: 8px 16px;
  font-size: 15px;
}

.chart-container {
  width: 100%;
  height: 500px;
}

.header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.buttons-container {
  display: flex;
  gap: 10px;
  /* 按钮之间的间距 */
}

.title {
  margin-right: auto;
  /* 标题靠左 */
}
.header-container {
  margin-bottom: 15px;
}

.title {
  margin-bottom: 10px;
}

.buttons-container {
  display: flex;
  gap: 12px;
  /* 按钮之间的间距 */
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  /* 增加内边距使按钮更大 */
  font-size: 15px;
  /* 稍微增加字体大小 */
  border-radius: 4px;
  border: none;
  cursor: pointer;
  min-width: 120px;
  /* 增加宽度 */
  height: 40px;
  /* 增加高度 */
  transition: all 0.2s;
}

.btn i {
  margin-right: 6px;
}

.btn-success {
  background-color: #4CAF50;
  color: white;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

/* 悬停效果 */
.btn:hover {
  opacity: 0.9;
}
</style>
