const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
const http = require('http');
const fs = require('fs');

// ─── 路径常量 ───
const isDev = !app.isPackaged;
const ROOT = isDev
  ? path.resolve(__dirname, '..')
  : path.resolve(process.resourcesPath);

const BACKEND_DIR = path.join(ROOT, 'backend');
const RENDERER_DIR = isDev
  ? path.join(__dirname, 'renderer')
  : path.join(process.resourcesPath, 'renderer');

// 打包后 venv 和数据库放在用户数据目录（可写），开发时放在 backend 目录
const USER_DATA_DIR = isDev ? BACKEND_DIR : app.getPath('userData');
const VENV_DIR = path.join(USER_DATA_DIR, '.venv');
const DB_PATH = path.join(USER_DATA_DIR, 'logistic.db');

const BACKEND_PORT = 8000;
let pythonProcess = null;
let mainWindow = null;

// ─── 常见 Python 安装路径 ───
const PYTHON_SEARCH_PATHS = [
  '/usr/local/bin/python3',
  '/opt/homebrew/bin/python3',
  '/usr/bin/python3',
  '/Library/Frameworks/Python.framework/Versions/Current/bin/python3',
  'C:\\Python312\\python.exe',
  'C:\\Python311\\python.exe',
  'C:\\Python310\\python.exe',
  'C:\\Program Files\\Python312\\python.exe',
  'C:\\Program Files\\Python311\\python.exe',
  'C:\\Program Files\\Python310\\python.exe',
];

// ─── 查找系统 Python ───
function findSystemPython() {
  // 先尝试 PATH 中的 python/python3
  try {
    const cmd = process.platform === 'win32' ? 'where python' : 'which python3';
    const output = execSync(cmd, { encoding: 'utf8', timeout: 5000 }).trim();
    // where 可能返回多行，取第一行
    const p = output.split('\n')[0].trim();
    if (p && fs.existsSync(p)) {
      console.log(`[Electron] Found python via PATH: ${p}`);
      return p;
    }
  } catch (e) {
    // which/where 失败，继续搜索
  }

  // 搜索常见安装路径
  for (const p of PYTHON_SEARCH_PATHS) {
    if (fs.existsSync(p)) {
      console.log(`[Electron] Found python3 at: ${p}`);
      return p;
    }
  }

  return null;
}

// ─── 查找 Python 可执行文件（优先 venv） ───
function findPython() {
  const venvPython = path.join(
    VENV_DIR,
    process.platform === 'win32' ? 'Scripts' : 'bin',
    process.platform === 'win32' ? 'python.exe' : 'python'
  );
  if (fs.existsSync(venvPython)) return venvPython;

  // 回退到系统 Python
  const systemPython = findSystemPython();
  if (systemPython) return systemPython;

  return process.platform === 'win32' ? 'python' : 'python3';
}

// ─── 检测 venv 是否存在，不存在则创建并安装依赖 ───
function ensureVenv() {
  return new Promise((resolve, reject) => {
    const venvPython = path.join(
      VENV_DIR,
      process.platform === 'win32' ? 'Scripts' : 'bin',
      process.platform === 'win32' ? 'python.exe' : 'python'
    );

    if (fs.existsSync(venvPython)) {
      // 验证 venv 中的依赖是否完整
      try {
        execSync(`"${venvPython}" -c "import uvicorn; import fastapi"`, { timeout: 10000, stdio: 'pipe' });
        console.log(`[Electron] venv already exists and is valid at: ${VENV_DIR}`);
        return resolve();
      } catch (e) {
        console.log('[Electron] venv exists but dependencies are missing, recreating...');
        fs.rmSync(VENV_DIR, { recursive: true, force: true });
      }
    }

    const systemPython = findSystemPython();
    if (!systemPython) {
      return reject(new Error(
        '未找到 Python 3 安装。\n请安装 Python 3.10+ 后重试。\n\n' +
        '推荐安装方式：\n' +
        '  brew install python3\n' +
        '  或从 https://www.python.org/downloads/ 下载'
      ));
    }

    // 确保 userData 目录存在
    if (!fs.existsSync(USER_DATA_DIR)) {
      fs.mkdirSync(USER_DATA_DIR, { recursive: true });
    }

    console.log(`[Electron] Creating venv at: ${VENV_DIR}`);
    const createVenv = spawn(systemPython, ['-m', 'venv', VENV_DIR], {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONUTF8: '1' },
    });

    let stderrOutput = '';
    createVenv.stderr.on('data', (data) => {
      stderrOutput += data.toString();
      console.error(`[venv] ${data.toString().trim()}`);
    });

    createVenv.on('close', (code) => {
      if (code !== 0) {
        return reject(new Error(`创建 Python venv 失败 (exit code ${code})\n${stderrOutput}`));
      }

      console.log('[Electron] Installing pip dependencies...');
      const pip = path.join(
        VENV_DIR,
        process.platform === 'win32' ? 'Scripts' : 'bin',
        process.platform === 'win32' ? 'pip.exe' : 'pip'
      );
      const requirementsPath = path.join(BACKEND_DIR, 'requirements.txt');
      const installDeps = spawn(pip, ['install', '-r', requirementsPath, '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'], {
        stdio: ['ignore', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONUTF8: '1' },
      });

      let pipStderr = '';
      installDeps.stdout.on('data', (data) => {
        console.log(`[pip] ${data.toString().trim()}`);
      });
      installDeps.stderr.on('data', (data) => {
        pipStderr += data.toString();
        console.error(`[pip] ${data.toString().trim()}`);
      });

      installDeps.on('close', (pipCode) => {
        if (pipCode !== 0) {
          return reject(new Error(`pip install 失败 (exit code ${pipCode})\n${pipStderr}`));
        }
        console.log('[Electron] Dependencies installed successfully');
        resolve();
      });

      installDeps.on('error', reject);
    });

    createVenv.on('error', (err) => {
      reject(new Error(`无法执行 Python: ${err.message}`));
    });
  });
}

