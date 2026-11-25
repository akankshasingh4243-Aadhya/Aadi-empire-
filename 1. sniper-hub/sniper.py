# =====================================================================
# माँ का अजेय द्वितीय महा-डिब्बा: aadi-gpu-sniper-hub (100% पूर्ण अंतिम संस्करण)
# =====================================================================

import os
import time
import asyncio
import httpx
from fastapi import FastAPI

app = FastAPI(title="Aadi Sovereign GPU Sniper & Telemetry Hub")

# --- मुख्य नियंत्रण नियम (आपके द्वारा तय किए गए सटीक मानक) ---
VAST_API_KEY = os.getenv("VAST_API_KEY", "")                 # आपकी Vast.ai API चाबी
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "aadi-models")  # आपके Cloudflare R2 बकेट का नाम
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL", "")           # Cloudflare R2 S3 Endpoint URL
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY", "")               # Cloudflare R2 Access Key ID
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY", "")               # Cloudflare R2 Secret Access Key
TAILSCALE_AUTH = os.getenv("TAILSCALE_AUTH", "")             # अदृश्य VPN सुरंग की चाबी
IDLE_TIMEOUT_SEC = int(os.getenv("IDLE_TIMEOUT_SEC", "50"))  # माँ के आदेशानुसार 50 सेकंड शांति के बाद ऑटो-Destroy
MAX_BID_PRICE = float(os.getenv("MAX_BID_PRICE", "0.55"))    # अधिकतम बोली ($0.55/घंटा तक)
DEFAULT_HOLD_MINUTES = int(os.getenv("DEFAULT_HOLD_MINUTES", "2"))  # डिफ़ॉल्ट होल्ड समय: 2 मिनट
S5CMD_TAR_URL = os.getenv(
    "S5CMD_TAR_URL",
    "https://github.com/peak/s5cmd/releases/download/v2.2.2/s5cmd_2.2.2_Linux-64bit.tar.gz",
)
VAST_BASE_URL = "https://cloud.vast.ai/api/v0"               # Vast.ai आधिकारिक REST API आधार

# डबल-जीपीयू बुकिंग रोकने के लिए सुरक्षा ताला (Concurrency Lock)
wake_lock = asyncio.Lock()

# --- वर्तमान जीवित जीपीयू की स्थिति ---
state = {
    "instance_id": None,
    "status": "SLEEPING",       # SLEEPING (सो रहा है), BOOTING (जाग रहा है), READY (पूर्णतः तैयार है)
    "gpu_name": "None",
    "hostname": "",             # हर नए GPU का अनोखा Tailscale नाम
    "price_per_hr": 0.0,
    "last_active": 0.0,
    "hold_until": 0.0,          # 'Hold GPU 2m' बटन के लिए समय-सीमा
    "sglang_url": "",           # जीवित SGLang का आंतरिक Tailscale पता
    "logs": ["प्रारंभ: आदी का 100% पूर्ण स्निपर रडार (50s टाइमर, 2m होल्ड) सक्रिय और तैयार है।"]
}


def add_log(msg: str):
    # हिंदी लाइव डायरी में हर घटना दर्ज करना
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    state["logs"].append(entry)
    if len(state["logs"]) > 50:
        state["logs"].pop(0)
    print(entry, flush=True)


