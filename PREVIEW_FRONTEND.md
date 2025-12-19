# 前端预览与回退机制（不影响线上）

这套机制用于：我改完前端后，你先在单独的预览地址确认效果；确认无误后再正式部署到 `https://metawebs.org`。

## 一、预览地址是什么

- 预览服务运行在服务器本机：`127.0.0.1:5051`
- 你需要通过 SSH 端口转发，在你自己的电脑打开：`http://127.0.0.1:5051/...`

注意：预览域名是 `127.0.0.1`，和线上域名不同，浏览器本地存储（token）不共享，可能需要重新登录一次。

## 二、如何在本地打开预览（推荐）

1. 在你电脑终端执行（保持窗口不关闭）：

```bash
ssh -L 5051:127.0.0.1:5051 metaweb-server
```

2. 浏览器打开：

- 首页：`http://127.0.0.1:5051/`
- PDC：`http://127.0.0.1:5051/personal-data-center`

如果你更想用本地 `5050`，也可以把本地 `5050` 映射到服务器 `5051`：

```bash
ssh -L 5050:127.0.0.1:5051 metaweb-server
```

然后打开：`http://127.0.0.1:5050/`

## 三、服务器端预览服务如何运行

预览服务脚本（已放在项目内）：

- 预览服务：`/home/linuxuser/openwebui-custom/tmp/preview-proxy.mjs`
- 启动脚本：`/home/linuxuser/openwebui-custom/tmp/tmp_front-preview-serve.sh`

在服务器上执行（如果预览服务没在跑）：

```bash
cd /home/linuxuser/openwebui-custom
./tmp/tmp_front-preview-serve.sh
```

默认监听：`127.0.0.1:5051`。

## 四、时间戳预览构建（可随时回退）

### 1) 打一个“代码快照”（改动前建议做）

```bash
cd /home/linuxuser/openwebui-custom
./tmp/tmp_front-snapshot.sh 20251217-141153
```

快照目录：`/home/linuxuser/openwebui-custom/tmp/front-snapshots/<timestamp>/`

### 2) 生成一个“预览构建产物”（不覆盖线上 build）

```bash
cd /home/linuxuser/openwebui-custom
./tmp/tmp_front-build-preview.sh 20251217-141153
```

它会把构建输出到：`/home/linuxuser/openwebui-custom/build-previews/<timestamp>/`
并把当前预览指针更新到：`/home/linuxuser/openwebui-custom/build-preview-current`。

### 3) 秒级切换预览版本（回退/对比）

```bash
cd /home/linuxuser/openwebui-custom
./tmp/tmp_front-preview-switch.sh 20251217-141153
```

切换后刷新浏览器预览页面即可。

### 4) 把前端代码直接回退到某个快照（会改源码）

```bash
cd /home/linuxuser/openwebui-custom
./tmp/tmp_front-restore.sh 20251217-141153
```

## 五、确认无误后如何正式部署到线上

预览确认 OK 后，才执行正式构建（覆盖线上使用的 `build/`）：

```bash
cd /home/linuxuser/openwebui-custom
npm run build
```

如需要重载/重启服务，再按现有运维流程执行。

## 六、常见问题：This site can’t be reached / refused to connect

出现这个提示通常是以下原因之一：

1) 本地没有建立 SSH 端口转发
- 预览服务跑在服务器本机 127.0.0.1，你本地直接打开 127.0.0.1:505x 会被拒绝。
- 在你电脑终端执行（保持窗口不关闭）：
  ssh -L 5051:127.0.0.1:5051 metaweb-server

2) 打开的端口和转发端口不一致
- 例如你用的是：ssh -L 5050:127.0.0.1:5051 metaweb-server
  那就打开：http://127.0.0.1:5050/

3) 服务器端预览服务未启动/端口被占用
- 在服务器执行：
  cd /home/linuxuser/openwebui-custom && ./tmp/tmp_front-preview-serve.sh
- 查看是否监听：
  ss -ltnp | grep ":505"  （没有 ss 就用 netstat -tulpn | grep ":505"）
- 查看日志：
  tail -n 50 /home/linuxuser/openwebui-custom/tmp/preview-proxy.log

提示：你也可以用本地脚本一键开启转发（自动挑空闲端口并打印最终URL）：
- ~/metaweb-preview.sh
