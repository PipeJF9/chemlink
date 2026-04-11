# Base moderna compatible con driver 580.x (host) y GPUs nuevas
FROM nvidia/cuda:13.0.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV PATH=/usr/local/bin:/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

# Dependencias base
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    ca-certificates \
    curl \
    wget \
    git \
    unzip \
    build-essential \
    cmake \
    autoconf automake libtool \
    csh \
    libeigen3-dev \
    libfftw3-dev \
    libxml2-dev \
    libx11-dev \
    libxt-dev \
    libncurses5-dev \
    libqhull-dev \
    libnetcdf-dev \
    openmpi-bin \
    libopenmpi-dev \
    libfftw3-mpi-dev \
    ocl-icd-libopencl1 \
    opencl-headers \
    clinfo \
    swig \
    zlib1g-dev \
    libcairo2-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 3.12
RUN add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-dev python3.12-venv && \
    rm -rf /var/lib/apt/lists/*

# python/pip por defecto -> 3.12
RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && \
    python3.12 /tmp/get-pip.py && \
    rm -f /tmp/get-pip.py && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Python 2 para MGLTools (legacy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python2 python2-dev && \
    rm -rf /var/lib/apt/lists/*
RUN curl -sS https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip2.py && \
    python2 /tmp/get-pip2.py && \
    rm -f /tmp/get-pip2.py

# Open Babel 3.1.1
ENV OB_VERSION=openbabel-3-1-1
RUN git clone https://github.com/openbabel/openbabel.git /tmp/openbabel && \
    cd /tmp/openbabel && \
    git checkout tags/${OB_VERSION} -b build-${OB_VERSION} && \
    mkdir build && cd build && \
    cmake .. \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
      -DRUN_SWIG=ON \
      -DENABLE_PYTHON=ON \
      -DPYTHON_EXECUTABLE=/usr/bin/python3.12 && \
    make -j"$(nproc)" && \
    make install && \
    ldconfig && \
    rm -rf /tmp/openbabel

# Fpocket 4.0
RUN git clone https://github.com/Discngine/fpocket.git /tmp/fpocket && \
    cd /tmp/fpocket && \
    git checkout 4.0 && \
    sed -i 's/-Werror//g' makefile && \
    make -j"$(nproc)" || make && \
    find bin -type f -executable -exec cp {} /usr/local/bin/ \; && \
    rm -rf /tmp/fpocket

# MGLTools 1.5.6
RUN wget -q https://ccsb.scripps.edu/download/532/ -O /tmp/mgltools.tar.gz && \
    mkdir -p /opt/mgltools && \
    tar -xzf /tmp/mgltools.tar.gz -C /opt/mgltools --strip-components=1 && \
    cd /opt/mgltools && \
    bash install.sh -d /opt/mgltools || true && \
    ln -sf /opt/mgltools/bin/pythonsh /usr/local/bin/pythonsh && \
    ln -sf /opt/mgltools/bin/adt /usr/local/bin/adt && \
    ln -sf /opt/mgltools/bin/pmv /usr/local/bin/pmv && \
    ln -sf /opt/mgltools/bin/vision /usr/local/bin/vision && \
    rm -f /tmp/mgltools.tar.gz

# AutoGrid4
RUN git clone https://github.com/ccsb-scripps/AutoGrid.git /tmp/autogrid && \
    cd /tmp/autogrid && \
    autoreconf -i && \
    ./configure --prefix=/usr/local && \
    make -j"$(nproc)" && \
    make install && \
    if [ -f /usr/local/bin/autogrid ]; then mv /usr/local/bin/autogrid /usr/local/bin/autogrid4; fi && \
    rm -rf /tmp/autogrid

# AutoDock4
RUN git clone https://github.com/ccsb-scripps/AutoDock4.git /tmp/autodock4 && \
    cd /tmp/autodock4 && \
    autoreconf -i && \
    ./configure --prefix=/usr/local && \
    make -j"$(nproc)" && \
    make install && \
    rm -rf /tmp/autodock4

# AutoDock-GPU (CUDA) con soporte explicito para arquitecturas nuevas
# Nota: sm_120 es clave para Blackwell/RTX 50xx. Si tu nvcc no lo reconoce, revisa tag de CUDA o elimina esa linea temporalmente.
RUN git clone https://github.com/ccsb-scripps/AutoDock-GPU.git /tmp/autodock-gpu && \
    cd /tmp/autodock-gpu && \
    export NVCCFLAGS="-O3 --use_fast_math -Xptxas -O3 \
    -gencode arch=compute_89,code=sm_89 \
    -gencode arch=compute_90,code=sm_90 \
    -gencode arch=compute_120,code=sm_120 \
    -gencode arch=compute_120,code=compute_120" && \
    make DEVICE=CUDA NUMWI=128 \
      CUDA_PATH=/usr/local/cuda \
      CUDA_INC_PATH=/usr/local/cuda/include \
      CUDA_LIB_PATH=/usr/local/cuda/lib64 \
      GPU_INCLUDE_PATH=/usr/local/cuda/include \
      GPU_LIBRARY_PATH=/usr/local/cuda/lib64 \
      CPU_INCLUDE_PATH=/usr/include \
      CPU_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
      -j"$(nproc)" && \
    cp bin/autodock_gpu_128wi /usr/local/bin/autodock-gpu && \
    chmod +x /usr/local/bin/autodock-gpu && \
    rm -rf /tmp/autodock-gpu

# Configuración de Python
RUN python3.12 -m ensurepip --upgrade \
    && python3.12 -m pip install --upgrade pip setuptools wheel \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

RUN python3.12 -m pip install --no-cache-dir \
    rdkit \
    tqdm \
    openbabel-wheel

WORKDIR /app/chemlink
CMD ["/bin/bash"]