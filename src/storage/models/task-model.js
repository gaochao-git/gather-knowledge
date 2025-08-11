import database from '../database.js';
import logger from '../../core/logger.js';

class TaskModel {
  constructor() {
    this.collectionName = 'tasks';
  }

  async getCollection() {
    const db = await database.connect();
    return db.collection(this.collectionName);
  }

  async create(taskData) {
    try {
      const collection = await this.getCollection();
      const task = {
        ...taskData,
        status: 'pending',
        createdAt: new Date(),
        updatedAt: new Date(),
        retryCount: 0
      };

      const result = await collection.insertOne(task);
      logger.info(`任务已创建: ${task.name}`);
      return { ...task, _id: result.insertedId };
    } catch (error) {
      logger.error('创建任务失败:', error);
      throw error;
    }
  }

  async findById(id) {
    try {
      const collection = await this.getCollection();
      return await collection.findOne({ _id: id });
    } catch (error) {
      logger.error('查询任务失败:', error);
      throw error;
    }
  }

  async findByName(name) {
    try {
      const collection = await this.getCollection();
      return await collection.findOne({ name });
    } catch (error) {
      logger.error('查询任务失败:', error);
      throw error;
    }
  }

  async findByStatus(status, limit = 50) {
    try {
      const collection = await this.getCollection();
      return await collection
        .find({ status })
        .sort({ createdAt: -1 })
        .limit(limit)
        .toArray();
    } catch (error) {
      logger.error('查询任务失败:', error);
      throw error;
    }
  }

  async getPendingTasks() {
    try {
      const collection = await this.getCollection();
      return await collection
        .find({ 
          status: 'pending',
          $or: [
            { nextRunTime: { $exists: false } },
            { nextRunTime: { $lte: new Date() } }
          ]
        })
        .sort({ priority: -1, createdAt: 1 })
        .toArray();
    } catch (error) {
      logger.error('获取待执行任务失败:', error);
      throw error;
    }
  }

  async updateStatus(id, status, result = null) {
    try {
      const collection = await this.getCollection();
      const updateData = {
        status,
        updatedAt: new Date()
      };

      if (result) {
        updateData.result = result;
      }

      if (status === 'running') {
        updateData.startTime = new Date();
      } else if (status === 'completed' || status === 'failed') {
        updateData.endTime = new Date();
      }

      const taskResult = await collection.updateOne(
        { _id: id },
        { $set: updateData }
      );
      
      return taskResult.modifiedCount > 0;
    } catch (error) {
      logger.error('更新任务状态失败:', error);
      throw error;
    }
  }

  async incrementRetry(id) {
    try {
      const collection = await this.getCollection();
      const result = await collection.updateOne(
        { _id: id },
        { 
          $inc: { retryCount: 1 },
          $set: { updatedAt: new Date() }
        }
      );
      
      return result.modifiedCount > 0;
    } catch (error) {
      logger.error('增加重试次数失败:', error);
      throw error;
    }
  }

  async setNextRunTime(id, nextRunTime) {
    try {
      const collection = await this.getCollection();
      const result = await collection.updateOne(
        { _id: id },
        { 
          $set: { 
            nextRunTime,
            updatedAt: new Date()
          }
        }
      );
      
      return result.modifiedCount > 0;
    } catch (error) {
      logger.error('设置下次运行时间失败:', error);
      throw error;
    }
  }

  async getTaskHistory(limit = 100) {
    try {
      const collection = await this.getCollection();
      return await collection
        .find({})
        .sort({ createdAt: -1 })
        .limit(limit)
        .toArray();
    } catch (error) {
      logger.error('获取任务历史失败:', error);
      throw error;
    }
  }

  async getStats() {
    try {
      const collection = await this.getCollection();
      
      const stats = await collection.aggregate([
        {
          $group: {
            _id: '$status',
            count: { $sum: 1 }
          }
        }
      ]).toArray();

      const result = {
        total: 0,
        pending: 0,
        running: 0,
        completed: 0,
        failed: 0
      };

      stats.forEach(stat => {
        result[stat._id] = stat.count;
        result.total += stat.count;
      });

      return result;
    } catch (error) {
      logger.error('获取任务统计失败:', error);
      throw error;
    }
  }

  async cleanup(olderThanDays = 30) {
    try {
      const collection = await this.getCollection();
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - olderThanDays);

      const result = await collection.deleteMany({
        status: { $in: ['completed', 'failed'] },
        endTime: { $lt: cutoffDate }
      });

      logger.info(`清理了 ${result.deletedCount} 个历史任务`);
      return result.deletedCount;
    } catch (error) {
      logger.error('清理任务失败:', error);
      throw error;
    }
  }
}

export default new TaskModel();