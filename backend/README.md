# 后端 (FastAPI)

## 启动

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

接口文档：http://127.0.0.1:8000/docs

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查 + 当前距离提供者 |
| GET | `/api/location/algorithms` | 列出选址可用算法 |
| POST | `/api/location/solve` | 选址求解（加权重心法） |
| GET | `/api/routing/algorithms` | 列出路线规划可用算法 |
| POST | `/api/routing/solve` | 路线规划求解（NN + 2-opt） |
| GET | `/api/clustering/algorithms` | 列出店群规划可用算法 |
| POST | `/api/clustering/solve` | 店群规划求解（K-Means） |

请求体示例见 `/docs` 的 Schema。

## 结构

```
app/
├── core/
│   ├── config.py        # 配置 (.env 注入) + 距离提供者依赖
│   ├── distance.py      # DistanceProvider 接口 + Haversine / AMapWebService 实现
│   └── registry.py      # 求解器注册表 (拓展点)
├── models/              # Pydantic 请求/响应 schema
├── solvers/             # 求解算法 (导入即注册)
└── api/                 # 路由 (每个模块独立 router)
```

## 拓展点

- **新算法**：`solvers/` 里写函数 + `registry.register(name, fn)`，路由自动可用。
- **新距离提供者**：`core/distance.py` 继承 `DistanceProvider` + 在 `get_provider` 注册，`.env` 切换。
- **新模块**：`models/` + `solvers/` + `api/` 各加一文件，`main.py` `include_router`。
