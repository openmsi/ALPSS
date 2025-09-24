# Platform Integration: Linking Samples, Experiments, and Analysis

At the core of the platform is the **IGSN** (International Geo Sample Number).  
It serves as the central identifier linking all layers of data:

---

## Workflow Overview

1. **Sample Registration**  
   - Each physical sample receives an IGSN.  

2. **Experiment Metadata**  
   - Laser shock experiments are logged using the JSON Schema.  
   - Metadata is tied to the IGSN and can be queried/exported.  

3. **PDV Trace Ingestion**  
   - The laser shock controller streams PDV traces to Kafka.  
   - Alternatively, metadata can be entered manually in the portal.  

4. **ALPSS Processing**  
   - ALPSS Processor consumes PDV traces in real-time.  
   - Outputs and configs are uploaded and automatically linked back to the IGSN.  

5. **Data Accessibility**  
   - Results can be searched by sample, experiment conditions, or ALPSS parameters.  
   - Exportable in standard formats (CSV/Excel).  

---

## Integration Diagram

> 📊 *[Placeholder for diagram: IGSN at center connecting Sample ↔ Experiment Metadata ↔ PDV Trace ↔ ALPSS Processor ↔ Results]*

This integration ensures that from a single IGSN, one can navigate:  
- The raw sample and flyer details  
- The experimental metadata  
- The PDV trace  
- The processed results and figures  
- The exact ALPSS configuration used  
