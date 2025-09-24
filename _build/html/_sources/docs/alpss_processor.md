# ALPSS Processor: Streaming Analysis

The **ALPSS Processor** extends ALPSS to a streaming environment. It integrates with [**openmsistream**](https://openmsistream.readthedocs.io/en/latest/) and Kafka to analyze PDV traces *as they are generated*.

---

## How It Works

1. **Input**: PDV traces are streamed from the laser shock setup onto a Kafka topic.  
2. **Processing**: ALPSS Processor consumes the PDV files and runs automatically using a config file.  
3. **Outputs**: Results (figures, data files) are uploaded to https://data.htmdec.org/, either in the AIMD-L or Malone Labc collection.  

---

## Metadata Enrichment

Each uploaded output file is enriched with metadata, making results fully **queryable** and **traceable**:

- All key/value pairs from the ALPSS config file
- ALPSS config file checksum (SHA-256)  
- Output identifiers, linking results back to input PDV trace (e.g., --volt, --velocity, etc)

This ensures that every result is tied back to:  
- The **specific experiment parameters** (via the JSON Schema)  
- The **exact ALPSS configuration** used in processing  

---

## Why It Matters

- Enables **continuous, automated analysis** of experimental data.  
- Guarantees **reproducibility** by associating every result with the exact configuration.  
- Makes downstream queries simple: you can search for all results generated with a certain config option or threshold.  