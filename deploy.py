import modal
import subprocess
import sys
import os

app = modal.App(name="wl-app-v1")

image = (
    modal.Image.debian_slim()
    .apt_install("curl")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".", remote_path="/workspace")
)

@app.function(
    timeout=43200,
    min_containers=1,
    cpu=0.125,
    memory=128,
    region="ap-northeast"
)

def run_app():
    os.chdir("/workspace")
    print("🟢 Starting app.py...")

    process = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())

    if process.returncode != 0:
        error = process.stderr.read()
        print(f"🔴 Process failed with code {process.returncode}: {error}")
        raise modal.exception.ExecutionError("Script execution failed")

if __name__ == "__main__":
    print("🚀 Deploying application...")
    app.deploy()  # ✅ 修复点：不要加参数

    print("⚙️ Launching remote run...")
    run_app.spawn()  # ✅ 异步执行函数
    print("✅ Deployment and remote launch complete.")


    # 设置Modal应用名称 - 修改这里可以更改部署到Modal平台的项目名称

    # 设置保活频率、容器个数、CPU、内存、地区域
    @modal.wsgi_app()
    def modal_web_server():
        from flask import Flask, Response
        import time
        import os

        print(f"Starting Modal web server")

        # 启动后台服务
        background_thread = threading.Thread(target=start_server_sync, daemon=True)
        background_thread.start()

        # 等待后台服务启动
        time.sleep(5)

        flask_app = Flask(__name__)

        @flask_app.route('/')
        def home():
            # 检查项目根目录是否存在index.html文件
            index_path = 'index.html'
            if os.path.exists(index_path):
                try:
                    with open(index_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # 返回HTML内容并设置正确的Content-Type
                    return Response(content, mimetype='text/html')
                except Exception as e:
                    print(f"Error reading index.html: {e}")
                    return 'Hello World!'
            else:
                return 'Hello World!'

        @flask_app.route('/health')
        def health():
            return 'OK'

        @flask_app.route(f'/{SUB_PATH}')
        def subscription():
            try:
                if os.path.exists(sub_path):
                    with open(sub_path, 'rb') as f:
                        content = f.read()
                    return Response(content, mimetype='text/plain')
                else:
                    return Response('Not Found', status=404)
            except Exception as e:
                print(f"Error reading subscription file: {e}")
                return Response('Error', status=500)

        print(f"Flask app ready")
        return flask_app
