import modal
import subprocess
import sys
import os

app = modal.App(name="web-app-v1")

image = (
    modal.Image.debian_slim()
    .apt_install("curl")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".", remote_path="/workspace")
)

@app.function(
    region="ap-northeast",
    image=image,
    timeout=42500
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
