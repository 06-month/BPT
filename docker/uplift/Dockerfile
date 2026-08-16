FROM python:3.8-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /workspace

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install \
        tensorflow==2.4.3 \
        tensorflow-addons==0.13.0 \
        protobuf==3.20.1 \
        einops==0.3.2 \
        numpy \
        scipy

CMD ["python", "scripts/run_uplift_inference_from_npz.py"]
