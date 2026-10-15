/**
 * electron-builder 配置
 * 文档: https://www.electron.build/configuration
 */
module.exports = {
  appId: 'com.logistic-planner.app',
  productName: '物流规划调度系统',
  copyright: 'Copyright © 2026',

  directories: {
    output: 'dist-electron',
    buildResources: 'build',
  },

  files: [
    'electron/**/*',
    '!electron/renderer/**/*',
  ],

  // 将后端代码和前端构建产物打入 Resources 目录
  extraResources: [
    {
      from: 'backend',
      to: 'backend',
      filter: [
        '**/*',
        '!.venv/**',
        '!__pycache__/**',
        '!**/__pycache__/**',
        '!*.pyc',
        '!.env',
        '!.claude/**',
      ],
    },
    {
      from: 'electron/renderer',
      to: 'renderer',
    },
  ],

  mac: {
    category: 'public.app-category.business',
    target: [
      {
        target: 'dmg',
        arch: ['arm64'],
      },
    ],
    icon: 'build/icon.icns',
    darkModeSupport: true,
  },

  dmg: {
    title: '物流规划调度系统',
    contents: [
      { x: 130, y: 220 },
      { x: 410, y: 220, type: 'link', path: '/Applications' },
    ],
  },

  win: {
    target: ['nsis'],
    icon: 'build/icon.ico',
  },

  linux: {
    target: ['AppImage'],
    category: 'Office',
  },
};
