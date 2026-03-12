# Cronograma de Desarrollo basado en Prototipos
## Malla temporal de desarrollo

Representación gráfica del cronograma del proyecto basada en los prototipos definidos para el desarrollo de ChemLink.

```
Semanas →     4     5     6     7     8     9     10    11    12    13    14    15
              │     │     │     │     │     │     │     │     │     │     │     │

Prototipo 1   █████████████
CLI + Infraestructura

Prototipo 2                █████████████████
Pipeline Docking Local

Prototipo 3                                 ██████████████████
Cluster + SLURM + NAS

Prototipo 4                                                   ██████████████████
Análisis y Optimización
```

## Prototipo 1 — CLI Base + Infraestructura (Semanas 4–6)

### Objetivo
Construir una versión mínima funcional del sistema que permita ejecutar comandos CLI y validar la integración básica con el entorno HPC.

### Actividades

**Semana 4**
- Análisis del entorno HPC del laboratorio  
- Caracterización del clúster Chemlab  
- Identificación de restricciones técnicas  
- Definición inicial de requerimientos  

**Semana 5**
- Diseño de arquitectura del sistema  
- Elaboración del modelo C4  
- Definición de capas del sistema:
  - CLI
  - Core
  - Adapters
  - Utils

**Semana 6**
- Implementación del CLI base  
- Creación de la estructura del proyecto  
- Implementación del sistema de logging  
- Implementación de comandos iniciales  

### Entregable (Prototipo 1)

CLI funcional que:

- Ejecuta comandos
- Valida argumentos
- Detecta el entorno de ejecución
- Establece conexión con el cluster

En esta etapa aún no se ejecuta docking real.

---

## Prototipo 2 — Pipeline de Docking Local (Semanas 7–9)

### Objetivo
Lograr que el sistema ejecute un docking completo localmente en un nodo. Esto permite validar el pipeline científico.

### Actividades

**Semana 7**
- Implementación del pipeline básico
- Integración con OpenBabel
- Preparación automática de moléculas

**Semana 8**
- Integración con Fpocket
- Detección automática de sitios de unión
- Generación automática del grid box

**Semana 9**
- Integración con AutoDock-GPU
- Ejecución de docking
- Parsing de resultados (.dlg)

### Entregable (Prototipo 2)

Sistema capaz de ejecutar:

```bash
chemlink dock protein.pdb ligand.pdb
```

Y generar:

- Resultados de docking
- Valores de afinidad
- Archivos de salida del experimento

Todo ejecutándose en modo local.

---

## Prototipo 3 — Ejecución Distribuida + NAS (Semanas 10–12)

### Objetivo
Permitir que ChemLink ejecute experimentos distribuidos en el cluster utilizando SLURM y almacene resultados en el NAS del laboratorio.

### Actividades

**Semana 10**
- Integración con SLURM
- Generación automática de scripts `sbatch`
- Sistema de envío de jobs al cluster

**Semana 11**
- Implementación del monitoreo de jobs mediante `squeue`
- Manejo de estados de ejecución:
  - pending
  - running
  - failed
  - completed

**Semana 12**
- Integración con NAS
- Implementación de almacenamiento estructurado:

```
/nas/chemlink/
   experiments/
   results/
   logs/
```

- Control de acceso y validación de rutas

### Entregable (Prototipo 3)

Sistema capaz de ejecutar:

```bash
chemlink dock dataset/ --cluster
```

Capacidades:

- Distribución automática de trabajos en múltiples nodos
- Almacenamiento automático de resultados en el NAS
- Monitoreo de ejecuciones del cluster

Este prototipo demuestra ejecución real en un entorno HPC.

---

## Prototipo 4 — Análisis y Optimización (Semanas 13–15)

### Objetivo
Agregar capacidades de análisis automático de resultados y evaluar el rendimiento del sistema.

### Actividades

**Semana 13**
- Implementación del módulo de análisis
- Extracción de métricas:
  - afinidad
  - RMSD

**Semana 14**
- Generación automática de ranking de ligandos
- Generación de reportes en formatos:
  - CSV
  - JSON
  - Markdown

**Semana 15**

Evaluación del sistema:

- Comparación entre ejecución secuencial y distribuida
- Medición de speedup
- Evaluación de eficiencia del cluster
- Identificación de cuellos de botella

Preparación final:

- Documentación técnica
- Pruebas integrales del sistema
- Preparación de presentación final

---

# Entregables Finales

1. Plataforma ChemLink funcional  
2. Ejecución distribuida en cluster HPC  
3. Integración con NAS para almacenamiento de resultados científicos  
4. Pipeline automatizado de docking molecular  
5. Generación de reportes reproducibles  
6. Evaluación de desempeño del sistema
