# HTTP 服务器

这是一个简单的 HTTP 服务器，您可以使用默认端口或指定端口来运行服务器，同时支持在后台挂载服务器。

## 运行 HTTP 服务器

### 默认使用 8000 端口运行

若不指定端口，可以通过以下命令运行 HTTP 服务器，默认使用端口 `8000`：

python3 httpserver.py

### 使用指定端口运行
指定端口运行，例如使用 8080 端口，可以运行以下命令：
python3 httpserver.py 8080

### 持续挂载在服务器上
如果希望服务器一直运行在后台（即挂载到服务器），可以使用 nohup 命令，同时将输出保存到日志文件中：
touch /home/username/httpserver.out

#### 启动 HTTP 服务器并挂载到后台，日志输出重定向到 httpserver.out
nohup python3 httpserver.py 8000 > /home/username/httpserver.out 2>&1 &

### 检查后台进程
使用以下命令来检查服务器是否正在后台运行：
ps aux | grep httpserver.py