# ChemLink: Framework CLI Integral para Modelado Molecular Distribuido en Cluster HPC

![ChemLink Banner](https://img.shields.io/badge/ChemLink-v1.0.0-black?style=for-the-badge&logo=gnu-bash&logoColor=white)
![Status](https://img.shields.io/badge/Estado-En_Desarrollo-orange?style=for-the-badge)
![License](https://img.shields.io/badge/Licencia-MIT-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Plataforma-Linux%20HPC-lightgrey?style=for-the-badge)

**ChemLink** es una solución de ingeniería de software diseñada para automatizar, orquestar y optimizar flujos de trabajo de química computacional (específicamente *Docking Molecular* y *Dinámica Molecular*) en entornos de Computación de Alto Desempeño (HPC).

Este proyecto representa el **Trabajo de Final de Grado** para el programa de **Ingeniería de Sistemas (2026-10)**, desarrollado bajo la línea de investigación en **Computación de Alto Desempeño, Arquitectura de Software y Sistemas Distribuidos**.

---

## 📑 Tabla de Contenidos

1.  [Introducción](#1-introducción)
2.  [Planteamiento del Problema](#2-planteamiento-del-problema)
3.  [Objetivos del Proyecto](#3-objetivos-del-proyecto)
4.  [Alcance y Funcionalidades](#4-alcance-y-funcionalidades)
5.  [Arquitectura del Sistema](#5-arquitectura-del-sistema)
6.  [Restricciones y Supuestos de Diseño](#6-restricciones-y-supuestos-de-diseño)
7.  [Stack Tecnológico](#7-stack-tecnológico)
8.  [Instalación y Uso](#8-instalación-y-uso)
9.  [Créditos](#9-créditos)

---

## 1. Introducción

La investigación en química computacional depende intrínsecamente de la capacidad de procesar modelos moleculares complejos mediante simulaciones masivas. En el contexto actual, el descubrimiento de fármacos *in silico* requiere una orquestación precisa de recursos de hardware.

**ChemLink** nace como respuesta a la necesidad operativa del laboratorio **Chemlab**, proponiendo un *framework* de interfaz de línea de comandos (CLI) modular. Su propósito es abstraer la complejidad del manejo de clusters HPC basados en **Ubuntu 24.04 LTS**, permitiendo a los investigadores ejecutar pipelines de *docking* molecular de manera distribuida, validada y reproducible.

Al integrar la detección automática de sitios de unión, la paralelización dinámica de tareas y la generación estructurada de reportes, ChemLink transforma un proceso manual y propenso a errores en una línea de producción científica robusta y escalable.

---

## 2. Planteamiento del Problema

El laboratorio Chemlab dispone de una infraestructura HPC moderna con nodos equipados con aceleración por GPU. No obstante, el flujo de trabajo actual presenta desafíos críticos que limitan la producción científica:

*   **Fragmentación del Flujo de Trabajo:** Los investigadores ejecutan manualmente múltiples herramientas dispares (preparación de ligandos, configuración de *grid boxes*, ejecución de `autodock-gpu`), rompiendo la continuidad del experimento y aumentando el error humano.
*   **Subutilización de Recursos:** La asignación estática y manual de trabajos a las GPUs provoca tiempos de inactividad en los nodos o cuellos de botella, desperdiciando la potencia de cálculo instalada.
*   **Falta de Trazabilidad y Reproducibilidad:** La gestión manual de archivos de entrada y salida genera una dispersión de datos que complica la auditoría. No existe garantía de que un experimento pueda ser replicado con exactitud bajo las mismas condiciones.
*   **Escalabilidad Limitada:** El enfoque actual hace inviable la realización de campañas de Cribado Virtual de Alto Rendimiento (*High-Throughput Virtual Screening - HTVS*) de manera eficiente.

---

## 3. Objetivos del Proyecto

### Objetivo General
Diseñar e implementar **ChemLink**, una plataforma CLI científica, modular y orientada a HPC que automatice y optimice la ejecución de experimentos de *docking* y dinámica molecular en un cluster distribuido, garantizando la gestión adaptativa de recursos (CPU/GPU), la paralelización eficiente y la trazabilidad experimental.

### Objetivos Específicos
1.  **Arquitectura Modular:** Diseñar una arquitectura de software en capas (*CLI, Core, Adapters, Utils*) que desacople la lógica de negocio de las herramientas científicas subyacentes.
2.  **Automatización del Pipeline:** Implementar la automatización *end-to-end*: detección automática de sitios de unión, generación dinámica de cajas, preparación de inputs y ejecución.
3.  **Ejecución Híbrida:** Desarrollar un sistema que soporte tanto el multiprocesamiento local como la generación automática de scripts de trabajo para gestores de colas (SLURM) en el cluster.
4.  **Gestión de Recursos y Tolerancia a Fallos:** Integrar validaciones de hardware (disponibilidad de GPU/Memoria) y mecanismos de recuperación ante *timeouts* o errores de ejecución.
5.  **Análisis Estructurado:** Implementar módulos de post-procesamiento para el cálculo de afinidad, RMSD y generación de reportes (CSV, JSON, Markdown).
6.  **Validación de Desempeño:** Evaluar el impacto de la solución mediante métricas de *Speedup*, Eficiencia Computacional y Tasa de Éxito frente al método manual.

---

## 4. Alcance y Funcionalidades

El proyecto abarca el ciclo de vida completo de ingeniería de software para ChemLink, desde el diseño arquitectónico hasta la validación en entorno real.

### Incluido (In Scope)
*   **Interfaz CLI Robusta:** Comandos intuitivos (`chemlink run`, `chemlink analyze`) optimizados para entornos *headless*.
*   **Wrappers de Docking:** Integración nativa con **AutoDock-GPU** y **Vina**.
*   **Preparación de Ligandos:** Conversión automática y validación de formatos moleculares (PDB $\leftrightarrow$ PDBQT).
*   **Distribución de Carga:** Balanceo dinámico de trabajos entre las GPUs disponibles.
*   **Sistema de Reportes:** Generación automática de tablas comparativas y rankings de mejores candidatos.
*   **Logging Estructurado:** Registro detallado de operaciones para auditoría y depuración.

### Excluido (Out of Scope)
*   Desarrollo de nuevos algoritmos de física cuántica o mecánica molecular (se orquestan los existentes).
*   Implementación de Interfaces Gráficas de Usuario (GUI) o dashboards web.
*   Mantenimiento físico o actualización de hardware del cluster.

---
## 5. Arquitectura del Sistema
### Descripción General

ChemLink se basa en una **Arquitectura Modular Orientada a Componentes y Capas de Orquestación**. A diferencia de los sistemas monolíticos, separa las responsabilidades en módulos independientes que se comunican de forma jerárquica para maximizar la escalabilidad.

- **Tipo de Arquitectura:** CLI (Command Line Interface) con Orquestación de Workflows.
- **Ámbito de Aplicación:** Diseñado para entornos locales y clústeres de alto rendimiento (HPC), actuando como un middleware entre el investigador y las herramientas bioinformáticas.
- **Enfoque de la Solución:** Se centra en la **Separación de Preocupaciones (SoC)** y la **Abstracción de Infraestructura**, permitiendo que la lógica química sea independiente de la configuración del servidor.
- **Relación con la Alternativa Seleccionada:** El sistema reemplaza los flujos manuales propensos a errores por una automatización basada en Ansible y gestores de tareas como Slurm, optimizando la tasa de éxito ($S_{success}$).

Además, ChemLink se plantea como un **orquestador de infraestructura distribuida ligera**, orientado a clústeres HPC de pequeña escala, donde las decisiones arquitectónicas se validan mediante experimentos A/B.

---

### Componentes del Sistema e Interacción

El sistema se organiza en cinco bloques funcionales que interactúan de forma descendente:

#### Capas Funcionales

1. **Capa de Interfaz (CLI & Workflows):** Punto de entrada del usuario. Traduce comandos de alto nivel en flujos de trabajo coordinados.  
2. **Capa de Negocio (Pipelines):** Orquesta los pasos lógicos del docking (preparación → ejecución → análisis).  
3. **Capa de Adaptación (Adapters):** Wrappers que estandarizan la comunicación con herramientas externas como `AutoDock-GPU` y `fpocket`.  
4. **Servicios de Soporte (Storage & Utils):** Gestión de persistencia en NAS, procesamiento químico y validación de datos.  
5. **Capa de Infraestructura (HPC):** Abstracción de bajo nivel para comunicación SSH, configuración de red y gestión de nodos.  

---

### Marco de Validación y Métricas

La arquitectura no solo es funcional, sino que su diseño ha sido validado mediante un **marco experimental cuantitativo** comparando dos configuraciones (A vs B).

#### Métricas de Evaluación

##### Rendimiento

| Métrica   | Definición                                                      | Unidad   |
|----------|------------------------------------------------------------------|----------|
| $T_{setup}$ | Tiempo total hasta conectividad funcional                     | segundos |
| $T_{exec}$  | Tiempo promedio de ejecución de una operación                 | segundos |

##### Fiabilidad

| Métrica       | Definición                     | Fórmula                                      |
|--------------|--------------------------------|----------------------------------------------|
| $E_{rate}$    | Tasa de error                  | $(n_{errores} / n_{ejecuciones}) \times 100$ |
| $S_{success}$ | Tasa de éxito del setup        | $(n_{setups\_exitosos} / n_{total}) \times 100$ |

##### Usabilidad

| Métrica     | Definición                                      | Escala         |
|------------|--------------------------------------------------|----------------|
| $N_{steps}$ | Número de comandos para completar el setup       | entero         |
| $C_{load}$  | Carga cognitiva percibida                        | Likert (1–5)   |
| $T_{learn}$ | Tiempo de aprendizaje del sistema                | minutos        |

##### Complejidad del Sistema

| Métrica         | Definición                                  |
|-----------------|----------------------------------------------|
| $LOC$           | Líneas de código por módulo                  |
| $M_{modularity}$| Número de módulos independientes             |
| $D_{coupling}$  | Número de dependencias entre módulos         |

##### Robustez

| Métrica            | Definición                          | Fórmula                                      |
|--------------------|--------------------------------------|----------------------------------------------|
| $R_{recovery}$     | Capacidad de recuperación           | errores recuperados / errores totales        |
| $F_{repeatability}$| Reproducibilidad del sistema        | ejecuciones consistentes / total             |

---

#### Decisiones Arquitectónicas Clave

Las siguientes decisiones fueron evaluadas experimentalmente:

##### Orquestación del sistema

| Configuración | Descripción                              |
|--------------|------------------------------------------|
| A            | Ejecución directa de comandos            |
| B            | Automatización mediante Ansible          |

Métricas: $T_{setup}$, $E_{rate}$, $LOC$, $R_{recovery}$

##### Configuración de red

| Configuración | Descripción                     |
|--------------|---------------------------------|
| A            | NetworkManager (nmcli)          |
| B            | Netplan                         |

Métricas: $E_{rate}$, $T_{setup}$, $F_{repeatability}$

##### Descubrimiento de nodos

| Configuración | Descripción                          |
|--------------|--------------------------------------|
| A            | Entrada manual de IP                 |
| B            | Descubrimiento automático con Nmap   |

Métricas: $N_{steps}$, $T_{setup}$, Precisión, Recall

##### Configuración SSH

| Configuración | Descripción                      |
|--------------|----------------------------------|
| A            | ssh-copy-id                     |
| B            | Configuración manual de claves  |

Métricas: $E_{rate}$, $T_{exec}$, $R_{recovery}$

##### Nivel de abstracción del CLI

| Configuración | Descripción                          |
|--------------|--------------------------------------|
| A            | Comandos de bajo nivel               |
| B            | Comandos de alto nivel (`cluster init`) |

Métricas: $N_{steps}$, $C_{load}$, $T_{learn}$

##### Gestión del estado del clúster

| Configuración | Descripción                  |
|--------------|------------------------------|
| A            | Estado centralizado          |
| B            | Estado distribuido           |

Métricas: $T_{exec}$, $F_{repeatability}$, $D_{coupling}$

---

### Metodología Experimental

#### Configuración Experimental

| Parámetro         | Valor        |
|------------------|-------------|
| Número de nodos  | 2–3         |
| Red              | 10.0.0.0/24 |
| Sistema operativo| Linux       |
| Repeticiones     | ≥ 30        |

#### Procedimiento

| Paso | Descripción                 |
|------|-----------------------------|
| 1    | Reset del entorno           |
| 2    | Ejecución del setup         |
| 3    | Registro de métricas        |
| 4    | Repetición del experimento  |

#### Estructura de Registro

| Campo      | Descripción              |
|------------|--------------------------|
| timestamp  | Marca temporal           |
| mode       | Configuración (A o B)    |
| $T_{setup}$| Tiempo total             |
| $E_{rate}$ | Tasa de error            |
| steps      | Número de pasos          |

---

### Análisis de Resultados

| Método     | Aplicación                         |
|------------|-----------------------------------|
| t-test     | Comparación de medias             |
| ANOVA      | Comparación entre múltiples grupos|
| Correlación| Relación entre métricas           |

---

### Validación de Comportamiento (Flujo de Datos)

La integridad del sistema se verifica a través de la interacción entre módulos. Por ejemplo, en el proceso de **Preparación de Ligandos**:

1. El **Pipeline** solicita archivos al módulo **Storage**.  
2. **Utils** realiza el procesamiento químico aislado (limpieza de moléculas).  
3. El **Adapter** de AutoDockTools genera los archivos `.pdbqt`.  
4. El **HPC Manager** distribuye los archivos a los nodos del clúster si es necesario.  
5. El sistema de **Logging** registra la trazabilidad completa, asegurando la reproducibilidad.  

## 6. Diagrama de Arquitectura
![Diagrama de Arquitectura](/Diagramas/Architecture.png)
## 7. Diagrama de Componentes
![Diagrama de Componentes](/Diagramas/Components.png)
## 8. Diagrama de Secuencia
![Diagrama de Secuencia](/Diagramas/Diagrama%20de%20secuencia.png)
