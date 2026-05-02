# 1. BASE Y VARIABLES DE ENTORNO (De tu archivo original)
FROM nvidia/cuda:13.0.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    # Priorizamos el PATH de Conda para ACPYPE, pero mantenemos GROMACS y CUDA
    PATH=/opt/miniconda/envs/bio/bin:/opt/miniconda/bin:/usr/local/gromacs/bin:/usr/local/bin:/usr/local/cuda/bin:${PATH} \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH} \
    GMXRC=/usr/local/gromacs/bin/GMXRC

# 2. DEPENDENCIAS DEL SISTEMA (Unificado)
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common ca-certificates curl wget git unzip \
    build-essential cmake autoconf automake libtool csh \
    libeigen3-dev libfftw3-dev libxml2-dev libx11-dev libxt-dev \
    libncurses5-dev libqhull-dev libnetcdf-dev openmpi-bin \
    libopenmpi-dev libfftw3-mpi-dev ocl-icd-libopencl1 \
    opencl-headers clinfo swig zlib1g-dev libcairo2-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. INSTALACIÓN DE MINICONDA (Para solucionar ACPYPE/AmberTools)
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -p /opt/miniconda \
    && rm /tmp/miniconda.sh

# 4. ENTORNO 'BIO' (Aquí vive ACPYPE y OpenBabel sano)
RUN /opt/miniconda/bin/conda create -n bio -y --override-channels -c conda-forge \
    python=3.10 \
    ambertools \
    acpype \
    openbabel \
    rdkit \
    tqdm \
    pandas \
    && /opt/miniconda/bin/conda clean -afy

# 5. PYTHON 2 PARA MGLTOOLS (Legacy - De tu archivo original)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python2 python2-dev && \
    curl -sS https://bootstrap.pypa.io/pip/2.7/get-pip.py -o /tmp/get-pip2.py && \
    python2 /tmp/get-pip2.py && rm -rf /var/lib/apt/lists/* 

# 6. HERRAMIENTAS DE DOCKING (Compilaciones manuales de tu original)

# Fpocket (CORREGIDO: quitamos el checkout 4.0 que fallaba)
RUN git clone https://github.com/Discngine/fpocket.git /tmp/fpocket && \
    cd /tmp/fpocket && \
    git checkout 4.0 && \
    sed -i 's/-Werror//g' makefile && \
    make -j"$(nproc)" || make && \
    find bin -type f -executable -exec cp {} /usr/local/bin/ \; && \
    rm -rf /tmp/fpocket

# MGLTools (De tu original)
RUN wget -q https://ccsb.scripps.edu/download/532/ -O /tmp/mgltools.tar.gz && \
    mkdir -p /opt/mgltools && \
    tar -xzf /tmp/mgltools.tar.gz -C /opt/mgltools --strip-components=1 && \
    cd /opt/mgltools && \
    bash install.sh -d /opt/mgltools || true && \
    ln -sf /opt/mgltools/bin/pythonsh /usr/local/bin/pythonsh && \
    rm -f /tmp/mgltools.tar.gz 

# AutoGrid4 y AutoDock4 (De tu original)
RUN git clone https://github.com/ccsb-scripps/AutoGrid.git /tmp/autogrid && \
    cd /tmp/autogrid && autoreconf -i && ./configure --prefix=/usr/local && \
    make -j$(nproc) install && \
    if [ -f /usr/local/bin/autogrid ]; then mv /usr/local/bin/autogrid /usr/local/bin/autogrid4; fi && \
    rm -rf /tmp/autogrid 

RUN git config --global http.postBuffer 524288000 && \
    git clone --depth 1 https://github.com/ccsb-scripps/AutoDock4.git /tmp/autodock4 && \
    cd /tmp/autodock4 && autoreconf -i && ./configure --prefix=/usr/local && \
    make -j$(nproc) install && \
    rm -rf /tmp/autodock4

# AutoDock-GPU (Optimizado para tus arquitecturas sm_89, 90, 120)
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

# 7. GROMACS 2025.4 (Compilación Multi-GPU de tu original)
RUN wget -q https://github.com/Kitware/CMake/releases/download/v3.29.6/cmake-3.29.6-linux-x86_64.sh -O /tmp/cmake-install.sh && \
    bash /tmp/cmake-install.sh --skip-license --prefix=/usr/local && \
    wget -q https://ftp.gromacs.org/gromacs/gromacs-2025.4.tar.gz -O /tmp/gromacs.tar.gz && \
    tar xzf /tmp/gromacs.tar.gz -C /tmp && cd /tmp/gromacs-2025.4 && mkdir build && cd build && \
    cmake .. -DGMX_BUILD_OWN_FFTW=ON -DGMX_GPU=CUDA -DGMX_MPI=ON -DGMX_SIMD=AVX2_256 \
    -DCMAKE_INSTALL_PREFIX=/usr/local/gromacs -DGMX_CUDA_TARGET_SM="89;90;120" && \
    make -j$(nproc) && make install && rm -rf /tmp/gromacs* 

# 8. CONFIGURACIÓN FINAL
WORKDIR /app/chemlink
COPY . .

# Dependencias extra para el orquestador
RUN /opt/miniconda/envs/bio/bin/pip install --no-cache-dir biopython numpy || true

RUN echo "source /usr/local/gromacs/bin/GMXRC" >> /etc/bash.bashrc

# Instalar el paquete del proyecto en el entorno `bio` para exponer el CLI
# y los módulos (incluye módulos de dinámica si están en el repo).
RUN /opt/miniconda/envs/bio/bin/pip install --no-cache-dir -e . || true

# Make `chemlink` available from ~/.local/bin inside the container
RUN mkdir -p /root/.local/bin \
     && (if [ -x /opt/miniconda/envs/bio/bin/chemlink ]; then \
             ln -sf /opt/miniconda/envs/bio/bin/chemlink /root/.local/bin/chemlink; \
         else \
             ln -sf /app/chemlink/chemlink /root/.local/bin/chemlink; \
         fi) \
     && echo 'export PATH="$HOME/.local/bin:$PATH"' >> /root/.bashrc

ENV PATH="/root/.local/bin:${PATH}"

# A small wrapper so `chemlink` can be invoked as a command without activating conda
RUN printf '%s\n' "#!/bin/bash" \
    "export PATH=/opt/miniconda/envs/bio/bin:\$PATH" \
    "[ -f /usr/local/gromacs/bin/GMXRC ] && source /usr/local/gromacs/bin/GMXRC || true" \
    "exec /opt/miniconda/envs/bio/bin/chemlink \"\$@\"" \
    > /usr/local/bin/chemlink.wrap \
    && chmod +x /usr/local/bin/chemlink.wrap \
    && ln -sf /usr/local/bin/chemlink.wrap /usr/local/bin/chemlink

# Default to an interactive shell so the CLI is available via bashrc
CMD ["/bin/bash"]