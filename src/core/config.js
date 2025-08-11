import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

dotenv.config();

const config = {
  server: {
    port: process.env.PORT || 3000,
    host: process.env.HOST || 'localhost'
  },
  database: {
    url: process.env.MONGODB_URL || 'mongodb://localhost:27017/gather-knowledge',
    options: {
      useNewUrlParser: true,
      useUnifiedTopology: true
    }
  },
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    dir: path.join(__dirname, '../../logs')
  },
  collectors: {
    wechat: {
      baseUrl: 'https://mp.weixin.qq.com',
      timeout: 30000,
      retryAttempts: 3,
      retryDelay: 1000
    }
  },
  scheduler: {
    timezone: 'Asia/Shanghai',
    maxConcurrentJobs: 5
  }
};

export default config;