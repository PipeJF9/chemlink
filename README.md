# ChemLink: Plataforma de Orquestación para Docking Molecular en Entornos HPC

## Informe Técnico I - Propuesta de Proyecto de Grado

---

## Autores

- **Juan Felipe Santos Rodríguez**
- **Samuel Matiz García**
- **Camilo Andrés Navarro Navarro**

**Universidad del Norte**  
Barranquilla, Colombia  
2026

**Docente:** Augusto Salazar  
**Co-asesor:** Daniel Romero

---

## Información del Documento

- **Título**: ChemLink: Plataforma de Orquestación para Docking Molecular en Entornos HPC
- **Tipo**: Informe Técnico Número I - Propuesta del Proyecto
- **Modalidad**: Trabajo de Final de Grado
- **Programa Académico**: Ingeniería de Sistemas  
- **Institución**: Universidad del Norte
- **Ubicación**: Barranquilla, Colombia
- **Período**: 2026-10
- **Fecha de Presentación**: Marzo 2026
- **Laboratorio**: Chemlab - Facultad de Ciencias

---

## Tabla de Contenidos

1. [Introducción](#-introducción)
2. [Planteamiento del Problema](#-planteamiento-del-problema)
3. [Justificación](#-justificación)
4. [Restricciones y Supuestos de Diseño](#-restricciones-y-supuestos-de-diseño)
5. [Objetivos](#-objetivos)
6. [Alcance](#-alcance)
7. [Estado del Arte y Soluciones Relacionadas](#-estado-del-arte-y-soluciones-relacionadas)
8. [Diagramas de Arquitectura (Modelo C4)](#-diagramas-de-arquitectura-modelo-c4)
9. [Requerimientos Preliminares](#-requerimientos-preliminares)
10. [Criterios de Aceptación Inicial](#-criterios-de-aceptación-inicial)
11. [Plan de Trabajo](#-plan-de-trabajo)
12. [Riesgos del Proyecto](#-riesgos-del-proyecto)
13. [Referencias Bibliográficas](#-referencias-bibliográficas)
14. [Anexos](#-anexos)

---

## Introducción

En las últimas décadas, la bioinformática y la química computacional se han consolidado como pilares fundamentales en el descubrimiento racional de fármacos y en la comprensión de mecanismos moleculares complejos. Estas disciplinas permiten modelar, simular y analizar interacciones biológicas a nivel atómico mediante herramientas computacionales avanzadas, reduciendo significativamente los costos y tiempos asociados a la experimentación exclusivamente experimental.

### Técnicas Relevantes en Química Computacional

Entre las técnicas más relevantes se encuentran:

- **Docking Molecular**: Permite predecir la orientación y afinidad de unión entre una proteína y un ligando.
- **Dinámica Molecular**: Posibilita evaluar la estabilidad estructural y el comportamiento temporal de complejos biomoleculares.

La ejecución eficiente de estas técnicas requiere altos recursos computacionales, lo que ha impulsado el uso de entornos de **Computación de Alto Rendimiento (HPC)**, capaces de distribuir cargas de trabajo y aprovechar aceleración mediante GPUs.

### Tendencias Actuales en Investigación Computacional

En este contexto, las tendencias actuales en investigación computacional apuntan hacia:

1. **Automatización de Pipelines Científicos**: Integración fluida de múltiples herramientas en flujos de trabajo reproducibles.
2. **Integración con Gestores de Colas**: Uso de sistemas como SLURM para optimizar la asignación de recursos computacionales.
3. **Arquitecturas Modulares**: Diseño de sistemas desacoplados que faciliten el mantenimiento y la extensibilidad.
4. **Almacenamiento Centralizado**: Implementación de sistemas que permitan manejar grandes volúmenes de datos de manera organizada.
5. **Reproducibilidad Científica**: Criterio esencial dentro de los estudios computacionales modernos.

### Problemática Actual

No obstante, en muchos entornos académicos y de investigación, la ejecución de experimentos de docking molecular aún depende de procesos manuales y de la integración *ad hoc* de diversas herramientas. Esta situación genera:

- Dificultades en la gestión de experimentos
- Limitaciones en la escalabilidad de los estudios
- Desafíos para mantener una trazabilidad clara de los resultados obtenidos

---

## Planteamiento del Problema

En los entornos académicos donde se desarrollan estudios de docking molecular, la ejecución de experimentos computacionales suele depender de una integración manual y fragmentada de múltiples herramientas. Aunque existen soluciones robustas para el cálculo molecular, como **AutoDock-GPU** [1], y gestores de colas ampliamente adoptados como **SLURM** [2], su articulación operativa dentro de un flujo experimental coherente no se encuentra formalizada ni automatizada.

### Naturaleza del Problema

**El problema no radica en la inexistencia de herramientas científicas eficientes**, sino en **la ausencia de un sistema integrador** que permita orquestar, monitorear y estructurar su ejecución bajo principios de automatización, control y reproducibilidad académica.

### Situación Actual

Actualmente, los investigadores deben:

- Preparar manualmente *scripts* de envío al clúster
- Configurar parámetros de ejecución
- Administrar rutas de almacenamiento distribuidas
- Monitorear el estado de los trabajos mediante comandos de bajo nivel

La integración entre herramientas de cálculo, gestión de recursos HPC y almacenamiento compartido **no responde a una arquitectura estructurada**, sino a prácticas individuales que varían entre usuarios.

### Efectos Negativos de la Fragmentación Técnica

Esta fragmentación técnica genera múltiples efectos negativos:

#### Retrasos Operativos
- Retrasos en los ciclos de experimentación debido a errores de configuración y reenvío de tareas

#### Pérdida de Reproducibilidad
- Pérdida de reproducibilidad al no existir trazabilidad formal de parámetros, versiones y resultados

#### Sobrecarga Técnica
- Sobrecarga técnica en los investigadores, quienes deben dedicar tiempo significativo a tareas operativas en lugar de análisis científico

#### Dificultad de Escalabilidad
- Dificultad para escalar experimentos cuando se requiere ejecutar múltiples simulaciones en paralelo dentro del clúster

### Consecuencias

Como consecuencia, el proceso de investigación computacional se vuelve:

- **Menos eficiente**
- **Más propenso a inconsistencias**
- **Dependiente del conocimiento técnico individual**

Esto limita el aprovechamiento óptimo de la infraestructura HPC disponible.

---

## Justificación

El desarrollo de herramientas que faciliten la gestión de experimentos computacionales se ha vuelto fundamental para aprovechar adecuadamente las infraestructuras de computación de alto rendimiento disponibles en entornos académicos.

### Necesidad Identificada

En el caso del docking molecular, la ausencia de sistemas que integren de manera estructurada:

- La ejecución de tareas
- La gestión de recursos
- El almacenamiento de resultados

...dificulta la realización de estudios eficientes y reproducibles.

### Solución Propuesta

Ante esta situación, resulta pertinente diseñar una **plataforma que permita automatizar y estructurar los pipelines de docking molecular en entornos HPC**.

### Contribuciones Esperadas

Una solución de este tipo contribuiría a:

1. **Optimizar el uso del clúster de cómputo**: Aprovechamiento eficiente de recursos GPU/CPU
2. **Reducir la carga operativa sobre los investigadores**: Automatización de tareas repetitivas
3. **Mejorar la trazabilidad de los experimentos**: Gestión organizada de parámetros y resultados

### Impacto

De esta manera, el proyecto busca aportar una herramienta que facilite la ejecución de estudios computacionales:

- Más eficientes
- Más escalables
- Más reproducibles

...dentro del ámbito académico.

---

## Restricciones y Supuestos de Diseño

El desarrollo del sistema considera algunas restricciones técnicas y operativas que pueden influir en su implementación:

### Restricción 1: Dependencia de Herramientas Externas

- El proyecto depende de herramientas externas especializadas como **AutoDock-GPU**
- Estas herramientas deben estar correctamente instaladas y configuradas en el entorno de ejecución
- Es necesario garantizar el funcionamiento del proceso de simulación molecular

### Restricción 2: Configuración de Entorno HPC

- El sistema requiere una configuración adecuada de permisos y del entorno de ejecución dentro del clúster
- Los usuarios deben tener acceso autorizado a:
  - GPU
  - Almacenamiento
  - Colas de procesamiento (SLURM)

### Restricción 3: Gestión de Recursos GPU

- Posible sobrecarga de las GPU si no se gestiona correctamente la distribución de tareas
- El diseño contempla mecanismos de control para:
  - Evitar la saturación de recursos
  - Asegurar un uso eficiente del hardware disponible

### Restricción 4: Tiempo de Pruebas

- El tiempo disponible para realizar pruebas en el entorno real será limitado
- Parte de la validación inicial del sistema deberá realizarse en entornos de prueba o simulación
- La ejecución completa en la infraestructura definitiva se realizará posteriormente

---

## Objetivos

### Objetivo 1: Diseñar Arquitectura Modular

**Diseñar** una arquitectura de software modular y desacoplada, organizada en capas (CLI, Core, Adapters y Utils), que permita:

- Estructurar claramente las responsabilidades del sistema
- Facilitar su mantenibilidad
- Habilitar futuras extensiones dentro del ecosistema HPC del laboratorio

### Objetivo 2: Automatizar Pipeline Completo

**Automatizar** el pipeline completo de docking molecular, integrando:

- Detección automática de sitios de unión
- Generación dinámica de cajas de docking
- Preparación y validación de archivos de entrada
- Ejecución paralela del docking con GPU
- Verificación estructurada de los resultados generados

### Objetivo 3: Implementar Sistema de Ejecución Híbrido

**Implementar** un sistema de ejecución paralela híbrido que permita:

- Multiprocesamiento local para desarrollo y pruebas
- Generación automática de scripts de SLURM para ejecución en clúster
- Gestión eficiente de recursos computacionales distribuidos

### Objetivo 4: Desarrollar Validación de Recursos

**Desarrollar** mecanismos de validación y control de recursos computacionales que:

- Evalúen la disponibilidad de CPU, memoria y GPU
- Realicen evaluaciones antes y durante la ejecución
- Prevengan sobrecargas del sistema
- Optimicen la asignación de tareas
- Garanticen la estabilidad operativa del clúster

### Objetivo 5: Incorporar Tolerancia a Fallos

**Incorporar** estrategias básicas de tolerancia a fallos, incluyendo:

- Control de timeouts
- Detección de ejecuciones incompletas o fallidas
- Registro estructurado de errores
- Asegurar la robustez del sistema ante eventos inesperados

### Objetivo 6: Diseñar Módulo de Análisis

**Diseñar e implementar** un módulo de análisis estructurado de resultados que permita:

- Extraer automáticamente métricas relevantes (afinidad, RMSD)
- Generar rankings globales de ligandos
- Calcular estadísticas descriptivas
- Exportar reportes reproducibles
- Facilitar la trazabilidad científica

### Objetivo 7: Evaluar Desempeño del Sistema

**Evaluar** el desempeño del sistema mediante:

- Comparación entre ejecución secuencial y distribuida
- Medición de métricas: tiempo total de ejecución, speedup paralelo, eficiencia computacional
- Análisis de tasa de éxito experimental
- Validación del impacto de la solución en el entorno HPC del laboratorio

---

## Alcance

El proyecto consiste en diseñar e implementar una **plataforma científica basada en línea de comandos (CLI)**, modular y orientada a entornos de cómputo de alto rendimiento (HPC), que permita automatizar y optimizar la ejecución de experimentos de docking molecular y dinámica molecular dentro de un clúster distribuido.

### Componentes Principales

La plataforma integrará:

1. **Herramientas especializadas**: AutoDock-GPU, fpocket, AutoDockTools
2. **Gestión eficiente de recursos computacionales**: CPU y GPU
3. **Mecanismos de paralelización**: Para mejorar el rendimiento en simulaciones
4. **Sistema de almacenamiento**: Integración con NAS del laboratorio

### Funcionalidades

Asimismo, el sistema permitirá:

- Organización y trazabilidad de los experimentos realizados
- Validación básica de resultados
- Generación automática de reportes reproducibles

### Objetivos del Alcance

Con esto se busca:

- Mejorar la eficiencia computacional
- Facilitar la gestión de experimentos científicos
- Proporcionar una base escalable para el desarrollo del ecosistema Chemlab

---

## Estado del Arte y Soluciones Relacionadas

### 1. Herramientas de Docking Molecular

#### AutoDock / AutoDock-GPU

En el ámbito del docking molecular, **AutoDock** [3] implementa:

- Algoritmos basados en búsquedas estocásticas
- Funciones de puntuación energéticas para estimar afinidad proteína-ligando

Su versión acelerada, **AutoDock-GPU** [1]:

- Optimiza el cálculo mediante paralelización masiva en GPU
- Reduce significativamente los tiempos de ejecución en entornos de alto rendimiento

**Limitaciones**:
- Orientadas principalmente al cálculo molecular en sí mismo
- No incluyen mecanismos nativos de orquestación distribuida
- Sin trazabilidad estructurada de experimentos
- Sin integración directa con sistemas de almacenamiento centralizado

### 2. Herramientas de Dinámica Molecular

#### GROMACS

Para simulaciones de dinámica molecular, **GROMACS** [4] ofrece:

- Paralelización híbrida (MPI + OpenMP)
- Escalabilidad en clústers
- Optimización para arquitecturas CPU/GPU

**Limitaciones**:
- Ejecución en entornos HPC requiere configuración manual de scripts
- Definición explícita de recursos necesaria
- Manejo independiente de resultados
- Incremento de complejidad operativa

### 3. Gestión de Recursos en Entornos HPC

#### SLURM Workload Manager

En la capa de infraestructura, **SLURM** [2] es uno de los gestores de colas más utilizados en clústers académicos:

**Características**:
- Asignación dinámica de recursos
- Control de prioridades
- Monitoreo del estado de los jobs

**Limitaciones**:
- Opera principalmente a nivel de administración de recursos
- No provee abstracciones orientadas a experimentos científicos
- Interacción basada en scripts y comandos de bajo nivel (`sbatch`, `squeue`, `scancel`)
- Exige conocimientos técnicos específicos por parte de los usuarios

### 4. Monitoreo de Infraestructura en Entornos HPC

#### Prometheus

En cuanto al monitoreo de infraestructuras distribuidas, **Prometheus** [5] se ha consolidado como una de las herramientas más utilizadas:

**Funcionalidades**:
- Recolección y análisis de métricas en sistemas distribuidos
- Modelo de series temporales
- Lenguaje de consulta especializado (PromQL)
- Supervisión de múltiples nodos en infraestructuras HPC

**Capacidades de Monitoreo**:
- Uso de CPU
- Memoria
- Almacenamiento
- Aceleradores GPU

**Limitaciones**:
- Proporciona capacidades robustas de observabilidad del sistema
- **NO** está orientado a la orquestación de pipelines científicos
- **NO** gestiona experimentos de docking molecular
- Funcionalidad limitada al monitoreo de infraestructura
- Sin automatización integral de flujos de trabajo científicos

### 5. Limitaciones del Ecosistema Actual

Desde una perspectiva arquitectónica, se observa que:

| Categoría | Herramientas | Enfoque |
|-----------|-------------|---------|
| **Cálculo Científico** | AutoDock-GPU, GROMACS | Procesamiento científico |
| **Gestión de Recursos** | SLURM | Administración de infraestructura |
| **Monitoreo** | Prometheus | Recolección y análisis de métricas del sistema |

**Ninguna integra de manera nativa**:
- Almacenamiento científico estructurado (NAS)
- Monitoreo orientado a experimentos
- Control de reproducibilidad específico para docking académico

### Vacío Identificado

Esta fragmentación implica que el investigador debe asumir la responsabilidad de integrar manualmente múltiples capas tecnológicas:

1. Preparación de datos
2. Generación de scripts
3. Envío al clúster
4. Seguimiento de ejecución
5. Recuperación de resultados
6. Análisis posterior

**Resultado**: Una arquitectura implícita, no formalizada, dependiente de prácticas individuales y vulnerable a inconsistencias.

### Conclusión

Por tanto, el vacío identificado no corresponde a la ausencia de herramientas de cálculo eficientes, sino a **la falta de una arquitectura integradora** que articule:

- Computación científica
- Gestión HPC
- Almacenamiento centralizado
- Monitoreo experimental

...bajo un modelo coherente, modular y reproducible.

---

## Diagramas de Arquitectura (Modelo C4)

Para ilustrar el diseño modular y desacoplado propuesto para ChemLink, se presenta a continuación el **Modelo C4** de la plataforma. Este modelo detalla la estructura desde el contexto de alto nivel hasta la implementación a nivel de código.

### Nivel 1: Diagrama de Contexto

El diagrama de contexto muestra cómo ChemLink interactúa con los usuarios (investigadores) y sistemas externos (SLURM, NAS, herramientas científicas).

![Diagrama de Contexto](/informes/images/c1model.drawio.png)

**Figura 1: Nivel 1 - Contexto del Sistema ChemLink**

Este nivel representa:
- Investigadores que interactúan con el sistema
- Relación con el clúster HPC via SLURM
- Integración con almacenamiento NAS
- Conexión con herramientas científicas (AutoDock-GPU, fpocket)

---

### Nivel 2: Diagrama de Contenedores

El diagrama de contenedores descompone ChemLink en sus componentes principales y muestra cómo se comunican entre sí.

![Diagrama de Contenedores](/informes/images/containermodel.drawio.png)

**Figura 2: Nivel 2 - Contenedores del Sistema**

Este nivel muestra:
- CLI Interface: Punto de entrada para usuarios
- Core Pipeline: Motor de orquestación
- Adapters: Wrappers para herramientas externas
- Storage Manager: Gestión de almacenamiento
- SLURM Interface: Comunicación con el gestor de colas

---

### Nivel 3: Diagrama de Componentes

El diagrama de componentes profundiza en la estructura interna de cada contenedor, mostrando los módulos específicos y sus responsabilidades.

![Diagrama de Componentes](/informes/images/Componentmodel.drawio.png)

**Figura 3: Nivel 3 - Componentes Detallados**

Este nivel detalla:
- Módulos del CLI (comandos: run, prepare, analyze, report)
- Componentes del Core (workflow manager, job orchestrator)
- Adaptadores específicos (AutoDock-GPU, fpocket, AutoDockTools)
- Utilidades (logger, validator, resource detector)

---

### Nivel 4: Diagrama de Código

El diagrama de código muestra la implementación a nivel de clases, interfaces y relaciones entre objetos.

![Diagrama de Código](/informes/images/Codediagram.drawio.png)

**Figura 4: Nivel 4 - Estructura de Clases**

Este nivel presenta:
- Clases del dominio (Ligand, Receptor, DockingResult)
- Interfaces de adaptadores (DockingAdapter, PocketDetectorAdapter)
- Implementaciones concretas
- Patrones de diseño aplicados (Adapter, Strategy, Pipeline)

---

### Resumen del Modelo C4

El Modelo C4 proporciona una visión completa de la arquitectura de ChemLink en cuatro niveles de abstracción:

1. **Contexto**: Vista de alto nivel del sistema y sus interacciones
2. **Contenedores**: Componentes de ejecución principales
3. **Componentes**: Módulos funcionales específicos
4. **Código**: Implementación detallada a nivel de clases

Esta arquitectura modular permite:
- Separación clara de responsabilidades
- Facilidad de mantenimiento y extensión
- Testeabilidad independiente de componentes
- Escalabilidad del sistema

---

## Requerimientos Preliminares

### Requerimientos Funcionales

El sistema debe cumplir con las siguientes funcionalidades:

#### RF1: Generación de Scripts para SLURM
- Generar automáticamente scripts de ejecución para SLURM
- Incluir configuración de recursos (CPU, GPU, memoria)
- Definir dependencias entre jobs

#### RF2: Envío de Jobs al Clúster
- Enviar jobs al clúster de cómputo mediante comandos SLURM
- Validar pre-condiciones antes del envío
- Manejar errores de envío

#### RF3: Monitoreo de Estado
- Monitorear el estado de ejecución de los experimentos
- Consultar estado mediante `squeue`/`sacct`
- Notificar cambios de estado relevantes

#### RF4: Ejecución de Herramientas Científicas
- Ejecutar herramientas científicas como:
  - AutoDock-GPU para docking molecular
  - Fpocket [6] para detección de sitios de unión
  - AutoDockTools para preparación de archivos

#### RF5: Almacenamiento de Resultados
- Almacenar resultados de experimentos en el sistema NAS del laboratorio
- Organizar resultados por experimento y timestamp
- Mantener estructura de directorios coherente

#### RF6: Generación de Reportes
- Generar reportes estructurados a partir de los resultados obtenidos
- Incluir métricas relevantes (afinidad, RMSD)
- Exportar en formatos múltiples (CSV, JSON, Markdown)

---

### Requerimientos No Funcionales

El sistema debe satisfacer los siguientes criterios de calidad:

#### RNF1: Rendimiento
- El sistema no debe introducir una sobrecarga mayor al **5%** respecto a la ejecución manual de los experimentos
- Mantener tiempos de respuesta aceptables en operaciones interactivas

#### RNF2: Disponibilidad
- Disponibilidad del sistema **≥ 95%** durante las pruebas experimentales
- Recuperación automática ante fallos menores

#### RNF3: Concurrencia
- Soporte para ejecución concurrente de múltiples experimentos
- Gestión adecuada de recursos compartidos
- Prevención de condiciones de carrera

#### RNF4: Trazabilidad
- Garantizar trazabilidad completa de los experimentos
- Registro de:
  - Parámetros de configuración
  - Historial de ejecuciones
  - Resultados generados
- Logs estructurados con timestamps

#### RNF5: Extensibilidad
- Arquitectura modular y extensible
- Permitir integrar nuevas herramientas científicas en el futuro
- Interfaces bien definidas entre componentes

#### RNF6: Usabilidad
- Interfaz CLI intuitiva y bien documentada
- Mensajes de error claros y accionables
- Documentación completa de comandos y opciones

---

## Criterios de Aceptación Inicial

Para considerar la primera versión del sistema como funcional, debe cumplir los siguientes criterios:

### CA1: Ejecución Completa con Comando Único
- El sistema ejecuta un docking completo con un solo comando
- El comando debe ser del tipo: `chemlink run --ligands <dir> --receptor <file>`

### CA2: Envío Correcto a SLURM
- El job es enviado correctamente a SLURM
- Se genera script sbatch válido
- El job aparece en la cola (`squeue`)

### CA3: Monitoreo Automático
- El estado puede ser consultado automáticamente
- El sistema detecta completitud o fallos
- Provee información actualizada del progreso

### CA4: Almacenamiento Correcto
- Los resultados se almacenan correctamente en NAS
- Estructura de directorios organizada
- Archivos de salida accesibles

### CA5: Generación de Reporte
- Se genera un reporte estructurado al finalizar
- Incluye métricas clave (afinidad, RMSD)
- Formato legible y reproducible

### CA6: Automatización Completa
- No se requieren intervenciones manuales intermedias
- El flujo completo es autónomo
- Manejo de errores sin supervisión humana

---

## Plan de Trabajo

El desarrollo del proyecto se organizará en **5 fases principales** distribuidas a lo largo de **12 semanas** (desde la semana 4 hasta la semana 15 del semestre académico).

### Fase 1: Análisis y Especificación (Semanas 4-7)

**Actividades**:
1. **Análisis del problema y entorno HPC** (S4-S5)
   - Caracterización del clúster Chemlab
   - Identificación de restricciones técnicas
   - Análisis de herramientas existentes

2. **Requerimientos y métricas** (S5-S6)
   - Definición de requerimientos funcionales
   - Especificación de métricas de desempeño
   - Criterios de aceptación

3. **Arquitectura de alto nivel** (S6-S7)
   - Diseño del Modelo C4
   - Definición de capas del sistema
   - Interfaces entre componentes

**Entregables**:
- Documento de requerimientos
- Documento de arquitectura
- Diagrama C4 completo

---

### Fase 2: Diseño Detallado y Preparación (Semanas 7-10)

**Actividades**:
1. **Diseño interno de módulos** (S7-S8)
   - Especificación de clases y métodos
   - Definición de interfaces de adaptadores
   - Diseño de estructuras de datos

2. **Diseño de paralelización híbrida** (S8-S9)
   - Estrategia de ejecución local (multiprocessing)
   - Estrategia de ejecución distribuida (SLURM)
   - Mecanismos de sincronización

3. **Validación de entorno HPC y baseline** (S9-S10)
   - Pruebas de conectividad con SLURM
   - Medición de tiempos de ejecución manual (baseline)
   - Validación de acceso a NAS

**Entregables**:
- Diseño detallado de módulos
- Especificación de paralelización
- Métricas baseline del sistema actual

---

### Fase 3: Implementación Modular (Semanas 10-14)

**Actividades**:
1. **Implementación CLI** (S10-S11)
   - Desarrollo de comandos principales
   - Validación de argumentos
   - Manejo de errores de usuario

2. **Implementación Core Pipeline** (S11-S12)
   - Workflow manager
   - Job orchestrator
   - Pipeline executor

3. **Integración con AutoDock-GPU** (S12-S13)
   - Adapter para AutoDock-GPU
   - Preparación de archivos PDBQT
   - Ejecución y parsing de resultados

4. **Paralelización multiproceso y clúster** (S13-S14)
   - Implementación de modo local
   - Generación de scripts SLURM
   - Monitoreo de jobs distribuidos

5. **Control de recursos y tolerancia a fallos** (S14-S15)
   - Detección de recursos disponibles
   - Timeouts y reintentos
   - Logging de errores

**Entregables**:
- Código fuente completo
- Suite de tests unitarios
- Documentación de código

---

### Fase 4: Análisis y Reportes (Semana 15)

**Actividades**:
1. **Módulo de análisis** (S15)
   - Cálculo de afinidad y RMSD
   - Ranking de ligandos
   - Estadísticas descriptivas

2. **Generación de reportes reproducibles** (S15)
   - Exportación a CSV/JSON
   - Generación de reportes Markdown
   - Visualización básica de resultados

**Entregables**:
- Módulo de análisis funcional
- Ejemplos de reportes generados

---

### Fase 5: Evaluación y Consolidación (Semana 15)

**Actividades**:
1. **Evaluación de desempeño**
   - Medición de speedup paralelo
   - Cálculo de eficiencia computacional
   - Comparación con baseline

2. **Optimización final**
   - Identificación de bottlenecks
   - Optimizaciones de performance
   - Ajuste de parámetros

3. **Integración total y preparación final**
   - Pruebas de integración completas
   - Documentación de usuario
   - Preparación de presentación

**Entregables**:
- Reporte de evaluación de desempeño
- Documentación completa del sistema
- Presentación final del proyecto

---

### Cronograma Visual

| Fase | Actividad | S4 | S5 | S6 | S7 | S8 | S9 | S10 | S11 | S12 | S13 | S14 | S15 |
|------|-----------|----|----|----|----|----|----|-----|-----|-----|-----|-----|-----|
| **Fase 1** | Análisis problema y HPC | X | X | | | | | | | | | | |
| | Requerimientos y métricas | | X | X | | | | | | | | | |
| | Arquitectura alto nivel | | | X | X | | | | | | | | |
| **Fase 2** | Diseño módulos | | | | X | X | | | | | | | |
| | Diseño paralelización | | | | | X | X | | | | | | |
| | Validación HPC y baseline | | | | | | X | X | | | | | |
| **Fase 3** | Implementación CLI | | | | | | | X | X | | | | |
| | Core Pipeline | | | | | | | | X | X | | | |
| | Integración AutoDock-GPU | | | | | | | | | X | X | | |
| | Paralelización | | | | | | | | | | X | X | |
| | Control recursos y fallos | | | | | | | | | | | X | X |
| **Fase 4** | Módulo análisis | | | | | | | | | | | | X |
| | Generación reportes | | | | | | | | | | | | X |
| **Fase 5** | Evaluación desempeño | | | | | | | | | | | | X |
| | Optimización final | | | | | | | | | | | | X |
| | Integración y preparación | | | | | | | | | | | | X |

**Nota**: Las semanas indicadas (S4 a S15) corresponden a las semanas académicas del semestre en curso, y no a las semanas transcurridas desde el inicio del proyecto.

---

## Riesgos del Proyecto

El desarrollo de una plataforma científica orientada a entornos de cómputo de alto rendimiento implica ciertos riesgos técnicos y operativos que deben ser identificados y gestionados:

### Riesgo 1: Complejidad Técnica de Integración

**Descripción**:  
El sistema debe integrar múltiples componentes heterogéneos:
- Generación de scripts para SLURM
- Ejecución de herramientas científicas como AutoDock-GPU
- Gestión de almacenamiento en NAS
- Coordinación en un entorno HPC distribuido

**Impacto**: Alto  
**Probabilidad**: Media

**Consecuencias**:
- Desafíos de estabilidad del sistema
- Problemas de coordinación de recursos
- Dificultades en la sincronización de componentes

**Mitigación**:
- Diseño modular con interfaces bien definidas
- Pruebas de integración continuas
- Implementación incremental con validación en cada fase

---

### Riesgo 2: Plazos de Desarrollo

**Descripción**:  
La implementación y las pruebas rigurosas en un entorno de clúster real pueden requerir más tiempo del previsto.

**Impacto**: Medio  
**Probabilidad**: Media

**Consecuencias**:
- Retraso en la fase de evaluación
- Tiempo insuficiente para optimizaciones
- Menor número de casos de prueba ejecutados

**Mitigación**:
- Planificación detallada con márgenes de tiempo
- Ejecución de pruebas en paralelo al desarrollo
- Priorización de funcionalidades críticas
- Uso de entornos de prueba simulados inicialmente

---

### Riesgo 3: Curva de Aprendizaje

**Descripción**:  
La adopción inicial del sistema por parte de los investigadores puede verse afectada si la interfaz de línea de comandos (CLI) y los flujos de uso no se diseñan de forma suficientemente clara e intuitiva.

**Impacto**: Bajo-Medio  
**Probabilidad**: Media

**Consecuencias**:
- Resistencia al uso del sistema
- Mayor necesidad de soporte y documentación
- Posibles errores de usuario

**Mitigación**:
- Diseño de CLI con mensajes claros y ayuda contextual
- Documentación exhaustiva con ejemplos
- Sesiones de capacitación para usuarios
- Validación de usabilidad con usuarios reales

---

### Riesgo 4: Disponibilidad de Recursos HPC

**Descripción**:  
El acceso al clúster HPC para pruebas puede verse limitado por:
- Uso concurrente por otros proyectos
- Mantenimientos programados
- Fallos de hardware

**Impacto**: Medio  
**Probabilidad**: Baja

**Consecuencias**:
- Retrasos en validación experimental
- Imposibilidad de realizar benchmarks completos
- Resultados de pruebas incompletos

**Mitigación**:
- Coordinación anticipada con administradores del clúster
- Desarrollo de entornos de prueba locales
- Planificación flexible de actividades de testing

---

### Riesgo 5: Cambios en Herramientas Externas

**Descripción**:  
Actualizaciones o cambios en herramientas externas (AutoDock-GPU, fpocket) pueden introducir incompatibilidades.

**Impacto**: Bajo  
**Probabilidad**: Baja

**Consecuencias**:
- Necesidad de adaptar código
- Fallos en ejecución de experimentos
- Resultados inconsistentes

**Mitigación**:
- Versionado explícito de dependencias
- Tests de regresión automatizados
- Implementación de adaptadores desacoplados

---

## Referencias Bibliográficas

### [1] AutoDock-GPU
A. Santos-Martins et al., "Accelerating AutoDock4 with GPUs and Gradient-Based Local Search," *Journal of Chemical Theory and Computation*, vol. 42, no. 2, pp. 1060-1073, 2021.  
Disponible: [https://github.com/ccsb-scripps/AutoDock-GPU](https://github.com/ccsb-scripps/AutoDock-GPU)

### [2] SLURM Workload Manager
A. B. Yoo, M. A. Jette, y M. Grondona, "Slurm: Simple linux utility for resource management," en *Job Scheduling Strategies for Parallel Processing*, 2003, pp. 44-60.  
Disponible: [https://slurm.schedmd.com/](https://slurm.schedmd.com/)

### [3] AutoDock Vina
O. Trott y A. J. Olson, "AutoDock Vina: Improving the speed and accuracy of docking with a new scoring function, efficient optimization, and multithreading," *Journal of Computational Chemistry*, vol. 31, no. 2, pp. 455-461, 2010.  
Disponible: [https://autodock.scripps.edu/](https://autodock.scripps.edu/)

### [4] GROMACS
M. J. Abraham et al., "GROMACS: High performance molecular simulations through multi-level parallelism from laptops to supercomputers," *SoftwareX*, vol. 1-2, pp. 19-25, 2015.  
Disponible: [https://www.gromacs.org/](https://www.gromacs.org/)

### [5] Prometheus Monitoring System
B. Sigelman et al., "Prometheus: A Next-Generation Monitoring System," in *Proc. IEEE/ACM Int. Conf. on Cloud Engineering (IC2E)*, Tempe, AZ, USA, 2015, pp. 27-32.  
Disponible: [https://prometheus.io/](https://prometheus.io/)

### [6] Fpocket
V. Le Guilloux, P. Schmidtke, y P. Tuffery, "Fpocket: An open source platform for ligand pocket detection," *BMC Bioinformatics*, vol. 10, no. 168, 2009.  
Disponible: [https://github.com/fpocket/fpocket](https://github.com/fpocket/fpocket)

---

## Anexos

### A. Estructura de Directorios del Proyecto

```
chemlink/
├── cli/                    # Interfaz CLI
│   ├── main.py            # Entry point
│   └── commands/          # Comandos implementados
│       ├── run.py         # Comando de ejecución
│       ├── prepare.py     # Preparación de archivos
│       ├── analyze.py     # Análisis de resultados
│       └── report.py      # Generación de reportes
├── adapters/              # Adaptadores externos
│   ├── autodock_gpu/      # Wrapper AutoDock-GPU
│   │   └── autodock_gpu_adapter.py
│   ├── autodocktools/     # Wrapper AutoDockTools
│   │   ├── __init__.py
│   │   └── autodocktools_adapter.py
│   └── fpocket/           # Wrapper fpocket
│       └── fpocket_adapter.py
├── pipelines/             # Pipelines de ejecución
│   ├── docking_pipeline.py
│   └── steps/             # Etapas del pipeline
├── workflows/             # Gestión de workflows
│   ├── workflow_manager.py
│   └── job_orchestrator.py
├── hpc/                   # Integración HPC
│   ├── slurm/             # Interface SLURM
│   │   └── slurm_monitor.py
│   └── cluster/           # Gestión de cluster
│       └── resource_detector.py
├── storage/               # Gestión de almacenamiento
│   ├── file_manager.py
│   ├── dataset_manager.py
│   └── nas_storage.py
├── analysis/              # Análisis de resultados
│   └── report_generator.py
├── utils/                 # Utilidades
│   ├── logger.py          # Sistema de logging
│   ├── validator.py       # Validación de inputs
│   └── molecule_processor.py
├── data/                  # Datos entrada/salida
│   └── input/
│       ├── ligands/       # Ligandos de entrada
│       └── receptors/     # Receptores (proteínas)
├── tests/                 # Suite de tests
│   ├── unit/              # Tests unitarios
│   ├── integration/       # Tests de integración
│   └── data/              # Datos de prueba
├── docs/                  # Documentación
│   ├── user_guide.md      # Guía de usuario
│   └── api_reference.md   # Referencia de API
├── images/                # Diagramas de arquitectura
│   ├── c1model.drawio.png
│   ├── containermodel.drawio.png
│   ├── Componentmodel.drawio.png
│   └── Codediagram.drawio.png
├── informes/              #
│   ├── Informe_I_Chemlink.pdf
│   └── README.md          # 
├── docker/                # Dockerfiles
├── scripts/               # Scripts auxiliares
├── pyproject.toml         # Configuración del proyecto
├── requirements.txt       # Dependencias Python
├── README.md              # README principal
├── ARCHITECTURE.md        # Documentación de arquitectura
├── PROPOSAL.md            # Propuesta técnica
└── LICENSE                # Licencia MIT
```

### B. Glosario de Términos

- **CADD**: Computer-Aided Drug Design (Diseño de Fármacos Asistido por Computador)
- **Docking Molecular**: Técnica computacional para predecir orientación de ligandos en sitios activos
- **GPU**: Graphics Processing Unit (Unidad de Procesamiento Gráfico)
- **HPC**: High-Performance Computing (Computación de Alto Rendimiento)
- **NAS**: Network-Attached Storage (Almacenamiento Conectado a la Red)
- **PDBQT**: Formato de archivo con cargas parciales para AutoDock
- **Pipeline**: Secuencia automatizada de pasos de procesamiento
- **RMSD**: Root Mean Square Deviation (Desviación Cuadrática Media)
- **SLURM**: Simple Linux Utility for Resource Management
- **Workflow**: Flujo de trabajo automatizado

### C. Acrónimos

- **API**: Application Programming Interface
- **CLI**: Command-Line Interface
- **CPU**: Central Processing Unit
- **CSV**: Comma-Separated Values
- **JSON**: JavaScript Object Notation
- **MPI**: Message Passing Interface
- **OpenMP**: Open Multi-Processing
- **PDB**: Protein Data Bank

### D. Contacto y Recursos del Proyecto

**Autores**:
- Juan Felipe Santos Rodríguez
- Samuel Matiz García
- Camilo Andrés Navarro Navarro

**Institución**:  
Universidad del Norte  
Barranquilla, Colombia

**Docente**: Augusto Salazar  
**Co-asesor**: Daniel Romero

**Laboratorio**: Chemlab - Facultad de Ciencias

**Recursos del Proyecto**:
- Repositorio GitHub: [github.com/chemlab/chemlink](https://github.com/chemlab/chemlink)
- Documentación: [chemlink.readthedocs.io](https://chemlink.readthedocs.io)

---

<p align="center">
  <i>Informe Técnico I - Propuesta de Proyecto</i><br/>
  <b>ChemLink</b><br/>
  Plataforma de Orquestación para Docking Molecular en Entornos HPC<br/>
  <br/>
  <i>Universidad del Norte - Barranquilla, Colombia</i><br/>
  <i>Marzo 2026</i>
</p>

---

## Contenido del PDF

Este README documenta completamente el contenido del archivo PDF adjunto:

**Informe_I_Chemlink.pdf** (Marzo 2026)  
Informe Técnico Número I - Propuesta del Proyecto  
Trabajo de Final de Grado - Ingeniería de Sistemas (2026-10)

El documento PDF y este README contienen la propuesta formal del proyecto ChemLink desarrollado en la Universidad del Norte por Juan Felipe Santos Rodríguez, Samuel Matiz García y Camilo Andrés Navarro Navarro, bajo la dirección del profesor Augusto Salazar y el co-asesor Daniel Romero.
