import EventEmitter from 'events';
import logger from '../core/logger.js';

class SystemMonitor extends EventEmitter {
  constructor() {
    super();
    this.metrics = {
      startTime: new Date(),
      requests: 0,
      errors: 0,
      collections: 0,
      articlesCollected: 0,
      activeTasks: 0,
      systemHealth: 'healthy'
    };
    
    this.thresholds = {
      errorRate: 0.1, // 10% 错误率
      responseTime: 5000, // 5秒响应时间
      memoryUsage: 0.8 // 80% 内存使用率
    };

    this.isMonitoring = false;
    this.monitorInterval = null;
  }

  start(intervalMs = 60000) {
    if (this.isMonitoring) {
      logger.warn('系统监控器已在运行');
      return;
    }

    logger.info('启动系统监控器');
    this.isMonitoring = true;
    this.metrics.startTime = new Date();

    this.monitorInterval = setInterval(() => {
      this.collectMetrics();
    }, intervalMs);

    this.emit('monitoring_started');
  }

  stop() {
    if (!this.isMonitoring) return;

    logger.info('停止系统监控器');
    this.isMonitoring = false;

    if (this.monitorInterval) {
      clearInterval(this.monitorInterval);
      this.monitorInterval = null;
    }

    this.emit('monitoring_stopped');
  }

  collectMetrics() {
    try {
      const systemMetrics = this.getSystemMetrics();
      const healthStatus = this.checkSystemHealth(systemMetrics);

      const previousHealth = this.metrics.systemHealth;
      this.metrics.systemHealth = healthStatus.status;

      // 健康状态变化时发出事件
      if (previousHealth !== healthStatus.status) {
        this.emit('health_changed', {
          from: previousHealth,
          to: healthStatus.status,
          reason: healthStatus.reason,
          metrics: systemMetrics
        });

        logger.info(`系统健康状态变化: ${previousHealth} -> ${healthStatus.status}`, {
          reason: healthStatus.reason
        });
      }

      // 发送指标更新事件
      this.emit('metrics_updated', {
        ...this.metrics,
        system: systemMetrics
      });

    } catch (error) {
      logger.error('收集系统指标失败:', error);
      this.recordError('metrics_collection_failed');
    }
  }

  getSystemMetrics() {
    const now = Date.now();
    const uptime = now - this.metrics.startTime.getTime();
    const memUsage = process.memoryUsage();

    return {
      uptime: Math.round(uptime / 1000), // 秒
      memory: {
        used: Math.round(memUsage.heapUsed / 1024 / 1024), // MB
        total: Math.round(memUsage.heapTotal / 1024 / 1024), // MB
        external: Math.round(memUsage.external / 1024 / 1024), // MB
        usage: memUsage.heapUsed / memUsage.heapTotal
      },
      cpu: {
        usage: process.cpuUsage()
      },
      errorRate: this.metrics.requests > 0 ? this.metrics.errors / this.metrics.requests : 0,
      collectionsPerHour: this.calculateRate(this.metrics.collections, uptime),
      articlesPerHour: this.calculateRate(this.metrics.articlesCollected, uptime)
    };
  }

  calculateRate(count, uptimeMs) {
    const hours = uptimeMs / (1000 * 60 * 60);
    return hours > 0 ? Math.round(count / hours) : 0;
  }

  checkSystemHealth(systemMetrics) {
    const issues = [];

    // 检查错误率
    if (systemMetrics.errorRate > this.thresholds.errorRate) {
      issues.push(`高错误率: ${Math.round(systemMetrics.errorRate * 100)}%`);
    }

    // 检查内存使用
    if (systemMetrics.memory.usage > this.thresholds.memoryUsage) {
      issues.push(`内存使用过高: ${Math.round(systemMetrics.memory.usage * 100)}%`);
    }

    // 检查活跃任务数
    if (this.metrics.activeTasks > 10) {
      issues.push(`活跃任务过多: ${this.metrics.activeTasks}`);
    }

    if (issues.length === 0) {
      return { status: 'healthy', reason: '所有指标正常' };
    } else if (issues.length <= 2) {
      return { status: 'warning', reason: issues.join(', ') };
    } else {
      return { status: 'critical', reason: issues.join(', ') };
    }
  }

  // 指标记录方法
  recordRequest() {
    this.metrics.requests++;
  }

  recordError(type = 'unknown') {
    this.metrics.errors++;
    this.emit('error_recorded', { type, timestamp: new Date() });
    logger.warn(`记录错误: ${type}`);
  }

  recordCollection(articlesCount = 0) {
    this.metrics.collections++;
    this.metrics.articlesCollected += articlesCount;
    this.emit('collection_recorded', { articlesCount, timestamp: new Date() });
  }

  recordTaskStart() {
    this.metrics.activeTasks++;
  }

  recordTaskEnd() {
    this.metrics.activeTasks = Math.max(0, this.metrics.activeTasks - 1);
  }

  // 获取指标和状态
  getMetrics() {
    return {
      ...this.metrics,
      system: this.getSystemMetrics()
    };
  }

  getHealthStatus() {
    const systemMetrics = this.getSystemMetrics();
    return this.checkSystemHealth(systemMetrics);
  }

  // 设置阈值
  setThresholds(newThresholds) {
    this.thresholds = { ...this.thresholds, ...newThresholds };
    logger.info('更新监控阈值:', this.thresholds);
  }

  // 重置指标
  resetMetrics() {
    this.metrics = {
      startTime: new Date(),
      requests: 0,
      errors: 0,
      collections: 0,
      articlesCollected: 0,
      activeTasks: 0,
      systemHealth: 'healthy'
    };
    logger.info('系统指标已重置');
    this.emit('metrics_reset');
  }

  // 生成监控报告
  generateReport() {
    const metrics = this.getMetrics();
    const uptime = Math.round((Date.now() - metrics.startTime.getTime()) / 1000);

    return {
      generatedAt: new Date(),
      uptime: `${Math.floor(uptime / 3600)}小时 ${Math.floor((uptime % 3600) / 60)}分钟`,
      health: this.getHealthStatus(),
      statistics: {
        totalRequests: metrics.requests,
        totalErrors: metrics.errors,
        errorRate: `${Math.round((metrics.errors / Math.max(metrics.requests, 1)) * 100)}%`,
        totalCollections: metrics.collections,
        totalArticles: metrics.articlesCollected,
        avgArticlesPerCollection: Math.round(metrics.articlesCollected / Math.max(metrics.collections, 1)),
        activeTasks: metrics.activeTasks
      },
      system: {
        memoryUsage: `${metrics.system.memory.used}MB / ${metrics.system.memory.total}MB (${Math.round(metrics.system.memory.usage * 100)}%)`,
        collectionsPerHour: metrics.system.collectionsPerHour,
        articlesPerHour: metrics.system.articlesPerHour
      }
    };
  }
}

export default SystemMonitor;