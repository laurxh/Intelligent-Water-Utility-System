<template>
    <div class="content">
        <!-- 标题 -->
        <div class="header-container">
            <h4 class="title">水网络拓扑图</h4>
            <div class="control-buttons">
                <button class="btn btn-primary btn-sm" @click="refreshNetworkData">
                    <i class="ti-reload"></i> 刷新数据
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
                        <circle v-for="(node, index) in networkData.nodes" :key="`node-${index}`" :cx="node.x"
                            :cy="node.y" :r="getNodeRadius(node.node_type)" :fill="getNodeColor(node.node_type)"
                            stroke="#fff" stroke-width="1.5" :class="`node ${node.node_type.toLowerCase()}`"
                            @click.stop="openElementPopup(node)" />

                        <!-- 节点标签 -->
                        <text v-for="(node, index) in networkData.nodes" :key="`label-${index}`" :x="node.x + 12"
                            :y="node.y + 4" font-size="10px" class="node-label">
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
                            <span class="detail-value">{{ selectedElement.diameter || 0 }} mm</span>
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

        <!-- 底部分隔线 -->
        <hr class="mt-5 mb-4">

        <!-- 底部操作按钮 -->
        <div class="action-buttons-container">
            <button class="btn btn-primary action-button" @click="runSimulation"
                :disabled="!networkData || isSimulating">
                <i class="ti-control-play mr-1"></i>
                {{ isSimulating ? '模拟中...' : '运行模拟' }}
            </button>
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
            dragStartY: 0
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

    methods: {
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
</style>
