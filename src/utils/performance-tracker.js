import logger from '../core/logger.js';

class PerformanceTracker {
  constructor() {
    this.operations = new Map();
    this.history = [];
    this.maxHistorySize = 1000;
  }

  start(operationName, metadata = {}) {
    const operation = {
      name: operationName,
      startTime: Date.now(),
      startMemory: process.memoryUsage(),
      metadata
    };

    this.operations.set(operationName, operation);
    
    logger.debug(`性能追踪开始: ${operationName}`, metadata);
    return operation;
  }

  end(operationName, result = {}) {
    const operation = this.operations.get(operationName);
    
    if (!operation) {
      logger.warn(`性能追踪未找到操作: ${operationName}`);
      return null;
    }

    const endTime = Date.now();
    const endMemory = process.memoryUsage();
    
    const performance = {
      ...operation,
      endTime,
      duration: endTime - operation.startTime,
      memoryDelta: {
        heapUsed: endMemory.heapUsed - operation.startMemory.heapUsed,
        heapTotal: endMemory.heapTotal - operation.startMemory.heapTotal,
        external: endMemory.external - operation.startMemory.external
      },
      result,
      timestamp: new Date()
    };

    // 记录到历史
    this.addToHistory(performance);
    
    // 移除正在进行的操作
    this.operations.delete(operationName);

    // 记录日志
    const logData = {
      duration: performance.duration,
      memoryUsed: Math.round(performance.memoryDelta.heapUsed / 1024 / 1024 * 100) / 100, // MB
      ...performance.metadata,
      ...result
    };

    if (performance.duration > 10000) { // 超过10秒记录警告
      logger.warn(`性能追踪完成（慢操作）: ${operationName}`, logData);
    } else {
      logger.debug(`性能追踪完成: ${operationName}`, logData);
    }

    return performance;
  }

  addToHistory(performance) {
    this.history.push(performance);
    
    // 保持历史记录在限制内
    if (this.history.length > this.maxHistorySize) {
      this.history.shift();
    }
  }

  getOperationStats(operationName, timeRangeMs = 3600000) { // 默认1小时
    const cutoffTime = Date.now() - timeRangeMs;
    
    const operations = this.history.filter(op => 
      op.name === operationName && op.endTime > cutoffTime
    );

    if (operations.length === 0) {
      return null;
    }

    const durations = operations.map(op => op.duration);
    const memoryUsages = operations.map(op => op.memoryDelta.heapUsed);

    return {
      operationName,
      timeRange: `${timeRangeMs / 1000}秒`,
      count: operations.length,
      duration: {
        total: durations.reduce((a, b) => a + b, 0),
        average: Math.round(durations.reduce((a, b) => a + b, 0) / durations.length),
        min: Math.min(...durations),
        max: Math.max(...durations),
        median: this.calculateMedian(durations)
      },
      memory: {
        totalUsed: Math.round(memoryUsages.reduce((a, b) => a + b, 0) / 1024 / 1024 * 100) / 100, // MB
        averageUsed: Math.round(memoryUsages.reduce((a, b) => a + b, 0) / memoryUsages.length / 1024 / 1024 * 100) / 100,
        minUsed: Math.round(Math.min(...memoryUsages) / 1024 / 1024 * 100) / 100,
        maxUsed: Math.round(Math.max(...memoryUsages) / 1024 / 1024 * 100) / 100
      }
    };
  }

  calculateMedian(numbers) {
    const sorted = numbers.slice().sort((a, b) => a - b);
    const middle = Math.floor(sorted.length / 2);
    
    if (sorted.length % 2 === 0) {
      return Math.round((sorted[middle - 1] + sorted[middle]) / 2);
    } else {
      return sorted[middle];
    }
  }

  getAllStats(timeRangeMs = 3600000) {
    const cutoffTime = Date.now() - timeRangeMs;
    const recentOperations = this.history.filter(op => op.endTime > cutoffTime);
    
    const operationNames = [...new Set(recentOperations.map(op => op.name))];
    const stats = {};
    
    operationNames.forEach(name => {
      stats[name] = this.getOperationStats(name, timeRangeMs);
    });

    return {
      timeRange: `${timeRangeMs / 1000}秒`,
      totalOperations: recentOperations.length,
      uniqueOperations: operationNames.length,
      stats
    };
  }

  getActiveOperations() {
    const now = Date.now();
    const active = [];
    
    this.operations.forEach((operation) => {
      active.push({
        ...operation,
        runningTime: now - operation.startTime
      });
    });

    return active.sort((a, b) => b.runningTime - a.runningTime);
  }

  // 装饰器模式，自动追踪异步函数
  async trackAsync(operationName, fn, metadata = {}) {
    this.start(operationName, metadata);
    
    try {
      const result = await fn();
      this.end(operationName, { success: true });
      return result;
    } catch (error) {
      this.end(operationName, { 
        success: false, 
        error: error.message 
      });
      throw error;
    }
  }

  // 清理历史记录
  clearHistory() {
    this.history = [];
    logger.info('性能追踪历史已清理');
  }

  // 获取慢操作报告
  getSlowOperations(thresholdMs = 5000, timeRangeMs = 3600000) {
    const cutoffTime = Date.now() - timeRangeMs;
    
    const slowOps = this.history.filter(op => 
      op.endTime > cutoffTime && op.duration > thresholdMs
    ).sort((a, b) => b.duration - a.duration);

    return {
      threshold: `${thresholdMs}毫秒`,
      timeRange: `${timeRangeMs / 1000}秒`,
      count: slowOps.length,
      operations: slowOps.slice(0, 20).map(op => ({
        name: op.name,
        duration: op.duration,
        memoryUsed: Math.round(op.memoryDelta.heapUsed / 1024 / 1024 * 100) / 100,
        timestamp: op.timestamp,
        metadata: op.metadata
      }))
    };
  }
}

export default new PerformanceTracker();