// ─── 检测后端是否已在运行 ───
function isBackendRunning() {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${BACKEND_PORT}/health`, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.setTimeout(1000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

// ─── 启动 Python 后端 ───
async function startBackend() {
  const alreadyRunning = await isBackendRunning();
  if (alreadyRunning) {
    console.log('[Electron] Backend already running on port ' + BACKEND_PORT + ', reusing...');
    return;
  }

  const python = findPython();
  console.log(`[Electron] Starting backend with: ${python}`);
  console.log(`[Electron] Backend dir: ${BACKEND_DIR}`);
  console.log(`[Electron] Database path: ${DB_PATH}`);

  // 如果打包模式下源 db 不在 userData，拷贝初始数据库过去
  if (!isDev) {
    const srcDb = path.join(BACKEND_DIR, 'logistic.db');
    if (fs.existsSync(srcDb) && !fs.existsSync(DB_PATH)) {
      console.log('[Electron] Copying initial database to userData...');
      fs.copyFileSync(srcDb, DB_PATH);
    }
  }

  pythonProcess = spawn(
    python,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)],
    {
      cwd: BACKEND_DIR,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: {
        ...process.env,
        PYTHONUTF8: '1',
        // 确保 macOS 下能找到常见命令
        PATH: `/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:${process.env.PATH || ''}`,
        CORS_ORIGINS: '*',
        // 告诉后端数据库文件放在用户数据目录
        DATABASE_PATH: DB_PATH,
      },
    }
  );

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Backend] ${data.toString().trim()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Backend] Process exited with code ${code}`);
    pythonProcess = null;
  });

  pythonProcess.on('error', (err) => {
    console.error('[Backend] Failed to start:', err.message);
    pythonProcess = null;
  });
}

// ─── 等待后端就绪 (health check) ───
function waitForBackend(maxRetries = 60, intervalMs = 500) {
  return new Promise((resolve, reject) => {
    let retries = 0;

    const check = () => {
      const req = http.get(`http://127.0.0.1:${BACKEND_PORT}/health`, (res) => {
        if (res.statusCode === 200) {
          console.log('[Electron] Backend is ready!');
          resolve();
        } else {
          retry();
        }
      });

      req.on('error', () => retry());
      req.setTimeout(1000, () => {
        req.destroy();
        retry();
      });
    };

    const retry = () => {
      retries++;
      if (retries >= maxRetries) {
        reject(new Error('后端服务在 30 秒内未响应，请检查 Python 环境'));
      } else {
        setTimeout(check, intervalMs);
      }
    };

    check();
  });
}

// ─── 创建主窗口 ───
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: '智能物流调度与路径规划系统',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    trafficLightPosition: { x: 16, y: 16 },
  });

  const indexPath = path.join(RENDERER_DIR, 'index.html');
  console.log(`[Electron] Loading: ${indexPath} (exists: ${fs.existsSync(indexPath)})`);

  if (fs.existsSync(indexPath)) {
    mainWindow.loadFile(indexPath);
  } else {
    mainWindow.loadURL(`data:text/html;charset=utf-8,
      <html><body style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;background:#1a1a2e;color:#eee;">
        <div style="text-align:center;">
          <h2>⚠️ 前端未构建</h2>
          <p>请先执行 <code style="background:#333;padding:4px 8px;border-radius:4px;">cd frontend && npm run build</code></p>
          <p style="color:#888;font-size:13px;">期望路径: ${indexPath}</p>
        </div>
      </body></html>
    `);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ─── 优雅终止后端进程 ───
function killBackend() {
  if (pythonProcess) {
    console.log('[Electron] Shutting down backend...');
    pythonProcess.kill('SIGTERM');

    setTimeout(() => {
      if (pythonProcess) {
        try {
          pythonProcess.kill('SIGKILL');
        } catch (e) {
          // 进程可能已退出
        }
      }
    }, 3000);
  }
}

// ─── App 生命周期 ───
app.whenReady().then(async () => {
  try {
    console.log(`[Electron] isDev: ${isDev}`);
    console.log(`[Electron] ROOT: ${ROOT}`);
    console.log(`[Electron] BACKEND_DIR: ${BACKEND_DIR}`);
    console.log(`[Electron] RENDERER_DIR: ${RENDERER_DIR}`);
    console.log(`[Electron] USER_DATA_DIR: ${USER_DATA_DIR}`);

    // 1. 确保 venv 就绪
    await ensureVenv();

    // 2. 启动后端
    await startBackend();

    // 3. 等待后端就绪
    await waitForBackend();

    // 4. 创建窗口
    createWindow();
  } catch (err) {
    console.error('[Electron] Startup failed:', err.message);
    dialog.showErrorBox(
      '启动失败',
      err.message
    );
    app.quit();
  }
});

app.on('window-all-closed', () => {
  killBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  killBackend();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', () => {
  killBackend();
});
