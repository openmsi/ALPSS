# Laser Shock Experiment 

The Laser Shock team performs experiments where flyers impact samples to study spallation behavior.  
Each experiment is described and stored using a **JSON Schema** that defines all the required metadata fields.  

This schema is rendered as a form in our platform, allowing researchers to fill in parameters such as:

- Experiment ID and Timestamp  
- Flyer ID, material, and thickness  
- Sample ID and material (linked via IGSN)  
- Laser parameters (energy, waveplate angle)  
- PDV file name and measurement parameters  

![Laser Shock Experiment Form on Data Portal](images/experiments.png)
![Laser Shock Experiment Record on Data Portal](images/experiment_record.png)

---

## JSON Schema and Data Accessibility

- The schema ensures **standardized metadata** across all experiments.  
- Data is **queryable and parseable** directly through the platform.  
- Metadata can be **downloaded as Excel or CSV files** for further offline analysis.  

---

## IGSN Integration

Each **sample** is registered with an **International Geo Sample Number (IGSN)**.  
The IGSN acts as the backbone for linking:

- Sample identity  
- Laser shock experimental metadata  
- PDV trace files  
- Subsequent ALPSS analysis results  

This guarantees that all data products — from raw experiment setup to processed analysis — can always be tied back to the correct sample.
