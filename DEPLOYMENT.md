# MetaWeb 部署文档

## 📋 开发到部署流程

### 1. 本地开发

在本地进行开发和测试：

```bash
# 安装依赖
npm install

# 后端依赖
cd backend
pip install -r requirements.txt

# 启动开发服务器
npm run dev
```

### 2. 提交到 GitHub

开发完成后，提交代码：

```bash
# 添加修改
git add .

# 提交
git commit -m "描述你的修改"

# 推送到 GitHub
git push origin main
```

### 3. 服务器部署

#### 方式一：使用部署脚本（推荐）

1. SSH 登录服务器：
```bash
ssh linuxuser@45.32.75.115
```

2. 进入项目目录：
```bash
cd openwebui
```

3. 首次部署需要配置环境变量：
```bash
# 复制环境变量模板
cp .env.production.example .env.production

# 编辑配置文件
nano .env.production
```

需要配置的内容：
- `OPENAI_API_KEY`: 你的 OpenRouter API 密钥
- `WEBUI_SECRET_KEY`: 生成方法 `openssl rand -base64 32`

4. 运行部署脚本：
```bash
./deploy.sh
```

#### 方式二：手动部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 停止旧容器
docker-compose -f docker-compose.prod.yml down

# 3. 构建新镜像
docker-compose -f docker-compose.prod.yml build --no-cache

# 4. 启动容器
docker-compose -f docker-compose.prod.yml up -d

# 5. 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

## 🔧 常用命令

### 查看容器状态
```bash
docker-compose -f docker-compose.prod.yml ps
```

### 查看实时日志
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### 重启容器
```bash
docker-compose -f docker-compose.prod.yml restart
```

### 停止容器
```bash
docker-compose -f docker-compose.prod.yml down
```

### 清理旧镜像
```bash
docker image prune -a
```

## 📁 项目结构

```
openwebui/
├── backend/              # Python 后端
├── src/                  # Svelte 前端
├── Dockerfile           # Docker 镜像构建
├── docker-compose.prod.yml  # 生产环境配置
├── .env.production      # 生产环境变量（不提交到 Git）
├── .env.production.example  # 环境变量模板
├── deploy.sh           # 部署脚本
└── DEPLOYMENT.md       # 本文档
```

## 🌐 访问应用

部署成功后访问：
- URL: `http://45.32.75.115:3000`
- 首次访问需要注册账号

## ⚠️ 注意事项

1. **环境变量安全**
   - `.env.production` 包含敏感信息，不要提交到 Git
   - 已在 `.gitignore` 中排除

2. **端口配置**
   - 应用运行在端口 3000
   - 确保服务器防火墙开放此端口

3. **数据持久化**
   - 用户数据保存在 Docker volume `metaweb-data`
   - 重新部署不会丢失数据

4. **更新流程**
   - 本地开发 → 测试
   - 提交到 GitHub
   - 服务器运行 `./deploy.sh`

## 🐛 故障排除

### 容器无法启动
```bash
# 查看详细日志
docker-compose -f docker-compose.prod.yml logs

# 检查环境变量
cat .env.production
```

### 构建失败
```bash
# 清理并重新构建
docker-compose -f docker-compose.prod.yml down
docker system prune -a
./deploy.sh
```

### Git 拉取失败
```bash
# 检查 SSH 连接
ssh -T git@github.com

# 如果失败，重新配置 SSH key
```

## 📞 支持

遇到问题请检查：
1. Docker 日志
2. 环境变量配置
3. 网络和防火墙设置
