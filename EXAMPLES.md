# 使用示例

## 启动服务

1. 安装依赖：
```bash
npm install
```

2. 配置环境变量（.env文件已创建）：
```bash
# 根据需要修改 .env 文件中的配置
```

3. 启动MongoDB（确保MongoDB服务运行在localhost:27017）

4. 启动服务：
```bash
npm start
```

开发模式启动：
```bash
npm run dev
```

## API使用示例

### 1. 测试微信文章采集

测试采集（不保存到数据库）：
```bash
curl -X POST http://localhost:3000/api/collectors/wechat/test \
  -H "Content-Type: application/json" \
  -d '{
    "articleUrls": [
      "https://mp.weixin.qq.com/s/your-article-url"
    ],
    "maxArticles": 3
  }'
```

### 2. 创建采集任务

立即执行采集任务：
```bash
curl -X POST http://localhost:3000/api/tasks/wechat/collect \
  -H "Content-Type: application/json" \
  -d '{
    "articleUrls": [
      "https://mp.weixin.qq.com/s/your-article-url-1",
      "https://mp.weixin.qq.com/s/your-article-url-2"
    ],
    "maxArticles": 10,
    "priority": 1
  }'
```

### 3. 创建定时采集任务

创建每天上午9点的定时采集：
```bash
curl -X POST http://localhost:3000/api/tasks/wechat/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_wechat_collection",
    "cronExpression": "0 9 * * *",
    "config": {
      "articleUrls": [
        "https://mp.weixin.qq.com/s/your-article-url"
      ],
      "maxArticles": 20
    }
  }'
```

### 4. 查询文章

获取文章列表：
```bash
curl "http://localhost:3000/api/articles?limit=10"
```

搜索文章：
```bash
curl -X POST http://localhost:3000/api/articles/search \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "技术分享",
    "limit": 20
  }'
```

### 5. 查看系统状态

```bash
curl "http://localhost:3000/api/system/status"
```

### 6. 查看任务状态

```bash
curl "http://localhost:3000/api/tasks?status=pending"
```

## 程序化使用示例

### 创建自定义采集任务

```javascript
import JobManager from './src/scheduler/job-manager.js';
import Application from './src/app.js';

const app = new Application();
await app.initialize();

const jobManager = app.getJobManager();

// 创建立即执行的采集任务
const task = await jobManager.createWechatCollectionTask({
  articleUrls: [
    'https://mp.weixin.qq.com/s/your-article-url'
  ],
  maxArticles: 10,
  priority: 1
});

console.log('任务已创建:', task.name);

// 创建定时任务
jobManager.createDailyWechatCollection('daily_collection', {
  articleUrls: [
    'https://mp.weixin.qq.com/s/your-article-url'
  ],
  maxArticles: 20
}, 9, 0); // 每天上午9点

console.log('定时任务已创建');
```

### 直接使用采集器

```javascript
import WechatArticleCollector from './src/collectors/wechat/article-collector.js';
import ArticleModel from './src/storage/models/article-model.js';
import database from './src/storage/database.js';

// 连接数据库
await database.connect();

// 创建采集器
const collector = new WechatArticleCollector({
  articleUrls: [
    'https://mp.weixin.qq.com/s/your-article-url'
  ],
  maxArticles: 5,
  requestDelay: 2000
});

// 监听采集事件
collector.on('article_collected', async (article) => {
  console.log('采集到文章:', article.title);
  
  // 保存到数据库
  try {
    await ArticleModel.create(article);
    console.log('文章已保存');
  } catch (error) {
    console.error('保存失败:', error);
  }
});

// 开始采集
await collector.start();
console.log('采集完成');
```

## 扩展新的采集器

### 1. 创建新的采集器目录

```bash
mkdir -p src/collectors/your-new-collector
```

### 2. 实现采集器类

```javascript
// src/collectors/your-new-collector/collector.js
import BaseCollector from '../../core/base-collector.js';

class YourNewCollector extends BaseCollector {
  constructor(options = {}) {
    super('your-new-collector', options);
  }

  async initialize() {
    await super.initialize();
    // 你的初始化逻辑
  }

  async collect() {
    // 你的采集逻辑
    this.incrementTotal();
    
    try {
      // 执行采集
      const result = await this.doCollect();
      this.incrementSuccess();
      this.emit('data_collected', result);
      return result;
    } catch (error) {
      this.incrementFailed();
      throw error;
    }
  }

  async doCollect() {
    // 具体的采集实现
  }
}

export default YourNewCollector;
```

### 3. 在任务调度器中注册新类型

在 `src/scheduler/task-scheduler.js` 的 `runTask` 方法中添加新的case：

```javascript
case 'your_new_collector':
  return await this.runYourNewCollector(taskConfig);
```

## 监控和日志

系统提供了完整的监控和日志功能：

- 应用日志保存在 `logs/` 目录
- 通过 `/api/system/status` 查看系统状态
- 通过 `/api/system/performance` 查看性能统计
- 支持实时监控和告警

## 注意事项

1. **反爬虫策略**：微信公众号有反爬虫策略，请合理设置请求延迟
2. **请求频率**：避免过于频繁的请求，建议设置2-5秒的延迟
3. **数据存储**：确保MongoDB有足够的存储空间
4. **错误处理**：系统有自动重试机制，但某些错误需要人工处理
5. **监控告警**：建议设置适当的监控阈值，及时发现问题