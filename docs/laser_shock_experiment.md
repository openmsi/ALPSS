# Laser Shock Experiment 

The Laser Shock team performs experiments where flyers impact samples to study spallation behavior.  
 
 ## IGSN Integration

Each **sample** and is registered with an **International Geo Sample Number (IGSN)**.  
The IGSN acts as the backbone for linking:

- Sample identity and activity
- Laser shock experimental metadata  
- Data artefacts, like PDV trace files  
- Subsequent analysis results 

This guarantees that all data products — from raw experiment setup to processed analysis — can always be tied back to the correct sample.

## Parameters (Metadata)
Each experiment is described and stored using a **JSON Schema** that defines all the required metadata fields. 
This schema is rendered as a form on https://data.htmdec.org/, allowing researchers to fill in parameters such as:

- Experiment ID and Timestamp  
- Flyer ID, material, and thickness  
- Sample ID and material (linked via IGSN)  
- Laser parameters (energy, waveplate angle)  
- PDV file name and measurement parameters  

The ingest can be done manually, by entering and saving details on the platform, or automatically. For example, in the AIMD-L lab, experiments run through the central controller automatically link to an IGSN, and all metadata is sent to the portal via a POST call, ensuring everything is linked together.

![Laser Shock Experiment Form on Data Portal](images/experiments.png)

![Laser Shock Experiment Record on Data Portal](images/experiment_record.png)

#### JSON Schema and Data Accessibility

- The schema ensures **standardized metadata** across all experiments.  
- Data is **queryable and parseable** directly through the platform.  
- Metadata can be **downloaded as Excel or CSV files** for further offline analysis.  

## Data artefacts ("Data")

Output files—such as PDV traces, beam profile images (.bmg), or camera images—are also tracked and linked to their IGSN. These files originate from different sources, most of which stream directly to https://data.htmdec.org/. Using standardized naming conventions, they are automatically associated with the correct IGSN and can be found in the AIMD-L or Malone Lab collections, depending on their origin.

---
