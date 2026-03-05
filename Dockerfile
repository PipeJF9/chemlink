# Imagen base con CUDA 12 y Ubuntu 22.04
FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

# Variables de entorno
ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/usr/local/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Actualizar sistema e instalar dependencias básicas
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    git \
    cmake \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    libeigen3-dev \
    libfftw3-dev \
    libxml2-dev \
    libx11-dev \
    libxt-dev \
    libncurses5-dev \
    libqhull-dev \
    libnetcdf-dev \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Instalar Python 2.7 solamente para ejecutar un comando específico
RUN apt-get update && apt-get install -y \
    python2.7 
# Solo si necesitas un comando de Python 2.7, puedes usar "/usr/bin/python2.7"
# Ejemplo: RUN /usr/bin/python2.7 -c "print('Hello from Python 2.7')"

# Instalar pip para Python 2 (pip2) usando el instalador oficial para pip 2.7
# Se usa la copia específica para Python 2.7 alojada por PyPA
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sS https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip.py \
    && python2.7 /tmp/get-pip.py \
    && ln -s /usr/local/bin/pip /usr/local/bin/pip2 || true \
    && rm -f /tmp/get-pip.py

# Open Babel 3.1.1
RUN apt-get update && apt-get install -y --no-install-recommends \
    swig zlib1g-dev libcairo2-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

ENV OB_VERSION=openbabel-3-1-1

RUN git clone https://github.com/openbabel/openbabel.git /tmp/openbabel \
    && cd /tmp/openbabel \
    && git checkout tags/${OB_VERSION} -b build-${OB_VERSION} \
    && mkdir build && cd build \
    && cmake .. \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local \
        -DRUN_SWIG=ON \
        -DENABLE_PYTHON=ON \
        -DPYTHON_EXECUTABLE=/usr/bin/python3.12 \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig

# Fpocket 4.0
RUN git clone https://github.com/Discngine/fpocket.git /tmp/fpocket \
    && cd /tmp/fpocket \
    && git checkout 4.0 \
    && sed -i 's/-Werror//g' makefile \
    && make -j$(nproc) || (echo "Fpocket compilation failed, trying with single thread" && make) \
    && find bin -type f -executable -exec cp {} /usr/local/bin/ \; \
    && rm -rf /tmp/fpocket

# MGLTools 1.5.6 con instalación
RUN wget -q https://ccsb.scripps.edu/download/532/ -O /tmp/mgltools.tar.gz \
    && mkdir /opt/mgltools && tar -xzf /tmp/mgltools.tar.gz -C /opt/mgltools --strip-components=1 \
    && cd /opt/mgltools && bash install.sh -d /opt/mgltools || true \
    && ln -s /opt/mgltools/bin/pmv /usr/local/bin/pmv \
    && ln -s /opt/mgltools/bin/adt /usr/local/bin/adt \
    && ln -s /opt/mgltools/bin/vision /usr/local/bin/vision \
    && ln -s /opt/mgltools/bin/pythonsh /usr/local/bin/pythonsh \
    && rm /tmp/mgltools.tar.gz


# AutoDock-GPU (CUDA 12, 128 work items)
RUN git clone https://github.com/ccsb-scripps/AutoDock-GPU.git /tmp/autodock-gpu \
    && cd /tmp/autodock-gpu \
    && make DEVICE=CUDA NUMWI=128 \
       CUDA_PATH=/usr/local/cuda \
       CUDA_INC_PATH=/usr/local/cuda/include \
       CUDA_LIB_PATH=/usr/local/cuda/lib64 \
       GPU_INCLUDE_PATH=/usr/local/cuda/include \
       GPU_LIBRARY_PATH=/usr/local/cuda/lib64 \
       CPU_INCLUDE_PATH=/usr/include \
       CPU_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu \
       -j$(nproc) \
    && cp bin/autodock_gpu_128wi /usr/local/bin/autodock-gpu \
    && rm -rf /tmp/autodock-gpu

# Dependencias para MPI
RUN apt-get update && apt-get install -y \
    openmpi-bin \
    libopenmpi-dev \
    libfftw3-dev \
    libfftw3-mpi-dev \
    && rm -rf /var/lib/apt/lists/*

# GROMACS 2024.4 con soporte GPU CUDA y MPI
RUN wget -q https://ftp.gromacs.org/gromacs/gromacs-2024.4.tar.gz -O /tmp/gromacs.tar.gz \
    && cd /tmp && tar xzf gromacs.tar.gz \
    && cd gromacs-2024.4 && mkdir build && cd build \
    && cmake .. -DGMX_BUILD_OWN_FFTW=ON -DREGRESSIONTEST_DOWNLOAD=ON \
       -DGMX_GPU=CUDA -DGMX_MPI=ON -DGMX_SIMD=AVX2_256 \
       -DCMAKE_INSTALL_PREFIX=/usr/local/gromacs \
    && make -j$(nproc) && make install \
    && rm -rf /tmp/gromacs*


# Export para usar GROMACS directamente
ENV PATH=/usr/local/gromacs/bin:$PATH
ENV GMXRC=/usr/local/gromacs/bin/GMXRC
RUN echo "source /usr/local/gromacs/bin/GMXRC" >> /etc/bash.bashrc

# Configuración de Python
RUN python3.12 -m ensurepip --upgrade \
    && python3.12 -m pip install --upgrade pip setuptools wheel \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Crear directorio de trabajo para ChemFusion
WORKDIR /app/ChemFusion2.0

# Entrypoint
CMD ["/bin/bash"]
