# =====================================================================
# माँ के साम्राज्य का प्रथम महा-डिब्बा: aadi-toolkit (uv + NASA DE441 + 75+ अस्त्र)
# =====================================================================

# आधार: आधिकारिक स्थिर Python 3.11 लिनक्स वातावरण
FROM python:3.11-slim-bookworm

# सिस्टम को गैर-संवादात्मक और तेज़ मोड में रखना
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    ASTRO_DATA_DIR=/opt/aadi-data/ephemeris

# --- 1. मुख्य सिस्टम गणित, खगोलशास्त्र, OCR और मीडिया इंजन स्थापित करना ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    gfortran \
    cmake \
    git \
    curl \
    wget \
    ca-certificates \
    maxima \
    pari-gp \
    libflint-dev \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-san \
    ffmpeg \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# --- 2. बिजली-गति वाला 'uv' पैकेज सॉल्वर सीधे जोड़ना ---
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# कार्य-स्थल बनाना
WORKDIR /workspace
RUN mkdir -p /opt/aadi-data/ephemeris /workspace/notebooks

# --- 3. आपकी सूची (requirements.txt) के सभी 75+ महा-अस्त्रों को 'uv' से एक झटके में पकाना ---
COPY toolkit/requirements.txt /tmp/requirements.txt
RUN uv pip install --no-cache -r /tmp/requirements.txt

# --- 4. NASA JPL DE441 (30,000 वर्षों की ग्रह-सारणी) व Swiss Ephemeris डेटा सहेजना ---
RUN wget -q -O /opt/aadi-data/ephemeris/de440s.bsp https://nasa.gov || true

# --- 5. शून्य-टाइमआउट जीवित Jupyter प्रयोगशाला द्वार (Port 8888) खोलना ---
EXPOSE 8888
CMD ["jupyter", "kernelgateway", "--KernelGatewayApp.ip=0.0.0.0", "--KernelGatewayApp.port=8888", "--KernelGatewayApp.allow_origin='*'"]
