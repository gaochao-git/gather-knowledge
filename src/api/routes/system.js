import express from 'express';
import database from '../../storage/database.js';
import performanceTracker from '../../utils/performance-tracker.js';
import logger from '../../core/logger.js';

const router = express.Router();

// 系统状态总览
router.get('/status', async (req, res, next) => {
  try {
    const systemMonitor = req.systemMonitor;
    const jobManager = req.jobManager;

    const metrics = systemMonitor.getMetrics();
    const healthStatus = systemMonitor.getHealthStatus();
    const schedulerStatus = jobManager.getSchedulerStatus();
    const dbStats = await database.getStats();

    res.json({
      success: true,
      data: {
        health: healthStatus,
        metrics,
        scheduler: schedulerStatus,
        database: dbStats,
        timestamp: new Date()
      }
    });
  } catch (error) {
    next(error);
  }
});

// 系统指标
router.get('/metrics', (req, res, next) => {
  try {
    const systemMonitor = req.systemMonitor;
    const metrics = systemMonitor.getMetrics();

    res.json({
      success: true,
      data: metrics
    });
  } catch (error) {
    next(error);
  }
});

// 性能统计
router.get('/performance', (req, res, next) => {
  try {
    const { timeRange = 3600000 } = req.query; // 默认1小时
    const stats = performanceTracker.getAllStats(parseInt(timeRange));

    res.json({
      success: true,
      data: stats
    });
  } catch (error) {
    next(error);
  }
});

// 慢操作报告
router.get('/performance/slow', (req, res, next) => {
  try {
    const { threshold = 5000, timeRange = 3600000 } = req.query;
    const slowOps = performanceTracker.getSlowOperations(
      parseInt(threshold), 
      parseInt(timeRange)
    );

    res.json({
      success: true,
      data: slowOps
    });
  } catch (error) {
    next(error);
  }
});

// 活跃操作
router.get('/performance/active', (req, res, next) => {
  try {
    const activeOps = performanceTracker.getActiveOperations();

    res.json({
      success: true,
      data: activeOps
    });
  } catch (error) {
    next(error);
  }
});

// 调度器状态
router.get('/scheduler', (req, res, next) => {
  try {
    const jobManager = req.jobManager;
    const status = jobManager.getSchedulerStatus();

    res.json({
      success: true,
      data: status
    });
  } catch (error) {
    next(error);
  }
});

// 数据库状态
router.get('/database', async (req, res, next) => {
  try {
    const stats = await database.getStats();
    const isHealthy = await database.ping();

    res.json({
      success: true,
      data: {
        ...stats,
        healthy: isHealthy,
        lastChecked: new Date()
      }
    });
  } catch (error) {
    next(error);
  }
});

// 系统健康检查
router.get('/health', async (req, res, next) => {
  try {
    const systemMonitor = req.systemMonitor;
    const healthStatus = systemMonitor.getHealthStatus();
    const dbHealthy = await database.ping();

    const overall = healthStatus.status === 'healthy' && dbHealthy ? 'healthy' : 
                   healthStatus.status === 'critical' || !dbHealthy ? 'critical' : 'warning';

    res.json({
      success: true,
      data: {
        overall,
        components: {
          system: healthStatus,
          database: { 
            status: dbHealthy ? 'healthy' : 'unhealthy',
            connected: dbHealthy
          }
        },
        timestamp: new Date()
      }
    });
  } catch (error) {
    next(error);
  }
});

// 系统监控报告
router.get('/report', (req, res, next) => {
  try {
    const systemMonitor = req.systemMonitor;
    const report = systemMonitor.generateReport();

    res.json({
      success: true,
      data: report
    });
  } catch (error) {
    next(error);
  }
});

// 清理性能历史
router.delete('/performance/history', (req, res, next) => {
  try {
    performanceTracker.clearHistory();
    
    res.json({
      success: true,
      message: '性能追踪历史已清理'
    });
  } catch (error) {
    next(error);
  }
});

// 重置系统指标
router.post('/metrics/reset', (req, res, next) => {
  try {
    const systemMonitor = req.systemMonitor;
    systemMonitor.resetMetrics();

    res.json({
      success: true,
      message: '系统指标已重置'
    });
  } catch (error) {
    next(error);
  }
});

// 设置监控阈值
router.put('/monitoring/thresholds', (req, res, next) => {
  try {
    const { errorRate, responseTime, memoryUsage } = req.body;
    const systemMonitor = req.systemMonitor;
    
    const thresholds = {};
    if (errorRate !== undefined) thresholds.errorRate = errorRate;
    if (responseTime !== undefined) thresholds.responseTime = responseTime;
    if (memoryUsage !== undefined) thresholds.memoryUsage = memoryUsage;

    systemMonitor.setThresholds(thresholds);

    res.json({
      success: true,
      message: '监控阈值已更新',
      data: thresholds
    });
  } catch (error) {
    next(error);
  }
});

export default router;