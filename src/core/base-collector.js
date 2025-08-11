import EventEmitter from 'events';
import logger from './logger.js';

class BaseCollector extends EventEmitter {
  constructor(name, config = {}) {
    super();
    this.name = name;
    this.config = {
      timeout: 30000,
      retryAttempts: 3,
      retryDelay: 1000,
      ...config
    };
    this.isRunning = false;
    this.stats = {
      totalTasks: 0,
      successTasks: 0,
      failedTasks: 0,
      startTime: null,
      endTime: null
    };
  }

  async start() {
    if (this.isRunning) {
      logger.warn(`Collector ${this.name} is already running`);
      return;
    }

    logger.info(`Starting collector: ${this.name}`);
    this.isRunning = true;
    this.stats.startTime = new Date();
    this.stats.totalTasks = 0;
    this.stats.successTasks = 0;
    this.stats.failedTasks = 0;

    this.emit('start');

    try {
      await this.initialize();
      await this.collect();
    } catch (error) {
      logger.error(`Collector ${this.name} failed:`, error);
      this.emit('error', error);
    } finally {
      await this.stop();
    }
  }

  async stop() {
    if (!this.isRunning) return;

    logger.info(`Stopping collector: ${this.name}`);
    this.isRunning = false;
    this.stats.endTime = new Date();

    await this.cleanup();
    this.emit('stop', this.getStats());
  }

  async initialize() {
    // 子类实现具体初始化逻辑
    logger.info(`Initializing collector: ${this.name}`);
  }

  async collect() {
    // 子类实现具体采集逻辑
    throw new Error('collect() method must be implemented by subclass');
  }

  async cleanup() {
    // 子类实现清理逻辑
    logger.info(`Cleaning up collector: ${this.name}`);
  }

  async executeWithRetry(fn, maxRetries = null) {
    const retries = maxRetries || this.config.retryAttempts;
    let lastError;

    for (let i = 0; i <= retries; i++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error;
        
        if (i === retries) {
          logger.error(`Task failed after ${retries} retries:`, error);
          this.stats.failedTasks++;
          throw error;
        }

        logger.warn(`Task failed, retrying (${i + 1}/${retries}):`, error.message);
        await this.delay(this.config.retryDelay * Math.pow(2, i)); // 指数退避
      }
    }
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  incrementSuccess() {
    this.stats.successTasks++;
    this.emit('task_success', this.stats);
  }

  incrementFailed() {
    this.stats.failedTasks++;
    this.emit('task_failed', this.stats);
  }

  incrementTotal() {
    this.stats.totalTasks++;
  }

  getStats() {
    const duration = this.stats.endTime 
      ? this.stats.endTime - this.stats.startTime 
      : Date.now() - this.stats.startTime;

    return {
      ...this.stats,
      duration: Math.round(duration / 1000), // 秒
      successRate: this.stats.totalTasks ? 
        Math.round((this.stats.successTasks / this.stats.totalTasks) * 100) : 0
    };
  }

  validateConfig() {
    // 子类可重写以验证特定配置
    return true;
  }
}

export default BaseCollector;