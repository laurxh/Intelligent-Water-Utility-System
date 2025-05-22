<!-- 调度算法-->
<template>
    <div class="content">
        <!-- 标题 -->
        <div class="header-container">
            <h4 class="title">水网络拓扑图</h4>
            <div class="control-buttons">
                <button class="btn btn-primary btn-sm" @click="refreshNetworkData">
                    <i class="ti-reload"></i> 刷新数据
                </button>
                <button class="btn btn-info btn-sm" @click="generateRandomDemands">
                    <i class="ti-bar-chart"></i> 生成随机需水量
                </button>
                <button class="btn btn-success btn-sm" @click="openImportModal">
                    <i class="ti-import"></i> 导入需水量
                </button>
                <button class="btn btn-warning btn-sm" @click="openUpdateDemandModal">
                    <i class="ti-pencil"></i> 修改需水量
                </button>
            </div>

        </div>

        <!-- 通知提示 -->
        <div v-if="notificationVisible" :class="['notification', notificationType]">
            <i :class="notificationIcon"></i>
            <span>{{ notificationMessage }}</span>
            <button class="close-btn" @click="closeNotification">×</button>
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
                <div class="legend-item">
                    <div class="legend-color water-plant"></div>
                    <span>水厂</span>
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
                    <g :transform="`translate(${translateX},${translateY}) scale(${scale})`">
                        <!-- 连接 -->
                        <line v-for="(link, index) in networkData.links" :key="`link-${index}`"
                            :x1="getNodeX(link.source)" :y1="getNodeY(link.source)" :x2="getNodeX(link.target)"
                            :y2="getNodeY(link.target)" :class="`link ${link.link_type.toLowerCase()}`"
                            :stroke="getLinkColor(link.link_type)" :stroke-width="link.link_type === 'Pipe' ? 2 : 3"
                            :stroke-dasharray="link.link_type === 'Pump' ? '5,5' : 'none'"
                            @click.stop="openElementPopup(link)" />

                        <!-- 节点 -->
                        <!-- 修改节点渲染部分 -->
                        <circle v-for="(node, index) in networkData.nodes" :key="`node-${index}`" :cx="node.x"
                            :cy="node.y" :r="node.is_water_plant ? 7 : getNodeRadius(node.node_type)"
                            :fill="node.is_water_plant ? '#d35400' : getNodeColor(node.node_type)" stroke="#fff"
                            stroke-width="1.5"
                            :class="`node ${node.is_water_plant ? 'water-plant' : node.node_type.toLowerCase()}`"
                            @click.stop="openElementPopup(node)" />


                        <!-- 节点标签 -->
                        <text v-for="(node, index) in networkData.nodes" :key="`label-${index}`" :x="node.x + 12"
                            :y="node.y + 4" font-size="10px" class="node-label">
                            {{ node.id }}
                        </text>
                    </g>
                    <!-- 水厂需水量标签（带框） -->
                    <!-- 水厂需水量标签（带框） -->
                    <!-- 左上角水厂需水量面板（仅在调度运行后显示） -->
                    <g v-if="isScheduleRunCompleted" class="demand-info-panel">
                        <!-- 面板背景 -->
                        <rect x="10" y="10" :width="180" height="30" rx="5" ry="5" fill="rgba(255, 255, 255, 0.95)"
                            stroke="#d35400" stroke-width="1" />

                        <!-- 标题 -->
                        <text x="20" y="30" font-size="14px" font-weight="bold" fill="#333">
                            水厂需水量
                        </text>

                        <!-- 需水量列表（单独的面板） -->
                        <g v-for="(node, index) in waterPlantNodes" :key="`demand-panel-${index}`">
                            <rect x="10" :y="50 + (index * 30)" width="180" height="25" rx="3" ry="3" fill="white"
                                stroke="#d3d3d3" stroke-width="1" />

                            <text :x="20" :y="68 + (index * 30)" font-size="12px" fill="#333">
                                {{ node.id }}：{{ formatDemand(node) }}
                            </text>
                        </g>
                    </g>

                </svg>
                <div class="network-water-plants" v-if="networkData && waterPlantNodes.length > 0 && hasRunSchedule">
                    <div class="panel-header">水厂需水量</div>
                    <div class="water-plant-list">
                        <div class="water-plant-item" v-for="(node, index) in waterPlantNodes" :key="`wp-${index}`">
                            <span class="water-plant-id">{{ node.id }}:</span>
                            <span class="water-plant-demand">{{ formatDemand(node) }}</span>
                        </div>
                    </div>
                </div>
                <div class="export-buttons" v-if="hasRunSchedule">
                    <button class="btn btn-info btn-sm" @click="exportWaterPlantData">
                        <i class="ti-download"></i> 导出需水量
                    </button>
                    <button class="btn btn-danger btn-sm" @click="generateHeatmap($event)">
                        <i class="ti-map"></i> 生成热力图
                    </button>
                </div>
            </div>
        </div>
        <div v-if="showImportModal" class="element-popup-overlay" @click="closeImportModal">
            <div class="element-popup" @click.stop>
                <div class="element-popup-header">
                    <h5>导入需水量数据</h5>
                    <button class="close-btn" @click="closeImportModal">×</button>
                </div>
                <div class="element-popup-body">
                    <p>请选择CSV文件，格式为：第一列为节点ID，第二列为需水量。</p>
                    <div class="form-group">
                        <label for="csv-file" class="form-label">CSV文件</label>
                        <input type="file" id="csv-file" style="display:none" accept=".csv" ref="fileInput"
                            @change="handleFileChange">
                        <div class="file-input-container">
                            <div class="file-input-box" @click="triggerFileInput">
                                {{ selectedFileName || '未选择文件' }}
                            </div>
                        </div>
                    </div>
                    <div v-if="importError" class="alert alert-danger mt-3">
                        {{ importError }}
                    </div>
                </div>
                <div class="element-popup-footer">
                    <button class="btn btn-secondary mr-2" @click="closeImportModal">取消</button>
                    <button class="btn btn-primary" @click="importDemands" :disabled="isImporting">
                        {{ isImporting ? '导入中...' : '导入' }}
                    </button>
                </div>
            </div>
        </div>
        <!-- 元素详情弹窗 -->
        <div v-if="importMessage" :class="['import-message', importMessageType]">
            {{ importMessage }}
            <ul v-if="importErrors.length > 0" class="error-list">
                <li v-for="(error, index) in importErrors" :key="index">{{ error }}</li>
            </ul>
        </div>
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
                        <!-- 只有在没有实际需水量时才显示基础需水量 -->
                        <div class="detail-item"
                            v-if="selectedElement.node_type === 'Junction' && selectedElement.actual_demand === undefined && selectedElement.base_demand !== undefined">
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
                            v-if="selectedElement.node_type === 'Reservoir' && selectedElement.current_head !== undefined">
                            <span class="detail-label">当前水头:</span>
                            <span class="detail-value">{{ selectedElement.current_head }} m</span>
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
        <div id="heatmapModal" class="heatmap-modal" v-if="showHeatmapModal">
            <div class="heatmap-modal-content">
                <div class="heatmap-modal-header">
                    <span class="heatmap-close-btn" @click="closeHeatmapModal">&times;</span>
                    <h2 class="heatmap-modal-title">压力热力图</h2>
                </div>
                <div class="heatmap-modal-body">
                    <img id="heatmapImage" :src="heatmapImageUrl" alt="网络热力图">
                    <div v-if="loadingHeatmap" class="heatmap-loading">
                        <div class="spinner-border text-primary" role="status">
                            <span class="sr-only">加载中...</span>
                        </div>
                    </div>
                </div>
                <div class="heatmap-modal-footer">
                    <button id="downloadHeatmapBtn" class="btn btn-success" @click="downloadHeatmap">
                        <i class="ti-download"></i> 下载热力图
                    </button>
                </div>
            </div>
        </div>
        <!-- 底部分隔线 -->
        <hr class="mt-5 mb-4">

        <!-- 底部操作按钮 -->
        <div class="action-buttons-container">
            <button class="btn btn-primary action-button" @click="runSimulation"
                :disabled="!networkData || isSimulating">
                <i class="ti-control-play mr-1"></i>
                {{ isSimulating ? '计算中...' : '运行调度' }}
            </button>
        </div>
        <div v-if="showUpdateDemandModal" class="element-popup-overlay" @click="closeUpdateDemandModal">
            <div class="element-popup" @click.stop>
                <div class="element-popup-header">
                    <h5>修改节点需水量</h5>
                    <button class="close-btn" @click="closeUpdateDemandModal">×</button>
                </div>
                <div class="element-popup-body">
                    <div class="form-group">
                        <label for="node-id" class="form-label">节点ID</label>
                        <input type="text" id="node-id" class="form-control" v-model="updateDemandForm.nodeId"
                            placeholder="请输入节点ID">
                    </div>
                    <div class="form-group mt-3">
                        <label for="demand-value" class="form-label">需水量</label>
                        <input type="number" id="demand-value" class="form-control" v-model="updateDemandForm.demand"
                            step="0.001" min="0" placeholder="请输入需水量值">
                        <small class="form-text text-muted">单位：立方米/秒</small>
                    </div>
                    <div v-if="updateDemandError" class="alert alert-danger mt-3">
                        {{ updateDemandError }}
                    </div>
                </div>
                <div class="element-popup-footer">
                    <button class="btn btn-secondary mr-2" @click="closeUpdateDemandModal">取消</button>
                    <button class="btn btn-primary" @click="updateDemand" :disabled="isUpdatingDemand">
                        {{ isUpdatingDemand ? '更新中...' : '更新' }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>


<script>
import axios from 'axios';

export default {
    data() {
        return {
            notificationVisible: false,
            notificationType: 'success',
            notificationMessage: '',
            notificationIcon: 'ti-check-circle',

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

            showImportModal: false,
            isImporting: false,
            importError: null,

            // 修改需水量相关
            showUpdateDemandModal: false,
            isUpdatingDemand: false,
            updateDemandError: null,
            notificationTimeout: null,
            updateDemandForm: {
                nodeId: '',
                demand: null
            },
            selectedFileName: '',
            selectedFile: null,
            hasRunSchedule: false,// 初始为false，运行调度后设置为true
            scheduledData: null, // 用于保存调度结果数据
            showHeatmapModal: false,
            heatmapImageUrl: '',
            loadingHeatmap: false,
            importMessage: '',
            importMessageType: 'success',
            importErrors: [],
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
            this.fetchNetworkData();
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
    computed: {
        waterPlantNodes() {
            if (!this.networkData || !this.networkData.nodes) return [];

            // 获取所有符合条件的水厂节点和 ID 为 26 的节点
            const nodes = this.networkData.nodes.filter(node =>
                (node.is_water_plant && (node.actual_demand !== undefined || node.base_demand !== undefined)) ||
                node.id === '26'
            );
            console.log(nodes)
            // 按 ID 排序
            return nodes.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }));
        }
    },
    methods: {

        exportWaterPlantData() {
            if (!this.scheduledData || !this.scheduledData.nodes || this.scheduledData.nodes.length === 0) {
                this.displayNotification('error', '没有可导出的水厂数据', 5000);
                return;
            }

            try {
                // 显示加载中通知
                this.displayNotification('info', '正在导出水厂需水量数据...', 5000);

                // 根据is_water_plant属性筛选水厂节点
                let waterPlantData = this.scheduledData.nodes
                    .filter(node => node.is_water_plant === true)
                    .map(node => {
                        // 优先级：actual_demand > base_demand > inflow
                        let demand;
                        if (node.actual_demand !== undefined) {
                            demand = node.actual_demand;
                        } else if (node.base_demand !== undefined) {
                            demand = node.base_demand;
                        } else if (node.inflow !== undefined) {
                            demand = node.inflow;
                        } else {
                            demand = 0; // 默认值为0
                        }

                        return {
                            id: node.id,
                            demand: demand
                        };
                    });

                // 特殊处理：添加节点26（即使它的is_water_plant为false）
                const node26 = this.scheduledData.nodes.find(node => node.id === '26');
                if (node26) {
                    let demand26;
                    if (node26.actual_demand !== undefined) {
                        demand26 = node26.actual_demand;
                    } else if (node26.base_demand !== undefined) {
                        demand26 = node26.base_demand;
                    } else if (node26.inflow !== undefined) {
                        demand26 = node26.inflow;
                    } else {
                        demand26 = 0;
                    }

                    // 检查节点26是否已经在列表中（避免重复）
                    const exists = waterPlantData.some(node => node.id === '26');
                    if (!exists) {
                        waterPlantData.push({
                            id: '26',
                            demand: demand26
                        });
                    }
                }

                // 按ID排序
                waterPlantData = waterPlantData.sort((a, b) =>
                    a.id.localeCompare(b.id, undefined, { numeric: true })
                );

                // 检查是否有水厂数据
                if (waterPlantData.length === 0) {
                    this.displayNotification('error', '未找到任何水厂节点', 5000);
                    return;
                }

                // 创建CSV内容
                let csvContent = "水厂ID,需水量(m³/s)\n";
                waterPlantData.forEach(plant => {
                    csvContent += `${plant.id},${plant.demand}\n`;
                });

                // 创建Blob对象，添加BOM标记以支持中文
                const blob = new Blob(["\uFEFF" + csvContent], { type: 'text/csv;charset=utf-8;' });

                // 创建下载链接
                const link = document.createElement('a');
                const url = URL.createObjectURL(blob);

                // 设置下载属性
                const timestamp = new Date().toISOString().replace(/[:.]/g, '_').replace(/T/g, '_').substring(0, 19);
                link.setAttribute('href', url);
                link.setAttribute('download', `water_plant_demands_${timestamp}.csv`);
                link.style.visibility = 'hidden';

                // 添加到文档并触发点击
                document.body.appendChild(link);
                link.click();

                // 清理
                document.body.removeChild(link);
                URL.revokeObjectURL(url);

                this.displayNotification('success', '水厂需水量数据导出成功', 5000);
                console.log('已导出水厂数据:', waterPlantData);
            } catch (error) {
                console.error('导出水厂数据出错:', error);
                this.displayNotification('error', '导出出错: ' + error.message, 8000);
            }
        },

        formatDemand(node) {
            // 优先使用 actual_demand，其次使用 base_demand，最后使用 inflow
            let demand;
            if (node.actual_demand !== undefined) {
                demand = node.actual_demand;
            } else if (node.base_demand !== undefined) {
                demand = node.base_demand;
            } else if (node.inflow !== undefined) {
                demand = node.inflow;
            }

            // 检查值是否为 NaN 或 undefined
            if (demand === undefined || isNaN(demand)) {
                return '0.0000000000 m³/s';
            }

            // 格式化数值，保留10位小数
            return `${demand.toFixed(10)} m³/s`;
        },
        getNodeColor(nodeType) {
            const colorMap = {
                'Junction': '#e74c3c',  // 红色
                'Reservoir': '#3498db', // 蓝色
                'Tank': '#2ecc71',      // 绿色
                'Pump': '#9b59b6',      // 紫色
                'Valve': '#f39c12',     // 橙色
                'WaterPlant': '#d35400' // 深橙色/棕色 - 水厂颜色
            };
            return colorMap[nodeType] || '#e74c3c'; // 默认红色
        },
        onScheduleCompleted() {
            this.isScheduleRunCompleted = true;
        },
        getNodeRadius(nodeType) {
            if (nodeType === 'WaterPlant') {
                return 7; // 水厂节点稍大一些
            }
            return 5; // 默认节点大小
        },

        // 修改元素详情弹窗中显示的类型名称
        getElementTypeName(element) {
            // 首先检查是否是水厂
            if (element && element.is_water_plant === true) {
                return '水厂';
            }

            // 如果不是水厂，再判断其他类型
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
        updateSvgSize() {
            if (this.$refs.networkContainer) {
                this.svgWidth = this.$refs.networkContainer.clientWidth;
                this.svgHeight = this.$refs.networkContainer.clientHeight || 600;
            }
        },

        async fetchNetworkData() {
            try {
                this.loadingNetwork = true;
                const response = await axios.get('http://localhost:5000/api/scheduler/network/data');

                if (response.data.success) {
                    // 先保存原始数据
                    const originalData = response.data.data;
                    console.log('原始数据:', originalData);

                    // 处理节点坐标
                    if (originalData && originalData.nodes) {
                        // 转换节点坐标格式
                        originalData.nodes = originalData.nodes.map((node, index) => {
                            // 检查节点是否有 coordinates 数组
                            if (node.coordinates && Array.isArray(node.coordinates) && node.coordinates.length >= 2) {
                                // 将 coordinates 数组转换为 x 和 y 属性
                                const width = 1000; // 视图宽度
                                const height = 600; // 视图高度

                                return {
                                    ...node,
                                    x: node.coordinates[0] * width, // 缩放 x 坐标
                                    y: node.coordinates[1] * height // 缩放 y 坐标
                                };
                            } else if (typeof node.x !== 'number' || isNaN(node.x) ||
                                typeof node.y !== 'number' || isNaN(node.y)) {
                                // 如果没有有效坐标，生成随机坐标
                                console.warn(`节点 ${index} 坐标无效，使用随机坐标:`, node);
                                return {
                                    ...node,
                                    x: Math.random() * 800 + 100, // 100-900 范围内
                                    y: Math.random() * 400 + 100  // 100-500 范围内
                                };
                            }

                            // 已有有效的 x 和 y，直接返回
                            return node;
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
            // 首先检查是否是水厂
            if (element.is_water_plant) {
                return '水厂';
            }

            // 如果不是水厂，再判断其他类型
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
            return '未知类型';
        },

        openElementPopup(element) {
            this.selectedElement = element;
            this.showElementPopup = true;
            console.log('Selected element:', this.selectedElement);
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
            }, 5000);
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
            // 先清除任何现有的定时器
            if (this.notificationTimeout) {
                clearTimeout(this.notificationTimeout);
                this.notificationTimeout = null;
            }

            // 设置通知内容和可见性
            this.notificationMessage = message;
            this.notificationType = type;
            this.notificationVisible = true;

            // 根据通知类型设置图标和自动关闭行为
            switch (type) {
                case 'success':
                    this.notificationIcon = 'ti-check-circle';
                    // 成功通知5秒后自动关闭
                    this.notificationTimeout = setTimeout(() => {
                        this.closeNotification();
                    }, 5000);
                    break;
                case 'error':
                    this.notificationIcon = 'ti-alert-circle';
                    // 错误通知不设置自动关闭定时器
                    break;
                case 'warning':
                    this.notificationIcon = 'ti-alert-triangle';
                    // 警告通知5秒后自动关闭
                    this.notificationTimeout = setTimeout(() => {
                        this.closeNotification();
                    }, 5000);
                    break;
                default: // info
                    this.notificationIcon = 'ti-info-circle';
                    // 默认通知5秒后自动关闭
                    this.notificationTimeout = setTimeout(() => {
                        this.closeNotification();
                    }, 5000);
            }

            // 确保错误通知显示在视口中（可选）
            if (type === 'error') {
                // 如果有通知容器，确保它可见
                const notificationEl = document.querySelector('.notification-container');
                if (notificationEl) {
                    notificationEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        },
        // 运行模拟
        async runSimulation() {
            if (!this.networkData || this.isSimulating) return;

            this.isSimulating = true;
            this.showNotification('正在运行水力模拟...', 'info');

            try {
                // 调用模拟API
                const response = await axios.post('http://localhost:5000/api/scheduler/network/simulate');
                console.log('模拟响应数据:', response.data);

                if (response.data.success) {
                    // 获取模拟后的网络数据
                    const simulatedData = response.data.network_data;
                    this.scheduledData = JSON.parse(JSON.stringify(response.data.network_data));
                    if (simulatedData && simulatedData.nodes) {
                        // 处理节点坐标
                        simulatedData.nodes = simulatedData.nodes.map(node => {
                            if (node.coordinates && Array.isArray(node.coordinates) && node.coordinates.length >= 2) {
                                const width = 1000;
                                const height = 600;

                                return {
                                    ...node,
                                    x: node.coordinates[0] * width,
                                    y: node.coordinates[1] * height
                                };
                            }
                            return node;
                        });

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
                        this.hasRunSchedule = true;
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
        async generateRandomDemands() {
            try {
                this.showNotification('正在生成随机需水量...', 'info');

                const response = await axios.post('http://localhost:5000/api/scheduler/network/generate-random');

                if (response.data.success) {
                    // 更新网络数据
                    const updatedData = response.data.data;

                    // 处理节点坐标
                    if (updatedData && updatedData.nodes) {
                        updatedData.nodes = updatedData.nodes.map(node => {
                            if (node.coordinates && Array.isArray(node.coordinates) && node.coordinates.length >= 2) {
                                const width = 1000;
                                const height = 600;

                                return {
                                    ...node,
                                    x: node.coordinates[0] * width,
                                    y: node.coordinates[1] * height
                                };
                            }
                            return node;
                        });
                    }

                    // 保存当前的视图状态
                    const currentTranslateX = this.translateX;
                    const currentTranslateY = this.translateY;
                    const currentScale = this.scale;

                    // 更新网络数据
                    this.networkData = updatedData;

                    // 恢复视图状态
                    this.translateX = currentTranslateX;
                    this.translateY = currentTranslateY;
                    this.scale = currentScale;

                    this.showNotification('随机需水量生成成功', 'success');
                    this.hasRunSchedule = false;
                } else {
                    this.showNotification(`生成失败: ${response.data.error}`, 'error');
                }
            } catch (error) {
                console.error('生成随机需水量出错:', error);
                this.showNotification(`生成随机需水量出错: ${error.message}`, 'error');
            }
        },

        // 打开导入模态框
        openImportModal() {
            this.showImportModal = true;
            this.selectedFileName = '';
            this.selectedFile = null;
            this.importError = null;
        },


        // 关闭导入模态框
        closeImportModal() {
            this.showImportModal = false;
            this.selectedFileName = '';
            this.selectedFile = null;
            this.importError = null;
        },

        // 导入需水量数据
        async importDemands() {
            if (!this.selectedFile) {
                this.importError = "请先选择文件";
                this.showNotification("请先选择文件", 'error');
                return;
            }

            try {
                this.isImporting = true;
                this.importError = "";

                const formData = new FormData();
                formData.append('file', this.selectedFile);

                // 使用正确的API路径
                const response = await axios.post('http://localhost:5000/api/scheduler/network/import-demands', formData);
                console.log("导入响应:", response.data);

                // 检查响应中是否包含错误信息
                if (response.data.success) {
                    // 更新网络数据
                    const updatedData = response.data.data;
                    this.importErrors = response.data.errors || [];

                    // 处理节点坐标
                    if (updatedData && updatedData.nodes) {
                        updatedData.nodes = updatedData.nodes.map(node => {
                            // 保留原有的水厂标记
                            const originalNode = this.networkData.nodes.find(n => n.id === node.id);
                            const isWaterPlant = originalNode ? originalNode.is_water_plant : false;

                            if (node.coordinates && Array.isArray(node.coordinates) && node.coordinates.length >= 2) {
                                const width = 1000;
                                const height = 600;

                                return {
                                    ...node,
                                    x: node.coordinates[0] * width,
                                    y: node.coordinates[1] * height,
                                    is_water_plant: isWaterPlant // 保留水厂标记
                                };
                            }
                            return {
                                ...node,
                                is_water_plant: isWaterPlant // 保留水厂标记
                            };
                        });
                    }

                    // 保存当前的视图状态
                    const currentTranslateX = this.translateX || 0;
                    const currentTranslateY = this.translateY || 0;
                    const currentScale = this.scale || 1;

                    // 更新网络数据
                    this.networkData = updatedData;

                    // 恢复视图状态
                    this.translateX = currentTranslateX;
                    this.translateY = currentTranslateY;
                    this.scale = currentScale;

                    this.closeImportModal();

                    if (this.importErrors && this.importErrors.length > 0) {
                        console.log("导入有错误:", this.importErrors);
                        const errorMessage = `部分数据导入成功，但存在以下错误:\n${this.importErrors.join('\n')}`;

                        // 1. 设置一个标志，表示这是警告通知
                        this.isErrorNotification = true;  // 您可能想将变量名改为isWarningNotification，但这取决于您的逻辑

                        // 2. 显示通知，将类型从'error'改为'warning'
                        this.showNotification(errorMessage, 'warning');

                        // 3. 清除自动关闭的定时器
                        if (this.notificationTimeout) {
                            clearTimeout(this.notificationTimeout);
                            this.notificationTimeout = null;
                        }
                    }
                    else {
                        // 正常的成功通知
                        this.isErrorNotification = false;
                        this.showNotification('成功导入需水量数据', 'success');
                    }

                    this.hasRunSchedule = false;
                    // 重新渲染网络图
                    this.$nextTick(() => {
                        this.renderNetwork();
                    });
                } else {
                    // 导入失败的情况
                    const errorMessage = response.data.error || response.data.message || "导入失败";
                    console.log("导入失败:", errorMessage);

                    this.showNotification(errorMessage, 'error');
                    // 清除自动关闭的定时器，让错误通知持续显示
                    clearTimeout(this.notificationTimeout);
                }
            } catch (error) {
                console.error("导入需水量数据出错:", error);
                if (error.response) {
                    console.error("错误状态码:", error.response.status);
                    console.error("错误数据:", error.response.data);
                }
                this.closeImportModal();

                // 获取详细的错误信息
                let errorMessage = "导入过程中发生错误";
                if (error.response && error.response.data) {
                    if (error.response.data.error) {
                        errorMessage = error.response.data.error;
                    } else if (error.response.data.message) {
                        errorMessage = error.response.data.message;
                    } else if (typeof error.response.data === 'string') {
                        errorMessage = error.response.data;
                    }
                } else if (error.message) {
                    errorMessage = error.message;
                }

                this.importError = errorMessage;
                console.log("显示错误通知:", errorMessage);

                this.showNotification(errorMessage, 'error');
                // 清除自动关闭的定时器，让错误通知持续显示
                clearTimeout(this.notificationTimeout);
            } finally {
                this.isImporting = false;
            }
        },

        // 添加renderNetwork方法
        renderNetwork() {
            if (!this.networkData || !this.networkData.nodes || !this.networkData.links) {
                console.warn('没有可用的网络数据进行渲染');
                return;
            }

            // 清除现有的SVG内容
            const container = d3.select("#network-svg-container");
            container.selectAll("svg").remove();

            // 创建新的SVG元素
            const svg = container.append("svg")
                .attr("width", "100%")
                .attr("height", "600px")
                .call(d3.zoom().on("zoom", (event) => {
                    // 更新视图状态
                    this.scale = event.transform.k;
                    this.translateX = event.transform.x;
                    this.translateY = event.transform.y;

                    // 应用变换
                    g.attr("transform", event.transform);
                }));

            // 应用当前的变换
            const g = svg.append("g");
            if (this.scale && this.translateX !== undefined && this.translateY !== undefined) {
                g.attr("transform", `translate(${this.translateX},${this.translateY}) scale(${this.scale})`);
            }

            // 绘制连接线
            g.selectAll("line")
                .data(this.networkData.links)
                .enter()
                .append("line")
                .attr("x1", d => {
                    const sourceNode = this.networkData.nodes.find(node => node.id === d.source);
                    return sourceNode && !isNaN(sourceNode.x) ? sourceNode.x : 0;
                })
                .attr("y1", d => {
                    const sourceNode = this.networkData.nodes.find(node => node.id === d.source);
                    return sourceNode && !isNaN(sourceNode.y) ? sourceNode.y : 0;
                })
                .attr("x2", d => {
                    const targetNode = this.networkData.nodes.find(node => node.id === d.target);
                    return targetNode && !isNaN(targetNode.x) ? targetNode.x : 0;
                })
                .attr("y2", d => {
                    const targetNode = this.networkData.nodes.find(node => node.id === d.target);
                    return targetNode && !isNaN(targetNode.y) ? targetNode.y : 0;
                })
                .attr("class", d => `link ${d.link_type.toLowerCase()}`);

            // 绘制节点
            const nodes = g.selectAll("circle")
                .data(this.networkData.nodes)
                .enter()
                .append("circle")
                .attr("cx", d => !isNaN(d.x) ? d.x : 0)
                .attr("cy", d => !isNaN(d.y) ? d.y : 0)
                .attr("r", d => d.is_water_plant ? 8 : 5) // 水厂节点稍大一些
                .attr("class", d => {
                    // 根据节点类型和是否为水厂设置不同的类
                    if (d.is_water_plant) {
                        return 'water-plant';
                    } else {
                        return d.type.toLowerCase();
                    }
                })
                .on("click", (event, d) => {
                    // 点击节点时显示详情或执行其他操作
                    this.showNodeDetails(d);
                });

            // 添加节点标签
            g.selectAll("text")
                .data(this.networkData.nodes)
                .enter()
                .append("text")
                .attr("x", d => !isNaN(d.x) ? d.x + 8 : 8)
                .attr("y", d => !isNaN(d.y) ? d.y + 3 : 3)
                .text(d => {
                    // 为水厂添加特殊标记
                    return d.is_water_plant ? `${d.id} (水厂)` : d.id;
                })
                .attr("font-size", "10px")
                .attr("fill", "#333");
        },

        // 添加显示节点详情的方法
        showNodeDetails(node) {
            // 设置更新需水量表单的初始值
            this.updateDemandForm = {
                nodeId: node.id,
                demand: node.demand || 0
            };

            // 显示节点详情或更新需水量的模态框
            this.showUpdateDemandModal = true;
        },


        // 打开修改需水量模态框
        openUpdateDemandModal() {
            this.showUpdateDemandModal = true;
            this.updateDemandError = null;
            this.updateDemandForm = {
                nodeId: '',
                demand: null
            };
        },

        // 关闭修改需水量模态框
        closeUpdateDemandModal() {
            this.showUpdateDemandModal = false;
        },

        // 更新节点需水量
        async updateDemand() {
            if (!this.updateDemandForm.nodeId) {
                this.updateDemandError = '请输入节点ID';
                return;
            }

            if (this.updateDemandForm.demand === null || isNaN(this.updateDemandForm.demand) || this.updateDemandForm.demand < 0) {
                this.updateDemandError = '请输入有效的需水量值（大于等于0）';
                return;
            }

            try {
                this.isUpdatingDemand = true;
                this.updateDemandError = null;

                const response = await axios.post('http://localhost:5000/api/scheduler/network/update-demand', {
                    node_id: this.updateDemandForm.nodeId,
                    demand: parseFloat(this.updateDemandForm.demand)
                });

                if (response.data.success) {
                    // 更新网络数据
                    const updatedData = response.data.data;

                    // 处理节点坐标
                    if (updatedData && updatedData.nodes) {
                        updatedData.nodes = updatedData.nodes.map(node => {
                            if (node.coordinates && Array.isArray(node.coordinates) && node.coordinates.length >= 2) {
                                const width = 1000;
                                const height = 600;

                                return {
                                    ...node,
                                    x: node.coordinates[0] * width,
                                    y: node.coordinates[1] * height
                                };
                            }
                            return node;
                        });
                    }

                    // 保存当前的视图状态
                    const currentTranslateX = this.translateX;
                    const currentTranslateY = this.translateY;
                    const currentScale = this.scale;

                    // 更新网络数据
                    this.networkData = updatedData;

                    // 恢复视图状态
                    this.translateX = currentTranslateX;
                    this.translateY = currentTranslateY;
                    this.scale = currentScale;

                    this.closeUpdateDemandModal();
                    this.showNotification(`成功更新节点 ${this.updateDemandForm.nodeId} 的需水量`, 'success');
                    this.hasRunSchedule = false;
                } else {
                    this.updateDemandError = response.data.error;
                }
            } catch (error) {
                console.error('更新需水量出错:', error);
                this.updateDemandError = error.response?.data?.error || error.message;
            } finally {
                this.isUpdatingDemand = false;
            }
        },
        triggerFileInput() {
            this.$refs.fileInput.click();
        },

        // 处理文件选择变化
        handleFileChange(event) {
            const file = event.target.files[0];
            if (file) {
                this.selectedFileName = file.name;
                this.selectedFile = file;
                this.importError = null; // 清除之前的错误
                console.log('已选择文件:', file.name);
            } else {
                this.selectedFileName = '';
                this.selectedFile = null;
            }
        },
        // 热力图生成函数
        generateHeatmap(event) {
            event.preventDefault();
            this.loadingHeatmap = true;
            this.showHeatmapModal = true;

            fetch('http://localhost:5000/api/scheduler/network/heatmap', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('网络响应异常');
                    }
                    return response.blob();
                })
                .then(blob => {
                    this.loadingHeatmap = false;
                    this.heatmapImageUrl = URL.createObjectURL(blob);
                })
                .catch(error => {
                    this.loadingHeatmap = false;
                    this.showNotification('error', '获取热力图失败: ' + error.message);
                    this.closeHeatmapModal();
                });
        },

        // 关闭热力图模态框
        closeHeatmapModal() {
            this.showHeatmapModal = false;
            // 清理 Blob URL
            if (this.heatmapImageUrl) {
                URL.revokeObjectURL(this.heatmapImageUrl);
                this.heatmapImageUrl = '';
            }
        },

        // 下载热力图
        downloadHeatmap() {
            if (!this.heatmapImageUrl) return;

            const a = document.createElement('a');
            a.href = this.heatmapImageUrl;
            a.download = '网络压力热力图.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        },

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

.control-buttons {
    display: flex;
    gap: 10px;
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

/* 在现有的 <style> 标签内添加 */
.form-group {
    margin-bottom: 15px;
}

.form-label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
}

.form-control {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 14px;
}

.form-text {
    font-size: 12px;
    margin-top: 4px;
}

.alert {
    padding: 10px 15px;
    border-radius: 4px;
    font-size: 14px;
}

.alert-danger {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.mr-2 {
    margin-right: 8px;
}

.mt-3 {
    margin-top: 15px;
}

.file-input-container {
    margin-top: 8px;
}

.file-input-box {
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 8px 12px;
    cursor: pointer;
    background-color: #fff;
    min-height: 38px;
    display: flex;
    align-items: center;
    color: #666;
}

.file-input-box:hover {
    border-color: #999;
}

/* 在<style>部分修改水厂的样式 */
/* 在<style>部分修改水厂的样式 */
.water-plant {
    fill: #d300b7;
    /* 使用深橙色/赭石色 */
    stroke: #333;
    stroke-width: 1.5px;
}

.legend-color.water-plant {
    background-color: #d300b7;
}

.demand-label {
    filter: drop-shadow(0px 0px 2px white);
}

.demand-box {
    filter: drop-shadow(0px 1px 3px rgba(0, 0, 0, 0.2));
    pointer-events: none;
    /* 确保框不会阻止点击事件 */
}

.demand-label {
    pointer-events: none;
    /* 确保文本不会阻止点击事件 */
}

.network-water-plants {
    position: absolute;
    top: 10px;
    left: 10px;
    background-color: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 8px 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    z-index: 10;
}

.panel-header {
    font-weight: bold;
    margin-bottom: 5px;
    color: #d35400;
    /* 橙色标题 */
    border-bottom: 1px solid #eee;
    padding-bottom: 3px;
}

.water-plant-list {
    max-height: 150px;
    overflow-y: auto;
}

.water-plant-item {
    display: flex;
    justify-content: space-between;
    margin: 3px 0;
    font-size: 12px;
    color: #d35400;
    /* 使所有文字都是橙色 */
}

.water-plant-id {
    margin-right: 8px;
    font-weight: 500;
}

.water-plant-demand {
    /* 不需要单独设置颜色，继承父元素颜色 */
}

.export-buttons {
    position: absolute;
    bottom: 20px;
    right: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    z-index: 100;
}

.export-buttons button {
    width: 120px;
    text-align: left;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
}

.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    color: white;
    z-index: 9999;
}

.loading-spinner {
    border: 5px solid #f3f3f3;
    border-top: 5px solid #3498db;
    border-radius: 50%;
    width: 50px;
    height: 50px;
    animation: spin 2s linear infinite;
    margin-bottom: 10px;
}

@keyframes spin {
    0% {
        transform: rotate(0deg);
    }

    100% {
        transform: rotate(360deg);
    }
}

.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-content {
    background-color: white;
    padding: 20px;
    border-radius: 5px;
    max-width: 90%;
    max-height: 90%;
    overflow: auto;
    position: relative;
}

.close-button {
    position: absolute;
    top: 10px;
    right: 10px;
    font-size: 24px;
    cursor: pointer;
}

.image-container {
    text-align: center;
    margin-top: 10px;
}

.image-container img {
    max-width: 100%;
    max-height: 70vh;
}

.heatmap-modal {
    display: block;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    overflow: auto;
}

.heatmap-modal-content {
    position: relative;
    background-color: #fefefe;
    margin: 2% auto;
    padding: 0;
    border-radius: 8px;
    width: 80%;
    max-width: 900px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    display: flex;
    flex-direction: column;
    max-height: 95vh;
}

.heatmap-modal-header {
    padding: 10px 16px;
    background-color: #f8f8f8;
    border-bottom: 1px solid #ddd;
    border-radius: 8px 8px 0 0;
    position: relative;
}

.heatmap-modal-title {
    margin: 0;
    text-align: center;
    font-size: 20px;
    color: #333;
}

.heatmap-close-btn {
    position: absolute;
    right: 16px;
    top: 10px;
    color: #888;
    font-size: 24px;
    font-weight: bold;
    cursor: pointer;
}

.heatmap-close-btn:hover {
    color: #000;
}

.heatmap-modal-body {
    padding: 16px;
    overflow: auto;
    text-align: center;
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
}

#heatmapImage {
    max-width: 100%;
    max-height: 70vh;
    object-fit: contain;
}

.heatmap-modal-footer {
    padding: 10px 16px;
    background-color: #f8f8f8;
    border-top: 1px solid #ddd;
    border-radius: 0 0 8px 8px;
    text-align: center;
}

.heatmap-loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10;
}
.import-message {
    margin: 10px 0;
    padding: 10px;
    border-radius: 4px;
}

.success {
    background-color: #f0f9eb;
    color: #67c23a;
    border: 1px solid #e1f3d8;
}

.warning {
    background-color: #fdf6ec;
    color: #e6a23c;
    border: 1px solid #faecd8;
}

.error {
    background-color: #fef0f0;
    color: #f56c6c;
    border: 1px solid #fde2e2;
}

.error-list {
    margin-top: 5px;
    padding-left: 20px;
}
</style>
