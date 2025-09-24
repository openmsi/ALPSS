# Platform Integration: Linking Samples, Experiments, and Analysis

At the core of the platform is the **IGSN** (International Geo Sample Number).  
It serves as the central identifier linking all layers of data:

---

## Workflow Overview

1. **Sample Registration**  
   - Each physical sample receives an IGSN.  

2. **Experiment Run + Metadata**  
   - Laser shock experiments are logged using the JSON Schema, either manually or automatically. 
   - Metadata is tied to the IGSN and can be queried/exported.  

3. **PDV Trace Ingestion**  
   - The laser shock systems produces raw PDV traces and other data artefacts, all streamed instantly using [**openmsistream**](https://openmsistream.readthedocs.io/en/latest/)
 to the portal.  

4. **ALPSS Processing**  
   - In parallel, ALPSS Processor consumes PDV traces from a stream using [**openmsistream**](https://openmsistream.readthedocs.io/en/latest/) in real-time.  
   - Outputs and configs are uploaded to the portal and automatically linked back to the IGSN.  

5. **Data Accessibility**  
   - Results can be searched by sample, experiment conditions, or ALPSS parameters.  
   - Exportable in standard formats (CSV/Excel).  

---

## Integration Diagram

![Diagram](images/ls_workflow.png)

This integration ensures that from a single IGSN, one can navigate:  
- The raw sample and flyer details  
- The experimental metadata  
- The PDV trace  
- The processed results and figures  
- The exact ALPSS configuration used  
