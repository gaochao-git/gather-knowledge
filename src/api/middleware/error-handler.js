import logger from '../../core/logger.js';

const errorHandler = (error, req, res, next) => {
  // 记录错误
  logger.error('API错误:', {
    error: error.message,
    stack: error.stack,
    method: req.method,
    path: req.path,
    body: req.body,
    params: req.params,
    query: req.query
  });

  // 默认错误响应
  let status = 500;
  let message = '内部服务器错误';
  let details = null;

  // 根据错误类型设置不同的响应
  if (error.name === 'ValidationError') {
    status = 400;
    message = '请求参数验证失败';
    details = error.details;
  } else if (error.name === 'MongoError' && error.code === 11000) {
    status = 409;
    message = '数据已存在';
  } else if (error.name === 'CastError') {
    status = 400;
    message = '无效的ID格式';
  } else if (error.status) {
    status = error.status;
    message = error.message;
  } else if (process.env.NODE_ENV === 'development') {
    message = error.message;
    details = error.stack;
  }

  const errorResponse = {
    error: message,
    status,
    timestamp: new Date().toISOString(),
    path: req.path
  };

  if (details) {
    errorResponse.details = details;
  }

  res.status(status).json(errorResponse);
};

export default errorHandler;