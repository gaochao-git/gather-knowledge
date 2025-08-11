import EventEmitter from 'events';
import cron from 'node-cron';
import logger from '../core/logger.js';
import config from '../core/config.js';
import TaskModel from '../storage/models/task-model.js';

class TaskScheduler extends EventEmitter {
  constructor() {
    super();
    this.jobs = new Map();
    this.running = false;
    this.maxConcurrentJobs = config.scheduler.maxConcurrentJobs || 5;
    this.runningJobs = new Map();
  }

  start() {
    if (this.running) {
      logger.warn('任务调度器已经在运行');
      return;
    }

    logger.info('启动任务调度器');
    this.running = true;

    // 启动任务检查定时器，每分钟检查一次待执行任务
    this.checkTasksJob = cron.schedule('* * * * *', () => {
      this.checkPendingTasks();
    }, {
      timezone: config.scheduler.timezone
    });

    // 启动清理定时器，每天凌晨2点清理历史任务
    this.cleanupJob = cron.schedule('0 2 * * *', () => {
      this.cleanupTasks();
    }, {
      timezone: config.scheduler.timezone
    });

    this.emit('started');
  }

  stop() {
    if (!this.running) return;

    logger.info('停止任务调度器');
    this.running = false;

    // 停止定时任务
    if (this.checkTasksJob) {
      this.checkTasksJob.destroy();
    }
    if (this.cleanupJob) {
      this.cleanupJob.destroy();
    }

    // 停止所有cron任务
    this.jobs.forEach((job) => {
      if (job.cronJob) {
        job.cronJob.destroy();
      }
    });

    // 等待运行中的任务完成
    this.waitForRunningJobs();

    this.emit('stopped');
  }

  async checkPendingTasks() {
    if (!this.running) return;

    try {
      const pendingTasks = await TaskModel.getPendingTasks();
      
      for (const task of pendingTasks) {
        if (this.runningJobs.size >= this.maxConcurrentJobs) {
          logger.info('达到最大并发任务数，跳过新任务');
          break;
        }

        await this.executeTask(task);
      }
    } catch (error) {
      logger.error('检查待执行任务失败:', error);
    }
  }

  async executeTask(task) {
    if (this.runningJobs.has(task._id.toString())) {
      logger.warn(`任务 ${task.name} 正在运行中，跳过`);
      return;
    }

    logger.info(`开始执行任务: ${task.name}`);
    
    try {
      // 更新任务状态为运行中
      await TaskModel.updateStatus(task._id, 'running');
      
      // 标记任务为运行中
      this.runningJobs.set(task._id.toString(), {
        task,
        startTime: new Date()
      });

      this.emit('task_started', task);

      // 执行任务
      const result = await this.runTask(task);

      // 更新任务状态为完成
      await TaskModel.updateStatus(task._id, 'completed', result);
      
      logger.info(`任务 ${task.name} 执行完成`);
      this.emit('task_completed', task, result);

    } catch (error) {
      logger.error(`任务 ${task.name} 执行失败:`, error);
      
      // 增加重试次数
      await TaskModel.incrementRetry(task._id);
      
      // 检查是否需要重试
      if (task.retryCount < (task.maxRetries || 3)) {
        // 设置下次重试时间
        const nextRunTime = new Date(Date.now() + (task.retryDelay || 5 * 60 * 1000));
        await TaskModel.setNextRunTime(task._id, nextRunTime);
        await TaskModel.updateStatus(task._id, 'pending');
        
        logger.info(`任务 ${task.name} 将在 ${nextRunTime.toISOString()} 重试`);
      } else {
        // 重试次数用完，标记为失败
        await TaskModel.updateStatus(task._id, 'failed', {
          error: error.message,
          stack: error.stack
        });
      }

      this.emit('task_failed', task, error);
    } finally {
      // 移除运行标记
      this.runningJobs.delete(task._id.toString());
    }
  }

  async runTask(task) {
    const { type, config: taskConfig } = task;

    switch (type) {
      case 'wechat_article_collection':
        return await this.runWechatArticleCollection(taskConfig);
      
      default:
        throw new Error(`不支持的任务类型: ${type}`);
    }
  }

  async runWechatArticleCollection(taskConfig) {
    // 动态导入避免循环依赖
    const { default: WechatArticleCollector } = await import('../collectors/wechat/article-collector.js');
    const { default: ArticleModel } = await import('../storage/models/article-model.js');

    const collector = new WechatArticleCollector(taskConfig);
    
    // 监听采集事件
    const collectedArticles = [];
    collector.on('article_collected', async (article) => {
      try {
        await ArticleModel.create(article);
        collectedArticles.push(article);
      } catch (error) {
        logger.error('保存文章失败:', error);
      }
    });

    await collector.start();
    
    return {
      collectedArticles: collectedArticles.length,
      stats: collector.getStats()
    };
  }

  scheduleRecurringTask(name, cronExpression, taskData) {
    if (this.jobs.has(name)) {
      logger.warn(`定时任务 ${name} 已存在，将被替换`);
      this.jobs.get(name).cronJob?.destroy();
    }

    const cronJob = cron.schedule(cronExpression, async () => {
      try {
        // 创建新的任务记录
        await TaskModel.create({
          name: `${name}_${Date.now()}`,
          type: taskData.type,
          config: taskData.config,
          priority: taskData.priority || 0,
          maxRetries: taskData.maxRetries || 3
        });

        logger.info(`定时任务 ${name} 已创建新的执行任务`);
      } catch (error) {
        logger.error(`定时任务 ${name} 创建失败:`, error);
      }
    }, {
      timezone: config.scheduler.timezone,
      scheduled: false
    });

    this.jobs.set(name, {
      cronExpression,
      taskData,
      cronJob,
      createdAt: new Date()
    });

    if (this.running) {
      cronJob.start();
    }

    logger.info(`定时任务 ${name} 已注册: ${cronExpression}`);
  }

  unscheduleTask(name) {
    if (this.jobs.has(name)) {
      const job = this.jobs.get(name);
      if (job.cronJob) {
        job.cronJob.destroy();
      }
      this.jobs.delete(name);
      logger.info(`定时任务 ${name} 已取消`);
      return true;
    }
    return false;
  }

  async cleanupTasks() {
    try {
      const deletedCount = await TaskModel.cleanup();
      logger.info(`清理了 ${deletedCount} 个历史任务`);
      this.emit('tasks_cleaned', deletedCount);
    } catch (error) {
      logger.error('清理任务失败:', error);
    }
  }

  async waitForRunningJobs(timeout = 30000) {
    if (this.runningJobs.size === 0) return;

    logger.info(`等待 ${this.runningJobs.size} 个运行中的任务完成...`);
    
    const startTime = Date.now();
    while (this.runningJobs.size > 0 && (Date.now() - startTime) < timeout) {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    if (this.runningJobs.size > 0) {
      logger.warn(`仍有 ${this.runningJobs.size} 个任务未完成，强制停止`);
    }
  }

  getStatus() {
    return {
      running: this.running,
      scheduledJobs: Array.from(this.jobs.keys()),
      runningJobs: Array.from(this.runningJobs.values()).map(job => ({
        name: job.task.name,
        startTime: job.startTime,
        duration: Math.round((Date.now() - job.startTime) / 1000)
      }))
    };
  }
}

export default TaskScheduler;