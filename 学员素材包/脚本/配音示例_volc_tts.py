"""火山语音合成（声音复刻）示例：一句话 -> 一个 mp3。
用法：python3 配音示例_volc_tts.py --text "你好" --output 配音输出/01.mp3
需要环境变量：VOLC_APPID、VOLC_TOKEN、VOLC_SPEAKER_ID（都在你自己的火山控制台里；不要把密钥写进文件、不要发给别人）。
说明：这是按火山 HTTP 接口写的示例，字段以火山控制台最新文档为准，接口有变动时让 Claude 帮你对照文档改。
克隆的声音必须是你自己的声音，或已获得本人授权。"""
import os, sys, json, uuid, base64, argparse, urllib.request
ap = argparse.ArgumentParser(); ap.add_argument("--text", required=True); ap.add_argument("--output", required=True)
ap.add_argument("--cluster", default=os.environ.get("VOLC_CLUSTER", "volcano_icl"))
a = ap.parse_args()
appid, token, spk = os.environ.get("VOLC_APPID"), os.environ.get("VOLC_TOKEN"), os.environ.get("VOLC_SPEAKER_ID")
if not (appid and token and spk): sys.exit("缺少环境变量 VOLC_APPID / VOLC_TOKEN / VOLC_SPEAKER_ID")
body = {"app": {"appid": appid, "token": token, "cluster": a.cluster}, "user": {"uid": "student"},
        "audio": {"voice_type": spk, "encoding": "mp3", "speed_ratio": 1.0},
        "request": {"reqid": str(uuid.uuid4()), "text": a.text, "operation": "query"}}
req = urllib.request.Request("https://openspeech.bytedance.com/api/v1/tts", data=json.dumps(body).encode(),
                             headers={"Content-Type": "application/json", "Authorization": "Bearer;" + token})
res = json.loads(urllib.request.urlopen(req, timeout=60).read())
if res.get("code") != 3000 or "data" not in res: sys.exit("合成失败：" + str(res.get("message", res))[:200])
os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
open(a.output, "wb").write(base64.b64decode(res["data"])); print("OK", a.output)
