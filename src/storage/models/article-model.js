import database from '../database.js';
import logger from '../../core/logger.js';

class ArticleModel {
  constructor() {
    this.collectionName = 'articles';
  }

  async getCollection() {
    const db = await database.connect();
    return db.collection(this.collectionName);
  }

  async create(articleData) {
    try {
      const collection = await this.getCollection();
      const article = {
        ...articleData,
        _id: this.generateId(articleData.url),
        createdAt: new Date(),
        updatedAt: new Date()
      };

      const result = await collection.insertOne(article);
      logger.info(`文章已保存: ${article.title}`);
      return { ...article, _id: result.insertedId };
    } catch (error) {
      if (error.code === 11000) {
        logger.warn(`文章已存在，跳过保存: ${articleData.title}`);
        return await this.findByUrl(articleData.url);
      }
      logger.error('保存文章失败:', error);
      throw error;
    }
  }

  async findByUrl(url) {
    try {
      const collection = await this.getCollection();
      return await collection.findOne({ url });
    } catch (error) {
      logger.error('查询文章失败:', error);
      throw error;
    }
  }

  async findById(id) {
    try {
      const collection = await this.getCollection();
      return await collection.findOne({ _id: id });
    } catch (error) {
      logger.error('查询文章失败:', error);
      throw error;
    }
  }

  async findByAccount(accountName, options = {}) {
    try {
      const collection = await this.getCollection();
      const query = { 'accountInfo.name': accountName };
      
      let cursor = collection.find(query);
      
      if (options.sort) {
        cursor = cursor.sort(options.sort);
      } else {
        cursor = cursor.sort({ publishTime: -1 });
      }
      
      if (options.limit) {
        cursor = cursor.limit(options.limit);
      }
      
      if (options.skip) {
        cursor = cursor.skip(options.skip);
      }

      return await cursor.toArray();
    } catch (error) {
      logger.error('查询账号文章失败:', error);
      throw error;
    }
  }

  async search(keyword, options = {}) {
    try {
      const collection = await this.getCollection();
      const query = {
        $text: { $search: keyword }
      };

      let cursor = collection.find(query);
      
      if (options.sort) {
        cursor = cursor.sort(options.sort);
      } else {
        cursor = cursor.sort({ score: { $meta: 'textScore' } });
      }
      
      if (options.limit) {
        cursor = cursor.limit(options.limit);
      }

      return await cursor.toArray();
    } catch (error) {
      logger.error('搜索文章失败:', error);
      throw error;
    }
  }

  async update(id, updateData) {
    try {
      const collection = await this.getCollection();
      const result = await collection.updateOne(
        { _id: id },
        { 
          $set: {
            ...updateData,
            updatedAt: new Date()
          }
        }
      );
      
      return result.modifiedCount > 0;
    } catch (error) {
      logger.error('更新文章失败:', error);
      throw error;
    }
  }

  async delete(id) {
    try {
      const collection = await this.getCollection();
      const result = await collection.deleteOne({ _id: id });
      return result.deletedCount > 0;
    } catch (error) {
      logger.error('删除文章失败:', error);
      throw error;
    }
  }

  async getRecentArticles(limit = 20) {
    try {
      const collection = await this.getCollection();
      return await collection
        .find({})
        .sort({ collectedAt: -1 })
        .limit(limit)
        .toArray();
    } catch (error) {
      logger.error('获取最新文章失败:', error);
      throw error;
    }
  }

  async getStats() {
    try {
      const collection = await this.getCollection();
      const total = await collection.countDocuments();
      
      const accountStats = await collection.aggregate([
        {
          $group: {
            _id: '$accountInfo.name',
            count: { $sum: 1 },
            lastCollected: { $max: '$collectedAt' }
          }
        },
        {
          $sort: { count: -1 }
        }
      ]).toArray();

      return {
        total,
        accountStats
      };
    } catch (error) {
      logger.error('获取文章统计失败:', error);
      throw error;
    }
  }

  generateId(url) {
    // 从URL中提取文章唯一标识
    const urlObj = new URL(url);
    const biz = urlObj.searchParams.get('__biz');
    const mid = urlObj.searchParams.get('mid');
    const idx = urlObj.searchParams.get('idx');
    const sn = urlObj.searchParams.get('sn');
    
    if (biz && mid && idx && sn) {
      return `${biz}_${mid}_${idx}`;
    }
    
    // 如果无法解析参数，使用URL的hash
    return Buffer.from(url).toString('base64').replace(/[/+=]/g, '');
  }
}

export default new ArticleModel();