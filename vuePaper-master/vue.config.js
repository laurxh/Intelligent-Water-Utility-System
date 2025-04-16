module.exports = {
  lintOnSave: false,
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': ''  // 移除/api前缀，使请求能匹配后端路由
        }
      }
    }
  }
};
