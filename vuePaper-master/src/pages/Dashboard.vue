<!-- 水力仿真-->
<template>
  <div class="content">
    <!-- 标题 -->

    <div class="header-container">
      <h4 class="title">水网络拓扑图</h4>
      <div class="control-buttons">
        <label for="inp-file-upload" class="btn btn-primary btn-sm">
          <i class="ti-upload"></i> 导入INP文件
        </label>
        <input type="file" id="inp-file-upload" accept=".inp" @change="uploadInpFile" style="display: none;">
        <button class="btn btn-success btn-sm" @click="generateCoverageMap" :disabled="!networkData">
          <i class="ti-map"></i> 生成监测率图
        </button>
        <button class="btn btn-info btn-sm" @click="generatePlan" :disabled="!networkData">
          <i class="ti-agenda"></i> 生成方案
        </button>
      </div>
    </div>
    <div v-if="notificationVisible" :class="['notification', notificationType]">
      <i :class="notificationIcon"></i>
      <span>{{ notificationMessage }}</span>
      <button class="close-btn" @click="closeNotification">×</button>
    </div>

    <!-- 网络状态提示 -->
    <div v-if="!networkData" class="no-network-message">
      <div class="alert alert-info">
        <i class="ti-info-circle mr-2"></i>
        请先导入INP文件以加载水网络数据
      </div>
    </div>

    <!-- 网络拓扑图容器 -->
    <div class="network-container">
      <div class="network-controls">
        <button class="btn btn-sm btn-outline-primary" @click="zoomIn">
          <i class="ti-zoom-in"></i>
        </button>
        <button class="btn btn-sm btn-outline-primary" @click="zoomOut">
          <i class="ti-zoom-out"></i>
        </button>
        <button class="btn btn-sm btn-outline-primary" @click="resetZoom">
          <i class="ti-arrows-corner"></i> 重置
        </button>
      </div>

      <div class="network-legend">
        <div class="legend-item">
          <div class="legend-color junction"></div>
          <span>节点</span>
        </div>
        <div class="legend-item">
          <div class="legend-color reservoir"></div>
          <span>水库</span>
        </div>
        <div class="legend-item">
          <div class="legend-color tank"></div>
          <span>水箱</span>
        </div>
        <div class="legend-item">
          <div class="legend-color pipe"></div>
          <span>管道</span>
        </div>
        <div class="legend-item">
          <div class="legend-color pump"></div>
          <span>水泵</span>
        </div>
        <div class="legend-item">
          <div class="legend-color valve"></div>
          <span>阀门</span>
        </div>
      </div>

      <div id="network-svg-container" ref="networkContainer" class="svg-container">
        <div v-if="loadingNetwork" class="network-loading">
          <div class="spinner-border text-primary" role="status">
            <span class="sr-only">加载中...</span>
          </div>
        </div>

        <!-- 使用纯SVG绘制网络图 -->
        <svg v-if="networkData" ref="networkSvg" :width="svgWidth" :height="svgHeight" @wheel="onWheel"
          @mousedown="startDrag" @touchstart="startDrag">
          <defs>
            <!-- 修改箭头定义，使其更小 -->
            <marker id="flowArrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto"
              markerUnits="strokeWidth">
              <path d="M0,0 L6,3 L0,6 z" fill="#333" />
            </marker>
          </defs>
          <g :transform="`translate(${translateX},${translateY}) scale(${scale})`">
            <!-- 连接线 -->
            <g v-for="(link, index) in networkData.links" :key="`link-${index}`">
              <!-- 基础连接线 -->
              <line :x1="getNodeX(link.source)" :y1="getNodeY(link.source)" :x2="getNodeX(link.target)"
                :y2="getNodeY(link.target)" :class="`link ${link.link_type.toLowerCase()}`"
                :stroke="getLinkColor(link.link_type)" :stroke-width="link.link_type === 'Pipe' ? 2 : 3"
                :stroke-dasharray="link.link_type === 'Pump' ? '5,5' : 'none'"
                style="cursor: pointer; stroke-linecap: round;" @click.stop="openElementPopup(link)" />

              <!-- 中间箭头指示器（更小的箭头） -->
              <line v-if="shouldShowFlowArrow(link)" :x1="getMidpointX(link) - getArrowDirectionX(link) * 5"
                :y1="getMidpointY(link) - getArrowDirectionY(link) * 5"
                :x2="getMidpointX(link) + getArrowDirectionX(link) * 5"
                :y2="getMidpointY(link) + getArrowDirectionY(link) * 5" :stroke="getLinkColor(link.link_type)"
                stroke-width="1.5" :marker-end="'url(#flowArrow)'" style="pointer-events: none;" />
            </g>

            <!-- 节点 -->
            <circle v-for="(node, index) in networkData.nodes" :key="`node-${index}`" :cx="node.x" :cy="node.y"
              :r="getNodeRadius(node.node_type) * (selectedSensorNodes.includes(node.id) ? 1.5 : 1)"
              :fill="selectedSensorNodes.includes(node.id) ? '#ff9800' : getNodeColor(node.node_type)"
              :stroke="selectedSensorNodes.includes(node.id) ? '#ff5722' : '#fff'"
              :stroke-width="selectedSensorNodes.includes(node.id) ? 2.5 : 1.5"
              :class="`node ${node.node_type.toLowerCase()} ${selectedSensorNodes.includes(node.id) ? 'selected-sensor' : ''}`"
              @click.stop="openElementPopup(node)" />

            <!-- 节点标签 -->
            <text v-for="(node, index) in networkData.nodes" :key="`label-${index}`" :x="node.x + 12" :y="node.y + 4"
              font-size="10px" class="node-label">
              {{ node.id }}
            </text>
          </g>
        </svg>

      </div>
    </div>

    <!-- 元素详情弹窗 -->
    <div v-if="showElementPopup" class="element-popup-overlay" @click="closeElementPopup">
      <div class="element-popup" @click.stop>
        <div class="element-popup-header">
          <h5>{{ selectedElement.id }} 详情</h5>
          <button class="close-btn" @click="closeElementPopup">×</button>
        </div>
        <div class="element-popup-body">
          <div class="detail-item">
            <span class="detail-label">类型:</span>
            <span class="detail-value">{{ getElementTypeName(selectedElement) }}</span>
          </div>

          <!-- 节点特有属性 -->
          <template v-if="selectedElement.node_type">
            <!-- 始终显示基础需水量（如果存在） -->
            <div class="detail-item"
              v-if="selectedElement.node_type === 'Junction' && selectedElement.base_demand !== undefined">
              <span class="detail-label">基础需求:</span>
              <span class="detail-value">{{ selectedElement.base_demand || 0 }} {{
                selectedElement.demand_unit || 'm^3/s' }}</span>
            </div>
            <!-- 如果有实际需水量，则显示实际需水量 -->
            <div class="detail-item"
              v-if="selectedElement.node_type === 'Junction' && selectedElement.actual_demand !== undefined">
              <span class="detail-label">实际需求:</span>
              <span class="detail-value">{{ selectedElement.actual_demand }} {{
                selectedElement.demand_unit || 'm^3/s' }}</span>
            </div>

            <!-- 其他属性保持不变 -->
            <div class="detail-item" v-if="selectedElement.node_type === 'Junction'">
              <span class="detail-label">高程:</span>
              <span class="detail-value">{{ selectedElement.elevation || 0 }} m</span>
            </div>
            <div class="detail-item"
              v-if="selectedElement.node_type === 'Junction' && selectedElement.pressure !== undefined">
              <span class="detail-label">压力:</span>
              <span class="detail-value">{{ selectedElement.pressure }} {{ selectedElement.pressure_unit
                || 'm' }}</span>
            </div>
            <div class="detail-item" v-if="selectedElement.node_type === 'Reservoir'">
              <span class="detail-label">水头:</span>
              <span class="detail-value">{{ selectedElement.head || 0 }} m</span>
            </div>
            <div class="detail-item"
              v-if="selectedElement.node_type === 'Reservoir' && selectedElement.pressure !== undefined">
              <span class="detail-label">压力:</span>
              <span class="detail-value">{{ selectedElement.pressure }} {{ selectedElement.pressure_unit
                || 'm' }}</span>
            </div>
            <div class="detail-item"
              v-if="selectedElement.node_type === 'Reservoir' && selectedElement.outflow !== undefined">
              <span class="detail-label">出水量:</span>
              <span class="detail-value">{{ selectedElement.outflow }} {{ selectedElement.outflow_unit ||
                'm^3/s' }}</span>
            </div>
            <div class="detail-item" v-if="selectedElement.node_type === 'Tank'">
              <span class="detail-label">水位:</span>
              <span class="detail-value">{{ selectedElement.level || 0 }} m</span>
            </div>
            <div class="detail-item" v-if="selectedElement.node_type === 'Tank'">
              <span class="detail-label">最大水位:</span>
              <span class="detail-value">{{ selectedElement.max_level || 0 }} m</span>
            </div>
            <div class="detail-item" v-if="selectedElement.node_type === 'Tank'">
              <span class="detail-label">最小水位:</span>
              <span class="detail-value">{{ selectedElement.min_level || 0 }} m</span>
            </div>
            <div class="detail-item"
              v-if="selectedElement.node_type === 'Tank' && selectedElement.pressure !== undefined">
              <span class="detail-label">压力:</span>
              <span class="detail-value">{{ selectedElement.pressure }} {{ selectedElement.pressure_unit
                || 'm' }}</span>
            </div>
            <div class="detail-item"
              v-if="selectedElement.node_type === 'Tank' && selectedElement.inflow !== undefined">
              <span class="detail-label">流入量:</span>
              <span class="detail-value">{{ selectedElement.inflow }} {{ selectedElement.inflow_unit ||
                'm^3/s' }}</span>
            </div>
          </template>


          <!-- 连接特有属性 -->
          <template v-if="selectedElement.link_type">
            <div class="detail-item">
              <span class="detail-label">起点:</span>
              <span class="detail-value">{{ getNodeId(selectedElement.source) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">终点:</span>
              <span class="detail-value">{{ getNodeId(selectedElement.target) }}</span>
            </div>
            <div class="detail-item" v-if="selectedElement.link_type === 'Pipe'">
              <span class="detail-label">长度:</span>
              <span class="detail-value">{{ selectedElement.length || 0 }} m</span>
            </div>
            <div class="detail-item"
              v-if="selectedElement.link_type === 'Pipe' || selectedElement.link_type === 'Valve'">
              <span class="detail-label">直径:</span>
              <span class="detail-value">{{ selectedElement.diameter || 0 }} m</span>
            </div>
            <div class="detail-item" v-if="selectedElement.link_type === 'Pipe'">
              <span class="detail-label">粗糙度:</span>
              <span class="detail-value">{{ selectedElement.roughness || 0 }}</span>
            </div>
            <div class="detail-item"
              v-if="selectedElement.link_type === 'Pump' || selectedElement.link_type === 'Valve'">
              <span class="detail-label">初始状态:</span>
              <span class="detail-value">{{ selectedElement.initial_status ? '开启' : '关闭' }}</span>
            </div>
            <div class="detail-item"
              v-if="(selectedElement.link_type === 'Pump' || selectedElement.link_type === 'Valve') && selectedElement.current_status !== undefined">
              <span class="detail-label">当前状态:</span>
              <span class="detail-value">{{ selectedElement.current_status === 'Open' ? '开启' : '关闭'
                }}</span>
            </div>
            <div class="detail-item" v-if="selectedElement.flow !== undefined">
              <span class="detail-label">流量:</span>
              <span class="detail-value">{{ selectedElement.flow }} {{ selectedElement.flow_unit ||
                'm^3/s' }}</span>
            </div>
          </template>
        </div>
        <div class="element-popup-footer">
          <button class="btn btn-secondary" @click="closeElementPopup">关闭</button>
        </div>
      </div>
    </div>
    <!-- 方案详情弹窗 -->
    <div v-if="showPlanPopup" class="element-popup-overlay" @click="closePlanPopup">
      <div class="element-popup" @click.stop style="width: 80%; max-width: 800px;">
        <div class="element-popup-header">
          <h5>方案详情</h5>
          <button class="close-btn" @click="closePlanPopup">×</button>
        </div>
        <div class="element-popup-body" style="max-height: 70vh; overflow-y: auto;">
          <div v-if="planDetails">
            <h6>优化方案信息</h6>
            <div style="height: 10px;"></div> <!-- 空白间隔元素 -->
            <div class="plan-info-item" style="padding-left: 15px;">
              <span class="label">观测点数量:</span>
              <span class="value">{{ planDetails.sensor_count }}</span>
            </div>
            <!-- 添加最大距离显示 -->
            <div class="plan-info-item" style="padding-left: 15px;">
              <span class="label">最大距离:</span>
              <span class="value">{{ planDetails.max_distance.toFixed(2) }} m</span>
            </div>

            <!-- 布点方案可视化区域 - 这是专门的小窗容器 -->
            <div class="plan-visualization-container">

              <div id="plan-visualization-svg" class="visualization-container"></div>


            </div>

            <!-- 观测点列表 -->
            <h6 class="mt-4">观测点列表</h6>
            <table class="table table-striped table-sm">
              <thead>
                <tr>
                  <th>序号</th>
                  <th>节点ID</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(nodeId, index) in (planDetails.sensorNodeIds ||
                  (planDetails.sensors ? planDetails.sensors.map(s => typeof s === 'object' ? s.node_id : s) : []))"
                  :key="index">
                  <td>{{ index + 1 }}</td>
                  <td>{{ nodeId }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="alert alert-info">
            <i class="ti-info-circle mr-2"></i>
            暂无方案数据
          </div>
        </div>
        <div class="element-popup-footer">
          <button class="btn btn-secondary" @click="closePlanPopup">关闭</button>
          <button class="btn btn-primary" @click="exportPlan" v-if="planDetails">导出方案</button>
        </div>
      </div>
    </div>

    <div v-if="showCoveragePopup" class="element-popup-overlay" @click="closeCoveragePopup">
      <div class="element-popup" @click.stop style="width: 80%; max-width: 800px;">
        <div class="element-popup-header">
          <h5>水网络监测分析</h5>
          <button class="close-btn" @click="closeCoveragePopup">×</button>
        </div>
        <div class="element-popup-body">
          <div class="coverage-chart-container">
            <canvas ref="coverageChart"></canvas>
          </div>

          <div class="coverage-table mt-4">
            <h6>监测距离数据表</h6>
            <div class="table-responsive">
              <table class="table table-striped table-sm">
                <thead>
                  <tr>
                    <th>布置点数</th>
                    <!-- 修改列标题 -->
                    <th>最大监测距离(m)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(coverage, points) in coverageData" :key="points">
                    <td>{{ points }}</td>
                    <!-- 直接显示为距离值，不添加百分号 -->
                    <td>{{ parseFloat(coverage).toFixed(2) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

        </div>
        <div class="element-popup-footer">
          <button class="btn btn-secondary" @click="closeCoveragePopup">关闭</button>
          <button class="btn btn-primary" @click="exportCoverageData">导出数据</button>
        </div>
      </div>
    </div>
    <!-- 布点数输入弹窗 -->
    <div v-if="showPointCountPopup" class="element-popup-overlay" @click="closePointCountPopup">
      <div class="element-popup" @click.stop style="width: 400px;">
        <div class="element-popup-header">
          <h5>请输入布点数</h5>
          <button class="close-btn" @click="closePointCountPopup">×</button>
        </div>
        <div class="element-popup-body">
          <div class="form-group">
            <label for="pointCount">布点数量 (1-{{ maxPointCount }})</label>
            <input type="number" class="form-control" id="pointCount" v-model.number="pointCount" min="1"
              :max="maxPointCount" placeholder="请输入布点数">
            <small class="form-text text-muted">请输入大于0且不超过节点总数的整数</small>
          </div>
        </div>
        <div class="element-popup-footer">
          <button class="btn btn-secondary" @click="closePointCountPopup">取消</button>
          <button class="btn btn-primary" @click="submitPointCount" :disabled="!isValidPointCount">确定</button>
        </div>
      </div>
    </div>

    <!-- 底部分隔线 -->
    <hr class="mt-5 mb-4">

    <!-- 底部操作按钮 -->
    <div class="action-buttons-container">
      <button class="btn btn-primary action-button" @click="runSimulation" :disabled="!networkData || isSimulating">
        <i class="ti-control-play mr-1"></i>
        {{ isSimulating ? '模拟中...' : '运行模拟' }}
      </button>
    </div>
  </div>
</template>


<script>
import axios from 'axios';
import Chart from 'chart.js/auto'  // 使用新版本的导入方式

export default {
  computed: {
    isValidPointCount() {
      return this.pointCount > 0 && this.pointCount <= this.maxPointCount;
    }
  },
  data() {
    return {
      notificationVisible: false,
      notificationType: 'success',
      notificationMessage: '',
      notificationIcon: 'ti-check-circle',
      planDetails: null,
      showPlanPopup: false,
      // 网络数据
      networkData: null,
      loadingNetwork: false,

      // 选中的元素
      selectedElement: null,
      showElementPopup: false,

      // 模拟相关
      isSimulating: false,

      // SVG相关
      svgWidth: 800,
      svgHeight: 600,
      scale: 1,
      translateX: 0,
      translateY: 0,
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0,
      coverageData: null,
      showCoveragePopup: false,
      coverageChartInstance: null,
      showPointCountPopup: false,
      pointCount: 1,
      maxPointCount: 0,
      selectedSensorNodes: [], // 存储被选为传感器的节点ID
    };
  },

  mounted() {
    // 设置SVG容器大小
    this.$nextTick(() => {
      if (this.$refs.networkContainer) {
        this.svgWidth = this.$refs.networkContainer.clientWidth;
        this.svgHeight = this.$refs.networkContainer.clientHeight || 600;
      }

      // 监听窗口大小变化
      window.addEventListener('resize', this.updateSvgSize);

      // 组件挂载后立即获取网络数据
    });

    // 添加键盘事件监听，按ESC关闭弹窗
    window.addEventListener('keydown', this.handleKeyDown);

    // 添加全局事件监听，用于拖动
    document.addEventListener('mousemove', this.handleMouseMove);
    document.addEventListener('mouseup', this.handleMouseUp);
    document.addEventListener('touchmove', this.handleTouchMove, { passive: false });
    document.addEventListener('touchend', this.handleTouchEnd);
  },

  beforeDestroy() {
    window.removeEventListener('resize', this.updateSvgSize);
    window.removeEventListener('keydown', this.handleKeyDown);

    // 移除全局事件监听
    document.removeEventListener('mousemove', this.handleMouseMove);
    document.removeEventListener('mouseup', this.handleMouseUp);
    document.removeEventListener('touchmove', this.handleTouchMove);
    document.removeEventListener('touchend', this.handleTouchEnd);
  },
  methods: {
    // 在 methods 中添加以下方法
    async generateCoverageMap() {
      if (!this.networkData) {
        this.displayNotification('error', '请先导入INP文件');
        return;
      }

      try {
        this.displayNotification('info', '正在生成监测率图...');

        const response = await axios.post('http://localhost:5000/api/hydraulic/generate-coverage-map');

        if (response.data.success) {
          this.displayNotification('success', '监测率图生成成功');

          // 如果后端返回了监测率数据，显示监测率图
          if (response.data.coverage_data) {
            this.coverageData = response.data.coverage_data;
            console.log(response.data.coverage_data)
            this.showCoveragePopup = true;
            this.renderCoverageChart();
          }
        } else {
          this.displayNotification('error', '生成监测率图失败: ' + response.data.error);
        }
      } catch (error) {
        console.error('生成监测率图出错:', error);
        this.displayNotification('error', '生成监测率图出错: ' + (error.response?.data?.error || error.message));
      }
    },

    // 在renderCoverageChart方法中修改
    renderCoverageChart() {
      this.$nextTick(() => {
        if (this.$refs.coverageChart) {
          // 准备图表数据
          const points = Object.keys(this.coverageData);

          // 确保数据是数值类型，移除可能的百分号，并直接使用值
          const coverageValues = Object.values(this.coverageData).map(value => {
            // 如果值是字符串且包含百分号，移除百分号并转换为数值
            if (typeof value === 'string' && value.includes('%')) {
              return parseFloat(value.replace('%', ''));
            }
            return parseFloat(value);
          });

          // 如果已经有图表实例，先销毁它
          if (this.coverageChartInstance) {
            this.coverageChartInstance.destroy();
          }

          // 创建新的图表
          const ctx = this.$refs.coverageChart.getContext('2d');
          this.coverageChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
              labels: points,
              datasets: [{
                label: '最大监测距离 (m)',
                data: coverageValues,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(75, 192, 192, 1)',
                pointRadius: 3,
                tension: 0.1
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                y: {
                  beginAtZero: true,
                  // 移除固定最大值，让图表自动适应数据范围
                  title: {
                    display: true,
                    text: '最大监测距离 (m)'
                  }
                },
                x: {
                  title: {
                    display: true,
                    text: '布置点数'
                  }
                }
              },
              plugins: {
                title: {
                  display: true,
                  text: '水网络监测距离分析',
                  font: {
                    size: 16
                  }
                },
                tooltip: {
                  callbacks: {
                    label: function (context) {
                      return `最大监测距离: ${context.parsed.y.toFixed(2)}m`;
                    }
                  }
                }
              }
            }
          });
        }
      });
    },

    // 同时修改exportCoverageData方法中的CSV表头和数据格式
    exportCoverageData() {
      if (!this.coverageData) return;

      try {
        // 修改CSV表头
        let csvContent = "布置点数,最大监测距离(m)\n";

        Object.entries(this.coverageData).forEach(([points, coverage]) => {
          // 处理可能包含百分号的值
          let coverageValue = coverage;
          if (typeof coverage === 'string' && coverage.includes('%')) {
            coverageValue = parseFloat(coverage.replace('%', ''));
          } else {
            coverageValue = parseFloat(coverage);
          }

          csvContent += `${points},${coverageValue.toFixed(2)}\n`;
        });

        // 创建Blob对象
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });

        // 创建下载链接
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'water_network_coverage_distance.csv';
        document.body.appendChild(a);
        a.click();

        // 清理
        setTimeout(() => {
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }, 0);

        this.displayNotification('success', '监测距离数据已导出');
      } catch (error) {
        console.error('导出监测距离数据出错:', error);
        this.displayNotification('error', '导出监测距离数据出错: ' + error.message);
      }
    },
    closeCoveragePopup() {
      this.showCoveragePopup = false;
      // 如果存在图表实例，需要销毁它以防止内存泄漏
      if (this.coverageChartInstance) {
        this.coverageChartInstance.destroy();
        this.coverageChartInstance = null;
      }
    },
    // 生成方案
    async generatePlan() {
      if (!this.networkData) {
        this.showNotification('请先导入网络数据', 'error');
        return;
      }

      // 显示布点数输入弹窗
      this.maxPointCount = this.networkData.nodes.length; // 使用所有节点的总数
      this.pointCount = Math.min(5, this.maxPointCount); // 默认设置为5或最大节点数
      this.showPointCountPopup = true;
    },

    // 关闭布点数输入弹窗
    closePointCountPopup() {
      this.showPointCountPopup = false;
    },
    openPlanPopup(planData) {
      console.log('打开方案弹窗，数据:', planData);
      this.planDetails = planData;
      this.showPlanPopup = true;

      // 使用nextTick确保DOM已经更新
      this.$nextTick(() => {
        // 增加延迟确保弹窗完全显示
        setTimeout(() => {
          console.log('准备渲染方案可视化，容器:', document.getElementById('plan-visualization-svg'));
          this.renderPlanVisualization();
        }, 300); // 增加延迟时间
      });
    },

    // 关闭方案详情弹窗
    closePlanPopup() {
      this.showPlanPopup = false;
    },
    openPlanPopup(planData) {
      this.planDetails = planData;
      this.showPlanPopup = true;

      // 使用nextTick确保DOM已经更新
      this.$nextTick(() => {
        this.renderPlanVisualization();
      });
    },
    // 渲染布点方案可视化

    // 添加图例到SVG中
    // 修改 addLegendToSvg 方法，将图例位置调整得更靠上
    addLegendToSvg(svg, width) {
      // 将图例位置调整到更靠右上角，y坐标从20改为10
      const legendGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      legendGroup.setAttribute("transform", `translate(${width - 100}, 10)`); // y坐标从20改为10

      // 添加背景矩形
      const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      bgRect.setAttribute("x", 0);
      bgRect.setAttribute("y", 0);
      bgRect.setAttribute("width", 80);
      bgRect.setAttribute("height", 45);
      bgRect.setAttribute("fill", "white");
      bgRect.setAttribute("fill-opacity", "0.8");
      bgRect.setAttribute("rx", "3");
      bgRect.setAttribute("ry", "3");
      bgRect.setAttribute("stroke", "#ddd");
      bgRect.setAttribute("stroke-width", "1");
      legendGroup.appendChild(bgRect);

      // 普通节点图例
      const normalCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      normalCircle.setAttribute("cx", 10);
      normalCircle.setAttribute("cy", 10);
      normalCircle.setAttribute("r", 4);
      normalCircle.setAttribute("fill", "#6CA6CD");
      normalCircle.setAttribute("stroke", "#5F9EA0");
      normalCircle.setAttribute("stroke-width", "1.5");
      legendGroup.appendChild(normalCircle);

      const normalText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      normalText.setAttribute("x", 20);
      normalText.setAttribute("y", 14);
      normalText.setAttribute("font-size", "10px");
      normalText.setAttribute("fill", "#333");
      normalText.textContent = "普通节点";
      legendGroup.appendChild(normalText);

      // 观测点图例
      const sensorCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      sensorCircle.setAttribute("cx", 10);
      sensorCircle.setAttribute("cy", 30);
      sensorCircle.setAttribute("r", 7);
      sensorCircle.setAttribute("fill", "#FF6347");
      sensorCircle.setAttribute("stroke", "#FF4500");
      sensorCircle.setAttribute("stroke-width", "1.5");
      legendGroup.appendChild(sensorCircle);

      const sensorText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      sensorText.setAttribute("x", 20);
      sensorText.setAttribute("y", 34);
      sensorText.setAttribute("font-size", "10px");
      sensorText.setAttribute("fill", "#333");
      sensorText.textContent = "观测点";
      legendGroup.appendChild(sensorText);

      svg.appendChild(legendGroup);
    },

    // 添加图例到SVG中的方法
    addLegendToSvg(svg, width) {
      const legendGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      legendGroup.setAttribute("transform", `translate(${width - 100}, 20)`);

      // 添加背景矩形
      const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      bgRect.setAttribute("x", 0);
      bgRect.setAttribute("y", 0);
      bgRect.setAttribute("width", 80);
      bgRect.setAttribute("height", 45);
      bgRect.setAttribute("fill", "white");
      bgRect.setAttribute("fill-opacity", "0.8");
      bgRect.setAttribute("rx", "3");
      bgRect.setAttribute("ry", "3");
      bgRect.setAttribute("stroke", "#ddd");
      bgRect.setAttribute("stroke-width", "1");
      legendGroup.appendChild(bgRect);

      // 普通节点图例
      const normalCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      normalCircle.setAttribute("cx", 10);
      normalCircle.setAttribute("cy", 10);
      normalCircle.setAttribute("r", 4);
      normalCircle.setAttribute("fill", "#6CA6CD");
      normalCircle.setAttribute("stroke", "#5F9EA0");
      normalCircle.setAttribute("stroke-width", "1.5");
      legendGroup.appendChild(normalCircle);

      const normalText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      normalText.setAttribute("x", 20);
      normalText.setAttribute("y", 14);
      normalText.setAttribute("font-size", "10px");
      normalText.setAttribute("fill", "#333");
      normalText.textContent = "普通节点";
      legendGroup.appendChild(normalText);

      // 观测点图例
      const sensorCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      sensorCircle.setAttribute("cx", 10);
      sensorCircle.setAttribute("cy", 30);
      sensorCircle.setAttribute("r", 7);
      sensorCircle.setAttribute("fill", "#FF6347");
      sensorCircle.setAttribute("stroke", "#FF4500");
      sensorCircle.setAttribute("stroke-width", "1.5");
      legendGroup.appendChild(sensorCircle);

      const sensorText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      sensorText.setAttribute("x", 20);
      sensorText.setAttribute("y", 34);
      sensorText.setAttribute("font-size", "10px");
      sensorText.setAttribute("fill", "#333");
      sensorText.textContent = "观测点";
      legendGroup.appendChild(sensorText);

      svg.appendChild(legendGroup);
    },
    // 添加图例到SVG中的新方法
    addLegendToSvg(svg, width) {
      const legendGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      legendGroup.setAttribute("transform", `translate(${width - 100}, 20)`);

      // 添加背景矩形
      const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      bgRect.setAttribute("x", 0);
      bgRect.setAttribute("y", 0);
      bgRect.setAttribute("width", 80);
      bgRect.setAttribute("height", 45);
      bgRect.setAttribute("fill", "white");
      bgRect.setAttribute("fill-opacity", "0.8");
      bgRect.setAttribute("rx", "3");
      bgRect.setAttribute("ry", "3");
      bgRect.setAttribute("stroke", "#ddd");
      bgRect.setAttribute("stroke-width", "1");
      legendGroup.appendChild(bgRect);

      // 普通节点图例
      const normalCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      normalCircle.setAttribute("cx", 10);
      normalCircle.setAttribute("cy", 10);
      normalCircle.setAttribute("r", 4);
      normalCircle.setAttribute("fill", "#6CA6CD");
      normalCircle.setAttribute("stroke", "#5F9EA0");
      normalCircle.setAttribute("stroke-width", "1.5");
      legendGroup.appendChild(normalCircle);

      const normalText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      normalText.setAttribute("x", 20);
      normalText.setAttribute("y", 14);
      normalText.setAttribute("font-size", "10px");
      normalText.setAttribute("fill", "#333");
      normalText.textContent = "普通节点";
      legendGroup.appendChild(normalText);

      // 观测点图例
      const sensorCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      sensorCircle.setAttribute("cx", 10);
      sensorCircle.setAttribute("cy", 30);
      sensorCircle.setAttribute("r", 7);
      sensorCircle.setAttribute("fill", "#FF6347");
      sensorCircle.setAttribute("stroke", "#FF4500");
      sensorCircle.setAttribute("stroke-width", "1.5");
      legendGroup.appendChild(sensorCircle);

      const sensorText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      sensorText.setAttribute("x", 20);
      sensorText.setAttribute("y", 34);
      sensorText.setAttribute("font-size", "10px");
      sensorText.setAttribute("fill", "#333");
      sensorText.textContent = "观测点";
      legendGroup.appendChild(sensorText);

      svg.appendChild(legendGroup);
    },
    // 提交布点数并生成方案
    // 提交布点数并生成方案
    // 提交布点数并生成方案
    // 提交布点数
    // 提交布点数
    submitPointCount() {
      if (!this.isValidPointCount) return;

      this.closePointCountPopup();
      this.loadingNetwork = true;

      axios.post('http://localhost:5000/api/hydraulic/generate-plan', {
        network_data: this.networkData,
        point_count: this.pointCount
      })
        .then(response => {
          this.loadingNetwork = false;

          if (response.data.success) {
            // 获取方案数据
            const planData = response.data.plan_data;

            if (!planData || !planData.sensors) {
              this.showNotification('方案数据格式不正确', 'error');
              return;
            }

            // 提取传感器节点ID，但不更新全局的selectedSensorNodes
            const sensorNodeIds = planData.sensors.map(sensor =>
              typeof sensor === 'object' ? sensor.node_id : sensor
            );

            // 创建一个新的方案数据对象，包含传感器节点ID
            const planWithSensors = {
              ...planData,
              sensorNodeIds: sensorNodeIds
            };

            // 打开方案详情弹窗，但不影响主画布
            this.openPlanPopup(planWithSensors);
            this.showNotification('方案生成成功', 'success');
          } else {
            this.showNotification('方案生成失败: ' + response.data.message, 'error');
          }
        })
        .catch(error => {
          this.loadingNetwork = false;
          console.error('生成方案错误:', error);
          this.showNotification('方案生成请求失败', 'error');
        });
    },
    // 显示方案详情
    showPlanDetails() {
      this.isPlanDetailsVisible = true;

      // 在弹窗显示后渲染可视化图
      this.$nextTick(() => {
        this.renderPlanVisualization();
      });
    },
    renderPlanVisualization() {
      console.log('开始渲染方案可视化');
      // 获取容器
      const container = document.getElementById('plan-visualization-svg');
      if (!container) {
        console.error('找不到可视化容器');
        return;
      }

      // 清空容器
      container.innerHTML = '';

      // 设置SVG尺寸
      const width = container.clientWidth || 600;
      const height = 400;

      // 确保容器高度设置正确
      container.style.height = height + 'px';

      // 创建SVG元素
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("width", width);
      svg.setAttribute("height", height);
      container.appendChild(svg);

      // 检查数据
      if (!this.planDetails || !this.networkData || !this.networkData.nodes) {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", width / 2);
        text.setAttribute("y", height / 2);
        text.setAttribute("text-anchor", "middle");
        text.textContent = '暂无布点方案数据';
        svg.appendChild(text);
        return;
      }

      // 获取传感器节点ID列表
      const sensorNodeIds = this.planDetails.sensorNodeIds ||
        (this.planDetails.sensors ?
          this.planDetails.sensors.map(s => typeof s === 'object' ? s.node_id : s) :
          []);

      console.log('传感器节点IDs:', sensorNodeIds);

      // 深拷贝网络数据以避免修改原始数据
      const nodes = JSON.parse(JSON.stringify(this.networkData.nodes));
      const links = JSON.parse(JSON.stringify(this.networkData.links));

      // 标记传感器节点
      nodes.forEach(node => {
        node.isSensor = sensorNodeIds.includes(node.id);
      });

      // 计算节点位置范围
      const xValues = nodes.map(n => n.x);
      const yValues = nodes.map(n => n.y);

      const xMin = Math.min(...xValues);
      const xMax = Math.max(...xValues);
      const yMin = Math.min(...yValues);
      const yMax = Math.max(...yValues);

      // 计算缩放和平移参数，确保图形完全显示在SVG中并留有边距
      const padding = 30;
      const availableWidth = width - padding * 2;
      const availableHeight = height - padding * 2;

      const xScale = availableWidth / (xMax - xMin || 1);
      const yScale = availableHeight / (yMax - yMin || 1);

      // 取较小的缩放比例以保持图形比例
      const scale = Math.min(xScale, yScale);

      // 创建一个转换坐标的函数
      const transformX = x => padding + (x - xMin) * scale;
      const transformY = y => padding + (y - yMin) * scale;

      // 先绘制连接线
      links.forEach(link => {
        const source = typeof link.source === 'string' ?
          nodes.find(n => n.id === link.source) : link.source;
        const target = typeof link.target === 'string' ?
          nodes.find(n => n.id === link.target) : link.target;

        if (source && target) {
          const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
          line.setAttribute("x1", transformX(source.x));
          line.setAttribute("y1", transformY(source.y));
          line.setAttribute("x2", transformX(target.x));
          line.setAttribute("y2", transformY(target.y));
          line.setAttribute("stroke", "#999");
          line.setAttribute("stroke-width", "1");
          svg.appendChild(line);
        }
      });

      // 绘制节点
      nodes.forEach(node => {
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", transformX(node.x));
        circle.setAttribute("cy", transformY(node.y));
        circle.setAttribute("r", node.isSensor ? "7" : "4");
        circle.setAttribute("fill", node.isSensor ? "#FF6347" : "#6CA6CD");
        circle.setAttribute("stroke", node.isSensor ? "#FF4500" : "#5F9EA0");
        circle.setAttribute("stroke-width", "1.5");
        svg.appendChild(circle);

        // 只为观测点添加节点ID标签
        if (node.isSensor) {
          const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
          text.setAttribute("x", transformX(node.x) + 8);
          text.setAttribute("y", transformY(node.y) + 3);
          text.setAttribute("font-size", "8px");
          text.setAttribute("fill", "#333");
          text.textContent = node.id;
          svg.appendChild(text);
        }
      });

      // 在这里直接添加图例，而不是调用 addLegendToSvg 方法
      // 将图例位置调整到更靠右上角，y坐标设为5
      const legendGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
      legendGroup.setAttribute("transform", `translate(${width - 100}, 5)`); // 将y坐标设为5，更靠上

      // 添加背景矩形
      const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      bgRect.setAttribute("x", 0);
      bgRect.setAttribute("y", 0);
      bgRect.setAttribute("width", 80);
      bgRect.setAttribute("height", 45);
      bgRect.setAttribute("fill", "white");
      bgRect.setAttribute("fill-opacity", "0.8");
      bgRect.setAttribute("rx", "3");
      bgRect.setAttribute("ry", "3");
      bgRect.setAttribute("stroke", "#ddd");
      bgRect.setAttribute("stroke-width", "1");
      legendGroup.appendChild(bgRect);

      // 普通节点图例
      const normalCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      normalCircle.setAttribute("cx", 10);
      normalCircle.setAttribute("cy", 10);
      normalCircle.setAttribute("r", 4);
      normalCircle.setAttribute("fill", "#6CA6CD");
      normalCircle.setAttribute("stroke", "#5F9EA0");
      normalCircle.setAttribute("stroke-width", "1.5");
      legendGroup.appendChild(normalCircle);

      const normalText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      normalText.setAttribute("x", 20);
      normalText.setAttribute("y", 14);
      normalText.setAttribute("font-size", "10px");
      normalText.setAttribute("fill", "#333");
      normalText.textContent = "普通节点";
      legendGroup.appendChild(normalText);

      // 观测点图例
      const sensorCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      sensorCircle.setAttribute("cx", 10);
      sensorCircle.setAttribute("cy", 30);
      sensorCircle.setAttribute("r", 7);
      sensorCircle.setAttribute("fill", "#FF6347");
      sensorCircle.setAttribute("stroke", "#FF4500");
      sensorCircle.setAttribute("stroke-width", "1.5");
      legendGroup.appendChild(sensorCircle);

      const sensorText = document.createElementNS("http://www.w3.org/2000/svg", "text");
      sensorText.setAttribute("x", 20);
      sensorText.setAttribute("y", 34);
      sensorText.setAttribute("font-size", "10px");
      sensorText.setAttribute("fill", "#333");
      sensorText.textContent = "观测点";
      legendGroup.appendChild(sensorText);

      svg.appendChild(legendGroup);

      console.log('方案可视化渲染完成');
    },
    // 关闭方案弹窗
    closePlanPopup() {
      this.showPlanPopup = false;
    },
    // 导出方案
    exportPlan() {
      if (!this.planDetails) {
        this.displayNotification('error', '没有可导出的方案数据');
        return;
      }

      // 获取传感器节点ID列表
      const sensorNodeIds = this.planDetails.sensorNodeIds ||
        (this.planDetails.sensors ?
          this.planDetails.sensors.map(s => typeof s === 'object' ? s.node_id : s) :
          []);

      if (sensorNodeIds.length === 0) {
        this.displayNotification('error', '没有可导出的传感器节点数据');
        return;
      }

      // 创建CSV内容
      let csvContent = "序号,节点ID\n";

      // 添加每行数据
      sensorNodeIds.forEach((nodeId, index) => {
        csvContent += `${index + 1},${nodeId}\n`;
      });

      // 创建Blob对象
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });

      // 创建下载链接
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);

      // 设置下载属性
      link.setAttribute('href', url);
      link.setAttribute('download', `${this.planDetails.plan_id || 'plan'}.csv`);
      link.style.visibility = 'hidden';

      // 添加到文档并触发点击
      document.body.appendChild(link);
      link.click();

      // 清理
      document.body.removeChild(link);
      this.displayNotification('success', '方案已导出为CSV文件');
    },
    // 高亮显示选中的传感器节点
    highlightSelectedNodes() {
      if (!this.$refs.networkSvg || !this.selectedSensorNodes.length) return;

      // 首先重置所有节点的样式
      d3.select(this.$refs.networkSvg)
        .selectAll('.node')
        .attr('r', d => d.size || 5)
        .attr('fill', d => d.color || '#69b3a2');

      // 高亮选中的节点
      d3.select(this.$refs.networkSvg)
        .selectAll('.node')
        .filter(d => this.selectedSensorNodes.includes(d.id))
        .attr('r', d => (d.size || 5) * 1.5)  // 放大1.5倍
        .attr('fill', '#ff5733')  // 使用醒目的颜色
        .attr('stroke', '#000')
        .attr('stroke-width', 2);

      // 添加动画效果（可选）
      d3.select(this.$refs.networkSvg)
        .selectAll('.node')
        .filter(d => this.selectedSensorNodes.includes(d.id))
        .transition()
        .duration(300)
        .attr('r', d => (d.size || 5) * 1.5)
        .attr('fill', '#ff5733');
    },
    updateSvgSize() {
      if (this.$refs.networkContainer) {
        this.svgWidth = this.$refs.networkContainer.clientWidth;
        this.svgHeight = this.$refs.networkContainer.clientHeight || 600;
      }
    },
    async uploadInpFile(event) {
      const file = event.target.files[0];
      if (!file) return;

      // 检查文件类型
      if (!file.name.toLowerCase().endsWith('.inp')) {
        this.displayNotification('error', '请上传.inp格式的文件');
        return;
      }
      try {
        const formData = new FormData();
        formData.append('file', file);

        this.loadingNetwork = true;
        this.displayNotification('info', '正在上传文件...');

        // 使用API端点上传文件
        const response = await axios.post('http://localhost:5000/api/hydraulic/upload-inp', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        if (response.data.success) {
          this.displayNotification('success', 'INP文件上传成功');
          this.currentFileName = file.name;
          // 上传成功后加载网络数据
          this.fetchNetworkData();
        } else {
          this.displayNotification('error', '上传失败: ' + response.data.error);
        }
      } catch (error) {
        console.error('上传文件出错:', error);
        this.displayNotification('error', '上传文件出错: ' + (error.response?.data?.error || error.message));
      } finally {
        this.loadingNetwork = false;
        // 重置文件输入，以便可以再次上传同一个文件
        event.target.value = '';
      }
    },
    async fetchNetworkData() {
      try {
        this.loadingNetwork = true;
        const response = await axios.get('http://localhost:5000/api/hydraulic/network-data');

        if (response.data.success) {
          // 先保存原始数据
          const originalData = response.data.data;
          console.log('原始数据:', originalData);

          // 处理节点坐标
          if (originalData && originalData.nodes) {
            // 定义视图尺寸
            const width = 1000; // 视图宽度
            const height = 600; // 视图高度

            // 转换节点坐标格式
            originalData.nodes = originalData.nodes.map((node, index) => {
              // 检查节点是否有 coordinates 数组
              if (node.coordinates && Array.isArray(node.coordinates) && node.coordinates.length >= 2) {
                // 将 coordinates 数组转换为 x 和 y 属性
                return {
                  ...node,
                  x: node.coordinates[0] * width,
                  y: node.coordinates[1] * height
                };
              }
              // 处理已有的 x 和 y 值（0到1之间的相对坐标）
              else if (typeof node.x === 'number' && typeof node.y === 'number') {
                // 将0-1之间的相对坐标转换为实际像素坐标
                return {
                  ...node,
                  x: node.x * width,
                  y: node.y * height
                };
              }
              // 如果没有有效坐标，生成随机坐标
              else {
                console.warn(`节点 ${index} 坐标无效，使用随机坐标:`, node);
                return {
                  ...node,
                  x: Math.random() * 800 + 100, // 100-900 范围内
                  y: Math.random() * 400 + 100  // 100-500 范围内
                };
              }
            });
          }

          // 更新处理后的数据
          this.networkData = originalData;

          // 调试信息
          if (originalData && originalData.nodes) {
            const nodes = originalData.nodes;
            console.log('处理后节点数量:', nodes.length);

            // 显示坐标范围
            const xValues = nodes.map(n => n.x).filter(x => !isNaN(x));
            const yValues = nodes.map(n => n.y).filter(y => !isNaN(y));

            if (xValues.length && yValues.length) {
              console.log('X范围:', Math.min(...xValues), '到', Math.max(...xValues));
              console.log('Y范围:', Math.min(...yValues), '到', Math.max(...yValues));
            }

            // 检查是否有节点坐标仍然无效
            const invalidNodes = nodes.filter(node =>
              typeof node.x !== 'number' || isNaN(node.x) ||
              typeof node.y !== 'number' || isNaN(node.y)
            );

            if (invalidNodes.length > 0) {
              console.error(`仍有 ${invalidNodes.length} 个节点坐标无效:`, invalidNodes);
            } else {
              console.log('所有节点坐标有效');
            }
          }

          this.displayNotification('success', '网络数据加载成功');
          this.centerNetworkGraph();
        } else {
          this.displayNotification('error', '加载网络数据失败: ' + response.data.error);
        }
      } catch (error) {
        console.error('获取网络数据出错:', error);
        this.displayNotification('error', '获取网络数据出错: ' + (error.response?.data?.error || error.message));
      } finally {
        this.loadingNetwork = false;
      }
    },

    refreshNetworkData() {
      this.fetchNetworkData();
    },

    centerNetworkGraph() {
      if (!this.networkData || !this.networkData.nodes || this.networkData.nodes.length === 0) return;

      // 计算节点的边界
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;

      this.networkData.nodes.forEach(node => {
        if (typeof node.x === 'number' && typeof node.y === 'number') {
          minX = Math.min(minX, node.x);
          minY = Math.min(minY, node.y);
          maxX = Math.max(maxX, node.x);
          maxY = Math.max(maxY, node.y);
        }
      });

      // 如果没有有效坐标，则退出
      if (minX === Infinity || minY === Infinity || maxX === -Infinity || maxY === -Infinity) {
        console.warn('无法确定网络边界，节点可能没有有效坐标');
        return;
      }

      // 计算网络的中心点
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;

      // 计算适当的缩放比例
      const graphWidth = maxX - minX;
      const graphHeight = maxY - minY;
      const containerWidth = this.svgWidth;
      const containerHeight = this.svgHeight;

      // 留出一些边距
      const padding = 50;
      const scaleX = (containerWidth - padding * 2) / (graphWidth || 1); // 避免除以零
      const scaleY = (containerHeight - padding * 2) / (graphHeight || 1);
      this.scale = Math.min(scaleX, scaleY, 1); // 限制最大缩放为1

      // 计算平移量，使网络居中
      this.translateX = (containerWidth / 2) - (centerX * this.scale);
      this.translateY = (containerHeight / 2) - (centerY * this.scale);
    },

    getNodeX(nodeId) {
      const node = this.networkData.nodes.find(n => n.id === nodeId);
      return node && typeof node.x === 'number' ? node.x : 0;
    },

    getNodeY(nodeId) {
      const node = this.networkData.nodes.find(n => n.id === nodeId);
      return node && typeof node.y === 'number' ? node.y : 0;
    },

    getNodeId(nodeId) {
      return nodeId;
    },

    getNodeRadius(nodeType) {
      switch (nodeType) {
        case 'Reservoir': return 8;
        case 'Tank': return 7;
        case 'Junction': return 5;
        default: return 5;
      }
    },

    getNodeColor(nodeType) {
      switch (nodeType) {
        case 'Reservoir': return '#3498db'; // 蓝色
        case 'Tank': return '#2ecc71';      // 绿色
        case 'Junction': return '#e74c3c';  // 红色
        default: return '#95a5a6';          // 灰色
      }
    },

    getLinkColor(linkType) {
      switch (linkType) {
        case 'Pipe': return '#34495e';      // 深灰色
        case 'Pump': return '#9b59b6';      // 紫色
        case 'Valve': return '#f39c12';     // 橙色
        default: return '#95a5a6';          // 灰色
      }
    },

    getElementTypeName(element) {
      if (element.node_type) {
        switch (element.node_type) {
          case 'Junction': return '节点';
          case 'Reservoir': return '水库';
          case 'Tank': return '水箱';
          default: return element.node_type;
        }
      } else if (element.link_type) {
        switch (element.link_type) {
          case 'Pipe': return '管道';
          case 'Pump': return '水泵';
          case 'Valve': return '阀门';
          default: return element.link_type;
        }
      }
      return '未知';
    },

    openElementPopup(element) {
      this.selectedElement = element;
      this.showElementPopup = true;
    },

    closeElementPopup() {
      this.showElementPopup = false;
    },

    handleKeyDown(event) {
      if (event.key === 'Escape') {
        this.closeElementPopup();
      }
    },

    displayNotification(type, message) {
      this.notificationType = type;
      this.notificationMessage = message;

      if (type === 'success') {
        this.notificationIcon = 'ti-check-circle';
      } else if (type === 'error') {
        this.notificationIcon = 'ti-alert-triangle';
      } else if (type === 'info') {
        this.notificationIcon = 'ti-info-circle';
      }

      this.notificationVisible = true;

      // 3秒后自动关闭
      setTimeout(() => {
        this.closeNotification();
      }, 3000);
    },

    closeNotification() {
      this.notificationVisible = false;
    },

    // 缩放功能
    zoomIn() {
      this.scale *= 1.2;
    },

    zoomOut() {
      this.scale /= 1.2;
    },

    resetZoom() {
      this.scale = 1;
      this.translateX = 0;
      this.translateY = 0;
      this.centerNetworkGraph();
    },

    onWheel(event) {
      event.preventDefault();
      const delta = event.deltaY > 0 ? -0.1 : 0.1;
      const newScale = this.scale * (1 + delta);

      // 限制缩放范围
      if (newScale > 0.1 && newScale < 5) {
        // 计算鼠标位置相对于SVG的坐标
        const rect = this.$refs.networkSvg.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        // 计算鼠标位置在缩放前的坐标系中的位置
        const oldMouseInGraphX = (mouseX - this.translateX) / this.scale;
        const oldMouseInGraphY = (mouseY - this.translateY) / this.scale;

        // 更新缩放比例
        this.scale = newScale;

        // 计算新的平移量，使鼠标位置保持不变
        this.translateX = mouseX - oldMouseInGraphX * this.scale;
        this.translateY = mouseY - oldMouseInGraphY * this.scale;
      }
    },

    // 开始拖动
    startDrag(event) {
      // 只在左键点击时触发拖动
      if (event.type === 'mousedown' && event.button !== 0) return;

      // 阻止默认行为和冒泡
      event.preventDefault();
      event.stopPropagation();

      // 获取鼠标/触摸位置
      const clientX = event.clientX || (event.touches && event.touches[0].clientX);
      const clientY = event.clientY || (event.touches && event.touches[0].clientY);

      // 设置拖动状态
      this.isDragging = true;
      this.dragStartX = clientX;
      this.dragStartY = clientY;

      // 更改光标样式
      document.body.style.cursor = 'grabbing';
    },

    // 处理鼠标移动
    handleMouseMove(event) {
      if (!this.isDragging) return;

      const clientX = event.clientX;
      const clientY = event.clientY;

      // 计算移动距离
      const deltaX = clientX - this.dragStartX;
      const deltaY = clientY - this.dragStartY;

      // 更新起始点，用于下一次移动计算
      this.dragStartX = clientX;
      this.dragStartY = clientY;

      // 更新平移量
      this.translateX += deltaX;
      this.translateY += deltaY;
    },

    // 处理触摸移动
    handleTouchMove(event) {
      if (!this.isDragging || !event.touches.length) return;

      // 防止滚动
      event.preventDefault();

      const touch = event.touches[0];

      // 计算移动距离
      const deltaX = touch.clientX - this.dragStartX;
      const deltaY = touch.clientY - this.dragStartY;

      // 更新起始点
      this.dragStartX = touch.clientX;
      this.dragStartY = touch.clientY;

      // 更新平移量
      this.translateX += deltaX;
      this.translateY += deltaY;
    },

    // 结束拖动
    handleMouseUp() {
      if (!this.isDragging) return;

      this.isDragging = false;
      document.body.style.cursor = '';
    },

    // 结束触摸拖动
    handleTouchEnd() {
      if (!this.isDragging) return;

      this.isDragging = false;
    },
    updateNetworkWithSimulationData(simulationData) {
      // 保存原有的平移和缩放状态
      const currentTranslateX = this.translateX;
      const currentTranslateY = this.translateY;
      const currentScale = this.scale;

      // 更新网络数据
      this.networkData = simulationData;

      // 恢复平移和缩放状态
      this.translateX = currentTranslateX;
      this.translateY = currentTranslateY;
      this.scale = currentScale;

      // 显示成功通知
      this.showNotification('模拟数据已更新', 'success');
    },
    showNotification(message, type = 'info') {
      this.notificationMessage = message;
      this.notificationType = type;

      switch (type) {
        case 'success':
          this.notificationIcon = 'ti-check-circle';
          break;
        case 'error':
          this.notificationIcon = 'ti-alert-circle';
          break;
        default:
          this.notificationIcon = 'ti-info-circle';
      }

      this.notificationVisible = true;

      // 5秒后自动关闭通知
      setTimeout(() => {
        this.closeNotification();
      }, 5000);
    },
    // 运行模拟
    // 在runSimulation方法中，修改处理模拟数据的部分

    async runSimulation() {
      if (!this.networkData || this.isSimulating) return;

      this.isSimulating = true;
      this.showNotification('正在运行水力模拟...', 'info');

      try {
        // 调用模拟API
        const response = await axios.post('http://localhost:5000/api/hydraulic/simulate');
        console.log('模拟响应数据:', response.data);

        if (response.data.success) {
          // 获取模拟后的网络数据
          const simulatedData = response.data.network_data;

          if (simulatedData && simulatedData.nodes) {
            // 定义视图尺寸
            const width = 1000;
            const height = 600;

            // 处理节点坐标和确保基础需求数据保留
            simulatedData.nodes = simulatedData.nodes.map((node, index) => {
              // 查找原始网络数据中对应的节点
              const originalNode = this.networkData.nodes && this.networkData.nodes[index]
                ? this.networkData.nodes[index]
                : null;

              // 确保保留基础需求数据
              if (originalNode && originalNode.base_demand !== undefined && node.base_demand === undefined) {
                node.base_demand = originalNode.base_demand;
                node.demand_unit = originalNode.demand_unit || 'm^3/s';
              }

              // 检查节点是否有 coordinates 数组
              if (node.coordinates && Array.isArray(node.coordinates) && node.coordinates.length >= 2) {
                return {
                  ...node,
                  x: node.coordinates[0] * width,
                  y: node.coordinates[1] * height
                };
              }
              // 处理已有的 x 和 y 值（0到1之间的相对坐标）
              else if (typeof node.x === 'number' && typeof node.y === 'number') {
                // 将0-1之间的相对坐标转换为实际像素坐标
                return {
                  ...node,
                  x: node.x * width,
                  y: node.y * height
                };
              }
              // 如果没有有效坐标，使用原始网络数据中对应节点的坐标（如果有的话）
              else if (originalNode) {
                if (typeof originalNode.x === 'number' && typeof originalNode.y === 'number') {
                  return {
                    ...node,
                    x: originalNode.x,
                    y: originalNode.y
                  };
                } else {
                  // 如果原始数据中也没有有效坐标，生成随机坐标
                  console.warn(`节点 ${index} 坐标无效，使用随机坐标:`, node);
                  return {
                    ...node,
                    x: Math.random() * 800 + 100, // 100-900 范围内
                    y: Math.random() * 400 + 100  // 100-500 范围内
                  };
                }
              }
              // 最后的备选方案：生成随机坐标
              else {
                console.warn(`节点 ${index} 坐标无效，使用随机坐标:`, node);
                return {
                  ...node,
                  x: Math.random() * 800 + 100,
                  y: Math.random() * 400 + 100
                };
              }
            });

            // 调试信息
            console.log('处理后节点数量:', simulatedData.nodes.length);
            console.log('节点数据示例:', simulatedData.nodes.slice(0, 3));

            const xValues = simulatedData.nodes.map(n => n.x).filter(x => !isNaN(x));
            const yValues = simulatedData.nodes.map(n => n.y).filter(y => !isNaN(y));

            if (xValues.length && yValues.length) {
              console.log('X范围:', Math.min(...xValues), '到', Math.max(...xValues));
              console.log('Y范围:', Math.min(...yValues), '到', Math.max(...yValues));
            }

            // 保存当前的视图状态
            const currentTranslateX = this.translateX;
            const currentTranslateY = this.translateY;
            const currentScale = this.scale;

            // 更新网络图数据
            this.networkData = simulatedData;

            // 恢复视图状态
            this.translateX = currentTranslateX;
            this.translateY = currentTranslateY;
            this.scale = currentScale;

            this.showNotification('模拟完成，网络数据已更新', 'success');
          } else {
            this.showNotification('模拟完成，但返回的数据格式不正确', 'error');
          }
        } else {
          this.showNotification(`模拟失败: ${response.data.error}`, 'error');
        }
      } catch (error) {
        console.error('模拟出错:', error);
        this.showNotification(`模拟出错: ${error.message}`, 'error');
      } finally {
        this.isSimulating = false;
      }
    },
    shouldShowFlowArrow(link) {
      // 检查流量是否存在且不为零（使用更小的阈值）
      return link.flow !== undefined && Math.abs(parseFloat(link.flow)) > 1e-18;
    },

    // 获取连接的中点X坐标
    getMidpointX(link) {
      return (this.getNodeX(link.source) + this.getNodeX(link.target)) / 2;
    },

    // 获取连接的中点Y坐标
    getMidpointY(link) {
      return (this.getNodeY(link.source) + this.getNodeY(link.target)) / 2;
    },

    // 获取箭头X方向（根据流量正负确定方向）
    getArrowDirectionX(link) {
      const dx = this.getNodeX(link.target) - this.getNodeX(link.source);
      const length = Math.sqrt(
        Math.pow(this.getNodeX(link.target) - this.getNodeX(link.source), 2) +
        Math.pow(this.getNodeY(link.target) - this.getNodeY(link.source), 2)
      );

      // 根据流量正负确定方向
      const flowValue = parseFloat(link.flow);
      const direction = flowValue >= 0 ? 1 : -1;

      return (dx / length) * direction;
    },

    // 获取箭头Y方向（根据流量正负确定方向）
    getArrowDirectionY(link) {
      const dy = this.getNodeY(link.target) - this.getNodeY(link.source);
      const length = Math.sqrt(
        Math.pow(this.getNodeX(link.target) - this.getNodeX(link.source), 2) +
        Math.pow(this.getNodeY(link.target) - this.getNodeY(link.source), 2)
      );

      // 根据流量正负确定方向
      const flowValue = parseFloat(link.flow);
      const direction = flowValue >= 0 ? 1 : -1;

      return (dy / length) * direction;
    }
  }
}
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

