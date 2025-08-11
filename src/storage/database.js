import { MongoClient } from 'mongodb';
import config from '../core/config.js';
import logger from '../core/logger.js';

class Database {
  constructor() {
    this.client = null;
    this.db = null;
    this.isConnected = false;
  }

  async connect() {
    try {
      if (this.isConnected) {
        return this.db;
      }

      logger.info('连接到数据库...');
      this.client = new MongoClient(config.database.url, config.database.options);
      
      await this.client.connect();
      
      // 从URL中提取数据库名称
      const dbName = config.database.url.split('/').pop().split('?')[0];
      this.db = this.client.db(dbName);
      this.isConnected = true;

      logger.info(`成功连接到数据库: ${dbName}`);
      
      // 创建索引
      await this.createIndexes();
      
      return this.db;
    } catch (error) {
      logger.error('数据库连接失败:', error);
      throw error;
    }
  }

  async createIndexes() {
    try {
      // 文章集合索引
      const articlesCollection = this.db.collection('articles');
      await articlesCollection.createIndex({ url: 1 }, { unique: true });
      await articlesCollection.createIndex({ title: 'text', content: 'text' });
      await articlesCollection.createIndex({ publishTime: -1 });
      await articlesCollection.createIndex({ collectedAt: -1 });
      await articlesCollection.createIndex({ 'accountInfo.name': 1 });

      // 任务集合索引
      const tasksCollection = this.db.collection('tasks');
      await tasksCollection.createIndex({ name: 1, status: 1 });
      await tasksCollection.createIndex({ createdAt: -1 });
      await tasksCollection.createIndex({ nextRunTime: 1 });

      logger.info('数据库索引创建完成');
    } catch (error) {
      logger.error('创建索引失败:', error);
    }
  }

  async disconnect() {
    if (this.client && this.isConnected) {
      await this.client.close();
      this.isConnected = false;
      logger.info('数据库连接已关闭');
    }
  }

  getCollection(name) {
    if (!this.isConnected || !this.db) {
      throw new Error('数据库未连接');
    }
    return this.db.collection(name);
  }

  async ping() {
    try {
      await this.db.admin().ping();
      return true;
    } catch (error) {
      logger.error('数据库ping失败:', error);
      return false;
    }
  }

  async getStats() {
    try {
      const stats = await this.db.stats();
      return {
        connected: this.isConnected,
        collections: stats.collections,
        dataSize: stats.dataSize,
        storageSize: stats.storageSize,
        objects: stats.objects
      };
    } catch (error) {
      logger.error('获取数据库统计失败:', error);
      return { connected: this.isConnected };
    }
  }
}

// 创建单例实例
const database = new Database();

export default database;