# ── Stage 1: clone yolov5 source ─────────────────────────────────────────────
# Done in a separate stage so the git install does NOT appear in the Lambda
# image's layer chain — all large pip layers keep their existing ECR hashes.
FROM alpine/git AS yolov5_clone
# v7.0 is the last tag before hubconf.py was refactored to depend on the ultralytics pip package.
RUN git clone --depth 1 --branch v7.0 https://github.com/ultralytics/yolov5.git /opt/yolov5_src

# ── Stage 2: Lambda runtime image ────────────────────────────────────────────
FROM public.ecr.aws/lambda/python:3.11

WORKDIR ${LAMBDA_TASK_ROOT}

# gcc/gcc-c++ for source-builds.
# UNCHANGED from previous builds — all subsequent pip layers keep their ECR hashes.
RUN yum install -y gcc gcc-c++ --setopt=install_weak_deps=False

# Copy yolov5 source from stage 1 — small layer (~20 MB), does NOT affect pip layer hashes.
COPY --from=yolov5_clone /opt/yolov5_src /opt/yolov5_src

# Install base API dependencies (build context = repo root)
COPY src/requirements-lambda.txt .

# Pin numpy 1.x BEFORE sklearn/torch — evita build from source no AL2 (GCC 7.3)
RUN pip install "numpy>=1.23,<2.0" --no-cache-dir

RUN pip install -r requirements-lambda.txt --no-cache-dir

# ML (AgriRiskModel) — scipy pin evita pull de scipy 1.17+ (exige numpy 2.x)
RUN pip install "scipy>=1.4.1,<1.14" --no-cache-dir
RUN pip install scikit-learn==1.5.2 joblib==1.4.2 --no-cache-dir

# CPU-only torch — avoids the ~2 GB CUDA build.
RUN pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu --no-cache-dir

# Runtime deps for yolov5 SOURCE inference (torch.hub.load).
# scipy / ultralytics / gitpython / huggingface-hub / thop are NOT needed — those
# were only required by the yolov5 PIP package and its broken dep chain.
# pandas pinned <2.0: pandas 2.x wheels are compiled for numpy 2.x ABI (96-byte dtype)
# which is incompatible with our numpy 1.x (88-byte dtype).
RUN pip install \
    "PyYAML>=5.3.1" \
    "tqdm>=4.41.0" \
    "opencv-python-headless==4.10.0.84" \
    "pandas>=1.1.4,<2.0" \
    "matplotlib>=3.3,<3.10" \
    "seaborn>=0.11.0" \
    "psutil" \
    "ipython" \
    "scipy>=1.4.1,<1.14" \
    "gitpython>=3.1.30" \
    --no-cache-dir

# Set matplotlib config dir to writable /tmp so the import doesn't warn.
ENV MPLCONFIGDIR=/tmp/matplotlib

# Runtime native libs required by opencv-python-headless on Amazon Linux 2.
# Placed after all pip installs — tiny layer, does not invalidate pip caches.
RUN yum install -y mesa-libGL libxcb git --setopt=install_weak_deps=False && \
    git config --system --add safe.directory /opt/yolov5_src

# Copy application source (+ BFF dashboard handlers used by dashboard_bff router)
COPY src/app/ app/
COPY src/dashboard/ dashboard/
COPY models/agri_risk_model.pkl models/agri_risk_scaler.pkl models/agri_risk_meta.pkl models/agri_risk_thresholds.json models/

# Lambda entry point: app.main.handler (Mangum wrapping FastAPI + S3 trigger router)
CMD ["app.main.handler"]
