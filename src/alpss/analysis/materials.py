from alpss.analysis.impedance import Material

# The table itself. Each entry is:  "name": (density, C0, S)
#   density in kg/m^3, C0 in m/s, S is a plain number.
MATERIAL_TABLE = {
  "copper": (8960.0, 3958.37, 1.489), 
  "aluminum": (2700.0, 4830.46, 1.338), 
  "glass": (2440, 4198, 1.61),
  "titanium": (4510.0, 4961.0,  0.957),
}
def list_materials():
  #give back the names you're allowed to look up, in alphabetical order
  return sorted(MATERIAL_TABLE.keys())

def get_material(name):
  #look up a material by name and return a Material object.
  #.strip() removes stray spaces, .lower() makes it case-insensitive, so
  #"Copper", "copper", and "  COPPER " all find the same entry.
  key=name.strip().lower()


  #if the name isn't in the table, fail with a message that lists the names that ARE available
  if key not in MATERIAL_TABLE:
    raise ValueError(
      "Unknown material'"+str(name)+"'."
      "Known materials are:"+", ".join(list_materials())
    )
  
  #pull the three numbers out of the tuple and build a Material
  density, C0, S = MATERIAL_TABLE[key]
  return Material(density, C0, S, name)

def material_from_config(inputs, prefix=""):
  #build ONE Material from a config dictionary (inputs).
  #first it looks for a material NAME at the key prefix+"material"; if there
  # isn't one, it falls back to raw numbers at prefix+"density"/"C0"/"S".
  #the prefix lets us reuse this for both materials:
  #  prefix=""        reads "material"  or "density"/"C0"/"S"        (sample)
  #  prefix="flyer_"  reads "flyer_material" or "flyer_density"/...  (flyer)
  name_key=prefix+"material"


  #if a name was given (and isn't blank) -> just look it up in the table
  if name_key in inputs and inputs[name_key]:
    return get_material(inputs[name_key])

  #otherwise build straight from the numbers in the config
  density = inputs[prefix+"density"]
  C0=inputs[prefix+"C0"]
  if  (prefix + "S") in inputs:
    S = inputs[prefix + "S"]
  else: 
    S = 0.0 #if S is missing, assume 0
  return Material (density, C0, S)

def materials_from_config(inputs): 
  #return a (flyer, target) pair of Materials from a config dictionary.
  #the sample/target uses "material" or "density"/"C0"/"S".
  #the flyer uses "flyer_material" or "flyer_density"/"flyer_C0"/"flyer_S".
 
  #build the sample first (no prefix)
  target = material_from_config(inputs, "")

  #does configuration describe a flyer
  flyer_given= False
  if"flyer_material" in inputs and inputs ["flyer_material"] !="":
    flyer_given =True
  if "flyer_density" in inputs: 
    flyer_given = True


  #if a flyer was given, build it (note the trailing underscore in "flyer_",
  #which is needed so the keys come out as "flyer_material", "flyer_density",
  #etc.). If no flyer was given, the flyer is the same material as the sample.
  if flyer_given: 
    flyer = material_from_config(inputs, prefix="flyer_")
  else: 
    flyer = target
  return flyer, target
  
