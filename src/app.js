import express from 'express';
import cors from 'cors';
import config from './core/config.js';
import logger from './core/logger.js';
import database from './storage/database.js';
import JobManager from './scheduler/job-manager.js';
import SystemMonitor from './utils/system-monitor.js';

// 导入路由
import articlesRouter from './api/routes/articles.js';
import tasksRouter from './api/routes/tasks.js';
import collectorsRouter from './api/routes/collectors.js';
import systemRouter from './api/routes/system.js';

// 导入中间件
import errorHandler from './api/middleware/error-handler.js';
import requestLogger from './api/middleware/request-logger.js';

class Application {
  constructor() {
    this.app = express();
    this.jobManager = new JobManager();
    this.systemMonitor = new SystemMonitor();
    this.server = null;
  }

  async initialize() {
    try {
      logger.info('初始化应用...');

      // 连接数据库
      await database.connect();

      // 配置Express
      this.setupMiddleware();
      this.setupRoutes();
      this.setupErrorHandling();

      // 启动任务管理器
      this.jobManager.start();

      // 启动系统监控
      this.systemMonitor.start();

      logger.info('应用初始化完成');
    } catch (error) {
      logger.error('应用初始化失败:', error);
      throw error;
    }
  }

  setupMiddleware() {
    // CORS
    this.app.use(cors());

    // JSON解析
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // 请求日志
    this.app.use(requestLogger);

    // 健康检查
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        version: process.env.npm_package_version || '1.0.0'
      });
    });

    // API根路径
    this.app.get('/', (req, res) => {
      res.json({
        message: 'Gather Knowledge API',
        version: '1.0.0',
        docs: '/api/docs',
        health: '/health'
      });
    });
  }

  setupRoutes() {
    // API路由
    this.app.use('/api/articles', articlesRouter);
    this.app.use('/api/tasks', tasksRouter);
    this.app.use('/api/collectors', collectorsRouter);
    this.app.use('/api/system', systemRouter);

    // 注入依赖到req对象
    this.app.use((req, res, next) => {
      req.jobManager = this.jobManager;
      req.systemMonitor = this.systemMonitor;
      next();
    });
  }

  setupErrorHandling() {
    // 404处理
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Not Found',
        message: `路径 ${req.originalUrl} 不存在`,
        timestamp: new Date().toISOString()
      });
    });

    // 错误处理中间件
    this.app.use(errorHandler);
  }

  async start() {
    try {
      await this.initialize();

      this.server = this.app.listen(config.server.port, config.server.host, () => {
        logger.info(`服务器启动成功 - http://${config.server.host}:${config.server.port}`);
        logger.info('可用的API端点:');
        logger.info('  GET  /health          - 健康检查');
        logger.info('  GET  /api/articles    - 文章管理');
        logger.info('  GET  /api/tasks       - 任务管理');
        logger.info('  GET  /api/collectors  - 采集器管理');
        logger.info('  GET  /api/system      - 系统状态');
      });

      // 优雅关闭处理
      this.setupGracefulShutdown();

    } catch (error) {
      logger.error('服务器启动失败:', error);
      process.exit(1);
    }
  }

  setupGracefulShutdown() {
    const shutdown = async (signal) => {
      logger.info(`收到 ${signal} 信号，开始优雅关闭...`);

      // 停止接收新的请求
      if (this.server) {
        this.server.close(() => {
          logger.info('HTTP服务器已关闭');
        });
      }

      try {
        // 停止任务管理器
        this.jobManager.stop();

        // 停止系统监控
        this.systemMonitor.stop();

        // 关闭数据库连接
        await database.disconnect();

        logger.info('优雅关闭完成');
        process.exit(0);
      } catch (error) {
        logger.error('优雅关闭过程中发生错误:', error);
        process.exit(1);
      }
    };

    // 监听关闭信号
    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));

    // 处理未捕获的异常
    process.on('uncaughtException', (error) => {
      logger.error('未捕获的异常:', error);
      shutdown('uncaughtException');
    });

    process.on('unhandledRejection', (reason, promise) => {
      logger.error('未处理的Promise拒绝:', reason);
      logger.error('Promise:', promise);
      shutdown('unhandledRejection');
    });
  }

  getApp() {
    return this.app;
  }

  getJobManager() {
    return this.jobManager;
  }

  getSystemMonitor() {
    return this.systemMonitor;
  }
}

// 如果直接运行此文件，启动应用
if (import.meta.url === `file://${process.argv[1]}`) {
  const app = new Application();
  app.start();
}

export default Application;