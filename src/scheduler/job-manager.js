import TaskScheduler from './task-scheduler.js';
import TaskModel from '../storage/models/task-model.js';
import logger from '../core/logger.js';

class JobManager {
  constructor() {
    this.scheduler = new TaskScheduler();
    this.setupEventListeners();
  }

  setupEventListeners() {
    this.scheduler.on('started', () => {
      logger.info('任务调度器已启动');
    });

    this.scheduler.on('stopped', () => {
      logger.info('任务调度器已停止');
    });

    this.scheduler.on('task_started', (task) => {
      logger.info(`任务开始执行: ${task.name}`);
    });

    this.scheduler.on('task_completed', (task, result) => {
      logger.info(`任务执行完成: ${task.name}`, result);
    });

    this.scheduler.on('task_failed', (task, error) => {
      logger.error(`任务执行失败: ${task.name}`, error);
    });

    this.scheduler.on('tasks_cleaned', (count) => {
      logger.info(`清理了 ${count} 个历史任务`);
    });
  }

  start() {
    this.scheduler.start();
  }

  stop() {
    this.scheduler.stop();
  }

  async createTask(taskData) {
    try {
      const task = await TaskModel.create(taskData);
      logger.info(`创建任务: ${task.name}`);
      return task;
    } catch (error) {
      logger.error('创建任务失败:', error);
      throw error;
    }
  }

  async createWechatCollectionTask(config) {
    const taskData = {
      name: `wechat_collection_${Date.now()}`,
      type: 'wechat_article_collection',
      config: {
        timeout: 30000,
        retryAttempts: 3,
        requestDelay: 2000,
        maxArticles: 20,
        ...config
      },
      priority: config.priority || 1,
      maxRetries: config.maxRetries || 3
    };

    return await this.createTask(taskData);
  }

  scheduleWechatCollection(name, cronExpression, config) {
    const taskData = {
      type: 'wechat_article_collection',
      config: {
        timeout: 30000,
        retryAttempts: 3,
        requestDelay: 2000,
        maxArticles: 20,
        ...config
      },
      priority: config.priority || 1,
      maxRetries: config.maxRetries || 3
    };

    this.scheduler.scheduleRecurringTask(name, cronExpression, taskData);
    logger.info(`已创建微信采集定时任务: ${name} (${cronExpression})`);
  }

  unscheduleTask(name) {
    return this.scheduler.unscheduleTask(name);
  }

  async getTaskHistory(limit = 50) {
    return await TaskModel.getTaskHistory(limit);
  }

  async getTaskStats() {
    return await TaskModel.getStats();
  }

  async getTaskById(id) {
    return await TaskModel.findById(id);
  }

  async getTasksByStatus(status, limit = 50) {
    return await TaskModel.findByStatus(status, limit);
  }

  getSchedulerStatus() {
    return this.scheduler.getStatus();
  }

  async cancelTask(id) {
    try {
      const task = await TaskModel.findById(id);
      if (!task) {
        throw new Error('任务不存在');
      }

      if (task.status === 'running') {
        throw new Error('无法取消正在运行的任务');
      }

      const success = await TaskModel.updateStatus(id, 'cancelled');
      if (success) {
        logger.info(`任务已取消: ${task.name}`);
      }
      
      return success;
    } catch (error) {
      logger.error('取消任务失败:', error);
      throw error;
    }
  }

  async retryTask(id) {
    try {
      const task = await TaskModel.findById(id);
      if (!task) {
        throw new Error('任务不存在');
      }

      if (task.status === 'running') {
        throw new Error('任务正在运行中');
      }

      // 重置任务状态
      const success = await TaskModel.updateStatus(id, 'pending');
      if (success) {
        await TaskModel.setNextRunTime(id, new Date());
        logger.info(`任务已重新排队: ${task.name}`);
      }
      
      return success;
    } catch (error) {
      logger.error('重试任务失败:', error);
      throw error;
    }
  }

  // 预设的定时任务模板
  createDailyWechatCollection(name, config, hour = 9, minute = 0) {
    const cronExpression = `${minute} ${hour} * * *`;
    this.scheduleWechatCollection(name, cronExpression, config);
  }

  createHourlyWechatCollection(name, config, minute = 0) {
    const cronExpression = `${minute} * * * *`;
    this.scheduleWechatCollection(name, cronExpression, config);
  }

  createWeeklyWechatCollection(name, config, dayOfWeek = 1, hour = 9, minute = 0) {
    const cronExpression = `${minute} ${hour} * * ${dayOfWeek}`;
    this.scheduleWechatCollection(name, cronExpression, config);
  }
}

export default JobManager;