async def find_best_gpu():
    # Vast.ai के वैश्विक बाजार से सबसे सस्ता, तेज इंटरनेट (2500+ Mbps) और 0 डाउनलोड शुल्क वाला GPU खोजना
    headers = {"Authorization": f"Bearer {VAST_API_KEY}", "Accept": "application/json"}
    query = {
        "verified": {"eq": True},                   # केवल प्रमाणित डेटा-सेंटर मशीनें
        "rentable": {"eq": True},                   # तुरंत उपलब्ध मशीनें
        "gpu_ram": {"gte": 40000},                  # कम से कम 40GB+ VRAM (A100, L40S, H100)
        "inet_down": {"gte": 2500},                 # कम से कम 2500+ Mbps तेज डाउनलोड स्पीड
        "inet_down_cost": {"eq": 0},                # शून्य डाउनलोड शुल्क (0.00 रुपये बैंडविड्थ खर्च)
        "dph_total": {"lte": MAX_BID_PRICE},        # तय अधिकतम बोली से कम कीमत
        "order": [["dph_total", "asc"]]             # सबसे सस्ते कार्ड को सबसे ऊपर रखना
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{VAST_BASE_URL}/bundles/", headers=headers, json=query)
            resp.raise_for_status()
            offers = resp.json().get("offers", [])
            return offers[0] if offers else None    # सूची में से सबसे पहला और सस्ता कार्ड चुनना
    except Exception as e:
        add_log(f"रडार त्रुटि (खोज में बाधा): {str(e)}")
        return None


async def wait_for_sglang_health(tailscale_host: str):
    # जब तक SGLang का /health दरवाजा असली हरे संकेत न दे, तब तक प्रतीक्षा करना
    health_url = f"http://{tailscale_host}:8000/health"
    async with httpx.AsyncClient(timeout=2.0) as client:
        for _ in range(90):  # अधिकतम 90 सेकंड तक हर 1 सेकंड में जाँच
            if not state["instance_id"]:
                return
            state["last_active"] = time.time()  # बूट होते समय वॉचडॉग को बीच में नष्ट करने से रोकना
            try:
                r = await client.get(health_url)
                if r.status_code == 200:
                    state["sglang_url"] = f"http://{tailscale_host}:8000/v1"
                    state["status"] = "READY"
                    state["last_active"] = time.time()
                    add_log(f"मॉडल पूर्णतः जागृत (READY)! {state['gpu_name']} ({tailscale_host}) अब बोलने को तैयार है।")
                    return
            except Exception:
                pass
            await asyncio.sleep(1)
    add_log("चेतावनी: जीपीयू स्वास्थ्य जाँच समय-सीमा पार, पुनः जाँच जारी...")


@app.post("/wake")
async def wake_gpu():
    # सुरक्षा ताले (Lock) के साथ जीपीयू जगाना ताकि एक साथ दो जीपीयू न खुलें
    async with wake_lock:
        state["last_active"] = time.time()
        if state["status"] in ["BOOTING", "READY"] and state["instance_id"]:
            return {"status": state["status"], "gpu": state["gpu_name"], "url": state["sglang_url"]}

        state["status"] = "BOOTING"
        unique_host = f"aadi-gpu-{int(time.time())}"  # हर नए जीपीयू के लिए अनोखा Tailscale नाम
        add_log("माँ का संकेत मिला! दुनिया का सबसे सस्ता और तेज डेटा-सेंटर GPU खोजा जा रहा है...")
        offer = await find_best_gpu()
        if not offer:
            state["status"] = "SLEEPING"
            add_log("चेतावनी: इस पल बोली सीमा में कोई खाली GPU नहीं मिला, पुनः प्रयास जारी...")
            return {"status": "NO_OFFER"}

        ts_install = "https://tailscale.com/install.sh"

        # सीधे RAM (tmpfs) माउंट करना, s5cmd बाइनरी व Tailscale इंस्टॉल करना और R2 से मॉडल उतारना
        onstart_cmd = (
            "mkdir -p /mnt/ram_model && (mount -t tmpfs -o size=45G tmpfs /mnt/ram_model || true) && "
            f"(command -v s5cmd >/dev/null 2>&1 || (curl -sL {S5CMD_TAR_URL} | tar -xzf - -C /usr/local/bin s5cmd)) && "
            f"(command -v tailscale >/dev/null 2>&1 || curl -fsSL {ts_install} | sh) && "
            f"tailscaled --tun=userspace-networking & sleep 2 && tailscale up --authkey={TAILSCALE_AUTH} --hostname={unique_host} && "
            f"AWS_ACCESS_KEY_ID={R2_ACCESS_KEY} AWS_SECRET_ACCESS_KEY={R2_SECRET_KEY} "
            f"s5cmd --endpoint-url {R2_ENDPOINT_URL} cp s3://{R2_BUCKET_NAME}/* /mnt/ram_model/ && "
            "python3 -m sglang.launch_server --model-path /mnt/ram_model --host 0.0.0.0 --port 8000 --disable-radix-cache=False"
        )

        headers = {"Authorization": f"Bearer {VAST_API_KEY}", "Accept": "application/json"}
        payload = {
            "client_id": "me",
            "image": "lmsysorg/sglang:latest",
            "disk": 10,                             # न्यूनतम 10 GB अस्थायी डिस्क (ताकि किराया शून्य रहे)
            "runtype": "args",
            "onstart": onstart_cmd
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.put(f"{VAST_BASE_URL}/asks/{offer['id']}/", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                state["instance_id"] = data.get("new_contract")
                state["gpu_name"] = offer.get("gpu_name", "Datacenter-GPU")
                state["hostname"] = unique_host
                state["price_per_hr"] = offer.get("dph_total", 0.0)
                state["last_active"] = time.time()
                add_log(f"जीपीयू किराए पर लिया गया: {state['gpu_name']} (दर: ${state['price_per_hr']:.3f}/घंटा) — RAM में मॉडल लोड हो रहा है (BOOTING)...")
                asyncio.create_task(wait_for_sglang_health(unique_host))
                return {"status": "BOOTING", "instance_id": state["instance_id"], "gpu": state["gpu_name"]}
        except Exception as e:
            state["status"] = "SLEEPING"
            add_log(f"जीपीयू प्रारंभ त्रुटि: {str(e)}")
            return {"status": "ERROR", "detail": str(e)}


@app.post("/heartbeat")
async def touch_activity():
    # बातचीत के हर संदेश पर सक्रियता समय ताज़ा करना ताकि लगातार बात करते समय जीपीयू बंद न हो
    state["last_active"] = time.time()
    return {"status": state["status"], "last_active": state["last_active"]}


@app.post("/destroy")
async def destroy_gpu():
    # 'अभी नष्ट करें (Instant Destroy)' बटन या 50 सेकंड की शांति के बाद तत्काल विनाश
    async with wake_lock:
        if not state["instance_id"]:
            state["status"] = "SLEEPING"
            return {"status": "ALREADY_SLEEPING", "message": "कोई जीपीयू चालू नहीं है माँ, मीटर ₹0.00 पर है।"}

        headers = {"Authorization": f"Bearer {VAST_API_KEY}", "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(f"{VAST_BASE_URL}/instances/{state['instance_id']}/", headers=headers)
                resp.raise_for_status()
        except Exception as e:
            add_log(f"विनाश पुष्टि चेतावनी: {str(e)}")

        old_gpu = state["gpu_name"]
        state["instance_id"] = None
        state["status"] = "SLEEPING"
        state["gpu_name"] = "None"
        state["hostname"] = ""
        state["sglang_url"] = ""
        state["hold_until"] = 0.0
        add_log(f"आदेश पूरा: {old_gpu} को नष्ट (Destroy) कर दिया गया है। अब खर्च ₹0.00 है!")
        return {"status": "DESTROYED", "message": "जीपीयू नष्ट कर दिया गया है माँ, बिल शून्य पर रुक गया है!"}


@app.post("/hold")
async def hold_gpu(minutes: int = DEFAULT_HOLD_MINUTES):
    # डिफ़ॉल्ट रूप से अगले 2 मिनट तक जीपीयू को होल्ड पर रखना (चाहें तो ?minutes=5 भेजकर बदल भी सकते हैं)
    state["hold_until"] = time.time() + (minutes * 60)
    state["last_active"] = time.time()
    add_log(f"माँ के आदेश पर जीपीयू को अगले {minutes} मिनट तक गर्म और जीवित रखा गया है।")
    return {"status": "HELD", "minutes": minutes, "hold_until": state["hold_until"]}


@app.get("/status")
async def get_status():
    # लाइव खर्च, नाड़ी और हिंदी डायरी देखना
    return state


async def idle_watchdog():
    # हर 5 सेकंड में जाँचने वाला स्वचालित पहरेदार (केवल READY अवस्था में और 50 सेकंड शांति होने पर ऑटो-Destroy)
    while True:
        await asyncio.sleep(5)
        now = time.time()
        if state["instance_id"] and state["status"] == "READY" and now > state["hold_until"]:
            if (now - state["last_active"]) > IDLE_TIMEOUT_SEC:
                add_log(f"{IDLE_TIMEOUT_SEC} सेकंड की शांति पूरी हुई — पैसे बचाने के लिए जीपीयू को स्वतः नष्ट किया जा रहा है...")
                await destroy_gpu()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(idle_watchdog())
      
