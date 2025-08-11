import logger from '../../core/logger.js';
import performanceTracker from '../../utils/performance-tracker.js';

const requestLogger = (req, res, next) => {
  const startTime = Date.now();
  const operationName = `${req.method} ${req.path}`;

  // 记录请求开始
  logger.info(`${req.method} ${req.originalUrl}`, {
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });

  // 开始性能追踪
  performanceTracker.start(operationName, {
    method: req.method,
    path: req.path,
    ip: req.ip
  });

  // 重写res.end以记录响应
  const originalEnd = res.end;
  res.end = function(...args) {
    const duration = Date.now() - startTime;
    
    // 记录响应
    logger.info(`${req.method} ${req.originalUrl} - ${res.statusCode} - ${duration}ms`);

    // 结束性能追踪
    performanceTracker.end(operationName, {
      statusCode: res.statusCode,
      success: res.statusCode < 400
    });

    originalEnd.apply(this, args);
  };

  next();
};

export default requestLogger;