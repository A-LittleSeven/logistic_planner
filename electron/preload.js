const { contextBridge } = require('electron');

// 将必要的 Electron API 安全暴露给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  platform: process.platform,
});
