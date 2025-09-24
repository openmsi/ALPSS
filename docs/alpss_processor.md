# ALPSS Processor: Streaming Analysis

The **ALPSS Processor** extends ALPSS to a streaming environment.  
It integrates with **OpenMSIStream** and Kafka to analyze PDV traces *as they are generated*.

---

## How It Works

1. **Input**: PDV traces are streamed from the laser shock setup onto a Kafka topic.  
2. **Processing**: ALPSS Processor consumes the PDV files and runs `alpss_main_with_config` automatically.  
3. **Outputs**: Results (figures, data files) are uploaded to the platform’s data repository.  

---

## Metadata Enrichment

Each uploaded output file is enriched with metadata, making results fully **queryable** and **traceable**:

- ALPSS config file checksum (SHA-256)  
- All key/value pairs from the ALPSS config (flattened)  
- Output identifiers (linking results back to input PDV trace)  

This ensures that every result is tied back to:  
- The **specific experiment parameters** (via the JSON Schema)  
- The **exact ALPSS configuration** used in processing  

---

## Why It Matters

- Enables **continuous, automated analysis** of experimental data.  
- Guarantees **reproducibility** by associating every result with the exact configuration.  
- Makes downstream queries simple: you can search for all results generated with a certain config option or threshold.  