.control-buttons .btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  height: 40px;
  min-width: 120px;
}

.control-buttons .btn i {
  margin-right: 8px;
  font-size: 16px;
}

.control-buttons {
  display: flex;
  gap: 12px;
}

.notification {
  padding: 12px 15px;
  margin-bottom: 20px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  position: relative;
}

.notification.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.notification.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.notification.info {
  background-color: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

.notification i {
  margin-right: 10px;
}

.notification .close-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: inherit;
  opacity: 0.7;
}

.notification .close-btn:hover {
  opacity: 1;
}

.network-container {
  position: relative;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  background-color: #f8f9fa;
  height: 600px;
  overflow: hidden;
}

.network-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  display: flex;
  gap: 5px;
}

.network-legend {
  position: absolute;
  bottom: 10px;
  left: 10px;
  z-index: 10;
  background-color: rgba(255, 255, 255, 0.9);
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.legend-color {
  width: 15px;
  height: 15px;
  border-radius: 3px;
}

.legend-color.junction {
  background-color: #e74c3c;
}

.legend-color.reservoir {
  background-color: #3498db;
}

.legend-color.tank {
  background-color: #2ecc71;
}

.legend-color.pipe {
  background-color: #34495e;
}

.legend-color.pump {
  background-color: #9b59b6;
}

.legend-color.valve {
  background-color: #f39c12;
}

.svg-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  cursor: grab;
}

