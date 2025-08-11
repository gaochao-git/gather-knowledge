import axios from 'axios';
import logger from '../core/logger.js';

class HttpClient {
  constructor(config = {}) {
    this.config = {
      timeout: 30000,
      maxRedirects: 5,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      },
      ...config
    };

    this.client = axios.create(this.config);
    this.setupInterceptors();
  }

  setupInterceptors() {
    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        logger.debug(`HTTP Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        logger.error('HTTP Request Error:', error);
        return Promise.reject(error);
      }
    );

    // 响应拦截器
    this.client.interceptors.response.use(
      (response) => {
        logger.debug(`HTTP Response: ${response.status} ${response.config.url}`);
        return response;
      },
      (error) => {
        if (error.response) {
          logger.error(`HTTP Response Error: ${error.response.status} ${error.config?.url}`);
        } else if (error.request) {
          logger.error(`HTTP Request Timeout: ${error.config?.url}`);
        } else {
          logger.error('HTTP Error:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  async get(url, config = {}) {
    return this.client.get(url, config);
  }

  async post(url, data = {}, config = {}) {
    return this.client.post(url, data, config);
  }

  async put(url, data = {}, config = {}) {
    return this.client.put(url, data, config);
  }

  async delete(url, config = {}) {
    return this.client.delete(url, config);
  }

  setDefaultHeader(key, value) {
    this.client.defaults.headers.common[key] = value;
  }

  setDefaultHeaders(headers) {
    Object.assign(this.client.defaults.headers.common, headers);
  }

  setCookie(cookie) {
    this.setDefaultHeader('Cookie', cookie);
  }

  setTimeout(timeout) {
    this.client.defaults.timeout = timeout;
  }
}

export default HttpClient;