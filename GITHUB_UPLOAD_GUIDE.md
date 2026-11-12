# GitHub 上传说明

这个目录已经从原项目中独立整理出来，可作为 GitHub 仓库根目录。

## 已排除的本地内容

- `backend/.env`：本地密钥和配置
- `backend/data/`：数据库、向量库、上传文件和测试资料
- `.venv/`、`node_modules/`：本地依赖
- `.idea/`、`.workbuddy/`：编辑器和本地工具配置
- 缓存与构建产物

`backend/.env.example` 已保留。其他人在运行项目前，应复制它为 `backend/.env`，然后填写自己的配置。

## 上传步骤

1. 在 GitHub 新建一个空仓库，不勾选自动创建 README、许可证或 `.gitignore`。
2. 在本目录打开终端。
3. 执行：

```bash
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

上传前请再次检查 `git status`，确保 `.env`、数据库和个人资料没有进入暂存区。