.svg-container:active {
  cursor: grabbing;
}

.network-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.7);
  z-index: 20;
}

.node {
  cursor: pointer;
}

.node:hover {
  stroke: #000;
  stroke-width: 2px;
}

.link {
  cursor: pointer;
}

.link:hover {
  stroke-width: 4px;
}

.node-label {
  pointer-events: none;
  user-select: none;
  font-family: Arial, sans-serif;
}

.action-buttons-container {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.action-button {
  min-width: 150px;
}

/* 弹窗样式 */
.element-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.element-popup {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  width: 400px;
  max-width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.element-popup-header {
  padding: 15px 20px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.element-popup-header h5 {
  margin: 0;
  font-weight: 600;
}

.element-popup-body {
  padding: 20px;
  overflow-y: auto;
  max-height: 60vh;
}

.element-popup-footer {
  padding: 15px 20px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: flex-end;
}

.detail-item {
  margin-bottom: 10px;
  display: flex;
}

.detail-label {
  font-weight: 600;
  width: 100px;
  flex-shrink: 0;
}

.detail-value {
  flex-grow: 1;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #6c757d;
}

.close-btn:hover {
  color: #343a40;
}

.link {
  cursor: pointer;
}

.link:hover {
  stroke-width: 4px;
}

/* 方案信息样式 */
.plan-info {
  background-color: #f8f9fa;
  border-radius: 5px;
  padding: 15px;
  margin-bottom: 20px;
}

/* 表格样式 */
.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 8px;
  border-bottom: 1px solid #dee2e6;
}

.table-striped tbody tr:nth-of-type(odd) {
  background-color: rgba(0, 0, 0, 0.05);
}

/* 按钮间距 */
.element-popup-footer .btn {
  margin-left: 10px;
}

.coverage-chart-container {
  height: 400px;
  width: 100%;
  margin-bottom: 20px;
}

.coverage-table {
  max-height: 300px;
  overflow-y: auto;
}

.table-responsive {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 8px;
  border-bottom: 1px solid #dee2e6;
}

.table-striped tbody tr:nth-of-type(odd) {
  background-color: rgba(0, 0, 0, 0.05);
}

.node.selected-sensor {
  filter: drop-shadow(0 0 4px rgba(255, 152, 0, 0.8));
  cursor: pointer;
}

/* 表单样式 */
.form-group {
  margin-bottom: 1rem;
}

.form-control {
  display: block;
  width: 100%;
  padding: 0.375rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  color: #495057;
  background-color: #fff;
  background-clip: padding-box;
  border: 1px solid #ced4da;
  border-radius: 0.25rem;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-text {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.875rem;
  color: #6c757d;
}

.visualization-container {
  margin: 20px 0;
  padding: 15px;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.legend {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-left: 15px;
}

.legend-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-right: 5px;
  border-radius: 2px;
}

.plan-visualization-container {
  margin: 15px 0;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 10px;
  background-color: #f8f9fa;
}

#plan-visualization-svg {
  width: 100%;
  height: 400px;
  background-color: white;
  border-radius: 4px;
  overflow: hidden;
}

/* 添加到<style>部分 */
.plan-visualization-container {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.visualization-container {
  width: 100%;
  height: 400px;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}

/* 确保弹窗样式正确 */
.element-popup {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  max-width: 90%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1001;
}

.element-popup-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.visualization-container {
  width: 100%;
  height: 400px;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 15px;
}

.plan-info {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.plan-info-item {
  margin-bottom: 8px;
}

.plan-info-item .label {
  font-weight: 500;
  margin-right: 10px;
  display: inline-block;
  width: 100px;
}

.plan-visualization h6,
.plan-info h6,
.sensor-list h6 {
  margin-bottom: 10px;
  font-weight: 600;
}

.visualization-container {
  width: 100%;
  height: 400px;
  background-color: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 15px;
}

.plan-info {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.plan-info-item {
  margin-bottom: 8px;
}

.plan-info-item .label {
  font-weight: 500;
  margin-right: 10px;
  display: inline-block;
  width: 100px;
}

.plan-visualization h6,
.plan-info h6,
.sensor-list h6 {
  margin-bottom: 10px;
  font-weight: 600;
}

.visualization-container {
  width: 100%;
  height: 400px;
  border: 1px solid #ddd;
  margin-top: 15px;
  margin-bottom: 15px;
  overflow: hidden;
}

.plan-info-title {
  margin-bottom: 20px;
  /* 增加下方间距 */
  font-weight: 600;
}

/* 为数值添加加粗样式 */
.plan-info-value {
  font-weight: bold;
}
</style>
